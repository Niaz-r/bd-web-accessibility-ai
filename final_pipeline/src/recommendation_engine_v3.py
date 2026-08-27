import re
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = Path(
    "final_pipeline/data/final/contextual_recommendations"
)

CONTEXTUAL_RULES = {
    "generic_link_text",
    "empty_alt",
    "non_descriptive_alt"
}

GENERIC_LINK_TERMS = {
    "read more",
    "more",
    "click here",
    "here",
    "learn more",
    "details",
    "link"
}


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_space(value):

    return re.sub(
        r"\s+",
        " ",
        clean(value)
    ).strip()


def compact(
    value,
    max_length=220
):

    value = normalize_space(
        value
    )

    if len(value) <= max_length:
        return value

    return (
        value[:max_length - 3]
        .rstrip()
        + "..."
    )


def contains_bengali(text):

    return bool(
        re.search(
            r"[\u0980-\u09FF]",
            clean(text)
        )
    )


def contains_english(text):

    return bool(
        re.search(
            r"[A-Za-z]",
            clean(text)
        )
    )


def detect_language(text):

    text = clean(
        text
    )

    has_bn = contains_bengali(
        text
    )

    has_en = contains_english(
        text
    )

    if has_bn and has_en:
        return "mixed"

    if has_bn:
        return "bn"

    if has_en:
        return "en"

    return "other"


def preferred_language(text):

    """
    For mixed Bengali/English academic titles,
    prefer Bengali wording if Bengali characters exist.
    """

    if contains_bengali(
        text
    ):
        return "bn"

    if contains_english(
        text
    ):
        return "en"

    return "other"


def useful_context(value):

    value = normalize_space(
        value
    )

    if not value:
        return False

    if value.lower() in GENERIC_LINK_TERMS:
        return False

    if len(value) < 4:
        return False

    return True


# ============================================================
# REMOVE GENERIC LINK WORDING FROM PARENT TEXT
# ============================================================

def clean_parent_context(
    parent_text,
    existing_link_text
):

    text = normalize_space(
        parent_text
    )

    existing = normalize_space(
        existing_link_text
    )

    if not text:
        return ""

    if existing:

        text = re.sub(
            re.escape(
                existing
            ),
            " ",
            text,
            flags=re.IGNORECASE
        )

    for generic in GENERIC_LINK_TERMS:

        text = re.sub(
            r"\b"
            +
            re.escape(
                generic
            )
            +
            r"\b",
            " ",
            text,
            flags=re.IGNORECASE
        )

    text = normalize_space(
        text
    )

    return text


# ============================================================
# CONTEXT SELECTION
# ============================================================

def choose_link_context(row):
    """
    Select context conservatively.

    Priority:
        1. Nearby heading
        2. Figure caption
        3. Local parent text

    We intentionally do NOT automatically use next_text or
    previous_text because they may describe neighboring cards.
    """

    heading = normalize_space(
        row.get(
            "nearby_heading",
            ""
        )
    )

    if useful_context(
        heading
    ):

        return (
            heading,
            "nearby_heading",
            "high"
        )

    caption = normalize_space(
        row.get(
            "figcaption",
            ""
        )
    )

    if useful_context(
        caption
    ):

        return (
            caption,
            "figcaption",
            "medium"
        )

    parent = clean_parent_context(
        row.get(
            "parent_text",
            ""
        ),
        row.get(
            "text",
            ""
        )
    )

    if useful_context(
        parent
    ):

        return (
            parent,
            "parent_text",
            "medium"
        )

    return (
        "",
        "",
        "low"
    )


def choose_image_context(row):
    """
    Context is evidence about the image's surrounding content,
    NOT proof of what the image visually depicts.
    """

    caption = normalize_space(
        row.get(
            "figcaption",
            ""
        )
    )

    if useful_context(
        caption
    ):

        return (
            caption,
            "figcaption",
            "medium"
        )

    heading = normalize_space(
        row.get(
            "nearby_heading",
            ""
        )
    )

    if useful_context(
        heading
    ):

        return (
            heading,
            "nearby_heading",
            "medium"
        )

    parent = normalize_space(
        row.get(
            "parent_text",
            ""
        )
    )

    if useful_context(
        parent
    ):

        return (
            parent,
            "parent_text",
            "low"
        )

    return (
        "",
        "",
        "low"
    )


