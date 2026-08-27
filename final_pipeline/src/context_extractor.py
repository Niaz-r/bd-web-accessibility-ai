import os
import re
import sys

from pathlib import Path
from urllib.parse import (
    urljoin,
    urlparse,
    urlsplit,
    urlunsplit
)

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

TARGET_RULES = {
    "generic_link_text",
    "empty_alt",
    "non_descriptive_alt"
}


OUTPUT_DIR = Path(
    "final_pipeline/data/intermediate/context_live"
)


HEADINGS = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6"
]


CONTEXT_TAGS = [
    "p",
    "li",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6"
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(
        value
    ).strip()


def normalize_space(value):

    return re.sub(
        r"\s+",
        " ",
        clean(value)
    ).strip()


def compact_text(
    value,
    max_length=600
):

    value = normalize_space(
        value
    )

    if len(value) > max_length:

        return (
            value[:max_length]
            + "..."
        )

    return value


def normalize_url(
    value,
    base_url=""
):

    value = clean(
        value
    )

    if not value:
        return ""

    if base_url:

        value = urljoin(
            base_url,
            value
        )

    try:

        parts = urlsplit(
            value
        )

        scheme = (
            parts.scheme.lower()
        )

        netloc = (
            parts.netloc.lower()
        )

        path = parts.path

        if (
            path
            and
            path != "/"
        ):

            path = path.rstrip(
                "/"
            )

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


def normalize_html(
    value
):

    value = clean(
        value
    )

    if not value:
        return ""

    try:

        soup = BeautifulSoup(
            value,
            "html.parser"
        )

        return normalize_space(
            str(
                soup
            )
        )

    except Exception:

        return normalize_space(
            value
        )


# ============================================================
# ELEMENT HELPERS
# ============================================================

def element_text(
    element
):

    if element is None:
        return ""

    try:

        return compact_text(
            element.get_text(
                " ",
                strip=True
            )
        )

    except Exception:

        return ""


def element_html(
    element
):

    if element is None:
        return ""

    return normalize_html(
        str(
            element
        )
    )


def element_src(
    element,
    page_url
):

    if element is None:
        return ""

    return normalize_url(
        element.get(
            "src",
            ""
        ),
        page_url
    )


def element_href(
    element,
    page_url
):

    if element is None:
        return ""

    return normalize_url(
        element.get(
            "href",
            ""
        ),
        page_url
    )


# ============================================================
# MATCHING
# ============================================================

def get_candidates(
    soup,
    row,
    page_url
):

    candidates = []

    custom_issue = clean(
        row.get(
            "custom_issue",
            ""
        )
    )

    row_src = normalize_url(
        row.get(
            "src",
            ""
        ),
        page_url
    )

    row_href = normalize_url(
        row.get(
            "href",
            ""
        ),
        page_url
    )

    # --------------------------------------------------------
    # IMAGE-BASED FINDINGS
    # --------------------------------------------------------

    if custom_issue in [
        "empty_alt",
        "non_descriptive_alt"
    ]:

        for image in soup.find_all(
            "img"
        ):

            current_src = (
                element_src(
                    image,
                    page_url
                )
            )

            if (
                row_src
                and
                current_src
                ==
                row_src
            ):

                candidates.append(
                    image
                )

    # --------------------------------------------------------
    # LINK-BASED FINDINGS
    # --------------------------------------------------------

    elif (
        custom_issue
        ==
        "generic_link_text"
    ):

        for link in soup.find_all(
            "a"
        ):

            current_href = (
                element_href(
                    link,
                    page_url
                )
            )

            if (
                row_href
                and
                current_href
                ==
                row_href
            ):

                candidates.append(
                    link
                )

    # --------------------------------------------------------
    # CUSTOM SELECTOR FALLBACK
    # --------------------------------------------------------

    selector = clean(
        row.get(
            "custom_selector",
            ""
        )
    )

    if selector:

        try:

            selected = soup.select_one(
                selector
            )

            if (
                selected is not None
                and
                selected not in candidates
            ):

                candidates.append(
                    selected
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # TAG FALLBACK
    # --------------------------------------------------------

    if not candidates:

        if custom_issue in [
            "empty_alt",
            "non_descriptive_alt"
        ]:

            candidates.extend(
                soup.find_all(
                    "img"
                )
            )

        elif (
            custom_issue
            ==
            "generic_link_text"
        ):

            candidates.extend(
                soup.find_all(
                    "a"
                )
            )

    return candidates


def score_candidate(
    candidate,
    row,
    page_url
):

    score = 0
    methods = []

    row_src = normalize_url(
        row.get(
            "src",
            ""
        ),
        page_url
    )

    candidate_src = (
        element_src(
            candidate,
            page_url
        )
    )

    if (
        row_src
        and
        candidate_src
        and
        row_src == candidate_src
    ):

        score += 100

        methods.append(
            "same_src"
        )

    # --------------------------------------------------------
    # HREF
    # --------------------------------------------------------

    row_href = normalize_url(
        row.get(
            "href",
            ""
        ),
        page_url
    )

    candidate_href = (
        element_href(
            candidate,
            page_url
        )
    )

    if (
        row_href
        and
        candidate_href
        and
        row_href == candidate_href
    ):

        score += 100

        methods.append(
            "same_href"
        )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    row_html = normalize_html(
        row.get(
            "custom_html",
            ""
        )
    )

    candidate_html = (
        element_html(
            candidate
        )
    )

    if (
        row_html
        and
        candidate_html
        and
        row_html == candidate_html
    ):

        score += 90

        methods.append(
            "same_html"
        )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    row_text = normalize_space(
        row.get(
            "text",
            ""
        )
    ).lower()

    candidate_text = (
        element_text(
            candidate
        ).lower()
    )

    if (
        row_text
        and
        candidate_text
        and
        row_text == candidate_text
    ):

        score += 40

        methods.append(
            "same_text"
        )

    # --------------------------------------------------------
    # ALT
    # --------------------------------------------------------

    row_alt = normalize_space(
        row.get(
            "alt",
            ""
        )
    ).lower()

    candidate_alt = normalize_space(
        candidate.get(
            "alt",
            ""
        )
    ).lower()

    if (
        row_alt
        and
        candidate_alt
        and
        row_alt == candidate_alt
    ):

        score += 40

        methods.append(
            "same_alt"
        )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    row_id = clean(
        row.get(
            "element_id",
            ""
        )
    )

    candidate_id = clean(
        candidate.get(
            "id",
            ""
        )
    )

    if (
        row_id
        and
        candidate_id
        and
        row_id == candidate_id
    ):

        score += 80

        methods.append(
            "same_id"
        )

    return (
        score,
        "+".join(
            methods
        )
    )


def find_best_element(
    soup,
    row,
    page_url
):

    candidates = get_candidates(
        soup,
        row,
        page_url
    )

    if not candidates:

        return (
            None,
            0,
            ""
        )

    best_element = None

    best_score = -1

    best_method = ""

    for candidate in candidates:

        score, method = (
            score_candidate(
                candidate,
                row,
                page_url
            )
        )

        if score > best_score:

            best_score = score

            best_element = candidate

            best_method = method

    return (
        best_element,
        best_score,
        best_method
    )


# ============================================================
# CONTEXT EXTRACTION
# ============================================================

def find_nearby_heading(
    element
):

    if element is None:

        return (
            "",
            ""
        )

    # --------------------------------------------------------
    # Element may itself be inside a heading.
    # --------------------------------------------------------

    parent_heading = (
        element.find_parent(
            HEADINGS
        )
    )

    if parent_heading:

        return (
            parent_heading.name,
            compact_text(
                parent_heading.get_text(
                    " ",
                    strip=True
                )
            )
        )

    # --------------------------------------------------------
    # Otherwise use nearest previous heading.
    # --------------------------------------------------------

    previous_heading = (
        element.find_previous(
            HEADINGS
        )
    )

    if previous_heading:

        return (
            previous_heading.name,
            compact_text(
                previous_heading.get_text(
                    " ",
                    strip=True
                )
            )
        )

    return (
        "",
        ""
    )


def find_parent_text(
    element
):

    if element is None:
        return ""

    current = element.parent

    depth = 0

    best_text = ""

    while (
        current is not None
        and
        depth < 4
    ):

        try:

            text = compact_text(
                current.get_text(
                    " ",
                    strip=True
                ),
                max_length=700
            )

        except Exception:

            text = ""

        if text:

            best_text = text

            # Prefer a useful local block rather than
            # an entire page wrapper.
            if (
                len(text) >= 20
                and
                len(text) <= 700
            ):

                return text

        current = current.parent

        depth += 1

    return best_text


def find_previous_context(
    element
):

    if element is None:
        return ""

    previous = element.find_previous(
        CONTEXT_TAGS
    )

    if previous:

        return compact_text(
            previous.get_text(
                " ",
                strip=True
            ),
            max_length=350
        )

    return ""


def find_next_context(
    element
):

    if element is None:
        return ""

    next_element = element.find_next(
        CONTEXT_TAGS
    )

    if next_element:

        # Avoid returning itself when the element is nested
        # inside the next matched block.
        if next_element is element:
            return ""

        return compact_text(
            next_element.get_text(
                " ",
                strip=True
            ),
            max_length=350
        )

    return ""


def find_figcaption(
    element
):

    if element is None:
        return ""

    figure = element.find_parent(
        "figure"
    )

    if figure:

        caption = figure.find(
            "figcaption"
        )

        if caption:

            return compact_text(
                caption.get_text(
                    " ",
                    strip=True
                ),
                max_length=350
            )

    return ""


def image_filename(
    src
):

    src = clean(
        src
    )

    if not src:
        return ""

    try:

        path = urlparse(
            src
        ).path

        return os.path.basename(
            path
        )

    except Exception:

        return ""


def build_surrounding_context(
    values
):

    parts = []

    seen = set()

    for label, value in values:

        value = compact_text(
            value,
            max_length=500
        )

        if not value:
            continue

        normalized = (
            value.lower()
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        parts.append(
            f"{label}: {value}"
        )

    return compact_text(
        " | ".join(
            parts
        ),
        max_length=1800
    )


def extract_context(
    element,
    row,
    page_url
):

    heading_level, heading_text = (
        find_nearby_heading(
            element
        )
    )

    parent_text = (
        find_parent_text(
            element
        )
    )

    previous_text = (
        find_previous_context(
            element
        )
    )

    next_text = (
        find_next_context(
            element
        )
    )

    figcaption = (
        find_figcaption(
            element
        )
    )

    current_text = (
        element_text(
            element
        )
    )

    src = clean(
        row.get(
            "src",
            ""
        )
    )

    filename = image_filename(
        src
    )

    surrounding = (
        build_surrounding_context(
            [
                (
                    "Nearby heading",
                    heading_text
                ),
                (
                    "Element text",
                    current_text
                ),
                (
                    "Figure caption",
                    figcaption
                ),
                (
                    "Parent text",
                    parent_text
                ),
                (
                    "Previous text",
                    previous_text
                ),
                (
                    "Next text",
                    next_text
                ),
                (
                    "Image filename",
                    filename
                )
            ]
        )
    )

    return {

        "nearby_heading_level":
            heading_level,

        "nearby_heading":
            heading_text,

        "parent_text":
            parent_text,

        "previous_text":
            previous_text,

        "next_text":
            next_text,

        "figcaption":
            figcaption,

        "image_filename":
            filename,

        "surrounding_context":
            surrounding
    }


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
            "context_extractor.py "
            "<unified_findings.csv>"
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

    if df.empty:

        print(
            "No findings available "
            "for context extraction."
        )

        return

    page_url = clean(
        df.iloc[0].get(
            "page_url",
            ""
        )
    )

    if not page_url:

        print(
            "ERROR: page_url missing "
            "from unified findings."
        )

        sys.exit(1)

    print()
    print("=" * 80)
    print("CONTEXT EXTRACTION")
    print("=" * 80)

    print(
        "Page:",
        page_url
    )

    print(
        "Unified findings:",
        len(df)
    )

    target_mask = (
        df[
            "custom_issue"
        ]
        .fillna("")
        .isin(
            TARGET_RULES
        )
    )

    print(
        "Context-dependent findings:",
        int(
            target_mask.sum()
        )
    )

    # ========================================================
    # FETCH PAGE
    # ========================================================

    try:

        response = requests.get(
            page_url,
            timeout=30,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "Chrome/145 Safari/537.36"
            }
        )

        if response.status_code >= 400:

            print(
                "ERROR: Context page returned:",
                response.status_code
            )

            sys.exit(1)

    except Exception as error:

        print(
            "ERROR: Could not retrieve page "
            "for context extraction:"
        )

        print(
            error
        )

        sys.exit(1)

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ========================================================
    # OUTPUT COLUMNS
    # ========================================================

    # ========================================================
    # OUTPUT COLUMNS
    #
    # Use explicit/object-friendly dtypes because these
    # columns contain different kinds of values:
    # bool, numbers, and strings.
    # ========================================================

    if "context_match_found" not in df.columns:

        df[
            "context_match_found"
        ] = pd.Series(
            [False] * len(df),
            dtype="bool"
        )


    if "context_match_score" not in df.columns:

        df[
            "context_match_score"
        ] = pd.Series(
            [0] * len(df),
            dtype="int64"
        )


    text_context_columns = [

        "context_match_method",

        "nearby_heading_level",

        "nearby_heading",

        "parent_text",

        "previous_text",

        "next_text",

        "figcaption",

        "image_filename",

        "surrounding_context"
    ]


    for column in text_context_columns:

        if column not in df.columns:

            df[
                column
            ] = pd.Series(
                [""] * len(df),
                dtype="object"
            )
    # ========================================================
    # EXTRACT TARGET CONTEXT
    # ========================================================

    matched = 0

    unmatched = 0

    for index, row in df.iterrows():

        custom_issue = clean(
            row.get(
                "custom_issue",
                ""
            )
        )

        if custom_issue not in TARGET_RULES:
            continue

        element, score, method = (
            find_best_element(
                soup,
                row,
                page_url
            )
        )

        if element is None:

            df.at[
                index,
                "context_match_found"
            ] = False

            df.at[
                index,
                "context_match_score"
            ] = 0

            unmatched += 1

            continue

        context = extract_context(
            element,
            row,
            page_url
        )

        df.at[
            index,
            "context_match_found"
        ] = True

        df.at[
            index,
            "context_match_score"
        ] = score

        df.at[
            index,
            "context_match_method"
        ] = method

        for key, value in (
            context.items()
        ):

            df.at[
                index,
                key
            ] = value

        matched += 1

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
            "_unified_findings.csv",
            ""
        )
    )

    output_file = (
        OUTPUT_DIR
        /
        (
            base_name
            +
            "_context_findings.csv"
        )
    )

    df.to_csv(
        output_file,
        index=False
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("CONTEXT SUMMARY")
    print("=" * 80)

    print(
        "Matched:",
        matched
    )

    print(
        "Unmatched:",
        unmatched
    )

    print()

    target_rows = df[
        target_mask
    ]

    display_columns = [
        "custom_issue",
        "text",
        "alt",
        "href",
        "src",
        "nearby_heading",
        "surrounding_context"
    ]

    existing_columns = [
        column
        for column in display_columns
        if column in target_rows.columns
    ]

    if len(
        target_rows
    ):

        print(
            target_rows[
                existing_columns
            ]
            .head(15)
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


if __name__ == "__main__":
    main()
