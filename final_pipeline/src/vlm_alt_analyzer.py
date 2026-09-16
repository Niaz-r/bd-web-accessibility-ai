# ============================================================
# VLM ALT ANALYZER V3
# AI-Assisted Web Accessibility Project
#
# Supported findings:
#   - missing_alt
#   - empty_alt
#   - non_descriptive_alt
#
# Architecture:
#   Image finding
#       ↓
#   Download actual image
#       ↓
#   Qwen2.5-VL through Ollama
#       ↓
#   Visual interpretation
#       ↓
#   Deterministic accessibility guardrails
#       ↓
#   Safe recommendation
#       ↓
#   Human verification
#
# IMPORTANT:
# The VLM does not make the final accessibility decision.
# Deterministic rules validate/correct the VLM output.
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import hashlib
import json
import mimetypes
import re
import sys
import time

from io import BytesIO
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse

import ollama
import pandas as pd
import requests

from PIL import Image
from pydantic import BaseModel, ValidationError


# ============================================================
# PROJECT PATHS
# ============================================================

SRC_DIR = Path(__file__).resolve().parent

FINAL_PIPELINE_DIR = SRC_DIR.parent


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

CACHE_DIR = (
    FINAL_PIPELINE_DIR
    / "data"
    / "intermediate"
    / "vlm_cache"
)

IMAGE_DIR = (
    FINAL_PIPELINE_DIR
    / "data"
    / "intermediate"
    / "vlm_images"
)

OUTPUT_DIR = (
    FINAL_PIPELINE_DIR
    / "data"
    / "final"
    / "vlm_alt_reviews"
)


for directory in [
    CACHE_DIR,
    IMAGE_DIR,
    OUTPUT_DIR,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_MODEL = "qwen2.5vl:3b"

OLLAMA_HOST = "http://localhost:11434"

REQUEST_TIMEOUT = 30

MAX_IMAGE_BYTES = (
    15
    * 1024
    * 1024
)


# ============================================================
# CACHE VERSION
#
# V3 fixes generic_alt_detected so that deterministic
# detection has full authority.
#
# Old V1/V2 cache entries will not be reused.
# ============================================================

CACHE_VERSION = "vlm_alt_v3_generic_fix"


# ============================================================
# SUPPORTED IMAGE FORMATS
# ============================================================

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
}


# ============================================================
# GENERIC ALT TERMS
# ============================================================

GENERIC_ALT_TERMS = {
    "image",
    "img",
    "photo",
    "picture",
    "graphic",
    "icon",
    "thumbnail",
    "thumb",
    "news image",
    "event image",
    "banner",
    "banner image",
    "slider",
    "slider image",
    "post image",
    "featured image",
    "default image",
    "image here",
    "photo here",
    "picture here",
}


# ============================================================
# ELIGIBLE ACCESSIBILITY ISSUES
# ============================================================

ELIGIBLE_ISSUES = {
    "missing_alt",
    "empty_alt",
    "non_descriptive_alt",
}


# ============================================================
# STRUCTURED VLM OUTPUT
# ============================================================

class VlmAltDecision(BaseModel):

    image_role: Literal[
        "decorative",
        "informative",
        "functional",
        "complex",
        "unclear",
    ]

    alt_status: Literal[
        "keep_empty",
        "set_empty_alt",
        "replace_with_empty_alt",
        "needs_meaningful_alt",
        "improve_existing_alt",
        "needs_long_description",
        "manual_review",
    ]

    generic_alt_detected: bool

    suggested_alt: str

    recommended_action: str

    confidence: Literal[
        "low",
        "medium",
        "high",
    ]

    manual_review_required: bool

    visual_review_required: bool

    reason: str


# ============================================================
# PRINT HELPERS
# ============================================================

def divider():

    print()

    print(
        "=" * 80
    )


def heading(title):

    divider()

    print(
        title
    )

    divider()


# ============================================================
# STRING HELPERS
# ============================================================

def clean_text(value):

    if value is None:

        return ""

    try:

        if pd.isna(value):

            return ""

    except Exception:

        pass

    return str(
        value
    ).strip()


def normalize_spaces(text):

    return re.sub(
        r"\s+",
        " ",
        clean_text(text)
    ).strip()


def filename_safe(text):

    text = normalize_spaces(
        text
    )

    text = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        text
    )

    text = re.sub(
        r"_+",
        "_",
        text
    ).strip("_")

    return (
        text
        or
        "file"
    )


# ============================================================
# HASH HELPERS
# ============================================================

def sha256_bytes(data):

    return hashlib.sha256(
        data
    ).hexdigest()


def sha256_file(path):

    with open(
        path,
        "rb"
    ) as file:

        return sha256_bytes(
            file.read()
        )


# ============================================================
# GENERIC ALT DETECTION
# ============================================================

def is_generic_alt_text(alt_text):

    alt = (
        normalize_spaces(
            alt_text
        )
        .lower()
    )

    if not alt:

        return False


    # --------------------------------------------------------
    # Exact generic values
    # --------------------------------------------------------

    if alt in GENERIC_ALT_TERMS:

        return True


    # --------------------------------------------------------
    # Short generic patterns
    #
    # Examples:
    #   product image
    #   news photo
    # --------------------------------------------------------

    generic_suffixes = [
        " image",
        " photo",
        " picture",
        " thumbnail",
        " thumb",
    ]

    for suffix in generic_suffixes:

        if (
            alt.endswith(
                suffix
            )
            and
            len(
                alt.split()
            )
            <= 3
        ):

            return True


    # --------------------------------------------------------
    # Filename-like alternative text
    #
    # Examples:
    #   image123.jpg
    #   banner.png
    # --------------------------------------------------------

    if re.fullmatch(
        r".+\.(jpg|jpeg|png|gif|webp|bmp)",
        alt,
        flags=re.IGNORECASE
    ):

        return True


    # --------------------------------------------------------
    # Camera/system generated names
    #
    # Examples:
    #   IMG1234
    #   IMG_1234
    #   DSC0012
    # --------------------------------------------------------

    if re.fullmatch(
        r"(img|dsc|photo)[-_]?\d+",
        alt,
        flags=re.IGNORECASE
    ):

        return True


    return False


