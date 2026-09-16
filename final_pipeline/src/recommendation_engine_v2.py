import os
import sys
import glob
import html as html_lib

import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

CSV_OUTPUT_DIR = (
    "final_pipeline/data/final/"
    "live_recommendations"
)

HTML_OUTPUT_DIR = (
    "final_pipeline/reports/live"
)

VLM_REVIEW_DIR = (
    "final_pipeline/data/final/"
    "vlm_alt_reviews"
)


# ============================================================
# RECOMMENDATION KNOWLEDGE BASE
# ============================================================

RULES = {

    # ========================================================
    # IMAGES
    # ========================================================

    "image-alt": {

        "title":
            "Image does not have an appropriate text alternative",

        "category":
            "Images",

        "wcag":
            "1.1.1 Non-text Content",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Users who cannot perceive the image may not "
                "receive the information or function communicated "
                "by it."
            ),

        "recommendation":
            (
                "Determine whether the image is informative, "
                "functional, or decorative. Informative images "
                "should have concise alternative text describing "
                "their purpose. Decorative images should normally "
                "use alt=\"\"."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "The correct alternative depends on the purpose "
                "and surrounding context of the image."
            )
    },


    "missing_alt": {

        "title":
            "Image is missing an alt attribute",

        "category":
            "Images",

        "wcag":
            "1.1.1 Non-text Content",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "An image without a text alternative may not "
                "communicate its purpose to screen-reader users."
            ),

        "recommendation":
            (
                "Add an appropriate alt attribute. Use descriptive "
                "text for informative images or alt=\"\" for "
                "decorative images."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Image purpose must be determined before choosing "
                "appropriate alternative text."
            )
    },


    "empty_alt": {

        "title":
            "Image has an empty alternative",

        "category":
            "Images",

        "wcag":
            "1.1.1 Non-text Content",

        "wcag_level":
            "A",

        "certainty":
            "Context-dependent review",

        "why":
            (
                "Empty alt text is appropriate for decorative "
                "images but may hide meaningful content when used "
                "on informative images."
            ),

        "recommendation":
            (
                "Keep alt=\"\" if the image is decorative. "
                "If the image communicates information or performs "
                "a function, replace the empty value with meaningful "
                "alternative text."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Automation cannot reliably determine whether "
                "the image is decorative or informative."
            )
    },


    "non_descriptive_alt": {

        "title":
            "Image alternative text may not be descriptive",

        "category":
            "Images",

        "wcag":
            "1.1.1 Non-text Content",

        "wcag_level":
            "A",

        "certainty":
            "Context-dependent review",

        "why":
            (
                "Although the image has an alt attribute, generic "
                "text such as 'image', 'thumbnail', 'news image', "
                "'event image', or a filename may not communicate "
                "the image's actual content or purpose."
            ),

        "recommendation":
            (
                "Review the purpose of the image and replace generic "
                "or filename-like alternative text with a concise "
                "description that communicates the same relevant "
                "information or function. If the image is purely "
                "decorative, use alt=\"\" instead."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Alternative-text quality depends on the image's "
                "purpose and surrounding context. The automated rule "
                "identifies likely non-descriptive text but does not "
                "by itself establish a WCAG failure."
            )
    },


    # ========================================================
    # LINKS
    # ========================================================

    "link-name": {

        "title":
            "Link does not have a discernible accessible name",

        "category":
            "Links",

        "wcag":
            (
                "2.4.4 Link Purpose (In Context) / "
                "4.1.2 Name, Role, Value"
            ),

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Screen-reader users may encounter a link without "
                "being told what it does or where it goes."
            ),

        "recommendation":
            (
                "Provide meaningful visible link text or another "
                "valid accessible name. Icon-only links should expose "
                "a concise accessible name describing their action "
                "or destination."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Verify the final computed accessible name in the "
                "rendered browser accessibility tree."
            )
    },


    "empty_link_text": {

        "title":
            "Link does not have an accessible name",

        "category":
            "Links",

        "wcag":
            "2.4.4 Link Purpose (In Context)",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "A link without meaningful text or another accessible "
                "name may be unusable for screen-reader users."
            ),

        "recommendation":
            (
                "Provide descriptive visible link text or an "
                "appropriate accessible name for icon-only links."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "The computed accessible name should be checked "
                "in the rendered page."
            )
    },


    "generic_link_text": {

        "title":
            "Generic link wording requires contextual review",

        "category":
            "Links",

        "wcag":
            "2.4.4 Link Purpose (In Context)",

        "wcag_level":
            "A",

        "certainty":
            "Context-dependent review",

        "why":
            (
                "Text such as 'Read More', 'More', or 'Click Here' "
                "may not clearly identify the link destination when "
                "encountered outside its visual context."
            ),

        "recommendation":
            (
                "Prefer descriptive link text that communicates the "
                "destination or purpose. If generic wording is retained, "
                "verify that programmatically determined context makes "
                "the purpose clear."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Generic wording alone does not prove a WCAG failure; "
                "the programmatic context must be evaluated."
            )
    },


    # ========================================================
    # HEADINGS
    # ========================================================

    "empty-heading": {

        "title":
            "Heading is empty",

        "category":
            "Headings",

        "wcag":
            "2.4.6 Headings and Labels",

        "wcag_level":
            "AA",

        "certainty":
            "Accessibility / best-practice finding",

        "why":
            (
                "An empty heading creates an unhelpful navigation "
                "point for users who navigate content by headings."
            ),

        "recommendation":
            (
                "Remove the heading if it has no purpose or provide "
                "meaningful text describing the associated section."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Confirm the rendered heading and its purpose "
                "within the page structure."
            )
    },


    "empty_heading": {

        "title":
            "Heading is empty",

        "category":
            "Headings",

        "wcag":
            "2.4.6 Headings and Labels",

        "wcag_level":
            "AA",

        "certainty":
            "Accessibility / best-practice finding",

        "why":
            (
                "Empty headings may create confusing navigation "
                "points."
            ),

        "recommendation":
            (
                "Provide meaningful heading text or remove the "
                "heading element if it serves no semantic purpose."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            "Verify the complete rendered page structure."
    },


    "heading-order": {

        "title":
            "Heading hierarchy may be inconsistent",

        "category":
            "Headings",

        "wcag":
            "1.3.1 Info and Relationships",

        "wcag_level":
            "A",

        "certainty":
            "Structural best-practice review",

        "why":
            (
                "Unexpected heading-level jumps can make the "
                "relationship between sections harder to understand."
            ),

        "recommendation":
            (
                "Review the document outline and use heading levels "
                "according to the logical content hierarchy."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "A heading-level jump is not automatically a WCAG "
                "failure. The full document hierarchy must be reviewed."
            )
    },


    "heading_order": {

        "title":
            "Heading hierarchy may be inconsistent",

        "category":
            "Headings",

        "wcag":
            "1.3.1 Info and Relationships",

        "wcag_level":
            "A",

        "certainty":
            "Structural review",

        "why":
            (
                "Unexpected heading-level jumps may make section "
                "relationships harder to understand."
            ),

        "recommendation":
            (
                "Review the heading hierarchy and ensure that heading "
                "levels reflect the logical document structure."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            "Heading structure requires contextual evaluation."
    },


    "missing_h1": {

        "title":
            "Page does not contain an H1 heading",

        "category":
            "Headings",

        "wcag":
            "Related to 1.3.1 and 2.4.6",

        "wcag_level":
            "Review",

        "certainty":
            "Structural best-practice review",

        "why":
            (
                "A meaningful top-level heading can help users "
                "understand the main purpose of the page."
            ),

        "recommendation":
            (
                "Review the page structure and provide a meaningful "
                "top-level heading when appropriate."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "WCAG does not simply require exactly one H1 "
                "on every page."
            )
    },


    "multiple_h1": {

        "title":
            "Page contains multiple H1 headings",

        "category":
            "Headings",

        "wcag":
            "Related to 1.3.1 and 2.4.6",

        "wcag_level":
            "Review",

        "certainty":
            "Structural best-practice review",

        "why":
            (
                "Multiple top-level headings can make hierarchy "
                "unclear when they do not reflect the logical "
                "document structure."
            ),

        "recommendation":
            (
                "Review the heading structure. Do not remove H1 "
                "elements simply to satisfy a numerical rule; use "
                "headings according to semantic hierarchy."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Multiple H1 elements alone do not establish "
                "WCAG failure."
            )
    },


    # ========================================================
    # AXE — CONTROLS
    # ========================================================

    "button-name": {

        "title":
            "Button does not have a discernible accessible name",

        "category":
            "Controls",

        "wcag":
            "4.1.2 Name, Role, Value",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Users of assistive technology may encounter "
                "a button without knowing its purpose."
            ),

        "recommendation":
            (
                "Provide meaningful visible button text or an "
                "appropriate accessible name such as aria-label "
                "when the control is icon-only."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            "Verify the computed accessible name after the change."
    },


    # ========================================================
    # AXE — FRAMES
    # ========================================================

    "frame-title": {

        "title":
            "Embedded frame does not have an accessible name",

        "category":
            "Frames",

        "wcag":
            "4.1.2 Name, Role, Value",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Users may not know what content an iframe contains "
                "when it has no descriptive accessible name."
            ),

        "recommendation":
            (
                "Add a concise title attribute to the iframe "
                "describing the embedded content."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "The title should accurately describe the actual "
                "embedded content."
            )
    },


    # ========================================================
    # AXE — STRUCTURE
    # ========================================================

    "list": {

        "title":
            "List contains invalid direct child elements",

        "category":
            "Structure",

        "wcag":
            "1.3.1 Info and Relationships",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Incorrect list markup may prevent assistive "
                "technologies from communicating list structure "
                "correctly."
            ),

        "recommendation":
            (
                "Ensure direct children of <ul> and <ol> are "
                "appropriate <li>, <script>, or <template> elements."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            "Verify the intended semantic grouping of the content."
    },


    "listitem": {

        "title":
            "List item is not contained in a proper list",

        "category":
            "Structure",

        "wcag":
            "1.3.1 Info and Relationships",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "A list item outside a proper list container may "
                "not be announced correctly by assistive technologies."
            ),

        "recommendation":
            (
                "Place <li> elements inside an appropriate <ul> "
                "or <ol>, or use a different element if the content "
                "is not a list."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            "Verify the intended content structure."
    },


    # ========================================================
    # AXE — VIEWPORT
    # ========================================================

    "meta-viewport": {

        "title":
            "Page restricts zooming or scaling",

        "category":
            "Visual accessibility",

        "wcag":
            "1.4.4 Resize Text",

        "wcag_level":
            "AA",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Preventing browser zoom can make content difficult "
                "to use for people with low vision."
            ),

        "recommendation":
            (
                "Remove restrictions such as user-scalable=no and "
                "maximum-scale=1. Allow users to zoom the page."
            ),

        "manual_review":
            "No",

        "review_reason":
            ""
    },


    # ========================================================
    # AXE — ARIA
    # ========================================================

    "aria-allowed-attr": {

        "title":
            "Element uses an unsupported ARIA attribute",

        "category":
            "ARIA",

        "wcag":
            "4.1.2 Name, Role, Value",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "ARIA attributes that are unsupported for an "
                "element's role can expose incorrect accessibility "
                "information."
            ),

        "recommendation":
            (
                "Review the reported element and remove or replace "
                "the unsupported ARIA attribute according to its "
                "semantic role."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "The exact correction depends on the element's "
                "intended role."
            )
    },


    "aria-prohibited-attr": {

        "title":
            "Element uses a prohibited ARIA attribute",

        "category":
            "ARIA",

        "wcag":
            "4.1.2 Name, Role, Value",

        "wcag_level":
            "A",

        "certainty":
            "Strong automated finding",

        "why":
            (
                "Prohibited ARIA attributes can cause assistive "
                "technologies to receive incorrect semantic "
                "information."
            ),

        "recommendation":
            (
                "Remove the prohibited ARIA attribute or correct "
                "the element's role and semantics."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Inspect axe's failure summary to determine "
                "the exact attribute responsible."
            )
    },


    # ========================================================
    # AXE — LANDMARK
    # ========================================================

    "region": {

        "title":
            "Content is not contained within a landmark region",

        "category":
            "Landmarks",

        "wcag":
            "Best practice / structural navigation",

        "wcag_level":
            "Best practice",

        "certainty":
            "Best-practice finding",

        "why":
            (
                "Landmarks can help assistive-technology users "
                "navigate major areas of a page efficiently."
            ),

        "recommendation":
            (
                "Review whether the content belongs inside an "
                "appropriate semantic landmark such as <main>, "
                "<nav>, <header>, <footer>, or another labelled "
                "region."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "Adding landmarks blindly can create excessive "
                "or incorrect landmark structure."
            )
    },


    # ========================================================
    # AXE — COLOR CONTRAST
    # ========================================================

    "color-contrast": {

        "title":
            "Text color contrast requires review",

        "category":
            "Color contrast",

        "wcag":
            "1.4.3 Contrast (Minimum)",

        "wcag_level":
            "AA",

        "certainty":
            "Manual review / rendered-style analysis",

        "why":
            (
                "Insufficient contrast between text and its "
                "background can make content difficult to read "
                "for users with low vision or color-vision "
                "deficiencies."
            ),

        "recommendation":
            (
                "Check the computed foreground and background "
                "colors of the affected text. Normal-sized text "
                "should generally have a contrast ratio of at "
                "least 4.5:1, while qualifying large text should "
                "generally have a ratio of at least 3:1."
            ),

        "manual_review":
            "Yes",

        "review_reason":
            (
                "axe returned this finding as incomplete when "
                "contrast could not be conclusively evaluated "
                "automatically. Background images, gradients, "
                "transparency, overlapping elements, or other "
                "rendered styling can require manual inspection."
            )
    }
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def bool_value(value):

    if isinstance(value, bool):
        return value

    return clean(value).lower() in {
        "true",
        "1",
        "yes"
    }


