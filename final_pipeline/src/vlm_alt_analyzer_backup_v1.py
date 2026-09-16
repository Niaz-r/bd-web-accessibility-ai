# final_pipeline/src/vlm_alt_analyzer.py

import hashlib
import json
import mimetypes
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import ollama
import pandas as pd
import requests
from pydantic import BaseModel, ValidationError


# ============================================================
# PATHS
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
FINAL_PIPELINE_DIR = SRC_DIR.parent

CACHE_DIR = FINAL_PIPELINE_DIR / "data" / "intermediate" / "vlm_cache"
IMAGE_DIR = FINAL_PIPELINE_DIR / "data" / "intermediate" / "vlm_images"
OUTPUT_DIR = FINAL_PIPELINE_DIR / "data" / "final" / "vlm_alt_reviews"

for directory in [CACHE_DIR, IMAGE_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIG
# ============================================================

DEFAULT_MODEL = "qwen2.5vl:3b"
OLLAMA_HOST = "http://localhost:11434"
REQUEST_TIMEOUT = 30

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
}

GENERIC_ALT_TERMS = {
    "image",
    "img",
    "photo",
    "picture",
    "graphic",
    "icon",
    "logo",
    "thumbnail",
    "thumb",
    "news image",
    "event image",
    "banner",
    "slider image",
    "post image",
    "featured image",
    "image here",
    "default image",
}


# ============================================================
# OUTPUT SCHEMA
# ============================================================

class VlmAltDecision(BaseModel):
    image_role: str
    alt_status: str
    generic_alt_detected: bool
    suggested_alt: str
    recommended_action: str
    confidence: str
    manual_review_required: bool
    visual_review_required: bool
    reason: str


# ============================================================
# PRINT HELPERS
# ============================================================

def divider():
    print()
    print("=" * 80)


def heading(title):
    divider()
    print(title)
    divider()


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_spaces(text):
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def filename_safe(text):
    text = normalize_spaces(text)
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "file"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def infer_extension_from_response(response, url):
    content_type = clean_text(response.headers.get("Content-Type")).lower()

    if "image/" in content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix:
        return suffix

    return ".img"


def is_supported_image_extension(ext):
    return ext.lower() in SUPPORTED_IMAGE_EXTENSIONS


def is_generic_alt_text(alt_text):
    alt = normalize_spaces(alt_text).lower()
    if not alt:
        return False

    if alt in GENERIC_ALT_TERMS:
        return True

    if alt.endswith(" image") and len(alt.split()) <= 3:
        return True

    if alt.endswith(" photo") and len(alt.split()) <= 3:
        return True

    if alt.endswith(" picture") and len(alt.split()) <= 3:
        return True

    return False


def extract_json_object(text):
    if not text:
        raise ValueError("Model response is empty.")

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Could not find JSON object in model response.")

    return json.loads(match.group(0))


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

def download_image(url):
    url = clean_text(url)

    if not url:
        return {
            "ok": False,
            "error": "Empty image URL.",
            "local_path": None,
            "sha256": "",
        }

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
    except Exception as error:
        return {
            "ok": False,
            "error": f"Request failed: {error}",
            "local_path": None,
            "sha256": "",
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "error": f"HTTP {response.status_code}",
            "local_path": None,
            "sha256": "",
        }

    ext = infer_extension_from_response(response, url)

    if not is_supported_image_extension(ext):
        return {
            "ok": False,
            "error": f"Unsupported image format: {ext}",
            "local_path": None,
            "sha256": "",
        }

    content = response.content

    if not content:
        return {
            "ok": False,
            "error": "Downloaded image is empty.",
            "local_path": None,
            "sha256": "",
        }

    image_hash = sha256_bytes(content)
    local_path = IMAGE_DIR / f"{image_hash}{ext.lower()}"

    if not local_path.exists():
        local_path.write_bytes(content)

    return {
        "ok": True,
        "error": "",
        "local_path": local_path,
        "sha256": image_hash,
    }