# ============================================================
# IMAGE URL RESOLUTION
# ============================================================

def resolve_image_url(
    src,
    page_url=""
):

    src = clean_text(
        src
    )

    page_url = clean_text(
        page_url
    )

    if not src:

        return ""


    parsed = urlparse(
        src
    )


    # --------------------------------------------------------
    # Absolute HTTP/HTTPS URL
    # --------------------------------------------------------

    if parsed.scheme in {
        "http",
        "https",
    }:

        return src


    # --------------------------------------------------------
    # Protocol-relative
    #
    # //example.com/image.jpg
    # --------------------------------------------------------

    if src.startswith(
        "//"
    ):

        return (
            "https:"
            +
            src
        )


    # --------------------------------------------------------
    # Relative image URL
    # --------------------------------------------------------

    if page_url:

        return urljoin(
            page_url,
            src
        )


    return src


# ============================================================
# IMAGE EXTENSION
# ============================================================

def infer_extension_from_response(
    response,
    url
):

    content_type = (
        clean_text(
            response.headers.get(
                "Content-Type"
            )
        )
        .lower()
    )


    if "image/" in content_type:

        mime = (
            content_type
            .split(";")[0]
            .strip()
        )

        extension = mimetypes.guess_extension(
            mime
        )

        if extension:

            if extension == ".jpe":

                return ".jpg"

            return extension


    parsed = urlparse(
        url
    )

    suffix = (
        Path(
            parsed.path
        )
        .suffix
        .lower()
    )


    if suffix:

        return suffix


    return ".img"


def is_supported_image_extension(
    extension
):

    return (
        extension.lower()
        in
        SUPPORTED_IMAGE_EXTENSIONS
    )


# ============================================================
# NORMALIZE DOWNLOADED IMAGE
# ============================================================

def normalize_downloaded_image(
    content,
    image_hash
):

    """
    Decode and convert image into PNG for reliable
    VLM processing.

    Animated images use the first frame.
    """

    try:

        with Image.open(
            BytesIO(
                content
            )
        ) as image:


            # ------------------------------------------------
            # Use first frame if animated
            # ------------------------------------------------

            try:

                image.seek(
                    0
                )

            except Exception:

                pass


            # ------------------------------------------------
            # Normalize color mode
            # ------------------------------------------------

            if image.mode in {
                "RGBA",
                "LA",
            }:

                converted = image.convert(
                    "RGBA"
                )

            else:

                converted = image.convert(
                    "RGB"
                )


            output_path = (
                IMAGE_DIR
                /
                f"{image_hash}.png"
            )


            if not output_path.exists():

                converted.save(
                    output_path,
                    format="PNG"
                )


            return output_path


    except Exception as error:

        raise ValueError(
            (
                "Downloaded content could not "
                "be decoded as an image: "
                f"{error}"
            )
        )


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

def download_image(
    src,
    page_url=""
):

    resolved_url = resolve_image_url(
        src,
        page_url
    )


    if not resolved_url:

        return {
            "ok": False,
            "error": "Empty image URL.",
            "resolved_url": "",
            "local_path": None,
            "sha256": "",
        }


    parsed = urlparse(
        resolved_url
    )


    # --------------------------------------------------------
    # Only HTTP/HTTPS
    # --------------------------------------------------------

    if parsed.scheme not in {
        "http",
        "https",
    }:

        return {
            "ok": False,
            "error": (
                "Unsupported image URL scheme: "
                f"{parsed.scheme or '[NONE]'}"
            ),
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": "",
        }


    # --------------------------------------------------------
    # Request image
    # --------------------------------------------------------

    try:

        response = requests.get(

            resolved_url,

            timeout=REQUEST_TIMEOUT,

            allow_redirects=True,

            headers={
                "User-Agent":
                    (
                        "Mozilla/5.0 "
                        "(X11; Linux x86_64) "
                        "AppleWebKit/537.36 "
                        "Chrome/145 Safari/537.36"
                    ),

                "Accept":
                    (
                        "image/avif,"
                        "image/webp,"
                        "image/apng,"
                        "image/svg+xml,"
                        "image/*,"
                        "*/*;q=0.8"
                    ),
            }
        )


    except Exception as error:

        return {
            "ok": False,
            "error": (
                "Image request failed: "
                f"{error}"
            ),
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": "",
        }


    # --------------------------------------------------------
    # HTTP status
    # --------------------------------------------------------

    if response.status_code != 200:

        return {
            "ok": False,
            "error": (
                "Image request returned "
                f"HTTP {response.status_code}"
            ),
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": "",
        }


    # --------------------------------------------------------
    # Content-Length size protection
    # --------------------------------------------------------

    content_length = clean_text(
        response.headers.get(
            "Content-Length"
        )
    )


    if content_length:

        try:

            if int(
                content_length
            ) > MAX_IMAGE_BYTES:

                return {
                    "ok": False,
                    "error": (
                        "Image exceeds maximum allowed "
                        f"size of {MAX_IMAGE_BYTES} bytes."
                    ),
                    "resolved_url": resolved_url,
                    "local_path": None,
                    "sha256": "",
                }

        except ValueError:

            pass


    content = response.content


    if not content:

        return {
            "ok": False,
            "error": "Downloaded image is empty.",
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": "",
        }


    # --------------------------------------------------------
    # Actual downloaded size protection
    # --------------------------------------------------------

    if len(
        content
    ) > MAX_IMAGE_BYTES:

        return {
            "ok": False,
            "error": (
                "Downloaded image exceeds "
                "maximum allowed size."
            ),
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": "",
        }


    extension = infer_extension_from_response(
        response,
        resolved_url
    )


    if not is_supported_image_extension(
        extension
    ):

        return {
            "ok": False,
            "error": (
                "Unsupported image format: "
                f"{extension}"
            ),
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": "",
        }


    image_hash = sha256_bytes(
        content
    )


    try:

        local_path = normalize_downloaded_image(
            content,
            image_hash
        )


    except Exception as error:

        return {
            "ok": False,
            "error": str(
                error
            ),
            "resolved_url": resolved_url,
            "local_path": None,
            "sha256": image_hash,
        }


    return {
        "ok": True,
        "error": "",
        "resolved_url": resolved_url,
        "local_path": local_path,
        "sha256": image_hash,
    }