# ============================================================
# VLM INTEGRATION HELPERS
# ============================================================

VLM_ELIGIBLE_ISSUES = {
    "missing_alt",
    "empty_alt",
    "non_descriptive_alt",
}


def derive_base_name(input_file):

    input_name = os.path.basename(
        input_file
    )

    known_suffixes = [
        "__link_recommendations.csv",
        "_link_recommendations.csv",
        "__contextual_recommendations.csv",
        "_contextual_recommendations.csv",
        "__context_findings.csv",
        "_context_findings.csv",
        "__unified_findings.csv",
        "_unified_findings.csv",
    ]

    for suffix in known_suffixes:

        if input_name.endswith(
            suffix
        ):

            return input_name[
                :-len(
                    suffix
                )
            ]

    return os.path.splitext(
        input_name
    )[0]


def normalize_match_text(value):

    return " ".join(
        clean(
            value
        ).split()
    ).strip().lower()


def normalize_match_url(value):

    return clean(
        value
    ).strip()


def discover_vlm_review_file(
    base_name
):

    if not os.path.isdir(
        VLM_REVIEW_DIR
    ):

        return None

    exact_candidates = [
        os.path.join(
            VLM_REVIEW_DIR,
            (
                f"{base_name}"
                "_custom_findings"
                "__vlm_alt_reviews.csv"
            )
        ),
        os.path.join(
            VLM_REVIEW_DIR,
            (
                f"{base_name}"
                "__custom_findings"
                "__vlm_alt_reviews.csv"
            )
        ),
    ]

    for path in exact_candidates:

        if os.path.exists(
            path
        ):

            return path

    candidates = glob.glob(
        os.path.join(
            VLM_REVIEW_DIR,
            (
                f"{base_name}"
                "*__vlm_alt_reviews.csv"
            )
        )
    )

    if not candidates:

        return None

    candidates.sort(
        key=os.path.getmtime,
        reverse=True
    )

    return candidates[0]


def make_vlm_suggested_html(
    recommendation_row,
    vlm_row
):

    original = clean(
        recommendation_row.get(
            "preferred_html",
            ""
        )
    )

    if not original:

        return ""

    try:

        soup = BeautifulSoup(
            original,
            "html.parser"
        )

        element = soup.find()

        if (
            element is None
            or
            element.name != "img"
        ):

            return ""

        alt_status = clean(
            vlm_row.get(
                "alt_status",
                ""
            )
        ).lower()

        suggested_alt = clean(
            vlm_row.get(
                "suggested_alt",
                ""
            )
        )

        if alt_status in {
            "keep_empty",
            "set_empty_alt",
            "replace_with_empty_alt",
        }:

            element[
                "alt"
            ] = ""

            return str(
                element
            )

        if (
            alt_status
            in {
                "needs_meaningful_alt",
                "improve_existing_alt",
                "needs_long_description",
            }
            and
            suggested_alt
        ):

            element[
                "alt"
            ] = suggested_alt

            return str(
                element
            )

    except Exception:

        return ""

    return ""