# ============================================================
# CACHE
# ============================================================

def build_cache_key(image_sha, issue, current_alt):
    key_text = "||".join([
        clean_text(image_sha),
        clean_text(issue).lower(),
        normalize_spaces(current_alt).lower(),
    ])
    return hashlib.sha256(key_text.encode("utf-8")).hexdigest()


def load_cache(cache_key):
    path = CACHE_DIR / f"{cache_key}.json"
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_cache(cache_key, payload):
    path = CACHE_DIR / f"{cache_key}.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ============================================================
# OLLAMA VLM CALL
# ============================================================

def build_prompt(row, pre_generic_flag):
    page_url = clean_text(row.get("page_url"))
    issue = clean_text(row.get("issue"))
    current_alt = clean_text(row.get("alt"))
    selector = clean_text(row.get("selector"))
    nearby_heading = clean_text(row.get("nearby_heading"))
    surrounding_context = clean_text(row.get("surrounding_context"))
    href = clean_text(row.get("href"))

    prompt = f"""
You are assisting a web accessibility audit.

Review the attached webpage image and decide what should happen with its alt text.

Return ONLY valid JSON.
Do not add markdown.
Do not add explanation outside the JSON.

Use exactly this schema:
{{
  "image_role": "decorative|informative|functional|complex|unclear",
  "alt_status": "keep_empty|needs_meaningful_alt|improve_existing_alt|manual_review",
  "generic_alt_detected": true,
  "suggested_alt": "",
  "recommended_action": "",
  "confidence": "low|medium|high",
  "manual_review_required": true,
  "visual_review_required": true,
  "reason": ""
}}

Decision guidance:
- decorative: purely decorative, redundant, or stylistic image. Empty alt is usually acceptable.
- informative: image adds content or meaning. It needs concise meaningful alt text.
- functional: image acts like a control, button, linked logo, or navigation target. Alt should describe the function or destination.
- complex: chart, infographic, table, text-heavy visual, or image needing short alt plus longer description.
- unclear: the image cannot be understood confidently.

Rules:
- If decorative, set "suggested_alt" to an empty string.
- If the current alt is generic like "image", "thumb", "thumbnail", "news image", or "event image", set "generic_alt_detected" to true.
- Avoid hallucinating details that are not visible.
- If unsure, set "manual_review_required" to true.
- If the issue is "empty_alt", do NOT automatically assume it is wrong; decorative images may validly use empty alt.
- Keep suggested_alt concise and practical.

Metadata:
- Page URL: {page_url}
- Detected issue: {issue}
- Current alt text: {current_alt if current_alt else "[EMPTY]"}
- Pre-detected generic-alt flag: {pre_generic_flag}
- CSS selector: {selector if selector else "[NONE]"}
- Link target href: {href if href else "[NONE]"}
- Nearby heading: {nearby_heading if nearby_heading else "[NONE]"}
- Surrounding context: {surrounding_context if surrounding_context else "[NONE]"}
""".strip()

    return prompt


def call_vlm(client, model, image_path, row, pre_generic_flag):
    prompt = build_prompt(row, pre_generic_flag)

    response = client.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [str(image_path)],
            }
        ],
        options={
            "temperature": 0
        }
    )

    try:
        content = response["message"]["content"]
    except Exception:
        content = response.message.content

    parsed = extract_json_object(content)
    decision = VlmAltDecision(**parsed)

    return decision.model_dump()


# ============================================================
# FALLBACK RESULT
# ============================================================