# ============================================================
# CACHE
# ============================================================

def build_cache_key(
    image_sha,
    issue,
    current_alt
):

    key_text = "||".join(
        [
            CACHE_VERSION,

            clean_text(
                image_sha
            ),

            clean_text(
                issue
            ).lower(),

            normalize_spaces(
                current_alt
            ).lower(),
        ]
    )


    return hashlib.sha256(
        key_text.encode(
            "utf-8"
        )
    ).hexdigest()


def load_cache(
    cache_key
):

    path = (
        CACHE_DIR
        /
        f"{cache_key}.json"
    )


    if not path.exists():

        return None


    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )


        # ----------------------------------------------------
        # Validate cache structure
        # ----------------------------------------------------

        validated = (
            VlmAltDecision(
                **data
            )
            .model_dump()
        )


        return validated


    except Exception:

        return None


def save_cache(
    cache_key,
    payload
):

    path = (
        CACHE_DIR
        /
        f"{cache_key}.json"
    )


    path.write_text(

        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),

        encoding="utf-8"
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json_object(
    text
):

    if not text:

        raise ValueError(
            "Model response is empty."
        )


    text = text.strip()


    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:

        pass


    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    text = re.sub(
        r"^```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    )


    text = re.sub(
        r"```$",
        "",
        text
    )


    text = text.strip()


    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:

        pass


    # --------------------------------------------------------
    # Extract first JSON object
    # --------------------------------------------------------

    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL
    )


    if not match:

        raise ValueError(
            "Could not find JSON object in VLM response."
        )


    return json.loads(
        match.group(
            0
        )
    )


# ============================================================
# VLM PROMPT
# ============================================================

def build_prompt(
    row,
    pre_generic_flag
):

    page_url = clean_text(
        row.get(
            "page_url",
            ""
        )
    )


    issue = clean_text(
        row.get(
            "issue",
            ""
        )
    )


    current_alt = clean_text(
        row.get(
            "alt",
            ""
        )
    )


    selector = clean_text(
        row.get(
            "selector",
            ""
        )
    )


    nearby_heading = clean_text(
        row.get(
            "nearby_heading",
            ""
        )
    )


    surrounding_context = clean_text(
        row.get(
            "surrounding_context",
            ""
        )
    )


    # --------------------------------------------------------
    # Some versions use "context"
    # --------------------------------------------------------

    if not surrounding_context:

        surrounding_context = clean_text(
            row.get(
                "context",
                ""
            )
        )


    href = clean_text(
        row.get(
            "href",
            ""
        )
    )


    prompt = f"""
You are the visual-analysis component of a web accessibility
recommendation system.

Analyze the attached webpage image together with the supplied
page context.

Your job is to understand the likely PURPOSE of the image.

You are NOT the final accessibility decision maker.
A deterministic accessibility rules engine will validate your
output after you respond.

Return ONLY JSON matching the required schema.


IMAGE ROLE DEFINITIONS

decorative:
The image is purely decorative, redundant, ornamental, or adds
no meaningful information.

informative:
The image communicates meaningful visual content that users
would lose if the image were unavailable.

functional:
The image is used as a link, button, control, navigation item,
linked logo, or another functional interface element.
Alternative text should normally describe its function or
destination.

complex:
The image is a chart, graph, diagram, infographic, map,
text-heavy visual, or similar complex information source.

unclear:
There is not enough reliable visual/contextual evidence to
classify the image confidently.


ALT STATUS VALUES

keep_empty
set_empty_alt
replace_with_empty_alt
needs_meaningful_alt
improve_existing_alt
needs_long_description
manual_review


IMPORTANT CONSISTENCY RULES

1. Informative images MUST NOT use keep_empty.

2. Functional images MUST NOT use keep_empty.

3. Complex images MUST NOT use keep_empty.

4. Decorative images must return an empty suggested_alt.

5. If an informative or functional image cannot be described
   confidently, classify it as unclear instead of inventing
   visual details.

6. For complex images, suggested_alt should only identify the
   visual briefly. Important detailed information requires an
   accessible text equivalent or longer description.

7. Never hallucinate:
   - people's identities,
   - institution names,
   - event names,
   - locations,
   - dates,
   - relationships,
   unless clearly supported by visible evidence or supplied
   textual context.

8. If the current alternative text is generic, such as
   image, photo, picture, thumb, thumbnail, banner,
   news image, or event image, generic_alt_detected may be
   true.

9. For empty_alt, do NOT automatically assume empty alt is
   incorrect. Decorative images may correctly use alt="".

10. Keep suggested alternative text concise.

11. Human verification is required before applying an
    AI-generated alt-text recommendation.


PAGE METADATA

Page URL:
{page_url if page_url else "[UNKNOWN]"}

Detected accessibility issue:
{issue}

Current alt text:
{current_alt if current_alt else "[EMPTY]"}

Deterministic generic-alt flag:
{str(bool(pre_generic_flag)).lower()}

CSS selector:
{selector if selector else "[NONE]"}

Link target:
{href if href else "[NONE]"}

Nearby heading:
{nearby_heading if nearby_heading else "[NONE]"}

Surrounding textual context:
{surrounding_context if surrounding_context else "[NONE]"}


RETURN JSON WITH THESE FIELDS

{{
  "image_role": "decorative|informative|functional|complex|unclear",
  "alt_status": "keep_empty|set_empty_alt|replace_with_empty_alt|needs_meaningful_alt|improve_existing_alt|needs_long_description|manual_review",
  "generic_alt_detected": true,
  "suggested_alt": "",
  "recommended_action": "",
  "confidence": "low|medium|high",
  "manual_review_required": true,
  "visual_review_required": true,
  "reason": ""
}}
""".strip()


    return prompt


# ============================================================
# DETERMINISTIC ACCESSIBILITY GUARDRAILS
# ============================================================