# ============================================================
# GENERIC LINK RECOMMENDATION
# ============================================================

def build_link_suggestion(
    context,
    language
):

    context = compact(
        context,
        max_length=180
    )

    if language == "bn":

        return (
            "আরও পড়ুন: "
            + context
        )

    return (
        "Read more: "
        + context
    )


def build_link_html(
    original_html,
    accessible_name
):

    original_html = clean(
        original_html
    )

    if not original_html:
        return ""

    try:

        soup = BeautifulSoup(
            original_html,
            "html.parser"
        )

        element = soup.find(
            "a"
        )

        if element is None:
            return ""

        element[
            "aria-label"
        ] = accessible_name

        return str(
            element
        )

    except Exception:

        return ""


def recommend_generic_link(row):

    context, source, confidence = (
        choose_link_context(
            row
        )
    )

    if not context:

        return {

            "decision_code":
                "LINK_CONTEXT_NOT_FOUND",

            "action":
                "manual_link_purpose_review",

            "suggestion":
                "",

            "reason":
                (
                    "The current link text is generic, but "
                    "the extractor did not identify sufficiently "
                    "reliable local context for an automatic "
                    "replacement."
                ),

            "confidence":
                "low",

            "evidence_source":
                "",

            "language":
                "other",

            "visual_review_required":
                False,

            "manual_review_required":
                True,

            "suggested_html":
                ""
        }

    language = preferred_language(
        context
    )

    suggestion = build_link_suggestion(
        context,
        language
    )

    suggested_html = build_link_html(
        row.get(
            "preferred_html",
            ""
        ),
        suggestion
    )

    return {

        "decision_code":
            "LINK_CONTEXT_AVAILABLE",

        "action":
            "replace_or_expand_accessible_link_name",

        "suggestion":
            suggestion,

        "reason":
            (
                "The nearby "
                + source.replace(
                    "_",
                    " "
                )
                +
                " provides a specific description of "
                "the destination, so it can be used to "
                "make the generic link purpose clearer."
            ),

        "confidence":
            confidence,

        "evidence_source":
            source,

        "language":
            language,

        "visual_review_required":
            False,

        "manual_review_required":
            True,

        "suggested_html":
            suggested_html
    }


# ============================================================
# EMPTY ALT
# ============================================================

def recommend_empty_alt(row):

    context, source, confidence = (
        choose_image_context(
            row
        )
    )

    if context:

        context = compact(
            context,
            max_length=180
        )

        return {

            "decision_code":
                "EMPTY_ALT_CONTEXT_AVAILABLE",

            "action":
                "verify_decorative_or_informative",

            "suggestion":
                (
                    "Visually inspect the image. "
                    "If it communicates information related to "
                    f"“{context}”, replace alt=\"\" with a concise "
                    "description of what the image actually "
                    "communicates. If it is purely decorative, "
                    "keep alt=\"\"."
                ),

            "reason":
                (
                    "The surrounding "
                    + source.replace(
                        "_",
                        " "
                    )
                    +
                    " identifies the content context, but "
                    "textual context alone cannot determine "
                    "what the image visually contains."
                ),

            "confidence":
                confidence,

            "evidence_source":
                source,

            "language":
                preferred_language(
                    context
                ),

            "visual_review_required":
                True,

            "manual_review_required":
                True,

            "suggested_html":
                ""
        }

    return {

        "decision_code":
            "EMPTY_ALT_NO_CONTEXT",

        "action":
            "visual_review_required",

        "suggestion":
            (
                "Determine whether the image is decorative or "
                "informative. Keep alt=\"\" only when the image "
                "adds no meaningful information. Otherwise add "
                "a concise context-appropriate alternative."
            ),

        "reason":
            (
                "No sufficiently reliable textual context was "
                "available to infer the image's purpose."
            ),

        "confidence":
            "low",

        "evidence_source":
            "",

        "language":
            "other",

        "visual_review_required":
            True,

        "manual_review_required":
            True,

        "suggested_html":
            ""
    }


