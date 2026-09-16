#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

STATUS_CSV = Path(
    "final_pipeline/evaluation/five_site_validation/"
    "five_site_pipeline_status.csv"
)

OUT_DIR = Path(
    "final_pipeline/evaluation/five_site_validation/manual_validation"
)

ALL_CSV = OUT_DIR / "five_site_manual_validation_all.csv"
LINK_CSV = OUT_DIR / "five_site_link_v4_validation.csv"
ABSTAIN_CSV = OUT_DIR / "five_site_link_abstention_validation.csv"
VLM_CSV = OUT_DIR / "five_site_vlm_validation.csv"
GUIDE_TXT = OUT_DIR / "validation_guide.txt"


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def as_bool(value):
    if isinstance(value, bool):
        return value
    return clean(value).lower() in {"true", "1", "yes", "y"}


def first(row, names):
    for name in names:
        if name in row.index:
            value = clean(row.get(name, ""))
            if value:
                return value
    return ""


def link_rows(df):
    if "link_v4_processed" in df.columns:
        return df[df["link_v4_processed"].apply(as_bool)].copy()

    rules = {"empty_link_text", "link-name", "generic_link_text"}
    mask = pd.Series(False, index=df.index)
    for col in ["custom_issue", "axe_rule", "primary_rule", "rule"]:
        if col in df.columns:
            mask |= df[col].apply(clean).isin(rules)
    return df[mask].copy()


def vlm_rows(df):
    if "vlm_processed" in df.columns:
        return df[df["vlm_processed"].apply(as_bool)].copy()
    if "vlm_status" in df.columns:
        return df[df["vlm_status"].apply(clean).ne("")].copy()
    return df.iloc[0:0].copy()


def is_link_specific(row):
    return bool(
        first(row, [
            "link_v4_suggested_accessible_name",
            "link_v4_suggested_name",
            "link_suggested_accessible_name",
            "link_suggested_name",
        ])
        or
        first(row, [
            "link_v4_suggested_html",
            "link_suggested_html",
        ])
    )


def make_common(site, row):
    return {
        "site_id": site["site_id"],
        "website_name": site["website_name"],
        "category": site["category"],
        "language": site["language"],
        "page_url": first(row, ["page_url", "source_page_url", "requested_url"]),
        "unified_id": first(row, ["unified_id", "finding_id", "id"]),
        "issue": first(row, ["custom_issue", "axe_rule", "primary_rule", "rule"]),
        "finding_status": first(row, ["finding_status"]),
        "priority": first(row, ["priority"]),
        "selector": first(row, ["preferred_selector", "selector"]),
        "html": first(row, ["preferred_html", "affected_html", "html"]),
        "context": first(row, [
            "context",
            "nearby_context",
            "context_text",
            "contextual_evidence",
            "contextual_evidence_source",
        ]),
    }


def link_record(site, row):
    rec = make_common(site, row)
    specific = is_link_specific(row)

    rec.update({
        "component": "Link V4",
        "validation_type": (
            "link_recommendation"
            if specific
            else "link_abstention"
        ),
        "decision_or_role": first(row, [
            "link_v4_decision_code",
            "link_decision_code",
        ]),
        "confidence": first(row, [
            "link_v4_confidence",
            "link_confidence",
        ]),
        "current_text_or_alt": first(row, [
            "link_v4_current_text",
            "current_link_text",
            "link_text",
        ]),
        "destination_or_image": first(row, [
            "link_v4_destination",
            "link_destination",
            "href",
        ]),
        "suggestion": first(row, [
            "link_v4_suggested_accessible_name",
            "link_v4_suggested_name",
            "link_suggested_accessible_name",
            "link_suggested_name",
        ]),
        "recommended_action": first(row, [
            "link_v4_recommended_action",
            "link_v4_action",
            "link_recommended_action",
        ]),
        "suggested_html": first(row, [
            "link_v4_suggested_html",
            "link_suggested_html",
        ]),
        "model_or_engine": "Deterministic Link V4",
        "human_label": "",
        "human_comment": "",
    })
    return rec


def vlm_record(site, row):
    rec = make_common(site, row)

    rec.update({
        "component": "VLM",
        "validation_type": "vlm_recommendation",
        "decision_or_role": first(row, [
            "vlm_image_role",
            "image_role",
        ]),
        "confidence": first(row, [
            "vlm_confidence",
            "confidence",
        ]),
        "current_text_or_alt": first(row, [
            "vlm_current_alt",
            "current_alt",
        ]),
        "destination_or_image": first(row, [
            "vlm_resolved_image_url",
            "resolved_image_url",
            "image_url",
            "src",
        ]),
        "suggestion": first(row, [
            "vlm_suggested_alt",
            "suggested_alt",
        ]),
        "recommended_action": first(row, [
            "vlm_recommended_action",
            "recommended_action",
        ]),
        "suggested_html": first(row, [
            "vlm_suggested_html",
        ]),
        "model_or_engine": first(row, [
            "vlm_model",
            "model",
        ]) or "VLM",
        "human_label": "",
        "human_comment": "",
    })
    return rec