def fallback_decision(issue, current_alt, error_message, pre_generic_flag):
    current_alt = clean_text(current_alt)
    issue = clean_text(issue)

    if issue == "empty_alt":
        alt_status = "manual_review"
        recommended_action = (
            "Review whether this image is decorative or informative before deciding "
            "whether to keep empty alt or provide descriptive alt text."
        )
    elif issue == "missing_alt":
        alt_status = "manual_review"
        recommended_action = (
            "Review the image manually and add empty alt if decorative, or a concise "
            "meaningful alt if informative or functional."
        )
    elif issue == "non_descriptive_alt":
        alt_status = "improve_existing_alt"
        recommended_action = (
            "Replace the current generic alt text with concise, specific text that "
            "matches the image purpose."
        )
    else:
        alt_status = "manual_review"
        recommended_action = (
            "Review the image manually and decide the appropriate alt text treatment."
        )

    return {
        "image_role": "unclear",
        "alt_status": alt_status,
        "generic_alt_detected": bool(pre_generic_flag),
        "suggested_alt": "",
        "recommended_action": recommended_action,
        "confidence": "low",
        "manual_review_required": True,
        "visual_review_required": True,
        "reason": f"Fallback used because VLM analysis was unavailable: {error_message}",
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_file(input_csv, model=DEFAULT_MODEL):
    input_csv = Path(input_csv)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input file not found: {input_csv}")

    df = pd.read_csv(input_csv)

    heading("VLM ALT ANALYZER")

    print(f"Input file: {input_csv}")
    print(f"Rows in input: {len(df)}")
    print(f"Model: {model}")

    required_base_cols = ["issue", "src"]
    missing_required = [col for col in required_base_cols if col not in df.columns]
    if missing_required:
        raise ValueError(
            f"Input CSV is missing required columns: {', '.join(missing_required)}"
        )

    if "alt" not in df.columns:
        df["alt"] = ""

    eligible_issues = {
        "missing_alt",
        "empty_alt",
        "non_descriptive_alt",
    }

    image_df = df[
        df["issue"].astype(str).str.strip().isin(eligible_issues)
        &
        df["src"].astype(str).str.strip().ne("")
    ].copy()

    print(f"Eligible image findings: {len(image_df)}")

    if image_df.empty:
        print()
        print("No eligible image findings were found.")
        print("Expected issue values: missing_alt, empty_alt, non_descriptive_alt")
        return None

    client = ollama.Client(host=OLLAMA_HOST)

    results = []

    cache_hits = 0
    vlm_success = 0
    fallback_used = 0
    download_failed = 0

    for idx, (_, row) in enumerate(image_df.iterrows(), start=1):
        issue = clean_text(row.get("issue"))
        src = clean_text(row.get("src"))
        current_alt = clean_text(row.get("alt"))
        pre_generic_flag = is_generic_alt_text(current_alt)

        print()
        print("-" * 80)
        print(f"[{idx}/{len(image_df)}] {issue}")
        print(f"src: {src}")

        download_result = download_image(src)

        if not download_result["ok"]:
            print(f"Download failed: {download_result['error']}")
            download_failed += 1

            decision = fallback_decision(
                issue=issue,
                current_alt=current_alt,
                error_message=download_result["error"],
                pre_generic_flag=pre_generic_flag,
            )

            merged = row.to_dict()
            merged.update({
                "vlm_status": "download_failed",
                "cache_hit": False,
                "download_ok": False,
                "download_error": download_result["error"],
                "local_image_path": "",
                "image_sha256": "",
                "pre_generic_alt_flag": pre_generic_flag,
                **decision,
            })
            results.append(merged)
            continue

        image_path = download_result["local_path"]
        image_sha = download_result["sha256"]
        cache_key = build_cache_key(image_sha, issue, current_alt)
        cached = load_cache(cache_key)

        if cached is not None:
            print("Cache hit.")
            cache_hits += 1

            merged = row.to_dict()
            merged.update({
                "vlm_status": "cache",
                "cache_hit": True,
                "download_ok": True,
                "download_error": "",
                "local_image_path": str(image_path),
                "image_sha256": image_sha,
                "pre_generic_alt_flag": pre_generic_flag,
                **cached,
            })
            results.append(merged)
            continue

        try:
            decision = call_vlm(
                client=client,
                model=model,
                image_path=image_path,
                row=row,
                pre_generic_flag=pre_generic_flag,
            )
            save_cache(cache_key, decision)
            vlm_success += 1
            print("VLM analysis: success")

            merged = row.to_dict()
            merged.update({
                "vlm_status": "success",
                "cache_hit": False,
                "download_ok": True,
                "download_error": "",
                "local_image_path": str(image_path),
                "image_sha256": image_sha,
                "pre_generic_alt_flag": pre_generic_flag,
                **decision,
            })
            results.append(merged)

        except (ValidationError, ValueError, json.JSONDecodeError, Exception) as error:
            print(f"VLM analysis failed: {error}")
            fallback_used += 1

            decision = fallback_decision(
                issue=issue,
                current_alt=current_alt,
                error_message=str(error),
                pre_generic_flag=pre_generic_flag,
            )

            merged = row.to_dict()
            merged.update({
                "vlm_status": "fallback",
                "cache_hit": False,
                "download_ok": True,
                "download_error": "",
                "local_image_path": str(image_path),
                "image_sha256": image_sha,
                "pre_generic_alt_flag": pre_generic_flag,
                **decision,
            })
            results.append(merged)

        time.sleep(0.2)

    result_df = pd.DataFrame(results)

    stem = input_csv.stem
    output_csv = OUTPUT_DIR / f"{stem}__vlm_alt_reviews.csv"
    summary_csv = OUTPUT_DIR / f"{stem}__vlm_alt_summary.csv"

    result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    summary_rows = []

    summary_rows.append({
        "metric": "input_rows",
        "value": len(df),
    })
    summary_rows.append({
        "metric": "eligible_image_findings",
        "value": len(image_df),
    })
    summary_rows.append({
        "metric": "results_rows",
        "value": len(result_df),
    })
    summary_rows.append({
        "metric": "cache_hits",
        "value": cache_hits,
    })
    summary_rows.append({
        "metric": "vlm_success",
        "value": vlm_success,
    })
    summary_rows.append({
        "metric": "fallback_used",
        "value": fallback_used,
    })
    summary_rows.append({
        "metric": "download_failed",
        "value": download_failed,
    })

    if not result_df.empty:
        for value, count in result_df["image_role"].value_counts(dropna=False).items():
            summary_rows.append({
                "metric": f"image_role__{value}",
                "value": int(count),
            })

        for value, count in result_df["alt_status"].value_counts(dropna=False).items():
            summary_rows.append({
                "metric": f"alt_status__{value}",
                "value": int(count),
            })

        for value, count in result_df["vlm_status"].value_counts(dropna=False).items():
            summary_rows.append({
                "metric": f"vlm_status__{value}",
                "value": int(count),
            })

    pd.DataFrame(summary_rows).to_csv(summary_csv, index=False, encoding="utf-8-sig")

    heading("SUMMARY")
    print(f"Processed rows: {len(result_df)}")
    print(f"Cache hits: {cache_hits}")
    print(f"VLM success: {vlm_success}")
    print(f"Fallback used: {fallback_used}")
    print(f"Download failed: {download_failed}")

    if not result_df.empty:
        print()
        print("Image roles:")
        print(result_df["image_role"].value_counts(dropna=False).to_string())

        print()
        print("Alt status:")
        print(result_df["alt_status"].value_counts(dropna=False).to_string())

        print()
        print("VLM status:")
        print(result_df["vlm_status"].value_counts(dropna=False).to_string())

    print()
    print("Files created:")
    print(output_csv)
    print(summary_csv)

    return output_csv


# ============================================================
# ENTRY
# ============================================================

def main():
    if len(sys.argv) < 2:
        print()
        print("Usage:")
        print("python final_pipeline/src/vlm_alt_analyzer.py <input_csv> [model]")
        print()
        print("Example:")
        print(
            "python final_pipeline/src/vlm_alt_analyzer.py "
            "final_pipeline/data/intermediate/custom_live/www.du.ac.bd__custom_findings.csv"
        )
        print()
        sys.exit(1)

    input_csv = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_MODEL

    analyze_file(input_csv, model=model)


if __name__ == "__main__":
    main()