# ============================================================
# NON-DESCRIPTIVE ALT
# ============================================================

def recommend_non_descriptive_alt(row):

    existing_alt = normalize_space(
        row.get(
            "alt",
            ""
        )
    )

    context, source, confidence = (
        choose_image_context(
            row
        )
    )

    if context:

        context = compact(
            context,
            max_length=180
        )

        return {

            "decision_code":
                "GENERIC_ALT_CONTEXT_AVAILABLE",

            "action":
                "replace_generic_alt_after_visual_review",

            "suggestion":
                (
                    f'Replace the generic alt text '
                    f'“{existing_alt}” after visually inspecting '
                    f'the image. The surrounding context '
                    f'“{context}” can guide the description, '
                    f'but should not be copied as alt text unless '
                    f'it accurately represents the image.'
                ),

            "reason":
                (
                    "The current alt attribute exists but appears "
                    "non-descriptive. Context provides evidence "
                    "about the related content, not proof of the "
                    "image's visual content."
                ),

            "confidence":
                confidence,

            "evidence_source":
                source,

            "language":
                preferred_language(
                    context
                ),

            "visual_review_required":
                True,

            "manual_review_required":
                True,

            "suggested_html":
                ""
        }

    return {

        "decision_code":
            "GENERIC_ALT_NO_CONTEXT",

        "action":
            "replace_generic_alt_after_visual_review",

        "suggestion":
            (
                f'The existing alt text “{existing_alt}” is likely '
                "too generic. Visually inspect the image and replace "
                "it with a concise description of the image's actual "
                "content or function. Use alt=\"\" instead if the "
                "image is purely decorative."
            ),

        "reason":
            (
                "The scanner identified likely non-descriptive "
                "alternative text, but no reliable local context "
                "was available for a more specific recommendation."
            ),

        "confidence":
            "low",

        "evidence_source":
            "",

        "language":
            "other",

        "visual_review_required":
            True,

        "manual_review_required":
            True,

        "suggested_html":
            ""
    }


# ============================================================
# MAIN RULE ROUTER
# ============================================================