def apply_accessibility_guardrails(
    decision,
    issue,
    current_alt,
    pre_generic_flag
):

    decision = dict(
        decision
    )


    issue = (
        clean_text(
            issue
        )
        .lower()
    )


    current_alt = normalize_spaces(
        current_alt
    )


    role = (
        clean_text(
            decision.get(
                "image_role",
                "unclear"
            )
        )
        .lower()
    )


    suggested_alt = normalize_spaces(
        decision.get(
            "suggested_alt",
            ""
        )
    )


    # ========================================================
    # GENERIC ALT DETECTION — V3 FIX
    #
    # IMPORTANT:
    # Deterministic detector has FULL authority.
    #
    # The VLM is not allowed to determine whether an existing
    # alt value is syntactically generic.
    #
    # Therefore:
    #
    #   alt="Thumb"  → True
    #   alt="image"  → True
    #   alt=""       → False
    #   missing alt  → False
    #
    # ========================================================

    decision[
        "generic_alt_detected"
    ] = bool(
        pre_generic_flag
    )


    # ========================================================
    # HUMAN REVIEW ALWAYS REQUIRED
    # ========================================================

    decision[
        "manual_review_required"
    ] = True


    decision[
        "visual_review_required"
    ] = True


    # ========================================================
    # DECORATIVE IMAGE
    # ========================================================

    if role == "decorative":


        decision[
            "suggested_alt"
        ] = ""


        # ----------------------------------------------------
        # Missing alt attribute
        # ----------------------------------------------------

        if issue == "missing_alt":


            decision[
                "alt_status"
            ] = "set_empty_alt"


            decision[
                "recommended_action"
            ] = (
                "The image appears decorative. "
                "After human verification, add an explicit "
                'empty alternative text attribute: alt="".'
            )


        # ----------------------------------------------------
        # Existing empty alt
        # ----------------------------------------------------

        elif current_alt == "":


            decision[
                "alt_status"
            ] = "keep_empty"


            decision[
                "recommended_action"
            ] = (
                "The image appears decorative. "
                'Keep alt="" after human verification.'
            )


        # ----------------------------------------------------
        # Existing generic/unnecessary alt
        # ----------------------------------------------------

        else:


            decision[
                "alt_status"
            ] = "replace_with_empty_alt"


            decision[
                "recommended_action"
            ] = (
                "The image appears decorative. "
                "After human verification, remove the "
                "unnecessary textual alternative by using "
                'alt="".'
            )


        return decision


    # ========================================================
    # INFORMATIVE IMAGE
    # ========================================================

    if role == "informative":


        # ----------------------------------------------------
        # Informative image with no grounded suggestion
        # becomes unclear.
        # ----------------------------------------------------

        if not suggested_alt:


            decision[
                "image_role"
            ] = "unclear"


            decision[
                "alt_status"
            ] = "manual_review"


            decision[
                "confidence"
            ] = "low"


            decision[
                "suggested_alt"
            ] = ""


            decision[
                "recommended_action"
            ] = (
                "The image appears potentially informative, "
                "but the VLM did not produce sufficiently "
                "grounded alternative text. Inspect the image "
                "and its page context manually before writing "
                "alt text."
            )


            decision[
                "reason"
            ] = (
                "Guardrail changed the informative-image "
                "decision to unclear because no grounded "
                "alternative text was available."
            )


            return decision


        decision[
            "suggested_alt"
        ] = suggested_alt


        if issue in {
            "missing_alt",
            "empty_alt",
        }:


            decision[
                "alt_status"
            ] = "needs_meaningful_alt"


            decision[
                "recommended_action"
            ] = (
                "The image appears informative. Add concise "
                "alternative text describing the information "
                "or purpose communicated by the image. Review "
                "the VLM suggestion before use."
            )


        else:


            decision[
                "alt_status"
            ] = "improve_existing_alt"


            decision[
                "recommended_action"
            ] = (
                "The image appears informative and the current "
                "alt text is inadequate or generic. Replace it "
                "with concise alternative text reflecting the "
                "meaning or purpose of the image. Review the "
                "VLM suggestion before use."
            )


        return decision


    # ========================================================
    # FUNCTIONAL IMAGE
    # ========================================================

    if role == "functional":


        if not suggested_alt:


            decision[
                "image_role"
            ] = "unclear"


            decision[
                "alt_status"
            ] = "manual_review"


            decision[
                "confidence"
            ] = "low"


            decision[
                "suggested_alt"
            ] = ""


            decision[
                "recommended_action"
            ] = (
                "The image appears to have a functional role, "
                "but its accessible purpose could not be "
                "determined reliably. Inspect the surrounding "
                "link or control context manually."
            )


            decision[
                "reason"
            ] = (
                "Guardrail changed the functional-image "
                "decision to unclear because no grounded "
                "functional alternative was available."
            )


            return decision


        decision[
            "suggested_alt"
        ] = suggested_alt


        if issue in {
            "missing_alt",
            "empty_alt",
        }:


            decision[
                "alt_status"
            ] = "needs_meaningful_alt"


        else:


            decision[
                "alt_status"
            ] = "improve_existing_alt"


        decision[
            "recommended_action"
        ] = (
            "The image appears functional. Provide concise "
            "alternative text describing its function or "
            "destination rather than only its visual "
            "appearance. Verify the suggested text against "
            "the actual link or control purpose."
        )


        return decision


    # ========================================================
    # COMPLEX IMAGE
    # ========================================================

    if role == "complex":


        decision[
            "alt_status"
        ] = "needs_long_description"


        decision[
            "suggested_alt"
        ] = suggested_alt


        decision[
            "recommended_action"
        ] = (
            "This appears to be a complex visual such as a "
            "chart, diagram, infographic, map, or text-heavy "
            "image. Provide concise alt text identifying its "
            "purpose and make the important information "
            "available through nearby accessible text, a data "
            "table, or another suitable longer description."
        )


        return decision


    # ========================================================
    # UNCLEAR IMAGE
    # ========================================================

    decision[
        "image_role"
    ] = "unclear"


    decision[
        "alt_status"
    ] = "manual_review"


    decision[
        "confidence"
    ] = "low"


    decision[
        "suggested_alt"
    ] = ""


    decision[
        "recommended_action"
    ] = (
        "The image purpose could not be determined reliably "
        "from the visual and contextual evidence. Inspect the "
        "image and surrounding page content manually before "
        "deciding whether it needs meaningful alt text or an "
        "empty alt attribute."
    )


    return decision


