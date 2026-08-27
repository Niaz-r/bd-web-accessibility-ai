import os
import re
import sys
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# RULE MAPPING
#
# Only map rules that represent sufficiently similar checks.
# Do NOT force generic_link_text to axe link-name.
# ============================================================

RULE_MAPPING = {
    "missing_alt": "image-alt",
    "empty_link_text": "link-name",
    "empty_heading": "empty-heading",
    "heading_order": "heading-order",
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


def normalize_text(value):
    return normalize_space(
        value
    ).lower()


def normalize_url(value):
    value = clean(value)

    if not value:
        return ""

    try:
        parts = urlsplit(value)

        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()

        path = parts.path

        if path != "/":
            path = path.rstrip("/")

        return urlunsplit(
            (
                scheme,
                netloc,
                path,
                parts.query,
                ""
            )
        )

    except Exception:
        return value


def normalize_html(value):
    value = clean(value)

    if not value:
        return ""

    try:
        soup = BeautifulSoup(
            value,
            "html.parser"
        )

        return normalize_space(
            str(soup)
        )

    except Exception:
        return normalize_space(
            value
        )


def selector_similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================
# HTML METADATA
# ============================================================

def extract_html_metadata(html_value):

    result = {
        "tag": "",
        "id": "",
        "classes": "",
        "href": "",
        "src": "",
        "text": "",
        "alt": ""
    }

    html_value = clean(
        html_value
    )

    if not html_value:
        return result

    try:

        soup = BeautifulSoup(
            html_value,
            "html.parser"
        )

        element = soup.find()

        if element is None:
            return result

        result["tag"] = clean(
            element.name
        )

        result["id"] = clean(
            element.get(
                "id",
                ""
            )
        )

        classes = element.get(
            "class",
            []
        )

        result["classes"] = " ".join(
            str(x)
            for x in classes
        )

        # ----------------------------------------------------
        # Direct or descendant href
        # ----------------------------------------------------

        href = element.get(
            "href"
        )

        if not href:

            nested_link = element.find(
                "a",
                href=True
            )

            if nested_link:

                href = nested_link.get(
                    "href"
                )

        result["href"] = clean(
            href
        )

        # ----------------------------------------------------
        # Direct or descendant src
        # ----------------------------------------------------

        src = element.get(
            "src"
        )

        if not src:

            nested_source = element.find(
                [
                    "img",
                    "iframe",
                    "script"
                ],
                src=True
            )

            if nested_source:

                src = nested_source.get(
                    "src"
                )

        result["src"] = clean(
            src
        )

        result["alt"] = clean(
            element.get(
                "alt",
                ""
            )
        )

        result["text"] = normalize_space(
            element.get_text(
                " ",
                strip=True
            )
        )

    except Exception:
        pass

    return result


# ============================================================
# CUSTOM ROW METADATA
# ============================================================

def custom_metadata(row):

    html_meta = extract_html_metadata(
        row.get(
            "html_snippet",
            ""
        )
    )

    href = clean(
        row.get(
            "href",
            ""
        )
    )

    src = clean(
        row.get(
            "src",
            ""
        )
    )

    text = clean(
        row.get(
            "text",
            ""
        )
    )

    element_id = clean(
        row.get(
            "element_id",
            ""
        )
    )

    classes = clean(
        row.get(
            "element_classes",
            ""
        )
    )

    tag = clean(
        row.get(
            "tag",
            ""
        )
    )

    if not tag:
        tag = clean(
            row.get(
                "element",
                ""
            )
        )

    return {
        "tag":
            tag or html_meta["tag"],

        "id":
            element_id or html_meta["id"],

        "classes":
            classes or html_meta["classes"],

        "href":
            href or html_meta["href"],

        "src":
            src or html_meta["src"],

        "text":
            text or html_meta["text"],

        "alt":
            clean(
                row.get(
                    "alt",
                    ""
                )
            ) or html_meta["alt"]
    }


# ============================================================
# MATCH SCORE
# ============================================================

def calculate_match_score(
    custom_row,
    axe_row
):

    custom_issue = clean(
        custom_row.get(
            "issue",
            ""
        )
    )

    axe_rule = clean(
        axe_row.get(
            "rule_id",
            ""
        )
    )

    expected_axe_rule = (
        RULE_MAPPING.get(
            custom_issue
        )
    )

    # Rules must first be compatible.
    if expected_axe_rule != axe_rule:
        return 0, "incompatible_rule"

    custom_meta = custom_metadata(
        custom_row
    )

    axe_meta = extract_html_metadata(
        axe_row.get(
            "html",
            ""
        )
    )

    score = 0
    methods = []

    # --------------------------------------------------------
    # SRC — strongest for images / frames
    # --------------------------------------------------------

    custom_src = normalize_url(
        custom_meta["src"]
    )

    axe_src = normalize_url(
        axe_meta["src"]
    )

    if (
        custom_src
        and axe_src
        and custom_src == axe_src
    ):

        score += 100
        methods.append(
            "same_src"
        )

    # --------------------------------------------------------
    # HREF — strongest for links/headings containing links
    # --------------------------------------------------------

    custom_href = normalize_url(
        custom_meta["href"]
    )

    axe_href = normalize_url(
        axe_meta["href"]
    )

    if (
        custom_href
        and axe_href
        and custom_href == axe_href
    ):

        score += 100
        methods.append(
            "same_href"
        )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    if (
        custom_meta["id"]
        and axe_meta["id"]
        and
        normalize_text(
            custom_meta["id"]
        )
        ==
        normalize_text(
            axe_meta["id"]
        )
    ):

        score += 95
        methods.append(
            "same_id"
        )

    # --------------------------------------------------------
    # Normalized HTML
    # --------------------------------------------------------

    custom_html = normalize_html(
        custom_row.get(
            "html_snippet",
            ""
        )
    )

    axe_html = normalize_html(
        axe_row.get(
            "html",
            ""
        )
    )

    if (
        custom_html
        and axe_html
        and custom_html == axe_html
    ):

        score += 90
        methods.append(
            "same_html"
        )

    # --------------------------------------------------------
    # Element/tag
    # --------------------------------------------------------

    if (
        custom_meta["tag"]
        and axe_meta["tag"]
        and
        normalize_text(
            custom_meta["tag"]
        )
        ==
        normalize_text(
            axe_meta["tag"]
        )
    ):

        score += 10
        methods.append(
            "same_tag"
        )

    # --------------------------------------------------------
    # Visible text
    # --------------------------------------------------------

    custom_text = normalize_text(
        custom_meta["text"]
    )

    axe_text = normalize_text(
        axe_meta["text"]
    )

    if (
        custom_text
        and axe_text
        and custom_text == axe_text
    ):

        score += 30
        methods.append(
            "same_text"
        )

    # --------------------------------------------------------
    # Classes
    # --------------------------------------------------------

    custom_classes = set(
        normalize_text(
            custom_meta["classes"]
        ).split()
    )

    axe_classes = set(
        normalize_text(
            axe_meta["classes"]
        ).split()
    )

    if (
        custom_classes
        and axe_classes
        and custom_classes.intersection(
            axe_classes
        )
    ):

        score += 10
        methods.append(
            "class_overlap"
        )

    # --------------------------------------------------------
    # Selector similarity
    # --------------------------------------------------------

    similarity = selector_similarity(
        custom_row.get(
            "selector",
            ""
        ),
        axe_row.get(
            "selector",
            ""
        )
    )

    if similarity >= 0.90:

        score += 50
        methods.append(
            "selector_very_high"
        )

    elif similarity >= 0.75:

        score += 35
        methods.append(
            "selector_high"
        )

    elif similarity >= 0.55:

        score += 20
        methods.append(
            "selector_medium"
        )

    # --------------------------------------------------------
    # Empty-heading special support
    # --------------------------------------------------------

    if (
        custom_issue
        == "empty_heading"
        and
        custom_meta["tag"]
        == axe_meta["tag"]
        and
        not custom_text
        and
        not axe_text
    ):

        score += 15
        methods.append(
            "same_empty_heading_tag"
        )

    method = (
        "+".join(methods)
        if methods
        else "rule_only"
    )

    return score, method


# ============================================================
# OWNERSHIP / ACTIONABILITY
# ============================================================

def classify_ownership(
    axe_rule,
    axe_selector
):

    axe_rule = clean(
        axe_rule
    )

    selector = normalize_text(
        axe_selector
    )

    # frame-title belongs to the host page's iframe element.
    if axe_rule == "frame-title":

        return (
            "first_party_integration",
            "directly_fixable"
        )

    # Descendants inside an iframe are usually controlled
    # by the embedded third-party document.
    if "iframe" in selector:

        return (
            "third_party_embed",
            "third_party_controlled"
        )

    return (
        "page_content",
        "directly_reviewable"
    )


# ============================================================
# BUILD UNIFIED ROW
# ============================================================

def build_unified_row(
    unified_id,
    custom_row=None,
    axe_row=None,
    status="",
    match_score=0,
    match_method=""
):

    custom_exists = (
        custom_row is not None
    )

    axe_exists = (
        axe_row is not None
    )

    custom_issue = (
        clean(
            custom_row.get(
                "issue",
                ""
            )
        )
        if custom_exists
        else ""
    )

    axe_rule = (
        clean(
            axe_row.get(
                "rule_id",
                ""
            )
        )
        if axe_exists
        else ""
    )

    custom_selector = (
        clean(
            custom_row.get(
                "selector",
                ""
            )
        )
        if custom_exists
        else ""
    )

    axe_selector = (
        clean(
            axe_row.get(
                "selector",
                ""
            )
        )
        if axe_exists
        else ""
    )

    custom_html = (
        clean(
            custom_row.get(
                "html_snippet",
                ""
            )
        )
        if custom_exists
        else ""
    )

    axe_html = (
        clean(
            axe_row.get(
                "html",
                ""
            )
        )
        if axe_exists
        else ""
    )

    custom_meta = (
        custom_metadata(
            custom_row
        )
        if custom_exists
        else {
            "tag": "",
            "id": "",
            "classes": "",
            "href": "",
            "src": "",
            "text": "",
            "alt": ""
        }
    )

    axe_meta = (
        extract_html_metadata(
            axe_html
        )
        if axe_exists
        else {
            "tag": "",
            "id": "",
            "classes": "",
            "href": "",
            "src": "",
            "text": "",
            "alt": ""
        }
    )

    page_url = ""

    if custom_exists:

        page_url = clean(
            custom_row.get(
                "page_url",
                ""
            )
        )

    if not page_url and axe_exists:

        page_url = clean(
            axe_row.get(
                "page_url",
                ""
            )
        )

    # --------------------------------------------------------
    # Preferred location
    #
    # Prefer axe selector because it comes from rendered DOM.
    # --------------------------------------------------------

    preferred_selector = (
        axe_selector
        or custom_selector
    )

    preferred_html = (
        axe_html
        or custom_html
    )

    # --------------------------------------------------------
    # Preferred metadata
    # --------------------------------------------------------

    href = (
        custom_meta["href"]
        or axe_meta["href"]
    )

    src = (
        custom_meta["src"]
        or axe_meta["src"]
    )

    text = (
        custom_meta["text"]
        or axe_meta["text"]
    )

    alt = (
        custom_meta["alt"]
        or axe_meta["alt"]
    )

    tag = (
        axe_meta["tag"]
        or custom_meta["tag"]
    )

    element_id = (
        axe_meta["id"]
        or custom_meta["id"]
    )

    element_classes = (
        axe_meta["classes"]
        or custom_meta["classes"]
    )

    # --------------------------------------------------------
    # Ownership
    # --------------------------------------------------------

    if axe_exists:

        ownership_scope, actionability = (
            classify_ownership(
                axe_rule,
                axe_selector
            )
        )

    else:

        ownership_scope = (
            "page_content"
        )

        actionability = (
            "directly_reviewable"
        )

    # --------------------------------------------------------
    # Finding confidence
    # --------------------------------------------------------

    if status == "confirmed_by_both":

        finding_confidence = (
            "High - detected by both engines"
        )

    elif status == "axe_incomplete":

        finding_confidence = (
            "Manual review required"
        )

    elif status == "axe_only":

        finding_confidence = (
            "Axe automated finding"
        )

    else:

        if custom_issue in [
            "generic_link_text",
            "empty_alt",
            "heading_order",
            "missing_h1",
            "multiple_h1"
        ]:

            finding_confidence = (
                "Contextual/manual review"
            )

        else:

            finding_confidence = (
                "Custom automated finding"
            )

    return {

        "unified_id":
            unified_id,

        "page_url":
            page_url,

        # ----------------------------------------------------
        # Source information
        # ----------------------------------------------------

        "finding_status":
            status,

        "source_custom":
            custom_exists,

        "source_axe":
            axe_exists,

        "custom_issue":
            custom_issue,

        "axe_rule":
            axe_rule,

        "axe_result_type":
            (
                clean(
                    axe_row.get(
                        "result_type",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        # ----------------------------------------------------
        # Match information
        # ----------------------------------------------------

        "match_score":
            match_score,

        "match_method":
            match_method,

        "finding_confidence":
            finding_confidence,

        # ----------------------------------------------------
        # Classification
        # ----------------------------------------------------

        "custom_category":
            (
                clean(
                    custom_row.get(
                        "issue_category",
                        ""
                    )
                )
                if custom_exists
                else ""
            ),

        "custom_severity":
            (
                clean(
                    custom_row.get(
                        "severity",
                        ""
                    )
                )
                if custom_exists
                else ""
            ),

        "axe_impact":
            (
                clean(
                    axe_row.get(
                        "impact",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        "wcag_tags":
            (
                clean(
                    axe_row.get(
                        "wcag_tags",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        "custom_selector":
            custom_selector,

        "axe_selector":
            axe_selector,

        "preferred_selector":
            preferred_selector,

        "custom_html":
            custom_html,

        "axe_html":
            axe_html,

        "preferred_html":
            preferred_html,

        # ----------------------------------------------------
        # Element metadata
        # ----------------------------------------------------

        "element_tag":
            tag,

        "element_id":
            element_id,

        "element_classes":
            element_classes,

        "href":
            href,

        "src":
            src,

        "text":
            text,

        "alt":
            alt,

        "aria_label":
            (
                clean(
                    custom_row.get(
                        "aria_label",
                        ""
                    )
                )
                if custom_exists
                else ""
            ),

        "accessible_name":
            (
                clean(
                    custom_row.get(
                        "accessible_name",
                        ""
                    )
                )
                if custom_exists
                else ""
            ),

        # ----------------------------------------------------
        # Explanation
        # ----------------------------------------------------

        "custom_reason":
            (
                clean(
                    custom_row.get(
                        "reason",
                        ""
                    )
                )
                if custom_exists
                else ""
            ),

        "axe_description":
            (
                clean(
                    axe_row.get(
                        "description",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        "axe_help":
            (
                clean(
                    axe_row.get(
                        "help",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        "failure_summary":
            (
                clean(
                    axe_row.get(
                        "failure_summary",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        "help_url":
            (
                clean(
                    axe_row.get(
                        "help_url",
                        ""
                    )
                )
                if axe_exists
                else ""
            ),

        # ----------------------------------------------------
        # Ownership / fixability
        # ----------------------------------------------------

        "ownership_scope":
            ownership_scope,

        "actionability":
            actionability
    }


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) < 3:

        print()
        print(
            "Usage:"
        )

        print(
            "python final_pipeline/src/merge_findings.py "
            "<custom_csv> <axe_csv>"
        )

        return

    custom_file = (
        sys.argv[1]
    )

    axe_file = (
        sys.argv[2]
    )

    if not os.path.exists(
        custom_file
    ):

        print(
            "ERROR: Custom file not found:",
            custom_file
        )

        return

    if not os.path.exists(
        axe_file
    ):

        print(
            "ERROR: Axe file not found:",
            axe_file
        )

        return

    custom = pd.read_csv(
        custom_file
    )

    axe = pd.read_csv(
        axe_file
    )

    print()
    print("=" * 80)
    print("FINDING FUSION")
    print("=" * 80)

    print(
        "Custom findings:",
        len(custom)
    )

    print(
        "Axe nodes:",
        len(axe)
    )

    print()

    print(
        "Axe result types:"
    )

    print(
        axe[
            "result_type"
        ]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # SPLIT AXE
    # ========================================================

    axe_violations = axe[
        axe[
            "result_type"
        ]
        .astype(str)
        .str.lower()
        == "violation"
    ].copy()

    axe_incomplete = axe[
        axe[
            "result_type"
        ]
        .astype(str)
        .str.lower()
        == "incomplete"
    ].copy()

    # ========================================================
    # GREEDY MATCHING
    #
    # Each custom finding can match at most one axe violation.
    # Each axe violation node can match at most one custom row.
    # ========================================================

    candidates = []

    for custom_index, custom_row in (
        custom.iterrows()
    ):

        custom_issue = clean(
            custom_row.get(
                "issue",
                ""
            )
        )

        expected_rule = (
            RULE_MAPPING.get(
                custom_issue
            )
        )

        if not expected_rule:
            continue

        possible_axe = (
            axe_violations[
                axe_violations[
                    "rule_id"
                ] == expected_rule
            ]
        )

        for axe_index, axe_row in (
            possible_axe.iterrows()
        ):

            score, method = (
                calculate_match_score(
                    custom_row,
                    axe_row
                )
            )

            # Require actual element evidence,
            # not merely compatible rule names.
            if score >= 50:

                candidates.append(
                    {
                        "custom_index":
                            custom_index,

                        "axe_index":
                            axe_index,

                        "score":
                            score,

                        "method":
                            method
                    }
                )

    candidates = sorted(
        candidates,
        key=lambda x: x[
            "score"
        ],
        reverse=True
    )

    used_custom = set()
    used_axe = set()

    matches = []

    for candidate in candidates:

        custom_index = (
            candidate[
                "custom_index"
            ]
        )

        axe_index = (
            candidate[
                "axe_index"
            ]
        )

        if (
            custom_index
            in used_custom
        ):
            continue

        if (
            axe_index
            in used_axe
        ):
            continue

        used_custom.add(
            custom_index
        )

        used_axe.add(
            axe_index
        )

        matches.append(
            candidate
        )

    # ========================================================
    # BUILD UNIFIED DATASET
    # ========================================================

    unified_rows = []

    counter = 1

    # --------------------------------------------------------
    # Confirmed by both
    # --------------------------------------------------------

    for match in matches:

        custom_row = custom.loc[
            match[
                "custom_index"
            ]
        ]

        axe_row = axe_violations.loc[
            match[
                "axe_index"
            ]
        ]

        unified_rows.append(
            build_unified_row(
                unified_id=(
                    f"UF-{counter:05d}"
                ),

                custom_row=
                    custom_row,

                axe_row=
                    axe_row,

                status=
                    "confirmed_by_both",

                match_score=
                    match[
                        "score"
                    ],

                match_method=
                    match[
                        "method"
                    ]
            )
        )

        counter += 1

    # --------------------------------------------------------
    # Custom-only
    # --------------------------------------------------------

    for custom_index, custom_row in (
        custom.iterrows()
    ):

        if (
            custom_index
            in used_custom
        ):
            continue

        unified_rows.append(
            build_unified_row(
                unified_id=(
                    f"UF-{counter:05d}"
                ),

                custom_row=
                    custom_row,

                axe_row=
                    None,

                status=
                    "custom_only",

                match_score=
                    0,

                match_method=
                    ""
            )
        )

        counter += 1

    # --------------------------------------------------------
    # Axe-only violations
    # --------------------------------------------------------

    for axe_index, axe_row in (
        axe_violations.iterrows()
    ):

        if (
            axe_index
            in used_axe
        ):
            continue

        unified_rows.append(
            build_unified_row(
                unified_id=(
                    f"UF-{counter:05d}"
                ),

                custom_row=
                    None,

                axe_row=
                    axe_row,

                status=
                    "axe_only",

                match_score=
                    0,

                match_method=
                    ""
            )
        )

        counter += 1

    # --------------------------------------------------------
    # Axe incomplete
    # --------------------------------------------------------

    for _, axe_row in (
        axe_incomplete.iterrows()
    ):

        unified_rows.append(
            build_unified_row(
                unified_id=(
                    f"UF-{counter:05d}"
                ),

                custom_row=
                    None,

                axe_row=
                    axe_row,

                status=
                    "axe_incomplete",

                match_score=
                    0,

                match_method=
                    ""
            )
        )

        counter += 1

    unified = pd.DataFrame(
        unified_rows
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_dir = (
        "final_pipeline/data/intermediate/"
        "unified_live"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    custom_name = os.path.basename(
        custom_file
    )

    base_name = custom_name.replace(
        "_custom_findings.csv",
        ""
    )

    output_file = os.path.join(
        output_dir,
        f"{base_name}_unified_findings.csv"
    )

    unified.to_csv(
        output_file,
        index=False
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("FUSION RESULTS")
    print("=" * 80)

    print(
        "Compatible candidate pairs:",
        len(candidates)
    )

    print(
        "Confirmed matches:",
        len(matches)
    )

    print()

    print(
        "Unified finding statuses:"
    )

    print(
        unified[
            "finding_status"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "Confirmed rule pairs:"
    )

    confirmed = unified[
        unified[
            "finding_status"
        ] == "confirmed_by_both"
    ]

    if len(confirmed):

        print(
            confirmed.groupby(
                [
                    "custom_issue",
                    "axe_rule"
                ]
            )
            .size()
            .to_string()
        )

    else:

        print(
            "No confirmed matches."
        )

    print()
    print(
        "Ownership scope:"
    )

    print(
        unified[
            "ownership_scope"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("=" * 80)
    print("SAMPLE CONFIRMED FINDINGS")
    print("=" * 80)

    if len(confirmed):

        print(
            confirmed[
                [
                    "custom_issue",
                    "axe_rule",
                    "match_score",
                    "match_method",
                    "preferred_selector",
                    "src",
                    "href"
                ]
            ]
            .head(20)
            .to_string(
                index=False
            )
        )

    print()
    print(
        "Output:",
        output_file
    )


if __name__ == "__main__":
    main()