def contextual_recommendation(row):

    rule = clean(
        row.get(
            "custom_issue",
            ""
        )
    )

    if rule == "generic_link_text":

        return recommend_generic_link(
            row
        )

    if rule == "empty_alt":

        return recommend_empty_alt(
            row
        )

    if rule == "non_descriptive_alt":

        return recommend_non_descriptive_alt(
            row
        )

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )

        print(
            "python final_pipeline/src/"
            "recommendation_engine_v3.py "
            "<context_findings.csv>"
        )

        sys.exit(1)

    input_file = Path(
        sys.argv[1]
    )

    if not input_file.exists():

        print(
            "ERROR: File not found:"
        )

        print(
            input_file
        )

        sys.exit(1)

    df = pd.read_csv(
        input_file
    )

    print()
    print("=" * 80)
    print("RECOMMENDATION ENGINE V3")
    print("=" * 80)

    print(
        "Input:",
        input_file
    )

    print(
        "Total unified findings:",
        len(df)
    )

    # ========================================================
    # NEW OUTPUT COLUMNS
    # ========================================================

    new_columns = [

        "contextual_processed",

        "contextual_decision_code",

        "contextual_action",

        "contextual_suggestion",

        "contextual_reason",

        "contextual_confidence",

        "contextual_evidence_source",

        "contextual_language",

        "contextual_visual_review_required",

        "contextual_manual_review_required",

        "contextual_suggested_html"
    ]

    for column in new_columns:

        if column not in df.columns:

            df[
                column
            ] = pd.Series(
                [""] * len(df),
                dtype="object"
            )

    # ========================================================
    # PROCESS
    # ========================================================

    processed = 0

    rule_counts = {}

    decision_counts = {}

    confidence_counts = {}

    for index, row in df.iterrows():

        rule = clean(
            row.get(
                "custom_issue",
                ""
            )
        )

        if rule not in CONTEXTUAL_RULES:

            df.at[
                index,
                "contextual_processed"
            ] = False

            continue

        recommendation = (
            contextual_recommendation(
                row
            )
        )

        if recommendation is None:
            continue

        processed += 1

        rule_counts[
            rule
        ] = (
            rule_counts.get(
                rule,
                0
            )
            + 1
        )

        decision = recommendation[
            "decision_code"
        ]

        decision_counts[
            decision
        ] = (
            decision_counts.get(
                decision,
                0
            )
            + 1
        )

        confidence = recommendation[
            "confidence"
        ]

        confidence_counts[
            confidence
        ] = (
            confidence_counts.get(
                confidence,
                0
            )
            + 1
        )

        df.at[
            index,
            "contextual_processed"
        ] = True

        df.at[
            index,
            "contextual_decision_code"
        ] = recommendation[
            "decision_code"
        ]

        df.at[
            index,
            "contextual_action"
        ] = recommendation[
            "action"
        ]

        df.at[
            index,
            "contextual_suggestion"
        ] = recommendation[
            "suggestion"
        ]

        df.at[
            index,
            "contextual_reason"
        ] = recommendation[
            "reason"
        ]

        df.at[
            index,
            "contextual_confidence"
        ] = recommendation[
            "confidence"
        ]

        df.at[
            index,
            "contextual_evidence_source"
        ] = recommendation[
            "evidence_source"
        ]

        df.at[
            index,
            "contextual_language"
        ] = recommendation[
            "language"
        ]

        df.at[
            index,
            "contextual_visual_review_required"
        ] = recommendation[
            "visual_review_required"
        ]

        df.at[
            index,
            "contextual_manual_review_required"
        ] = recommendation[
            "manual_review_required"
        ]

        df.at[
            index,
            "contextual_suggested_html"
        ] = recommendation[
            "suggested_html"
        ]

    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    base_name = (
        input_file.name
        .replace(
            "_context_findings.csv",
            ""
        )
    )

    output_file = (
        OUTPUT_DIR
        /
        (
            base_name
            +
            "_contextual_recommendations.csv"
        )
    )

    df.to_csv(
        output_file,
        index=False
    )

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("CONTEXTUAL RECOMMENDATION SUMMARY")
    print("=" * 80)

    print(
        "Processed contextual findings:",
        processed
    )

    print()

    print(
        "By rule:"
    )

    if rule_counts:

        for rule, count in sorted(
            rule_counts.items()
        ):

            print(
                f"  {rule}: {count}"
            )

    else:

        print(
            "  None"
        )

    print()

    print(
        "Decision codes:"
    )

    if decision_counts:

        for decision, count in sorted(
            decision_counts.items()
        ):

            print(
                f"  {decision}: {count}"
            )

    print()

    print(
        "Confidence:"
    )

    if confidence_counts:

        for confidence, count in sorted(
            confidence_counts.items()
        ):

            print(
                f"  {confidence}: {count}"
            )

    # ========================================================
    # SAMPLE
    # ========================================================

    processed_rows = df[
        df[
            "contextual_processed"
        ]
        .astype(str)
        .str.lower()
        ==
        "true"
    ]

    print()
    print("=" * 80)
    print("SAMPLE CONTEXTUAL RECOMMENDATIONS")
    print("=" * 80)

    if len(
        processed_rows
    ):

        columns = [

            "custom_issue",

            "text",

            "alt",

            "nearby_heading",

            "contextual_action",

            "contextual_suggestion",

            "contextual_confidence",

            "contextual_evidence_source"
        ]

        existing = [

            column
            for column in columns
            if column
            in processed_rows.columns
        ]

        print(
            processed_rows[
                existing
            ]
            .head(12)
            .to_string(
                index=False
            )
        )

    print()
    print(
        "Output:"
    )

    print(
        output_file
    )

    print()
    print(
        "Important:"
    )

    print(
        "Recommendations are generated by the "
        "research system's deterministic contextual "
        "decision rules. Image-alt recommendations "
        "still require visual/human verification."
    )


if __name__ == "__main__":
    main()