# ============================================================
# CALL OLLAMA VLM
# ============================================================

def call_vlm(
    client,
    model,
    image_path,
    row,
    pre_generic_flag
):


    prompt = build_prompt(
        row,
        pre_generic_flag
    )


    response = client.chat(

        model=model,

        messages=[
            {
                "role": "user",

                "content": prompt,

                "images": [
                    str(
                        image_path
                    )
                ],
            }
        ],

        format=(
            VlmAltDecision
            .model_json_schema()
        ),

        options={
            "temperature": 0
        }
    )


    # --------------------------------------------------------
    # Ollama response compatibility
    # --------------------------------------------------------

    try:

        content = (
            response[
                "message"
            ][
                "content"
            ]
        )

    except Exception:

        content = (
            response
            .message
            .content
        )


    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    parsed = extract_json_object(
        content
    )


    # --------------------------------------------------------
    # First validation
    # --------------------------------------------------------

    decision = (
        VlmAltDecision(
            **parsed
        )
        .model_dump()
    )


    # --------------------------------------------------------
    # Deterministic guardrails
    # --------------------------------------------------------

    decision = apply_accessibility_guardrails(

        decision=decision,

        issue=row.get(
            "issue",
            ""
        ),

        current_alt=row.get(
            "alt",
            ""
        ),

        pre_generic_flag=(
            pre_generic_flag
        )
    )


    # --------------------------------------------------------
    # Validate again after guardrails
    # --------------------------------------------------------

    decision = (
        VlmAltDecision(
            **decision
        )
        .model_dump()
    )


    return decision


# ============================================================
# SAFE DETERMINISTIC FALLBACK
# ============================================================

def fallback_decision(
    issue,
    current_alt,
    error_message,
    pre_generic_flag
):


    issue = (
        clean_text(
            issue
        )
        .lower()
    )


    current_alt = clean_text(
        current_alt
    )


    # ========================================================
    # EMPTY ALT
    # ========================================================

    if issue == "empty_alt":


        alt_status = "manual_review"


        recommended_action = (
            "Review whether this image is decorative, "
            "informative, functional, or complex. If it is "
            "decorative, alt=\"\" may be appropriate. If it "
            "communicates information or performs a function, "
            "provide suitable alternative text."
        )


    # ========================================================
    # MISSING ALT
    # ========================================================

    elif issue == "missing_alt":


        alt_status = "manual_review"


        recommended_action = (
            "Inspect the image and its purpose manually. Add "
            'alt="" if the image is purely decorative, or add '
            "concise meaningful alternative text if it is "
            "informative or functional."
        )


    # ========================================================
    # NON-DESCRIPTIVE ALT
    # ========================================================

    elif issue == "non_descriptive_alt":


        alt_status = "improve_existing_alt"


        recommended_action = (
            "The current alt text appears generic or "
            "non-descriptive. Inspect the image manually and "
            "replace the current value with concise text that "
            "communicates the image purpose."
        )


    # ========================================================
    # UNKNOWN
    # ========================================================

    else:


        alt_status = "manual_review"


        recommended_action = (
            "Review the image manually and determine the "
            "appropriate alternative-text treatment."
        )


    return {
        "image_role":
            "unclear",

        "alt_status":
            alt_status,

        # ----------------------------------------------------
        # Deterministic generic detector only.
        # ----------------------------------------------------

        "generic_alt_detected":
            bool(
                pre_generic_flag
            ),

        "suggested_alt":
            "",

        "recommended_action":
            recommended_action,

        "confidence":
            "low",

        "manual_review_required":
            True,

        "visual_review_required":
            True,

        "reason":
            (
                "Deterministic fallback used because VLM "
                "analysis was unavailable or invalid. "
                f"Technical detail: {error_message}"
            ),
    }


# ============================================================
# CONTRADICTION DETECTION
# ============================================================

def has_logical_contradiction(
    decision
):


    role = clean_text(
        decision.get(
            "image_role",
            ""
        )
    )


    status = clean_text(
        decision.get(
            "alt_status",
            ""
        )
    )


    suggested_alt = normalize_spaces(
        decision.get(
            "suggested_alt",
            ""
        )
    )


    # --------------------------------------------------------
    # Meaningful images must not receive empty-alt actions.
    # --------------------------------------------------------

    if (
        role
        in {
            "informative",
            "functional",
            "complex",
        }

        and

        status
        in {
            "keep_empty",
            "set_empty_alt",
            "replace_with_empty_alt",
        }
    ):

        return True


    # --------------------------------------------------------
    # Decorative images should not receive generated alt text.
    # --------------------------------------------------------

    if (
        role == "decorative"
        and
        suggested_alt
    ):

        return True


    return False


# ============================================================
# ANALYZE INPUT CSV
# ============================================================