def main():
    if not STATUS_CSV.exists():
        print("ERROR:")
        print(f"Could not find: {STATUS_CSV.resolve()}")
        print("Run from ~/bd-web-accessibility-ai")
        sys.exit(2)

    status = pd.read_csv(STATUS_CSV)

    required = {
        "site_id",
        "website_name",
        "category",
        "recommendation_csv",
    }

    missing = required - set(status.columns)
    if missing:
        print("ERROR: status CSV missing columns:", ", ".join(sorted(missing)))
        sys.exit(2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = []

    for _, srow in status.iterrows():
        site = {
            "site_id": clean(srow.get("site_id", "")),
            "website_name": clean(srow.get("website_name", "")),
            "category": clean(srow.get("category", "")),
            "language": clean(srow.get("language", "")),
        }

        rec_path = Path(clean(srow.get("recommendation_csv", "")))
        if not rec_path.exists():
            print(f"WARNING: missing recommendations for {site['site_id']}: {rec_path}")
            continue

        df = pd.read_csv(rec_path)

        for _, row in link_rows(df).iterrows():
            records.append(link_record(site, row))

        for _, row in vlm_rows(df).iterrows():
            records.append(vlm_record(site, row))

    out = pd.DataFrame(records)

    if out.empty:
        print("ERROR: no validation rows found.")
        sys.exit(2)

    # Stable IDs make manual review and reproducibility easier.
    out.insert(
        0,
        "validation_id",
        [f"VAL{i:03d}" for i in range(1, len(out) + 1)],
    )

    preferred_order = [
        "validation_id",
        "site_id",
        "website_name",
        "category",
        "language",
        "component",
        "validation_type",
        "page_url",
        "unified_id",
        "issue",
        "finding_status",
        "priority",
        "selector",
        "html",
        "context",
        "decision_or_role",
        "confidence",
        "current_text_or_alt",
        "destination_or_image",
        "suggestion",
        "recommended_action",
        "suggested_html",
        "model_or_engine",
        "human_label",
        "human_comment",
    ]

    out = out[
        [c for c in preferred_order if c in out.columns]
    ]

    link_specific = out[out["validation_type"] == "link_recommendation"].copy()
    link_abstain = out[out["validation_type"] == "link_abstention"].copy()
    vlm = out[out["validation_type"] == "vlm_recommendation"].copy()

    out.to_csv(ALL_CSV, index=False, encoding="utf-8-sig")
    link_specific.to_csv(LINK_CSV, index=False, encoding="utf-8-sig")
    link_abstain.to_csv(ABSTAIN_CSV, index=False, encoding="utf-8-sig")
    vlm.to_csv(VLM_CSV, index=False, encoding="utf-8-sig")

    guide = f"""FIVE-SITE HUMAN VALIDATION GUIDE

Primary purpose
---------------
Evaluate the finalized system exactly as produced. Do not modify the recommendation
before assigning a label.

Dataset
-------
Websites: {out['site_id'].nunique()}
Total decisions: {len(out)}
Link V4 recommendations: {len(link_specific)}
Link V4 abstentions/manual-review decisions: {len(link_abstain)}
VLM recommendations: {len(vlm)}

Labels for link_recommendation and vlm_recommendation
-----------------------------------------------------
Correct
    Appropriate as written, or only trivial wording/punctuation editing is needed.

Partially Correct
    Main idea is appropriate, but a meaningful wording, contextual, semantic,
    or code change is needed before applying it.

Incorrect
    Recommendation is misleading, inappropriate, unsafe, or should not be applied.

Labels for link_abstention
--------------------------
Correct
    Abstaining/manual review is appropriate because evidence is genuinely insufficient.

Partially Correct
    Abstention is defensible, but the available evidence probably supports a useful
    candidate recommendation.

Incorrect
    The system should clearly have produced a recommendation from strong evidence,
    so abstaining was inappropriate.

Important VLM rule
------------------
Judge the visual recommendation against the ACTUAL IMAGE and its page purpose.
A visually accurate description is not automatically good alt text.

Human review fields
-------------------
Fill only:
    human_label
    human_comment

Use exactly:
    Correct
    Partially Correct
    Incorrect
"""

    GUIDE_TXT.write_text(guide, encoding="utf-8")

    print("=" * 92)
    print("FIVE-SITE MANUAL VALIDATION DATASET")
    print("=" * 92)
    print()
    print(f"Websites:                    {out['site_id'].nunique()}")
    print(f"Total decisions:             {len(out)}")
    print(f"Link V4 recommendations:     {len(link_specific)}")
    print(f"Link V4 abstentions:         {len(link_abstain)}")
    print(f"VLM recommendations:         {len(vlm)}")
    print()
    print("Files created:")
    print(ALL_CSV.resolve())
    print(LINK_CSV.resolve())
    print(ABSTAIN_CSV.resolve())
    print(VLM_CSV.resolve())
    print(GUIDE_TXT.resolve())
    print()
    print("Next: manually fill human_label and human_comment in the ALL CSV.")


if __name__ == "__main__":
    main()