def enrich_recommendations_with_vlm(
    recommendations,
    base_name
):

    vlm_boolean_columns = [
        "vlm_processed",
        "vlm_generic_alt_detected",
        "vlm_manual_review_required",
        "vlm_visual_review_required",
        "vlm_cache_hit",
        "vlm_guardrail_passed",
    ]

    vlm_text_columns = [
        "vlm_status",
        "vlm_model",
        "vlm_issue",
        "vlm_image_role",
        "vlm_alt_status",
        "vlm_current_alt",
        "vlm_suggested_alt",
        "vlm_recommended_action",
        "vlm_confidence",
        "vlm_reason",
        "vlm_resolved_image_url",
        "vlm_suggested_html",
        "vlm_review_file",
    ]

    # --------------------------------------------------------
    # Pandas 3.x uses stricter string dtypes. Initializing every
    # VLM column with an empty string makes columns such as
    # vlm_processed dtype=str, and assigning True/False later
    # raises TypeError. Keep Boolean and text fields explicitly
    # separated so enrichment remains type-safe.
    # --------------------------------------------------------

    for column in vlm_boolean_columns:

        if column not in recommendations.columns:

            recommendations[column] = pd.Series(
                False,
                index=recommendations.index,
                dtype="bool"
            )

        else:

            recommendations[column] = (
                recommendations[column]
                .map(bool_value)
                .astype("bool")
            )

    for column in vlm_text_columns:

        if column not in recommendations.columns:

            recommendations[column] = pd.Series(
                "",
                index=recommendations.index,
                dtype="object"
            )

        else:

            recommendations[column] = (
                recommendations[column]
                .astype("object")
            )

    if len(
        recommendations
    ) == 0:

        return (
            recommendations,
            None,
            0
        )

    vlm_file = discover_vlm_review_file(
        base_name
    )

    if vlm_file is None:

        return (
            recommendations,
            None,
            0
        )

    try:

        vlm_df = pd.read_csv(
            vlm_file
        )

    except Exception as error:

        print()
        print(
            "WARNING: Could not read VLM review file:"
        )
        print(
            vlm_file
        )
        print(
            error
        )

        return (
            recommendations,
            vlm_file,
            0
        )

    if len(
        vlm_df
    ) == 0:

        return (
            recommendations,
            vlm_file,
            0
        )

    if "issue" not in vlm_df.columns:

        return (
            recommendations,
            vlm_file,
            0
        )

    used_vlm_indices = set()
    matched_count = 0

    for rec_index, rec_row in recommendations.iterrows():

        custom_issue = normalize_match_text(
            rec_row.get(
                "custom_issue",
                ""
            )
        )

        if (
            custom_issue
            not in VLM_ELIGIBLE_ISSUES
        ):

            continue

        rec_src = normalize_match_url(
            rec_row.get(
                "src",
                ""
            )
        )

        rec_selector = clean(
            rec_row.get(
                "preferred_selector",
                ""
            )
        )

        rec_alt = normalize_match_text(
            rec_row.get(
                "alt",
                ""
            )
        )

        rec_page_url = normalize_match_url(
            rec_row.get(
                "page_url",
                ""
            )
        )

        best_index = None
        best_score = -1

        for vlm_index, vlm_row in vlm_df.iterrows():

            if vlm_index in used_vlm_indices:

                continue

            vlm_issue = normalize_match_text(
                vlm_row.get(
                    "issue",
                    ""
                )
            )

            if vlm_issue != custom_issue:

                continue

            vlm_src = normalize_match_url(
                vlm_row.get(
                    "src",
                    ""
                )
            )

            vlm_selector = clean(
                vlm_row.get(
                    "selector",
                    ""
                )
            )

            vlm_alt = normalize_match_text(
                vlm_row.get(
                    "alt",
                    ""
                )
            )

            vlm_page_url = normalize_match_url(
                vlm_row.get(
                    "page_url",
                    ""
                )
            )

            score = 0

            same_src = (
                rec_src
                and
                vlm_src
                and
                rec_src == vlm_src
            )

            same_selector = (
                rec_selector
                and
                vlm_selector
                and
                rec_selector == vlm_selector
            )

            if same_src:

                score += 140

            if same_selector:

                score += 120

            if rec_alt == vlm_alt:

                score += 15

            if (
                rec_page_url
                and
                vlm_page_url
                and
                rec_page_url.rstrip("/")
                ==
                vlm_page_url.rstrip("/")
            ):

                score += 10

            # Alt text alone is not sufficient because generic
            # values such as "Thumb" can occur on many images.
            if (
                (same_src or same_selector)
                and
                score > best_score
            ):

                best_index = vlm_index
                best_score = score

        if best_index is None:

            continue

        vlm_row = vlm_df.loc[
            best_index
        ]

        used_vlm_indices.add(
            best_index
        )

        matched_count += 1

        recommendations.at[
            rec_index,
            "vlm_processed"
        ] = True

        recommendations.at[
            rec_index,
            "vlm_status"
        ] = clean(
            vlm_row.get(
                "vlm_status",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_model"
        ] = clean(
            vlm_row.get(
                "vlm_model",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_issue"
        ] = clean(
            vlm_row.get(
                "issue",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_image_role"
        ] = clean(
            vlm_row.get(
                "image_role",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_alt_status"
        ] = clean(
            vlm_row.get(
                "alt_status",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_current_alt"
        ] = clean(
            vlm_row.get(
                "alt",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_suggested_alt"
        ] = clean(
            vlm_row.get(
                "suggested_alt",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_recommended_action"
        ] = clean(
            vlm_row.get(
                "recommended_action",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_confidence"
        ] = clean(
            vlm_row.get(
                "confidence",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_generic_alt_detected"
        ] = bool_value(
            vlm_row.get(
                "generic_alt_detected",
                False
            )
        )

        recommendations.at[
            rec_index,
            "vlm_manual_review_required"
        ] = bool_value(
            vlm_row.get(
                "manual_review_required",
                True
            )
        )

        recommendations.at[
            rec_index,
            "vlm_visual_review_required"
        ] = bool_value(
            vlm_row.get(
                "visual_review_required",
                True
            )
        )

        recommendations.at[
            rec_index,
            "vlm_reason"
        ] = clean(
            vlm_row.get(
                "reason",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_resolved_image_url"
        ] = clean(
            vlm_row.get(
                "resolved_image_url",
                ""
            )
        )

        recommendations.at[
            rec_index,
            "vlm_cache_hit"
        ] = bool_value(
            vlm_row.get(
                "cache_hit",
                False
            )
        )

        recommendations.at[
            rec_index,
            "vlm_guardrail_passed"
        ] = bool_value(
            vlm_row.get(
                "guardrail_passed",
                False
            )
        )

        recommendations.at[
            rec_index,
            "vlm_suggested_html"
        ] = make_vlm_suggested_html(
            rec_row,
            vlm_row
        )

        recommendations.at[
            rec_index,
            "vlm_review_file"
        ] = vlm_file

    return (
        recommendations,
        vlm_file,
        matched_count
    )


# ============================================================
# SELECT PRIMARY RULE
# ============================================================

def select_rule(row):

    axe_rule = clean(
        row.get(
            "axe_rule",
            ""
        )
    )

    custom_issue = clean(
        row.get(
            "custom_issue",
            ""
        )
    )

    if axe_rule and axe_rule in RULES:
        return axe_rule

    if custom_issue and custom_issue in RULES:
        return custom_issue

    return (
        axe_rule
        or
        custom_issue
    )


# ============================================================
# PRIORITY
# ============================================================

def determine_priority(row):

    result_type = clean(
        row.get(
            "axe_result_type",
            ""
        )
    ).lower()

    if result_type == "incomplete":
        return "Review"

    impact = clean(
        row.get(
            "axe_impact",
            ""
        )
    ).lower()

    impact_map = {

        "critical":
            "Critical",

        "serious":
            "High",

        "moderate":
            "Medium",

        "minor":
            "Low"
    }

    if impact in impact_map:
        return impact_map[
            impact
        ]

    severity = clean(
        row.get(
            "custom_severity",
            ""
        )
    ).lower()

    if severity == "high":
        return "High"

    if severity == "medium":
        return "Medium"

    return "Review"


# ============================================================
# SUGGESTED HTML
# ============================================================

def suggested_html(
    row,
    rule
):

    original = clean(
        row.get(
            "preferred_html",
            ""
        )
    )

    # --------------------------------------------------------
    # Page-level H1
    # --------------------------------------------------------

    if rule == "missing_h1":

        return (
            "<h1>Describe the main page topic</h1>"
        )

    if not original:
        return ""

    try:

        soup = BeautifulSoup(
            original,
            "html.parser"
        )

        element = soup.find()

        if element is None:
            return ""

        # ----------------------------------------------------
        # Missing image alt
        # ----------------------------------------------------

        if rule in [
            "image-alt",
            "missing_alt"
        ]:

            if element.name == "img":

                element[
                    "alt"
                ] = (
                    "[Describe the image purpose]"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Empty alt
        # ----------------------------------------------------

        if rule == "empty_alt":

            if element.name == "img":

                element[
                    "alt"
                ] = (
                    "[Describe image if informative]"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Non-descriptive alt
        # ----------------------------------------------------

        if rule == "non_descriptive_alt":

            if element.name == "img":

                element[
                    "alt"
                ] = (
                    "[Replace with a meaningful "
                    "context-specific description]"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Empty link / link-name
        # ----------------------------------------------------

        if rule in [
            "link-name",
            "empty_link_text"
        ]:

            if element.name == "a":

                element[
                    "aria-label"
                ] = (
                    "Describe link destination"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Generic link
        # ----------------------------------------------------

        if rule == "generic_link_text":

            if element.name == "a":

                element.clear()

                element.string = (
                    "Describe the link destination"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Empty heading
        # ----------------------------------------------------

        if rule in [
            "empty-heading",
            "empty_heading"
        ]:

            if element.name in [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6"
            ]:

                element.clear()

                element.string = (
                    "Describe this section"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Button
        # ----------------------------------------------------

        if rule == "button-name":

            if element.name == "button":

                element[
                    "aria-label"
                ] = (
                    "Describe button action"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Frame
        # ----------------------------------------------------

        if rule == "frame-title":

            if element.name == "iframe":

                element[
                    "title"
                ] = (
                    "Describe embedded content"
                )

                return str(
                    element
                )

        # ----------------------------------------------------
        # Meta viewport
        # ----------------------------------------------------

        if rule == "meta-viewport":

            if (
                element.name == "meta"
                and
                clean(
                    element.get(
                        "name",
                        ""
                    )
                ).lower()
                == "viewport"
            ):

                element[
                    "content"
                ] = (
                    "width=device-width, "
                    "initial-scale=1.0"
                )

                return str(
                    element
                )

    except Exception:
        return ""

    return ""


# ============================================================
# LOCATION NOTE
# ============================================================

def location_note(row):

    selector = clean(
        row.get(
            "preferred_selector",
            ""
        )
    )

    ownership = clean(
        row.get(
            "ownership_scope",
            ""
        )
    )

    actionability = clean(
        row.get(
            "actionability",
            ""
        )
    )

    notes = []

    if selector:

        notes.append(
            f"DOM selector: {selector}"
        )

    if ownership:

        notes.append(
            f"Ownership: {ownership}"
        )

    if actionability:

        notes.append(
            f"Actionability: {actionability}"
        )

    return " | ".join(
        notes
    )


# ============================================================
# INTERACTIVE HTML REPORT
# ============================================================

def create_html_report(
    recommendations,
    output_file,
    page_url
):

    # ========================================================
    # HELPERS
    # ========================================================

    def esc(value):

        return html_lib.escape(
            clean(value),
            quote=True
        )


    def source_label(row):

        status = clean(
            row.get(
                "finding_status",
                ""
            )
        )

        if status == "confirmed_by_both":
            return "Custom + axe"

        if status == "custom_only":
            return "Custom"

        if status == "axe_only":
            return "axe"

        if status == "axe_incomplete":
            return "axe — manual review"

        return status


    def has_custom(row):

        return bool_value(
            row.get(
                "source_custom",
                False
            )
        )


    def has_axe(row):

        return bool_value(
            row.get(
                "source_axe",
                False
            )
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    total = len(
        recommendations
    )

    def count_status(value):

        if (
            "finding_status"
            not in recommendations.columns
        ):
            return 0

        return int(
            recommendations[
                "finding_status"
            ]
            .eq(
                value
            )
            .sum()
        )


    def count_priority(value):

        if (
            "priority"
            not in recommendations.columns
        ):
            return 0

        return int(
            recommendations[
                "priority"
            ]
            .eq(
                value
            )
            .sum()
        )


    confirmed = count_status(
        "confirmed_by_both"
    )

    custom_only = count_status(
        "custom_only"
    )

    axe_only = count_status(
        "axe_only"
    )

    incomplete = count_status(
        "axe_incomplete"
    )

    critical_count = count_priority(
        "Critical"
    )

    high_count = count_priority(
        "High"
    )

    medium_count = count_priority(
        "Medium"
    )

    low_count = count_priority(
        "Low"
    )

    review_count = count_priority(
        "Review"
    )

    if (
        "vlm_processed"
        in recommendations.columns
    ):

        vlm_count = sum(
            bool_value(
                value
            )
            for value
            in recommendations[
                "vlm_processed"
            ]
        )

    else:

        vlm_count = 0


    # ========================================================
    # HTML
    # ========================================================

    content = []

    content.append(
        """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Accessibility Analysis Report</title>

<style>

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {

    margin: 0;

    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    background: #f3f6fa;

    color: #1f2937;

    line-height: 1.55;
}

button,
input,
select {
    font: inherit;
}

.container {

    max-width: 1440px;

    margin: 0 auto;

    padding: 28px 24px 70px;
}


/* ==========================================================
   HEADER
   ========================================================== */

.report-header {

    color: white;

    background:
        linear-gradient(
            135deg,
            #172554,
            #1e3a8a,
            #2563eb
        );

    border-radius: 18px;

    padding: 34px;

    margin-bottom: 22px;

    box-shadow:
        0 12px 35px
        rgba(
            15,
            23,
            42,
            0.15
        );
}

.report-header h1 {

    margin: 0 0 8px;

    font-size: 32px;
}

.report-url {

    overflow-wrap: anywhere;

    color: #dbeafe;
}

.report-subtitle {

    max-width: 900px;

    color: #e0e7ff;
}


/* ==========================================================
   SUMMARY CARDS
   ========================================================== */

.summary-grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(155px, 1fr)
        );

    gap: 14px;

    margin: 22px 0;
}

.summary-card {

    background: white;

    border: 1px solid #e5e7eb;

    border-radius: 14px;

    padding: 18px;

    box-shadow:
        0 3px 12px
        rgba(
            15,
            23,
            42,
            0.05
        );
}

.summary-number {

    font-size: 30px;

    font-weight: 750;
}

.summary-label {

    color: #64748b;

    font-size: 13px;

    margin-top: 2px;
}


/* ==========================================================
   PROGRESS
   ========================================================== */

.progress-panel {

    background: white;

    border: 1px solid #e2e8f0;

    border-radius: 14px;

    padding: 18px;

    margin-bottom: 20px;
}

.progress-header {

    display: flex;

    justify-content: space-between;

    gap: 15px;

    margin-bottom: 10px;

    font-weight: 600;
}

.progress-track {

    height: 12px;

    background: #e2e8f0;

    border-radius: 999px;

    overflow: hidden;
}

.progress-bar {

    height: 100%;

    width: 0;

    background:
        linear-gradient(
            90deg,
            #16a34a,
            #22c55e
        );

    border-radius: 999px;

    transition: width 0.25s ease;
}


/* ==========================================================
   TOOLBAR
   ========================================================== */

.toolbar {

    position: static;

    background: white;

    border: 1px solid #e2e8f0;

    border-radius: 16px;

    padding: 20px;

    margin-bottom: 22px;

    box-shadow:
        0 6px 20px
        rgba(
            15,
            23,
            42,
            0.07
        );
}

.toolbar-title {

    font-weight: 700;

    font-size: 18px;

    margin-bottom: 14px;
}

.tool-row {

    display: flex;

    flex-wrap: wrap;

    gap: 10px;

    align-items: center;

    margin-bottom: 13px;
}

.tool-row:last-child {
    margin-bottom: 0;
}

.tool-label {

    min-width: 95px;

    font-size: 13px;

    font-weight: 700;

    color: #475569;
}

.filter-button,
.action-button {

    border: 1px solid #cbd5e1;

    background: white;

    color: #334155;

    border-radius: 999px;

    padding: 7px 13px;

    cursor: pointer;

    transition: 0.15s ease;
}

.filter-button:hover,
.action-button:hover {

    border-color: #2563eb;

    color: #1d4ed8;

    background: #eff6ff;
}

.filter-button.active,
.action-button.active {

    color: white;

    background: #2563eb;

    border-color: #2563eb;
}

.search-input {

    flex: 1;

    min-width: 230px;

    border: 1px solid #cbd5e1;

    border-radius: 9px;

    padding: 9px 12px;
}

.sort-select {

    border: 1px solid #cbd5e1;

    background: white;

    border-radius: 9px;

    padding: 9px 12px;
}


/* ==========================================================
   RESULTS BAR
   ========================================================== */

.results-bar {

    display: flex;

    flex-wrap: wrap;

    align-items: center;

    justify-content: space-between;

    gap: 10px;

    margin: 18px 0;

    color: #475569;
}

.results-count {

    font-weight: 700;
}


/* ==========================================================
   FINDING CARD
   ========================================================== */

.finding {

    position: relative;

    background: white;

    border: 1px solid #e2e8f0;

    border-left:
        6px solid #94a3b8;

    border-radius: 14px;

    margin-bottom: 18px;

    overflow: hidden;

    box-shadow:
        0 4px 14px
        rgba(
            15,
            23,
            42,
            0.055
        );

    transition:
        opacity 0.2s ease,
        transform 0.2s ease,
        border-color 0.2s ease;
}

.finding:hover {

    transform:
        translateY(-1px);

    box-shadow:
        0 8px 22px
        rgba(
            15,
            23,
            42,
            0.08
        );
}

.finding[data-priority="Critical"] {
    border-left-color: #991b1b;
}

.finding[data-priority="High"] {
    border-left-color: #dc2626;
}

.finding[data-priority="Medium"] {
    border-left-color: #f59e0b;
}

.finding[data-priority="Low"] {
    border-left-color: #3b82f6;
}

.finding[data-priority="Review"] {
    border-left-color: #7c3aed;
}

.finding.reviewed {

    opacity: 0.62;

    border-left-color: #16a34a;
}

.finding.reviewed .finding-title {

    text-decoration: line-through;

    text-decoration-thickness: 1px;
}


/* ==========================================================
   FINDING TOP
   ========================================================== */

.finding-top {

    display: flex;

    align-items: flex-start;

    gap: 14px;

    padding: 19px 20px 16px;
}

.issue-number {

    min-width: 64px;

    height: 34px;

    display: inline-flex;

    justify-content: center;

    align-items: center;

    border-radius: 999px;

    background: #0f172a;

    color: white;

    font-size: 13px;

    font-weight: 750;
}

.finding-heading {
    flex: 1;
}

.finding-title {

    margin: 0 0 7px;

    font-size: 20px;

    line-height: 1.3;
}

.rule-name {

    color: #64748b;

    font-family: monospace;

    font-size: 13px;
}


/* ==========================================================
   REVIEW CHECKBOX
   ========================================================== */

.review-control {

    display: flex;

    align-items: center;

    gap: 8px;

    padding: 7px 10px;

    background: #f8fafc;

    border: 1px solid #cbd5e1;

    border-radius: 9px;

    white-space: nowrap;

    cursor: pointer;
}

.review-checkbox {

    width: 19px;

    height: 19px;

    cursor: pointer;
}


/* ==========================================================
   BADGES
   ========================================================== */

.badges {

    display: flex;

    flex-wrap: wrap;

    gap: 7px;

    padding: 0 20px 15px;
}

.badge {

    display: inline-flex;

    align-items: center;

    border-radius: 999px;

    padding: 5px 9px;

    font-size: 12px;

    font-weight: 650;

    background: #f1f5f9;

    color: #334155;
}

.badge-critical {

    background: #fee2e2;

    color: #991b1b;
}

.badge-high {

    background: #fee2e2;

    color: #b91c1c;
}

.badge-medium {

    background: #fef3c7;

    color: #92400e;
}

.badge-low {

    background: #dbeafe;

    color: #1d4ed8;
}

.badge-review {

    background: #ede9fe;

    color: #6d28d9;
}

.badge-both {

    background: #dcfce7;

    color: #166534;
}

.badge-custom {

    background: #e0f2fe;

    color: #075985;
}

.badge-axe {

    background: #f3e8ff;

    color: #7e22ce;
}

.badge-contextual {

    background: #ccfbf1;

    color: #115e59;

    border: 1px solid #99f6e4;
}

.badge-vlm {

    background: #eef2ff;

    color: #3730a3;

    border: 1px solid #c7d2fe;
}


/* ==========================================================
   DETAILS
   ========================================================== */

.finding-details {

    border-top:
        1px solid #e2e8f0;
}

.finding-details summary {

    cursor: pointer;

    padding: 13px 20px;

    font-weight: 650;

    color: #1d4ed8;

    user-select: none;
}

.finding-content {

    padding: 5px 20px 23px;
}

.detail-section {

    margin-top: 22px;
}

.detail-section h3 {

    font-size: 15px;

    margin: 0 0 7px;

    color: #334155;
}

.detail-section p {
    margin: 0;
}


/* ==========================================================
   CODE / LOCATION
   ========================================================== */

.code-box {

    white-space: pre-wrap;

    overflow-wrap: anywhere;

    background: #0f172a;

    color: #e2e8f0;

    padding: 14px;

    border-radius: 9px;

    overflow-x: auto;

    font-family:
        "Ubuntu Mono",
        Consolas,
        monospace;

    font-size: 13px;
}

.location-box {

    padding: 12px;

    background: #eff6ff;

    border-left:
        4px solid #3b82f6;

    border-radius: 8px;

    overflow-wrap: anywhere;
}

.recommendation-box {

    padding: 14px;

    background: #f0fdf4;

    border-left:
        4px solid #22c55e;

    border-radius: 8px;
}

.warning-box {

    padding: 14px;

    background: #fff7ed;

    border-left:
        4px solid #f97316;

    border-radius: 8px;

    margin-top: 18px;
}

.manual-box {

    padding: 14px;

    background: #faf5ff;

    border-left:
        4px solid #8b5cf6;

    border-radius: 8px;
}


/* ==========================================================
   CONTEXT-AWARE RECOMMENDATION
   ========================================================== */

.contextual-box {

    padding: 17px;

    background: #f0fdfa;

    border: 1px solid #99f6e4;

    border-left:
        5px solid #0d9488;

    border-radius: 9px;
}

.contextual-suggestion {

    font-size: 17px;

    font-weight: 650;

    margin: 10px 0;

    line-height: 1.6;
}

.contextual-meta {

    display: flex;

    flex-wrap: wrap;

    gap: 8px;

    margin-top: 13px;
}

.contextual-meta span {

    background: white;

    border: 1px solid #99f6e4;

    border-radius: 999px;

    padding: 5px 9px;

    font-size: 12px;

    color: #115e59;
}


/* ==========================================================
   VLM VISUAL ALT ANALYSIS
   ========================================================== */

.vlm-box {

    padding: 17px;

    background: #f5f3ff;

    border: 1px solid #ddd6fe;

    border-left: 5px solid #7c3aed;

    border-radius: 9px;
}

.vlm-suggestion {

    margin: 12px 0;

    padding: 13px;

    background: white;

    border: 1px solid #ddd6fe;

    border-radius: 8px;

    font-size: 16px;

    font-weight: 650;

    overflow-wrap: anywhere;
}

.vlm-meta {

    display: flex;

    flex-wrap: wrap;

    gap: 8px;

    margin: 12px 0;
}

.vlm-meta span {

    background: white;

    border: 1px solid #c4b5fd;

    border-radius: 999px;

    padding: 5px 9px;

    font-size: 12px;

    color: #5b21b6;
}

.vlm-note {

    margin-top: 14px;

    font-size: 13px;

    color: #5b21b6;
}

.vlm-image-link {

    overflow-wrap: anywhere;
}


/* ==========================================================
   LINK RECOMMENDATION ENGINE V4
   ========================================================== */

.link-v4-box {
    padding: 17px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 5px solid #2563eb;
    border-radius: 9px;
}

.link-v4-suggestion {
    font-size: 17px;
    font-weight: 650;
    margin: 10px 0;
    line-height: 1.6;
}

.link-v4-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 13px;
}

.link-v4-meta span {
    background: white;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 5px 9px;
    font-size: 12px;
    color: #1e40af;
}

.badge-link-v4 {
    background: #dbeafe;
    color: #1e40af;
    border: 1px solid #bfdbfe;
}


/* ==========================================================
   EMPTY RESULT
   ========================================================== */

.empty-results {

    display: none;

    padding: 45px;

    text-align: center;

    background: white;

    border:
        1px dashed #94a3b8;

    border-radius: 14px;

    color: #64748b;
}


/* ==========================================================
   FOOTER
   ========================================================== */

.footer-note {

    margin-top: 35px;

    background: #fffbeb;

    border: 1px solid #fde68a;

    border-radius: 12px;

    padding: 18px;

    color: #78350f;
}


/* ==========================================================
   MOBILE
   ========================================================== */

@media (
    max-width: 700px
) {

    .container {
        padding: 14px;
    }

    .report-header {
        padding: 24px;
    }

    .report-header h1 {
        font-size: 25px;
    }

    .finding-top {
        flex-wrap: wrap;
    }

    .review-control {

        width: 100%;

        justify-content: center;
    }
}


/* ==========================================================
   PRINT
   ========================================================== */

@media print {

    body {
        background: white;
    }

    .toolbar,
    .progress-panel,
    .results-bar {

        display: none !important;
    }

    .finding {

        break-inside: avoid;

        box-shadow: none;
    }

}

</style>

</head>

<body>

<div class="container">
"""
    )


    # ========================================================
    # HEADER
    # ========================================================

    content.append(
        f"""
<div class="report-header">

    <h1>
        Accessibility Analysis Report
    </h1>

    <div class="report-url">

        <strong>
            Analyzed page:
        </strong>

        {esc(page_url)}

    </div>

    <p class="report-subtitle">

        Combined analysis from the custom static scanner
        and axe-core rendered-DOM testing.

        Context-dependent findings may also include
        recommendations generated by the proposed
        deterministic contextual decision engine.

        Eligible image-alt findings may additionally include
        local VLM-assisted visual interpretation that is
        validated by deterministic accessibility guardrails
        and requires human verification.

    </p>

</div>
"""
    )


    # ========================================================
    # SUMMARY CARDS
    # ========================================================

    summary_items = [

        (
            total,
            "Unified findings"
        ),

        (
            confirmed,
            "Confirmed by both"
        ),

        (
            custom_only,
            "Custom only"
        ),

        (
            axe_only,
            "axe only"
        ),

        (
            incomplete,
            "Needs manual review"
        ),

        (
            vlm_count,
            "VLM visual reviews"
        ),

        (
            critical_count,
            "Critical"
        ),

        (
            high_count,
            "High"
        ),

        (
            medium_count,
            "Medium"
        ),

        (
            low_count,
            "Low"
        ),

        (
            review_count,
            "Review"
        )
    ]

    content.append(
        '<div class="summary-grid">'
    )

    for value, label in summary_items:

        content.append(
            f"""
<div class="summary-card">

    <div class="summary-number">
        {value}
    </div>

    <div class="summary-label">
        {esc(label)}
    </div>

</div>
"""
        )

    content.append(
        "</div>"
    )


    # ========================================================
    # REVIEW PROGRESS
    # ========================================================

    content.append(
        f"""
<div class="progress-panel">

    <div class="progress-header">

        <span>
            Review Progress
        </span>

        <span id="progressText">
            0 / {total} reviewed
        </span>

    </div>

    <div class="progress-track">

        <div
            id="progressBar"
            class="progress-bar"
        ></div>

    </div>

</div>
"""
    )


    # ========================================================
    # TOOLBAR
    # ========================================================

    content.append(
        """
<div class="toolbar">

    <div class="toolbar-title">
        Review & Filter Findings
    </div>


    <div class="tool-row">

        <span class="tool-label">
            Search
        </span>

        <input
            id="searchInput"
            class="search-input"
            type="search"
            placeholder="Search rule, issue, selector, HTML, WCAG..."
        >

    </div>


    <div class="tool-row">

        <span class="tool-label">
            Priority
        </span>

        <div id="priorityFilters">

            <button
                class="filter-button active"
                data-filter="all"
            >
                All
            </button>

            <button
                class="filter-button"
                data-filter="Critical"
            >
                Critical
            </button>

            <button
                class="filter-button"
                data-filter="High"
            >
                High
            </button>

            <button
                class="filter-button"
                data-filter="Medium"
            >
                Medium
            </button>

            <button
                class="filter-button"
                data-filter="Low"
            >
                Low
            </button>

            <button
                class="filter-button"
                data-filter="Review"
            >
                Review
            </button>

        </div>

    </div>


    <div class="tool-row">

        <span class="tool-label">
            Source
        </span>

        <div id="sourceFilters">

            <button
                class="filter-button active"
                data-filter="all"
            >
                All
            </button>

            <button
                class="filter-button"
                data-filter="custom"
            >
                Custom involved
            </button>

            <button
                class="filter-button"
                data-filter="axe"
            >
                axe involved
            </button>

            <button
                class="filter-button"
                data-filter="both"
            >
                Both
            </button>

            <button
                class="filter-button"
                data-filter="custom_only"
            >
                Custom only
            </button>

            <button
                class="filter-button"
                data-filter="axe_only"
            >
                axe only
            </button>

            <button
                class="filter-button"
                data-filter="axe_incomplete"
            >
                axe incomplete
            </button>

        </div>

    </div>


    <div class="tool-row">

        <span class="tool-label">
            Category
        </span>

        <div id="categoryFilters"></div>

    </div>


    <div class="tool-row">

        <span class="tool-label">
            Issue Type
        </span>

        <div id="ruleFilters"></div>

    </div>


    <div class="tool-row">

        <span class="tool-label">
            Sort
        </span>

        <select
            id="sortSelect"
            class="sort-select"
        >

            <option value="number">
                Issue number
            </option>

            <option value="priority-desc">
                Priority: Critical → Low
            </option>

            <option value="priority-asc">
                Priority: Low → Critical
            </option>

            <option value="category">
                Category A → Z
            </option>

            <option value="rule">
                Issue type A → Z
            </option>

            <option value="source">
                Source
            </option>

            <option value="unchecked-first">
                Unchecked first
            </option>

        </select>


        <button
            id="uncheckedOnlyButton"
            class="action-button"
            type="button"
        >
            ☐ Unchecked only
        </button>


        <button
            id="expandAllButton"
            class="action-button"
            type="button"
        >
            Expand visible
        </button>


        <button
            id="collapseAllButton"
            class="action-button"
            type="button"
        >
            Collapse all
        </button>


        <button
            id="printButton"
            class="action-button"
            type="button"
        >
            Print
        </button>


        <button
            id="resetFiltersButton"
            class="action-button"
            type="button"
        >
            Reset filters
        </button>


        <button
            id="clearReviewButton"
            class="action-button"
            type="button"
        >
            Clear review checks
        </button>

    </div>

</div>
"""
    )


    # ========================================================
    # RESULTS
    # ========================================================

    content.append(
        f"""
<div class="results-bar">

    <div>

        <span
            id="visibleCount"
            class="results-count"
        >
            {total}
        </span>

        of

        <span>
            {total}
        </span>

        findings shown

    </div>

    <div id="activeFilterText">
        Showing all findings
    </div>

</div>


<div
    id="emptyResults"
    class="empty-results"
>
    No findings match the selected filters.
</div>


<div id="findingsContainer">
"""
    )


    # ========================================================
    # FINDING CARDS
    # ========================================================

    for number, (_, row) in enumerate(
        recommendations.iterrows(),
        start=1
    ):

        unified_id = clean(
            row.get(
                "unified_id",
                f"UF-{number:05d}"
            )
        )

        status = clean(
            row.get(
                "finding_status",
                ""
            )
        )

        priority = clean(
            row.get(
                "priority",
                ""
            )
        )

        category = clean(
            row.get(
                "category",
                ""
            )
        )

        rule = clean(
            row.get(
                "primary_rule",
                ""
            )
        )

        finding_title = clean(
            row.get(
                "finding_title",
                ""
            )
        )

        custom_present = has_custom(
            row
        )

        axe_present = has_axe(
            row
        )

        source_text = source_label(
            row
        )

        selector = clean(
            row.get(
                "preferred_selector",
                ""
            )
        )

        affected_html = clean(
            row.get(
                "preferred_html",
                ""
            )
        )

        wcag = clean(
            row.get(
                "wcag",
                ""
            )
        )

        wcag_level = clean(
            row.get(
                "wcag_level",
                ""
            )
        )

        why = clean(
            row.get(
                "why_it_matters",
                ""
            )
        )

        recommendation = clean(
            row.get(
                "recommendation",
                ""
            )
        )

        suggested = clean(
            row.get(
                "suggested_html",
                ""
            )
        )

        failure_summary = clean(
            row.get(
                "failure_summary",
                ""
            )
        )

        manual_required = clean(
            row.get(
                "manual_review_required",
                ""
            )
        )

        manual_reason = clean(
            row.get(
                "manual_review_reason",
                ""
            )
        )

        ownership = clean(
            row.get(
                "ownership_scope",
                ""
            )
        )

        actionability = clean(
            row.get(
                "actionability",
                ""
            )
        )

        confidence = clean(
            row.get(
                "finding_confidence",
                ""
            )
        )

        custom_reason = clean(
            row.get(
                "custom_reason",
                ""
            )
        )

        axe_description = clean(
            row.get(
                "axe_description",
                ""
            )
        )

        help_url = clean(
            row.get(
                "help_url",
                ""
            )
        )


        # ====================================================
        # V3 CONTEXT-AWARE FIELDS
        # ====================================================

        contextual_processed = (
            clean(
                row.get(
                    "contextual_processed",
                    ""
                )
            ).lower()
            ==
            "true"
        )

        contextual_decision = clean(
            row.get(
                "contextual_decision_code",
                ""
            )
        )

        contextual_action = clean(
            row.get(
                "contextual_action",
                ""
            )
        )

        contextual_suggestion = clean(
            row.get(
                "contextual_suggestion",
                ""
            )
        )

        contextual_reason = clean(
            row.get(
                "contextual_reason",
                ""
            )
        )

        contextual_confidence = clean(
            row.get(
                "contextual_confidence",
                ""
            )
        )

        contextual_evidence = clean(
            row.get(
                "contextual_evidence_source",
                ""
            )
        )

        contextual_language = clean(
            row.get(
                "contextual_language",
                ""
            )
        )

        contextual_visual_review = clean(
            row.get(
                "contextual_visual_review_required",
                ""
            )
        )

        contextual_manual_review = clean(
            row.get(
                "contextual_manual_review_required",
                ""
            )
        )

        contextual_html = clean(
            row.get(
                "contextual_suggested_html",
                ""
            )
        )


        # ====================================================
        # LINK RECOMMENDATION ENGINE V4 FIELDS
        # ====================================================

        link_v4_processed = bool_value(
            row.get("link_v4_processed", False)
        )

        link_v4_issue_family = clean(
            row.get("link_v4_issue_family", "")
        )

        link_v4_decision = clean(
            row.get("link_v4_decision_code", "")
        )

        link_v4_current_text = clean(
            row.get("link_v4_current_text", "")
        )

        link_v4_current_name = clean(
            row.get("link_v4_current_accessible_name", "")
        )

        link_v4_href = clean(
            row.get("link_v4_href", "")
        )

        link_v4_suggested_name = clean(
            row.get("link_v4_suggested_name", "")
        )

        link_v4_action = clean(
            row.get("link_v4_recommended_action", "")
        )

        link_v4_confidence = clean(
            row.get("link_v4_confidence", "")
        )

        link_v4_evidence_source = clean(
            row.get("link_v4_evidence_source", "")
        )

        link_v4_evidence_text = clean(
            row.get("link_v4_evidence_text", "")
        )

        link_v4_reason = clean(
            row.get("link_v4_reason", "")
        )

        link_v4_html = clean(
            row.get("link_v4_suggested_html", "")
        )

        link_v4_manual_review = bool_value(
            row.get("link_v4_manual_review_required", False)
        )

        link_v4_semantics_review = bool_value(
            row.get("link_v4_semantics_review_required", False)
        )


        # ====================================================
        # VLM VISUAL ALT FIELDS
        # ====================================================

        vlm_processed = bool_value(
            row.get(
                "vlm_processed",
                False
            )
        )

        vlm_status = clean(
            row.get(
                "vlm_status",
                ""
            )
        )

        vlm_model = clean(
            row.get(
                "vlm_model",
                ""
            )
        )

        vlm_issue = clean(
            row.get(
                "vlm_issue",
                ""
            )
        )

        vlm_image_role = clean(
            row.get(
                "vlm_image_role",
                ""
            )
        )

        vlm_alt_status = clean(
            row.get(
                "vlm_alt_status",
                ""
            )
        )

        vlm_current_alt = clean(
            row.get(
                "vlm_current_alt",
                ""
            )
        )

        vlm_suggested_alt = clean(
            row.get(
                "vlm_suggested_alt",
                ""
            )
        )

        vlm_recommended_action = clean(
            row.get(
                "vlm_recommended_action",
                ""
            )
        )

        vlm_confidence = clean(
            row.get(
                "vlm_confidence",
                ""
            )
        )

        vlm_generic_alt = bool_value(
            row.get(
                "vlm_generic_alt_detected",
                False
            )
        )

        vlm_manual_review = bool_value(
            row.get(
                "vlm_manual_review_required",
                False
            )
        )

        vlm_visual_review = bool_value(
            row.get(
                "vlm_visual_review_required",
                False
            )
        )

        vlm_reason = clean(
            row.get(
                "vlm_reason",
                ""
            )
        )

        vlm_image_url = clean(
            row.get(
                "vlm_resolved_image_url",
                ""
            )
        )

        vlm_cache_hit = bool_value(
            row.get(
                "vlm_cache_hit",
                False
            )
        )

        vlm_guardrail_passed = bool_value(
            row.get(
                "vlm_guardrail_passed",
                False
            )
        )

        vlm_suggested_code = clean(
            row.get(
                "vlm_suggested_html",
                ""
            )
        )


        # ====================================================
        # SEARCHABLE TEXT
        # ====================================================

        search_text = " ".join(
            [
                unified_id,
                status,
                priority,
                category,
                rule,
                finding_title,
                source_text,
                selector,
                affected_html,
                wcag,
                why,
                recommendation,
                failure_summary,
                contextual_decision,
                contextual_action,
                contextual_suggestion,
                contextual_reason,
                contextual_evidence,
                contextual_language,
                link_v4_issue_family,
                link_v4_decision,
                link_v4_current_text,
                link_v4_current_name,
                link_v4_href,
                link_v4_suggested_name,
                link_v4_action,
                link_v4_confidence,
                link_v4_evidence_source,
                link_v4_evidence_text,
                link_v4_reason,
                vlm_status,
                vlm_model,
                vlm_issue,
                vlm_image_role,
                vlm_alt_status,
                vlm_current_alt,
                vlm_suggested_alt,
                vlm_recommended_action,
                vlm_confidence,
                vlm_reason
            ]
        )


        priority_class = (
            priority.lower()
            if priority
            else "review"
        )


        if status == "confirmed_by_both":

            source_badge_class = (
                "badge-both"
            )

        elif status == "custom_only":

            source_badge_class = (
                "badge-custom"
            )

        else:

            source_badge_class = (
                "badge-axe"
            )


        # ====================================================
        # CARD START
        # ====================================================

        content.append(
            f"""
<article
    class="finding"

    id="finding-{esc(unified_id)}"

    data-number="{number}"

    data-priority="{esc(priority)}"

    data-category="{esc(category)}"

    data-rule="{esc(rule)}"

    data-status="{esc(status)}"

    data-has-custom="{'true' if custom_present else 'false'}"

    data-has-axe="{'true' if axe_present else 'false'}"

    data-search="{esc(search_text.lower())}"
>
"""
        )


        # ====================================================
        # CARD HEADER
        # ====================================================

        content.append(
            f"""
<div class="finding-top">

    <div class="issue-number">
        #{number:03d}
    </div>


    <div class="finding-heading">

        <h2 class="finding-title">
            {esc(finding_title)}
        </h2>

        <div class="rule-name">

            {esc(rule)}

            &nbsp;•&nbsp;

            {esc(unified_id)}

        </div>

    </div>


    <label class="review-control">

        <input
            class="review-checkbox"
            type="checkbox"
            data-issue-id="{esc(unified_id)}"
        >

        Reviewed

    </label>

</div>
"""
        )


        # ====================================================
        # BADGES
        # ====================================================

        content.append(
            '<div class="badges">'
        )

        content.append(
            f"""
<span
    class="badge badge-{esc(priority_class)}"
>
    {esc(priority)}
</span>
"""
        )

        content.append(
            f"""
<span class="badge {source_badge_class}">
    {esc(source_text)}
</span>
"""
        )

        content.append(
            f"""
<span class="badge">
    {esc(category)}
</span>
"""
        )

        content.append(
            f"""
<span class="badge">
    WCAG {esc(wcag)}
</span>
"""
        )

        if wcag_level:

            content.append(
                f"""
<span class="badge">
    Level {esc(wcag_level)}
</span>
"""
            )


        if confidence:

            content.append(
                f"""
<span class="badge">
    {esc(confidence)}
</span>
"""
            )


        if contextual_processed:

            content.append(
                """
<span class="badge badge-contextual">
    Context-aware recommendation
</span>
"""
            )


        if link_v4_processed:

            content.append(
                """
<span class="badge badge-link-v4">
    Link recommendation V4
</span>
"""
            )


        if vlm_processed:

            content.append(
                """
<span class="badge badge-vlm">
    VLM visual analysis
</span>
"""
            )


        content.append(
            "</div>"
        )


        # ====================================================
        # DETAILS
        # ====================================================

        content.append(
            """
<details class="finding-details">

    <summary>
        View issue details and remediation
    </summary>

    <div class="finding-content">
"""
        )


        # ====================================================
        # WHY IT MATTERS
        # ====================================================

        if why:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Why this matters
    </h3>

    <p>
        {esc(why)}
    </p>

</div>
"""
            )


        # ====================================================
        # LOCATION
        # ====================================================

        location_parts = []

        if selector:

            location_parts.append(
                "DOM selector: "
                +
                selector
            )

        if ownership:

            location_parts.append(
                "Ownership: "
                +
                ownership
            )

        if actionability:

            location_parts.append(
                "Actionability: "
                +
                actionability
            )


        if location_parts:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Location
    </h3>

    <div class="location-box">
        {esc(" | ".join(location_parts))}
    </div>

</div>
"""
            )


        # ====================================================
        # AFFECTED HTML
        # ====================================================

        if affected_html:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Affected HTML
    </h3>

    <pre class="code-box">{esc(affected_html)}</pre>

</div>
"""
            )


        # ====================================================
        # AXE EVIDENCE
        # ====================================================

        if failure_summary:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        axe automated evidence
    </h3>

    <pre class="code-box">{esc(failure_summary)}</pre>

</div>
"""
            )


        # ====================================================
        # CUSTOM EVIDENCE
        # ====================================================

        if custom_reason:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Custom scanner evidence
    </h3>

    <p>
        {esc(custom_reason)}
    </p>

</div>
"""
            )


        # ====================================================
        # AXE DESCRIPTION
        # ====================================================

        if axe_description:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        axe description
    </h3>

    <p>
        {esc(axe_description)}
    </p>

</div>
"""
            )


        # ====================================================
        # STANDARD RECOMMENDATION
        # ====================================================

        if recommendation:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Recommended change
    </h3>

    <div class="recommendation-box">
        {esc(recommendation)}
    </div>

</div>
"""
            )


        # ====================================================
        # V3 CONTEXT-AWARE RECOMMENDATION
        # ====================================================

        if contextual_processed:

            content.append(
                """
<div class="detail-section">

    <h3>
        Context-Aware Recommendation
    </h3>

    <div class="contextual-box">
"""
            )


            if contextual_suggestion:

                content.append(
                    f"""
<div class="contextual-suggestion">
    {esc(contextual_suggestion)}
</div>
"""
                )


            if contextual_reason:

                content.append(
                    f"""
<p>

    <strong>
        Why this suggestion was made:
    </strong>

    {esc(contextual_reason)}

</p>
"""
                )


            content.append(
                '<div class="contextual-meta">'
            )


            if contextual_evidence:

                content.append(
                    f"""
<span>
    Evidence:
    {esc(
        contextual_evidence.replace(
            "_",
            " "
        )
    )}
</span>
"""
                )


            if contextual_confidence:

                content.append(
                    f"""
<span>
    Context confidence:
    {esc(contextual_confidence)}
</span>
"""
                )


            if contextual_language:

                content.append(
                    f"""
<span>
    Language:
    {esc(contextual_language)}
</span>
"""
                )


            if contextual_decision:

                content.append(
                    f"""
<span>
    Decision:
    {esc(contextual_decision)}
</span>
"""
                )


            content.append(
                "</div>"
            )


            if contextual_action:

                content.append(
                    f"""
<p style="margin-top: 14px;">

    <strong>
        Recommended action:
    </strong>

    {esc(
        contextual_action.replace(
            "_",
            " "
        )
    )}

</p>
"""
                )


            if (
                contextual_visual_review.lower()
                ==
                "true"
            ):

                content.append(
                    """
<div class="warning-box">

    <strong>
        Visual review required
    </strong>

    <br><br>

    The surrounding text provides contextual evidence,
    but the image itself must be inspected before final
    alternative text is written.

</div>
"""
                )


            if (
                contextual_manual_review.lower()
                ==
                "true"
            ):

                content.append(
                    """
<p style="margin-top: 14px;">

    <strong>
        Human verification:
    </strong>

    Required before implementation.

</p>
"""
                )


            content.append(
                """
<p style="margin-top: 14px;">

    <em>

        This recommendation was generated by the
        proposed deterministic contextual decision
        engine. Context confidence describes the
        strength of the extracted contextual evidence,
        not WCAG conformance certainty.

    </em>

</p>

</div>

</div>
"""
            )


            # ------------------------------------------------
            # V3 suggested HTML
            # ------------------------------------------------

            if contextual_html:

                content.append(
                    f"""
<div class="detail-section">

    <h3>
        Context-Aware Suggested HTML
    </h3>

    <pre class="code-box">{esc(contextual_html)}</pre>

</div>
"""
                )


        # ====================================================
        # LINK RECOMMENDATION ENGINE V4
        # ====================================================

        if link_v4_processed:

            content.append(
                """
<div class="detail-section">

    <h3>
        Context-Aware Link Recommendation
    </h3>

    <div class="link-v4-box">
"""
            )

            if link_v4_current_text:
                content.append(
                    f"""
<p>
    <strong>Current visible text:</strong>
    {esc(link_v4_current_text)}
</p>
"""
                )

            if link_v4_current_name:
                content.append(
                    f"""
<p style="margin-top: 10px;">
    <strong>Current accessible name evidence:</strong>
    {esc(link_v4_current_name)}
</p>
"""
                )

            if link_v4_href:
                content.append(
                    f"""
<p style="margin-top: 10px;">
    <strong>Destination / action:</strong>
    {esc(link_v4_href)}
</p>
"""
                )

            if link_v4_suggested_name:
                content.append(
                    f"""
<div class="link-v4-suggestion">

    Suggested accessible name:
    <br>

    “{esc(link_v4_suggested_name)}”

</div>
"""
                )
            else:
                content.append(
                    """
<div class="warning-box">

    <strong>
        No automatic link name proposed
    </strong>

    <br><br>

    The available destination and contextual evidence was
    not strong enough to generate a specific accessible
    name safely.

</div>
"""
                )

            if link_v4_action:
                content.append(
                    f"""
<p style="margin-top: 14px;">

    <strong>
        Recommended action:
    </strong>

    {esc(link_v4_action)}

</p>
"""
                )

            if link_v4_reason:
                content.append(
                    f"""
<p style="margin-top: 14px;">

    <strong>
        Why this suggestion was made:
    </strong>

    {esc(link_v4_reason)}

</p>
"""
                )

            content.append(
                '<div class="link-v4-meta">'
            )

            if link_v4_issue_family:
                content.append(
                    f"""
<span>
    Issue:
    {esc(link_v4_issue_family.replace("_", " "))}
</span>
"""
                )

            if link_v4_decision:
                content.append(
                    f"""
<span>
    Decision:
    {esc(link_v4_decision.replace("_", " "))}
</span>
"""
                )

            if link_v4_confidence:
                content.append(
                    f"""
<span>
    Context confidence:
    {esc(link_v4_confidence)}
</span>
"""
                )

            if link_v4_evidence_source:
                content.append(
                    f"""
<span>
    Evidence:
    {esc(link_v4_evidence_source.replace("_", " "))}
</span>
"""
                )

            content.append(
                "</div>"
            )

            if link_v4_evidence_text:
                content.append(
                    f"""
<p style="margin-top: 14px;">

    <strong>
        Evidence used:
    </strong>

    {esc(link_v4_evidence_text)}

</p>
"""
                )

            if link_v4_semantics_review:
                content.append(
                    """
<div class="warning-box">

    <strong>
        Element semantics also require review
    </strong>

    <br><br>

    This element may perform an interface action rather
    than navigation. Verify whether a semantic
    &lt;button&gt; would be more appropriate than a link.

</div>
"""
                )

            if link_v4_manual_review:
                content.append(
                    """
<p style="margin-top: 14px;">

    <strong>
        Human verification:
    </strong>

    Required before implementation.

</p>
"""
                )

            content.append(
                """
<p style="margin-top: 14px;">

    <em>

        This candidate was generated by deterministic
        destination and context rules. Confidence describes
        the strength of the available evidence and does not
        establish WCAG conformance.

    </em>

</p>

</div>

</div>
"""
            )

            if link_v4_html:
                content.append(
                    f"""
<div class="detail-section">

    <h3>
        Link V4 Suggested HTML
    </h3>

    <pre class="code-box">{esc(link_v4_html)}</pre>

</div>
"""
                )


        # ====================================================
        # VLM VISUAL ALT ANALYSIS
        # ====================================================

        if vlm_processed:

            if vlm_suggested_alt:

                vlm_display_alt = (
                    vlm_suggested_alt
                )

            elif vlm_alt_status in {
                "keep_empty",
                "set_empty_alt",
                "replace_with_empty_alt",
            }:

                vlm_display_alt = (
                    'alt=""'
                )

            else:

                vlm_display_alt = (
                    "No automatic alt text proposed."
                )

            if vlm_current_alt:

                vlm_display_current = (
                    vlm_current_alt
                )

            elif vlm_issue == "missing_alt":

                vlm_display_current = (
                    "[ALT ATTRIBUTE MISSING]"
                )

            elif vlm_issue == "empty_alt":

                vlm_display_current = (
                    'alt=""'
                )

            else:

                vlm_display_current = (
                    "[EMPTY]"
                )

            content.append(
                f"""
<div class="detail-section">

    <h3>
        AI Visual Analysis
    </h3>

    <div class="vlm-box">

        <p>
            <strong>
                Current alt:
            </strong>
            {esc(vlm_display_current)}
        </p>

        <p style="margin-top: 10px;">
            <strong>
                Image role:
            </strong>
            {esc(
                vlm_image_role
                or
                "unclear"
            )}
        </p>

        <div class="vlm-suggestion">

            <strong>
                Suggested alt / treatment:
            </strong>

            <br><br>

            {esc(vlm_display_alt)}

        </div>
"""
            )

            if vlm_recommended_action:

                content.append(
                    f"""
<p>
    <strong>
        Recommended action:
    </strong>

    {esc(vlm_recommended_action)}
</p>
"""
                )

            if vlm_reason:

                content.append(
                    f"""
<p style="margin-top: 12px;">

    <strong>
        Visual reasoning:
    </strong>

    {esc(vlm_reason)}

</p>
"""
                )

            content.append(
                '<div class="vlm-meta">'
            )

            if vlm_status:

                content.append(
                    f"""
<span>
    Status:
    {esc(vlm_status)}
</span>
"""
                )

            if vlm_model:

                content.append(
                    f"""
<span>
    Model:
    {esc(vlm_model)}
</span>
"""
                )

            if vlm_confidence:

                content.append(
                    f"""
<span>
    Confidence:
    {esc(vlm_confidence)}
</span>
"""
                )

            if vlm_alt_status:

                content.append(
                    f"""
<span>
    Alt decision:
    {esc(
        vlm_alt_status.replace(
            "_",
            " "
        )
    )}
</span>
"""
                )

            if vlm_generic_alt:

                content.append(
                    """
<span>
    Generic alt detected
</span>
"""
                )

            if vlm_cache_hit:

                content.append(
                    """
<span>
    Cached visual result
</span>
"""
                )

            if vlm_guardrail_passed:

                content.append(
                    """
<span>
    Guardrail validation passed
</span>
"""
                )

            content.append(
                "</div>"
            )

            if vlm_image_url:

                content.append(
                    f"""
<p class="vlm-image-link">

    <strong>
        Analyzed image:
    </strong>

    <a
        href="{esc(vlm_image_url)}"
        target="_blank"
        rel="noopener noreferrer"
    >
        Open image
    </a>

</p>
"""
                )

            if (
                vlm_visual_review
                or
                vlm_manual_review
            ):

                content.append(
                    """
<div class="warning-box">

    <strong>
        Human verification required
    </strong>

    <br><br>

    The visual interpretation and suggested alternative
    text are decision-support evidence. Verify the image
    purpose, page context, and final wording before
    implementation.

</div>
"""
                )

            content.append(
                """
<p class="vlm-note">

    <em>

        The VLM supplies visual-semantic evidence only.
        The proposed system applies deterministic
        accessibility guardrails after VLM inference.
        This output does not independently establish a
        WCAG failure or conformance decision.

    </em>

</p>

    </div>

</div>
"""
            )

            if vlm_suggested_code:

                content.append(
                    f"""
<div class="detail-section">

    <h3>
        VLM-Assisted Suggested HTML
    </h3>

    <pre class="code-box">{esc(vlm_suggested_code)}</pre>

    <p style="margin-top: 8px;">

        <em>
            Apply only after human verification.
        </em>

    </p>

</div>
"""
                )


        # ====================================================
        # STANDARD SUGGESTED HTML
        #
        # Do not show the generic placeholder code when a
        # more specific Link V4 or VLM code suggestion exists.
        # This avoids duplicate remediation blocks such as:
        #
        #   Link V4 Suggested HTML
        #   + Suggested code pattern
        #
        # or:
        #
        #   VLM-Assisted Suggested HTML
        #   + Suggested code pattern
        #
        # The generic code pattern remains available as a
        # fallback when V4/VLM cannot safely produce specific
        # code.
        # ====================================================

        specific_v4_code_available = bool(
            link_v4_processed
            and
            link_v4_html
        )

        specific_vlm_code_available = bool(
            vlm_processed
            and
            vlm_suggested_code
        )

        show_standard_suggested_code = (
            bool(suggested)
            and
            not specific_v4_code_available
            and
            not specific_vlm_code_available
        )

        if show_standard_suggested_code:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Suggested code pattern
    </h3>

    <pre class="code-box">{esc(suggested)}</pre>

    <p style="margin-top: 8px;">

        <em>

            Replace placeholder text with wording that
            correctly reflects the real page context.

        </em>

    </p>

</div>
"""
            )


        # ====================================================
        # MANUAL REVIEW
        # ====================================================

        if (
            manual_required
            or
            manual_reason
        ):

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Manual review
    </h3>

    <div class="manual-box">

        <strong>
            Required:
        </strong>

        {esc(manual_required)}

        <br><br>

        {esc(manual_reason)}

    </div>

</div>
"""
            )


        # ====================================================
        # THIRD PARTY
        # ====================================================

        if ownership == "third_party_embed":

            content.append(
                """
<div class="warning-box">

    <strong>
        Third-party content
    </strong>

    <br><br>

    This finding appears inside an embedded third-party
    document.

    The website owner may not directly control the
    internal markup.

    Review the embed configuration, integration,
    provider options, or whether a more accessible
    alternative is available.

</div>
"""
            )


        # ====================================================
        # HELP URL
        # ====================================================

        if help_url:

            content.append(
                f"""
<div class="detail-section">

    <h3>
        Reference
    </h3>

    <p>

        <a
            href="{esc(help_url)}"
            target="_blank"
            rel="noopener noreferrer"
        >
            Open axe rule documentation
        </a>

    </p>

</div>
"""
            )


        # ====================================================
        # CARD END
        # ====================================================

        content.append(
            """
    </div>

</details>

</article>
"""
        )


    # ========================================================
    # CLOSE FINDINGS
    # ========================================================

    content.append(
        """
</div>


<div class="footer-note">

    <strong>
        Methodology note:
    </strong>

    Automated accessibility testing can identify many
    important problems, but it cannot establish complete
    WCAG conformance.

    Context-dependent and incomplete findings require
    human review.

    Context-aware recommendations are produced by
    deterministic rules using extracted local page context
    and should be verified before implementation.

    VLM-assisted image recommendations use visual-semantic
    evidence from a local vision-language model, followed by
    deterministic accessibility guardrails. They remain
    human-review recommendations rather than automatic WCAG
    conformance decisions.

</div>
"""
    )


    # ========================================================
    # JAVASCRIPT
    # ========================================================

    content.append(
        """
<script>

(function () {

    "use strict";


    // ======================================================
    // ELEMENTS
    // ======================================================

    const container =
        document.getElementById(
            "findingsContainer"
        );

    const findings =
        Array.from(
            document.querySelectorAll(
                ".finding"
            )
        );

    const searchInput =
        document.getElementById(
            "searchInput"
        );

    const sortSelect =
        document.getElementById(
            "sortSelect"
        );

    const visibleCount =
        document.getElementById(
            "visibleCount"
        );

    const emptyResults =
        document.getElementById(
            "emptyResults"
        );

    const progressBar =
        document.getElementById(
            "progressBar"
        );

    const progressText =
        document.getElementById(
            "progressText"
        );

    const activeFilterText =
        document.getElementById(
            "activeFilterText"
        );


    // ======================================================
    // STATE
    // ======================================================

    const state = {

        priority:
            "all",

        source:
            "all",

        category:
            "all",

        rule:
            "all",

        search:
            "",

        uncheckedOnly:
            false
    };


    // ======================================================
    // LOCAL STORAGE
    // ======================================================

    const storagePrefix =
        "accessibility-review:"
        +
        window.location.pathname
        +
        ":";


    function loadReviewState() {

        findings.forEach(
            finding => {

                const checkbox =
                    finding.querySelector(
                        ".review-checkbox"
                    );

                if (!checkbox) {
                    return;
                }

                const id =
                    checkbox.dataset.issueId;

                const saved =
                    localStorage.getItem(
                        storagePrefix + id
                    );

                if (saved === "true") {

                    checkbox.checked =
                        true;

                    finding.classList.add(
                        "reviewed"
                    );
                }
            }
        );
    }


    function saveReviewState(
        checkbox,
        finding
    ) {

        const id =
            checkbox.dataset.issueId;

        localStorage.setItem(
            storagePrefix + id,
            checkbox.checked
                ? "true"
                : "false"
        );

        finding.classList.toggle(
            "reviewed",
            checkbox.checked
        );
    }


    // ======================================================
    // PROGRESS
    // ======================================================

    function updateProgress() {

        const reviewed =
            findings.filter(
                finding => {

                    const checkbox =
                        finding.querySelector(
                            ".review-checkbox"
                        );

                    return (
                        checkbox
                        &&
                        checkbox.checked
                    );
                }
            ).length;

        const total =
            findings.length;

        const percentage =
            total
                ?
                (
                    reviewed
                    /
                    total
                )
                *
                100
                :
                0;

        progressBar.style.width =
            percentage
            +
            "%";

        progressText.textContent =
            reviewed
            +
            " / "
            +
            total
            +
            " reviewed";
    }


    // ======================================================
    // DYNAMIC CATEGORY / RULE FILTERS
    // ======================================================

    function createDynamicFilters(
        containerId,
        attribute,
        stateKey
    ) {

        const filterContainer =
            document.getElementById(
                containerId
            );

        const values =
            Array.from(
                new Set(
                    findings.map(
                        finding =>
                            finding.dataset[
                                attribute
                            ]
                    )
                )
            )
            .filter(
                Boolean
            )
            .sort(
                (a, b) =>
                    a.localeCompare(
                        b
                    )
            );


        const allButton =
            document.createElement(
                "button"
            );

        allButton.type =
            "button";

        allButton.className =
            "filter-button active";

        allButton.dataset.filter =
            "all";

        allButton.textContent =
            "All";

        filterContainer.appendChild(
            allButton
        );


        values.forEach(
            value => {

                const button =
                    document.createElement(
                        "button"
                    );

                button.type =
                    "button";

                button.className =
                    "filter-button";

                button.dataset.filter =
                    value;

                button.textContent =
                    value;

                filterContainer.appendChild(
                    button
                );
            }
        );


        filterContainer.addEventListener(
            "click",
            event => {

                const button =
                    event.target.closest(
                        ".filter-button"
                    );

                if (!button) {
                    return;
                }


                filterContainer
                    .querySelectorAll(
                        ".filter-button"
                    )
                    .forEach(
                        item =>
                            item.classList.remove(
                                "active"
                            )
                    );


                button.classList.add(
                    "active"
                );


                state[
                    stateKey
                ] = (
                    button.dataset.filter
                );


                applyFilters();
            }
        );
    }


    createDynamicFilters(
        "categoryFilters",
        "category",
        "category"
    );


    createDynamicFilters(
        "ruleFilters",
        "rule",
        "rule"
    );


    // ======================================================
    // PRIORITY FILTER
    // ======================================================

    document
        .getElementById(
            "priorityFilters"
        )
        .addEventListener(
            "click",
            event => {

                const button =
                    event.target.closest(
                        ".filter-button"
                    );

                if (!button) {
                    return;
                }

                document
                    .querySelectorAll(
                        "#priorityFilters .filter-button"
                    )
                    .forEach(
                        item =>
                            item.classList.remove(
                                "active"
                            )
                    );

                button.classList.add(
                    "active"
                );

                state.priority =
                    button.dataset.filter;

                applyFilters();
            }
        );


    // ======================================================
    // SOURCE FILTER
    // ======================================================

    document
        .getElementById(
            "sourceFilters"
        )
        .addEventListener(
            "click",
            event => {

                const button =
                    event.target.closest(
                        ".filter-button"
                    );

                if (!button) {
                    return;
                }

                document
                    .querySelectorAll(
                        "#sourceFilters .filter-button"
                    )
                    .forEach(
                        item =>
                            item.classList.remove(
                                "active"
                            )
                    );

                button.classList.add(
                    "active"
                );

                state.source =
                    button.dataset.filter;

                applyFilters();
            }
        );


    // ======================================================
    // SOURCE MATCHING
    // ======================================================

    function matchesSource(
        finding
    ) {

        const source =
            state.source;

        if (source === "all") {
            return true;
        }

        const hasCustom =
            finding.dataset.hasCustom
            ===
            "true";

        const hasAxe =
            finding.dataset.hasAxe
            ===
            "true";

        const status =
            finding.dataset.status;


        if (source === "custom") {
            return hasCustom;
        }

        if (source === "axe") {
            return hasAxe;
        }

        if (source === "both") {

            return (
                hasCustom
                &&
                hasAxe
            );
        }

        if (source === "custom_only") {

            return (
                status
                ===
                "custom_only"
            );
        }

        if (source === "axe_only") {

            return (
                status
                ===
                "axe_only"
            );
        }

        if (
            source
            ===
            "axe_incomplete"
        ) {

            return (
                status
                ===
                "axe_incomplete"
            );
        }

        return true;
    }


    // ======================================================
    // FILTER
    // ======================================================

    function applyFilters() {

        let shown =
            0;


        findings.forEach(
            finding => {

                const checkbox =
                    finding.querySelector(
                        ".review-checkbox"
                    );


                const priorityMatch =
                    (
                        state.priority
                        ===
                        "all"
                    )
                    ||
                    (
                        finding.dataset.priority
                        ===
                        state.priority
                    );


                const categoryMatch =
                    (
                        state.category
                        ===
                        "all"
                    )
                    ||
                    (
                        finding.dataset.category
                        ===
                        state.category
                    );


                const ruleMatch =
                    (
                        state.rule
                        ===
                        "all"
                    )
                    ||
                    (
                        finding.dataset.rule
                        ===
                        state.rule
                    );


                const sourceMatch =
                    matchesSource(
                        finding
                    );


                const searchMatch =
                    (
                        !state.search
                    )
                    ||
                    (
                        finding.dataset.search
                        .includes(
                            state.search
                        )
                    );


                const uncheckedMatch =
                    (
                        !state.uncheckedOnly
                    )
                    ||
                    (
                        checkbox
                        &&
                        !checkbox.checked
                    );


                const show =
                    priorityMatch
                    &&
                    categoryMatch
                    &&
                    ruleMatch
                    &&
                    sourceMatch
                    &&
                    searchMatch
                    &&
                    uncheckedMatch;


                finding.style.display =
                    show
                        ?
                        ""
                        :
                        "none";


                if (show) {
                    shown++;
                }
            }
        );


        visibleCount.textContent =
            shown;


        emptyResults.style.display =
            shown === 0
                ?
                "block"
                :
                "none";


        updateActiveFilterText();

        sortFindings();
    }


    // ======================================================
    // ACTIVE FILTER TEXT
    // ======================================================

    function updateActiveFilterText() {

        const filters =
            [];


        if (
            state.priority
            !==
            "all"
        ) {

            filters.push(
                "Priority: "
                +
                state.priority
            );
        }


        if (
            state.source
            !==
            "all"
        ) {

            filters.push(
                "Source: "
                +
                state.source
            );
        }


        if (
            state.category
            !==
            "all"
        ) {

            filters.push(
                "Category: "
                +
                state.category
            );
        }


        if (
            state.rule
            !==
            "all"
        ) {

            filters.push(
                "Issue: "
                +
                state.rule
            );
        }


        if (
            state.uncheckedOnly
        ) {

            filters.push(
                "Unchecked only"
            );
        }


        if (
            state.search
        ) {

            filters.push(
                'Search: "'
                +
                state.search
                +
                '"'
            );
        }


        activeFilterText.textContent =
            filters.length
                ?
                filters.join(
                    " • "
                )
                :
                "Showing all findings";
    }


    // ======================================================
    // SEARCH
    // ======================================================

    searchInput.addEventListener(
        "input",
        () => {

            state.search =
                searchInput.value
                    .trim()
                    .toLowerCase();

            applyFilters();
        }
    );


    // ======================================================
    // PRIORITY RANK
    // ======================================================

    const priorityRank = {

        Critical: 5,

        High: 4,

        Medium: 3,

        Low: 2,

        Review: 1
    };


    // ======================================================
    // SORT
    // ======================================================

    function sortFindings() {

        const mode =
            sortSelect.value;


        const sorted =
            [...findings];


        sorted.sort(
            (a, b) => {

                if (
                    mode
                    ===
                    "priority-desc"
                ) {

                    return (
                        (
                            priorityRank[
                                b.dataset.priority
                            ]
                            ||
                            0
                        )
                        -
                        (
                            priorityRank[
                                a.dataset.priority
                            ]
                            ||
                            0
                        )
                    );
                }


                if (
                    mode
                    ===
                    "priority-asc"
                ) {

                    return (
                        (
                            priorityRank[
                                a.dataset.priority
                            ]
                            ||
                            0
                        )
                        -
                        (
                            priorityRank[
                                b.dataset.priority
                            ]
                            ||
                            0
                        )
                    );
                }


                if (
                    mode
                    ===
                    "category"
                ) {

                    return (
                        a.dataset.category
                        .localeCompare(
                            b.dataset.category
                        )
                    );
                }


                if (
                    mode
                    ===
                    "rule"
                ) {

                    return (
                        a.dataset.rule
                        .localeCompare(
                            b.dataset.rule
                        )
                    );
                }


                if (
                    mode
                    ===
                    "source"
                ) {

                    return (
                        a.dataset.status
                        .localeCompare(
                            b.dataset.status
                        )
                    );
                }


                if (
                    mode
                    ===
                    "unchecked-first"
                ) {

                    const aChecked =
                        a.querySelector(
                            ".review-checkbox"
                        ).checked
                            ?
                            1
                            :
                            0;

                    const bChecked =
                        b.querySelector(
                            ".review-checkbox"
                        ).checked
                            ?
                            1
                            :
                            0;


                    if (
                        aChecked
                        !==
                        bChecked
                    ) {

                        return (
                            aChecked
                            -
                            bChecked
                        );
                    }
                }


                return (
                    Number(
                        a.dataset.number
                    )
                    -
                    Number(
                        b.dataset.number
                    )
                );
            }
        );


        sorted.forEach(
            finding => {

                container.appendChild(
                    finding
                );
            }
        );
    }


    sortSelect.addEventListener(
        "change",
        sortFindings
    );


    // ======================================================
    // REVIEW CHECKBOX
    // ======================================================

    findings.forEach(
        finding => {

            const checkbox =
                finding.querySelector(
                    ".review-checkbox"
                );


            if (!checkbox) {
                return;
            }


            checkbox.addEventListener(
                "change",
                () => {

                    saveReviewState(
                        checkbox,
                        finding
                    );


                    updateProgress();


                    if (
                        state.uncheckedOnly
                    ) {

                        applyFilters();
                    }


                    if (
                        sortSelect.value
                        ===
                        "unchecked-first"
                    ) {

                        sortFindings();
                    }
                }
            );
        }
    );


    // ======================================================
    // UNCHECKED ONLY
    // ======================================================

    const uncheckedButton =
        document.getElementById(
            "uncheckedOnlyButton"
        );


    uncheckedButton.addEventListener(
        "click",
        () => {

            state.uncheckedOnly =
                !state.uncheckedOnly;


            uncheckedButton.classList.toggle(
                "active",
                state.uncheckedOnly
            );


            uncheckedButton.textContent =
                state.uncheckedOnly
                    ?
                    "☑ Unchecked only"
                    :
                    "☐ Unchecked only";


            applyFilters();
        }
    );


    // ======================================================
    // EXPAND
    // ======================================================

    document
        .getElementById(
            "expandAllButton"
        )
        .addEventListener(
            "click",
            () => {

                findings.forEach(
                    finding => {

                        if (
                            finding.style.display
                            ===
                            "none"
                        ) {

                            return;
                        }


                        const details =
                            finding.querySelector(
                                "details"
                            );


                        if (details) {

                            details.open =
                                true;
                        }
                    }
                );
            }
        );


    // ======================================================
    // COLLAPSE
    // ======================================================

    document
        .getElementById(
            "collapseAllButton"
        )
        .addEventListener(
            "click",
            () => {

                findings.forEach(
                    finding => {

                        const details =
                            finding.querySelector(
                                "details"
                            );


                        if (details) {

                            details.open =
                                false;
                        }
                    }
                );
            }
        );


    // ======================================================
    // PRINT
    // ======================================================

    document
        .getElementById(
            "printButton"
        )
        .addEventListener(
            "click",
            () => {

                window.print();
            }
        );


    // ======================================================
    // RESET FILTERS
    // ======================================================

    document
        .getElementById(
            "resetFiltersButton"
        )
        .addEventListener(
            "click",
            () => {

                state.priority =
                    "all";

                state.source =
                    "all";

                state.category =
                    "all";

                state.rule =
                    "all";

                state.search =
                    "";

                state.uncheckedOnly =
                    false;


                searchInput.value =
                    "";


                uncheckedButton.classList.remove(
                    "active"
                );


                uncheckedButton.textContent =
                    "☐ Unchecked only";


                document
                    .querySelectorAll(
                        ".filter-button"
                    )
                    .forEach(
                        button =>
                            button.classList.remove(
                                "active"
                            )
                    );


                document
                    .querySelectorAll(
                        '[data-filter="all"]'
                    )
                    .forEach(
                        button =>
                            button.classList.add(
                                "active"
                            )
                    );


                sortSelect.value =
                    "number";


                applyFilters();
            }
        );


    // ======================================================
    // CLEAR REVIEW CHECKS
    // ======================================================

    document
        .getElementById(
            "clearReviewButton"
        )
        .addEventListener(
            "click",
            () => {

                const confirmed =
                    window.confirm(
                        "Clear all reviewed checkmarks "
                        +
                        "for this report?"
                    );


                if (!confirmed) {
                    return;
                }


                findings.forEach(
                    finding => {

                        const checkbox =
                            finding.querySelector(
                                ".review-checkbox"
                            );


                        if (!checkbox) {
                            return;
                        }


                        checkbox.checked =
                            false;


                        finding.classList.remove(
                            "reviewed"
                        );


                        localStorage.removeItem(
                            storagePrefix
                            +
                            checkbox.dataset.issueId
                        );
                    }
                );


                updateProgress();

                applyFilters();
            }
        );


    // ======================================================
    // INITIALIZE
    // ======================================================

    loadReviewState();

    updateProgress();

    applyFilters();

})();

</script>
"""
    )


    # ========================================================
    # CLOSE PAGE
    # ========================================================

    content.append(
        """
</div>

</body>

</html>
"""
    )


    # ========================================================
    # SAVE REPORT
    # ========================================================

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(
                content
            )
        )


# ============================================================
# MAIN
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
            "python final_pipeline/src/"
            "recommendation_engine_v2.py "
            "<input_findings.csv>"
        )

        return


    input_file = (
        sys.argv[1]
    )


    if not os.path.exists(
        input_file
    ):

        print(
            "ERROR: File not found:"
        )

        print(
            input_file
        )

        return


    # ========================================================
    # LOAD
    # ========================================================

    df = pd.read_csv(
        input_file
    )


    print()
    print("=" * 80)
    print("RECOMMENDATION ENGINE V2")
    print("=" * 80)


    print(
        "Input:",
        input_file
    )


    print(
        "Unified findings:",
        len(df)
    )


    # ========================================================
    # GENERATE BASE RECOMMENDATIONS
    # ========================================================

    output_rows = []

    unknown_rules = set()


    for _, row in df.iterrows():

        rule = select_rule(
            row
        )


        knowledge = RULES.get(
            rule
        )


        # ====================================================
        # FALLBACK
        # ====================================================

        if knowledge is None:

            if rule:

                unknown_rules.add(
                    rule
                )


            knowledge = {

                "title":
                    (
                        clean(
                            row.get(
                                "axe_help",
                                ""
                            )
                        )
                        or
                        clean(
                            row.get(
                                "custom_issue",
                                ""
                            )
                        )
                        or
                        "Accessibility finding"
                    ),

                "category":
                    "Other",

                "wcag":
                    (
                        clean(
                            row.get(
                                "wcag_tags",
                                ""
                            )
                        )
                        or
                        "Review rule documentation"
                    ),

                "wcag_level":
                    "Review",

                "certainty":
                    "Automated finding",

                "why":
                    (
                        clean(
                            row.get(
                                "axe_description",
                                ""
                            )
                        )
                        or
                        clean(
                            row.get(
                                "custom_reason",
                                ""
                            )
                        )
                    ),

                "recommendation":
                    (
                        clean(
                            row.get(
                                "axe_help",
                                ""
                            )
                        )
                        or
                        (
                            "Review and correct "
                            "the affected element."
                        )
                    ),

                "manual_review":
                    "Yes",

                "review_reason":
                    (
                        "No dedicated remediation template "
                        "has yet been defined for this rule."
                    )
            }


        output = (
            row.to_dict()
        )


        output[
            "primary_rule"
        ] = rule


        output[
            "finding_title"
        ] = knowledge[
            "title"
        ]


        output[
            "category"
        ] = knowledge[
            "category"
        ]


        output[
            "wcag"
        ] = knowledge[
            "wcag"
        ]


        output[
            "wcag_level"
        ] = knowledge[
            "wcag_level"
        ]


        output[
            "recommendation_certainty"
        ] = knowledge[
            "certainty"
        ]


        output[
            "why_it_matters"
        ] = knowledge[
            "why"
        ]


        output[
            "recommendation"
        ] = knowledge[
            "recommendation"
        ]


        output[
            "manual_review_required"
        ] = knowledge[
            "manual_review"
        ]


        output[
            "manual_review_reason"
        ] = knowledge[
            "review_reason"
        ]


        output[
            "priority"
        ] = determine_priority(
            row
        )


        output[
            "suggested_html"
        ] = suggested_html(
            row,
            rule
        )


        output[
            "location_note"
        ] = location_note(
            row
        )


        output_rows.append(
            output
        )


    # ========================================================
    # DATAFRAME
    # ========================================================

    if output_rows:

        recommendations = pd.DataFrame(
            output_rows
        )

    else:

        recommendations = df.copy()


        extra_columns = [

            "primary_rule",

            "finding_title",

            "category",

            "wcag",

            "wcag_level",

            "recommendation_certainty",

            "why_it_matters",

            "recommendation",

            "manual_review_required",

            "manual_review_reason",

            "priority",

            "suggested_html",

            "location_note"
        ]


        for column in extra_columns:

            if (
                column
                not in recommendations.columns
            ):

                recommendations[
                    column
                ] = pd.Series(
                    dtype="object"
                )


    # ========================================================
    # VLM VISUAL-ALT ENRICHMENT
    # ========================================================

    base_name = derive_base_name(
        input_file
    )

    (
        recommendations,
        vlm_review_file,
        vlm_matched_count
    ) = enrich_recommendations_with_vlm(
        recommendations,
        base_name
    )

    if vlm_review_file:

        print()
        print(
            "VLM review input:"
        )
        print(
            vlm_review_file
        )
        print(
            "VLM findings matched to unified findings:",
            vlm_matched_count
        )

    else:

        print()
        print(
            "VLM review input: not available "
            "for this analysis."
        )


    # ========================================================
    # OUTPUT DIRECTORIES
    # ========================================================

    os.makedirs(
        CSV_OUTPUT_DIR,
        exist_ok=True
    )


    os.makedirs(
        HTML_OUTPUT_DIR,
        exist_ok=True
    )


    # ========================================================
    # OUTPUT BASENAME
    #
    # base_name was derived before VLM enrichment using the
    # same flexible single/double-underscore suffix handling.
    # ========================================================

    csv_output = os.path.join(
        CSV_OUTPUT_DIR,
        f"{base_name}__recommendations.csv"
    )


    html_output = os.path.join(
        HTML_OUTPUT_DIR,
        f"{base_name}__accessibility_report.html"
    )


    # ========================================================
    # SAVE CSV
    # ========================================================

    recommendations.to_csv(
        csv_output,
        index=False
    )


    # ========================================================
    # PAGE URL
    # ========================================================

    page_url = ""


    if len(
        recommendations
    ):

        page_url = clean(
            recommendations.iloc[
                0
            ].get(
                "page_url",
                ""
            )
        )


    # ========================================================
    # CREATE HTML
    # ========================================================

    create_html_report(
        recommendations,
        html_output,
        page_url
    )


    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("RECOMMENDATION SUMMARY")
    print("=" * 80)


    print()
    print(
        "Finding status:"
    )


    if (
        "finding_status"
        in recommendations.columns
        and
        len(
            recommendations
        )
    ):

        print(
            recommendations[
                "finding_status"
            ]
            .value_counts()
            .to_string()
        )

    else:

        print(
            "No findings."
        )


    print()
    print(
        "Priority:"
    )


    if (
        "priority"
        in recommendations.columns
        and
        len(
            recommendations
        )
    ):

        print(
            recommendations[
                "priority"
            ]
            .value_counts()
            .to_string()
        )

    else:

        print(
            "No findings."
        )


    print()
    print(
        "Categories:"
    )


    if (
        "category"
        in recommendations.columns
        and
        len(
            recommendations
        )
    ):

        print(
            recommendations[
                "category"
            ]
            .value_counts()
            .to_string()
        )

    else:

        print(
            "No findings."
        )


    print()
    print(
        "Top rules:"
    )


    if (
        "primary_rule"
        in recommendations.columns
        and
        len(
            recommendations
        )
    ):

        print(
            recommendations[
                "primary_rule"
            ]
            .value_counts()
            .head(
                20
            )
            .to_string()
        )

    else:

        print(
            "No findings."
        )


    # ========================================================
    # CONTEXTUAL SUMMARY
    # ========================================================

    if (
        "contextual_processed"
        in recommendations.columns
    ):

        contextual_count = sum(
            bool_value(
                value
            )
            for value
            in recommendations[
                "contextual_processed"
            ]
        )


        print()
        print(
            "Context-aware recommendations:",
            contextual_count
        )


    # ========================================================
    # VLM SUMMARY
    # ========================================================

    print()
    link_v4_count = 0

    if "link_v4_processed" in recommendations.columns:

        link_v4_count = int(
            recommendations[
                "link_v4_processed"
            ]
            .fillna(False)
            .astype(bool)
            .sum()
        )

    print()
    print(
        "Link V4 recommendations:",
        link_v4_count
    )


    print(
        "VLM-enhanced image findings:",
        vlm_matched_count
    )

    if (
        "vlm_status"
        in recommendations.columns
        and
        vlm_matched_count
    ):

        vlm_rows = recommendations[
            recommendations[
                "vlm_processed"
            ].apply(
                bool_value
            )
        ]

        if len(
            vlm_rows
        ):

            print()

            print(
                "VLM status:"
            )

            print(
                vlm_rows[
                    "vlm_status"
                ]
                .value_counts(
                    dropna=False
                )
                .to_string()
            )


    # ========================================================
    # THIRD-PARTY
    # ========================================================

    if (
        "ownership_scope"
        in recommendations.columns
    ):

        third_party_count = int(
            (
                recommendations[
                    "ownership_scope"
                ]
                ==
                "third_party_embed"
            )
            .sum()
        )

    else:

        third_party_count = 0


    print()
    print(
        "Third-party findings:",
        third_party_count
    )


    # ========================================================
    # FALLBACK
    # ========================================================

    if unknown_rules:

        print()
        print(
            "Rules using fallback recommendation:"
        )


        for rule in sorted(
            unknown_rules
        ):

            print(
                " -",
                rule
            )


    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("=" * 80)
    print("FILES CREATED")
    print("=" * 80)


    print(
        csv_output
    )


    print(
        html_output
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