def analyze_file(
    input_csv,
    model=DEFAULT_MODEL
):


    input_csv = Path(
        input_csv
    )


    if not input_csv.exists():

        raise FileNotFoundError(
            f"Input file not found: {input_csv}"
        )


    # ========================================================
    # LOAD DATA
    # ========================================================

    df = pd.read_csv(
        input_csv
    )


    heading(
        "VLM ALT ANALYZER V3"
    )


    print(
        f"Input file: {input_csv}"
    )


    print(
        f"Rows in input: {len(df)}"
    )


    print(
        f"Model: {model}"
    )


    print(
        f"Cache version: {CACHE_VERSION}"
    )


    # ========================================================
    # REQUIRED COLUMNS
    # ========================================================

    required_columns = [
        "issue",
        "src",
    ]


    missing_required = [
        column
        for column
        in required_columns
        if column not in df.columns
    ]


    if missing_required:

        raise ValueError(
            (
                "Input CSV is missing required columns: "
                +
                ", ".join(
                    missing_required
                )
            )
        )


    # ========================================================
    # OPTIONAL COLUMNS
    # ========================================================

    optional_columns = {
        "alt": "",
        "page_url": "",
        "selector": "",
        "nearby_heading": "",
        "surrounding_context": "",
        "context": "",
        "href": "",
    }


    for (
        column,
        default_value
    ) in optional_columns.items():


        if column not in df.columns:

            df[
                column
            ] = default_value


    # ========================================================
    # FILTER ELIGIBLE IMAGE FINDINGS
    # ========================================================

    issue_series = (
        df[
            "issue"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )


    src_series = (
        df[
            "src"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    image_df = df[
        issue_series.isin(
            ELIGIBLE_ISSUES
        )
        &
        src_series.ne("")
    ].copy()


    print(
        (
            "Eligible image findings: "
            f"{len(image_df)}"
        )
    )


    if image_df.empty:


        print()

        print(
            "No eligible image findings were found."
        )


        print(
            (
                "Expected issue values: "
                "missing_alt, empty_alt, "
                "non_descriptive_alt"
            )
        )


        return None


    # ========================================================
    # OLLAMA CLIENT
    # ========================================================

    client = ollama.Client(
        host=OLLAMA_HOST
    )


    # ========================================================
    # COUNTERS
    # ========================================================

    results = []

    cache_hits = 0

    vlm_success = 0

    fallback_used = 0

    download_failed = 0

    contradiction_count = 0


    total_findings = len(
        image_df
    )


    # ========================================================
    # PROCESS EACH FINDING
    # ========================================================

    for (
        position,
        (_, row)
    ) in enumerate(
        image_df.iterrows(),
        start=1
    ):


        issue = (
            clean_text(
                row.get(
                    "issue",
                    ""
                )
            )
            .lower()
        )


        src = clean_text(
            row.get(
                "src",
                ""
            )
        )


        page_url = clean_text(
            row.get(
                "page_url",
                ""
            )
        )


        current_alt = clean_text(
            row.get(
                "alt",
                ""
            )
        )


        pre_generic_flag = is_generic_alt_text(
            current_alt
        )


        print()

        print(
            "-" * 80
        )


        print(
            (
                f"[{position}/{total_findings}] "
                f"{issue}"
            )
        )


        print(
            f"src: {src}"
        )


        # ====================================================
        # DOWNLOAD IMAGE
        # ====================================================

        download_result = download_image(
            src=src,
            page_url=page_url
        )


        # ====================================================
        # DOWNLOAD FAILURE
        # ====================================================

        if not download_result[
            "ok"
        ]:


            print(
                (
                    "Download failed: "
                    f"{download_result['error']}"
                )
            )


            download_failed += 1


            decision = fallback_decision(

                issue=issue,

                current_alt=current_alt,

                error_message=(
                    download_result[
                        "error"
                    ]
                ),

                pre_generic_flag=(
                    pre_generic_flag
                )
            )


            merged = row.to_dict()


            merged.update(
                {
                    "vlm_status":
                        "download_failed",

                    "vlm_model":
                        model,

                    "cache_version":
                        CACHE_VERSION,

                    "cache_hit":
                        False,

                    "download_ok":
                        False,

                    "download_error":
                        download_result[
                            "error"
                        ],

                    "resolved_image_url":
                        download_result[
                            "resolved_url"
                        ],

                    "local_image_path":
                        "",

                    "image_sha256":
                        download_result.get(
                            "sha256",
                            ""
                        ),

                    "pre_generic_alt_flag":
                        pre_generic_flag,

                    "guardrail_passed":
                        True,

                    **decision,
                }
            )


            results.append(
                merged
            )


            continue


        # ====================================================
        # IMAGE DOWNLOAD SUCCESS
        # ====================================================

        image_path = download_result[
            "local_path"
        ]


        image_sha = download_result[
            "sha256"
        ]


        # ====================================================
        # CACHE KEY
        # ====================================================

        cache_key = build_cache_key(

            image_sha=image_sha,

            issue=issue,

            current_alt=current_alt
        )


        cached = load_cache(
            cache_key
        )


        # ====================================================
        # CACHE HIT
        # ====================================================

        if cached is not None:


            print(
                "Cache hit."
            )


            # ------------------------------------------------
            # Apply guardrails again for safety.
            # ------------------------------------------------

            cached = apply_accessibility_guardrails(

                decision=cached,

                issue=issue,

                current_alt=current_alt,

                pre_generic_flag=(
                    pre_generic_flag
                )
            )


            contradiction = has_logical_contradiction(
                cached
            )


            if contradiction:


                contradiction_count += 1


                cached = fallback_decision(

                    issue=issue,

                    current_alt=current_alt,

                    error_message=(
                        "Cached result failed logical "
                        "guardrail validation."
                    ),

                    pre_generic_flag=(
                        pre_generic_flag
                    )
                )


            cache_hits += 1


            merged = row.to_dict()


            merged.update(
                {
                    "vlm_status":
                        "cache",

                    "vlm_model":
                        model,

                    "cache_version":
                        CACHE_VERSION,

                    "cache_hit":
                        True,

                    "download_ok":
                        True,

                    "download_error":
                        "",

                    "resolved_image_url":
                        download_result[
                            "resolved_url"
                        ],

                    "local_image_path":
                        str(
                            image_path
                        ),

                    "image_sha256":
                        image_sha,

                    "pre_generic_alt_flag":
                        pre_generic_flag,

                    "guardrail_passed":
                        not contradiction,

                    **cached,
                }
            )


            results.append(
                merged
            )


            continue


        # ====================================================
        # VLM ANALYSIS
        # ====================================================

        try:


            decision = call_vlm(

                client=client,

                model=model,

                image_path=image_path,

                row=row,

                pre_generic_flag=(
                    pre_generic_flag
                )
            )


            # =================================================
            # FINAL CONTRADICTION CHECK
            # =================================================

            contradiction = has_logical_contradiction(
                decision
            )


            if contradiction:


                contradiction_count += 1


                decision = fallback_decision(

                    issue=issue,

                    current_alt=current_alt,

                    error_message=(
                        "VLM result remained logically "
                        "inconsistent after deterministic "
                        "guardrail processing."
                    ),

                    pre_generic_flag=(
                        pre_generic_flag
                    )
                )


                result_status = (
                    "guardrail_fallback"
                )


                fallback_used += 1


                print(
                    "Guardrail fallback used."
                )


            else:


                result_status = (
                    "success"
                )


                vlm_success += 1


                print(
                    "VLM analysis: success"
                )


                # --------------------------------------------
                # Cache only validated decisions.
                # --------------------------------------------

                save_cache(
                    cache_key,
                    decision
                )


            # =================================================
            # STORE RESULT
            # =================================================

            merged = row.to_dict()


            merged.update(
                {
                    "vlm_status":
                        result_status,

                    "vlm_model":
                        model,

                    "cache_version":
                        CACHE_VERSION,

                    "cache_hit":
                        False,

                    "download_ok":
                        True,

                    "download_error":
                        "",

                    "resolved_image_url":
                        download_result[
                            "resolved_url"
                        ],

                    "local_image_path":
                        str(
                            image_path
                        ),

                    "image_sha256":
                        image_sha,

                    "pre_generic_alt_flag":
                        pre_generic_flag,

                    "guardrail_passed":
                        not contradiction,

                    **decision,
                }
            )


            results.append(
                merged
            )


        # ====================================================
        # PYDANTIC VALIDATION FAILURE
        # ====================================================

        except ValidationError as error:


            print(
                (
                    "VLM validation failed: "
                    f"{error}"
                )
            )


            fallback_used += 1


            decision = fallback_decision(

                issue=issue,

                current_alt=current_alt,

                error_message=str(
                    error
                ),

                pre_generic_flag=(
                    pre_generic_flag
                )
            )


            merged = row.to_dict()


            merged.update(
                {
                    "vlm_status":
                        "validation_fallback",

                    "vlm_model":
                        model,

                    "cache_version":
                        CACHE_VERSION,

                    "cache_hit":
                        False,

                    "download_ok":
                        True,

                    "download_error":
                        "",

                    "resolved_image_url":
                        download_result[
                            "resolved_url"
                        ],

                    "local_image_path":
                        str(
                            image_path
                        ),

                    "image_sha256":
                        image_sha,

                    "pre_generic_alt_flag":
                        pre_generic_flag,

                    "guardrail_passed":
                        True,

                    **decision,
                }
            )


            results.append(
                merged
            )


        # ====================================================
        # OTHER VLM FAILURE
        # ====================================================

        except Exception as error:


            print(
                (
                    "VLM analysis failed: "
                    f"{error}"
                )
            )


            fallback_used += 1


            decision = fallback_decision(

                issue=issue,

                current_alt=current_alt,

                error_message=str(
                    error
                ),

                pre_generic_flag=(
                    pre_generic_flag
                )
            )


            merged = row.to_dict()


            merged.update(
                {
                    "vlm_status":
                        "fallback",

                    "vlm_model":
                        model,

                    "cache_version":
                        CACHE_VERSION,

                    "cache_hit":
                        False,

                    "download_ok":
                        True,

                    "download_error":
                        "",

                    "resolved_image_url":
                        download_result[
                            "resolved_url"
                        ],

                    "local_image_path":
                        str(
                            image_path
                        ),

                    "image_sha256":
                        image_sha,

                    "pre_generic_alt_flag":
                        pre_generic_flag,

                    "guardrail_passed":
                        True,

                    **decision,
                }
            )


            results.append(
                merged
            )


        # ====================================================
        # SMALL DELAY
        # ====================================================

        time.sleep(
            0.2
        )


    # ========================================================
    # RESULTS DATAFRAME
    # ========================================================

    result_df = pd.DataFrame(
        results
    )


    # ========================================================
    # FINAL LOGICAL SAFETY CHECK
    # ========================================================

    if not result_df.empty:


        contradiction_mask = (

            result_df[
                "image_role"
            ]
            .isin(
                [
                    "informative",
                    "functional",
                    "complex",
                ]
            )

            &

            result_df[
                "alt_status"
            ]
            .isin(
                [
                    "keep_empty",
                    "set_empty_alt",
                    "replace_with_empty_alt",
                ]
            )
        )


        remaining_contradictions = int(
            contradiction_mask.sum()
        )


    else:

        remaining_contradictions = 0


    # ========================================================
    # WRONG GENERIC-ALT FLAGS CHECK
    #
    # missing_alt / empty_alt should never be considered
    # generic alt text.
    # ========================================================

    if not result_df.empty:


        wrong_generic_mask = (

            result_df[
                "issue"
            ]
            .fillna("")
            .astype(str)
            .str.lower()
            .isin(
                [
                    "missing_alt",
                    "empty_alt",
                ]
            )

            &

            result_df[
                "generic_alt_detected"
            ]
            .eq(
                True
            )
        )


        wrong_generic_count = int(
            wrong_generic_mask.sum()
        )


    else:

        wrong_generic_count = 0


    # ========================================================
    # OUTPUT FILES
    # ========================================================

    input_stem = input_csv.stem


    output_csv = (
        OUTPUT_DIR
        /
        (
            f"{input_stem}"
            "__vlm_alt_reviews.csv"
        )
    )


    summary_csv = (
        OUTPUT_DIR
        /
        (
            f"{input_stem}"
            "__vlm_alt_summary.csv"
        )
    )


    # ========================================================
    # SAVE DETAILED OUTPUT
    # ========================================================

    result_df.to_csv(

        output_csv,

        index=False,

        encoding="utf-8-sig"
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    summary_rows = []


    def add_summary(
        metric,
        value
    ):

        summary_rows.append(
            {
                "metric":
                    metric,

                "value":
                    value,
            }
        )


    add_summary(
        "input_rows",
        len(df)
    )


    add_summary(
        "eligible_image_findings",
        len(image_df)
    )


    add_summary(
        "results_rows",
        len(result_df)
    )


    add_summary(
        "cache_hits",
        cache_hits
    )


    add_summary(
        "vlm_success",
        vlm_success
    )


    add_summary(
        "fallback_used",
        fallback_used
    )


    add_summary(
        "download_failed",
        download_failed
    )


    add_summary(
        "guardrail_interventions",
        contradiction_count
    )


    add_summary(
        "remaining_logical_contradictions",
        remaining_contradictions
    )


    add_summary(
        "wrong_generic_alt_flags",
        wrong_generic_count
    )


    # ========================================================
    # IMAGE ROLE COUNTS
    # ========================================================

    if (
        not result_df.empty
        and
        "image_role"
        in result_df.columns
    ):


        counts = (
            result_df[
                "image_role"
            ]
            .value_counts(
                dropna=False
            )
        )


        for (
            value,
            count
        ) in counts.items():


            add_summary(
                (
                    "image_role__"
                    f"{value}"
                ),
                int(
                    count
                )
            )


    # ========================================================
    # ALT STATUS COUNTS
    # ========================================================

    if (
        not result_df.empty
        and
        "alt_status"
        in result_df.columns
    ):


        counts = (
            result_df[
                "alt_status"
            ]
            .value_counts(
                dropna=False
            )
        )


        for (
            value,
            count
        ) in counts.items():


            add_summary(
                (
                    "alt_status__"
                    f"{value}"
                ),
                int(
                    count
                )
            )


    # ========================================================
    # VLM STATUS COUNTS
    # ========================================================

    if (
        not result_df.empty
        and
        "vlm_status"
        in result_df.columns
    ):


        counts = (
            result_df[
                "vlm_status"
            ]
            .value_counts(
                dropna=False
            )
        )


        for (
            value,
            count
        ) in counts.items():


            add_summary(
                (
                    "vlm_status__"
                    f"{value}"
                ),
                int(
                    count
                )
            )


    # ========================================================
    # CONFIDENCE COUNTS
    # ========================================================

    if (
        not result_df.empty
        and
        "confidence"
        in result_df.columns
    ):


        counts = (
            result_df[
                "confidence"
            ]
            .value_counts(
                dropna=False
            )
        )


        for (
            value,
            count
        ) in counts.items():


            add_summary(
                (
                    "confidence__"
                    f"{value}"
                ),
                int(
                    count
                )
            )


    # ========================================================
    # GENERIC ALT COUNT
    # ========================================================

    if (
        not result_df.empty
        and
        "generic_alt_detected"
        in result_df.columns
    ):


        generic_count = int(
            result_df[
                "generic_alt_detected"
            ]
            .fillna(
                False
            )
            .astype(
                bool
            )
            .sum()
        )


        add_summary(
            "generic_alt_detected",
            generic_count
        )


    # ========================================================
    # SAVE SUMMARY
    # ========================================================

    summary_df = pd.DataFrame(
        summary_rows
    )


    summary_df.to_csv(

        summary_csv,

        index=False,

        encoding="utf-8-sig"
    )


    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    heading(
        "VLM ALT ANALYZER V3 SUMMARY"
    )


    print(
        (
            "Processed rows: "
            f"{len(result_df)}"
        )
    )


    print(
        (
            "Cache hits: "
            f"{cache_hits}"
        )
    )


    print(
        (
            "VLM success: "
            f"{vlm_success}"
        )
    )


    print(
        (
            "Fallback used: "
            f"{fallback_used}"
        )
    )


    print(
        (
            "Download failed: "
            f"{download_failed}"
        )
    )


    print(
        (
            "Guardrail interventions: "
            f"{contradiction_count}"
        )
    )


    print(
        (
            "Remaining logical contradictions: "
            f"{remaining_contradictions}"
        )
    )


    print(
        (
            "Wrong generic-alt flags: "
            f"{wrong_generic_count}"
        )
    )


    # ========================================================
    # IMAGE ROLES
    # ========================================================

    if (
        not result_df.empty
        and
        "image_role"
        in result_df.columns
    ):


        print()

        print(
            "Image roles:"
        )


        print(
            result_df[
                "image_role"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )


    # ========================================================
    # ALT STATUS
    # ========================================================

    if (
        not result_df.empty
        and
        "alt_status"
        in result_df.columns
    ):


        print()

        print(
            "Alt status:"
        )


        print(
            result_df[
                "alt_status"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )


    # ========================================================
    # VLM STATUS
    # ========================================================

    if (
        not result_df.empty
        and
        "vlm_status"
        in result_df.columns
    ):


        print()

        print(
            "VLM status:"
        )


        print(
            result_df[
                "vlm_status"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )


    # ========================================================
    # CONFIDENCE
    # ========================================================

    if (
        not result_df.empty
        and
        "confidence"
        in result_df.columns
    ):


        print()

        print(
            "Confidence:"
        )


        print(
            result_df[
                "confidence"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )


    # ========================================================
    # FINAL SAFETY CHECK
    # ========================================================

    print()


    if (
        remaining_contradictions == 0
        and
        wrong_generic_count == 0
    ):


        print(
            "FINAL VLM SAFETY CHECK: PASS"
        )


        print(
            (
                "No meaningful-image/empty-alt "
                "contradictions remain."
            )
        )


        print(
            "No incorrect generic-alt flags remain."
        )


    else:


        print(
            "FINAL VLM SAFETY CHECK: FAIL"
        )


        print(
            (
                "Remaining logical contradictions: "
                f"{remaining_contradictions}"
            )
        )


        print(
            (
                "Wrong generic-alt flags: "
                f"{wrong_generic_count}"
            )
        )


    # ========================================================
    # FILES CREATED
    # ========================================================

    print()

    print(
        "Files created:"
    )


    print(
        output_csv
    )


    print(
        summary_csv
    )


    return output_csv


# ============================================================
# COMMAND-LINE ENTRY
# ============================================================

def main():


    if len(
        sys.argv
    ) < 2:


        print()

        print(
            "Usage:"
        )


        print(
            (
                "python "
                "final_pipeline/src/vlm_alt_analyzer.py "
                "<input_csv> [model]"
            )
        )


        print()

        print(
            "Example:"
        )


        print(
            (
                "python "
                "final_pipeline/src/vlm_alt_analyzer.py "
                "final_pipeline/data/intermediate/"
                "custom_live/"
                "www.du.ac.bd__custom_findings.csv"
            )
        )


        print()

        sys.exit(
            1
        )


    input_csv = sys.argv[
        1
    ]


    if len(
        sys.argv
    ) >= 3:


        model = sys.argv[
            2
        ]


    else:


        model = DEFAULT_MODEL


    analyze_file(
        input_csv,
        model=model
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
