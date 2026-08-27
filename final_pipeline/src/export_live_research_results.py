import sys
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

SRC_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

FINAL_PIPELINE_DIR = (
    SRC_DIR.parent
)


# ============================================================
# INPUT DIRECTORIES
# ============================================================

UNIFIED_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "intermediate"
    /
    "unified_live"
)

CONTEXTUAL_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "final"
    /
    "contextual_recommendations"
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = (
    FINAL_PIPELINE_DIR
    /
    "reports"
    /
    "research_live"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(
        value
    ).strip()


def bool_value(value):

    if isinstance(
        value,
        bool
    ):
        return value

    return (
        clean(value).lower()
        in {
            "true",
            "1",
            "yes"
        }
    )


def safe_percent(
    numerator,
    denominator
):

    if not denominator:
        return 0.0

    return round(
        (
            numerator
            /
            denominator
        )
        *
        100,
        2
    )


def get_page_url(df):

    if (
        df.empty
        or
        "page_url"
        not in df.columns
    ):

        return ""

    return clean(
        df.iloc[0].get(
            "page_url",
            ""
        )
    )


def get_analysis_id(
    file_path,
    suffix
):

    name = (
        Path(
            file_path
        ).name
    )

    if name.endswith(
        suffix
    ):

        return name[
            :-len(
                suffix
            )
        ]

    return (
        Path(
            file_path
        ).stem
    )


def status_count(
    df,
    status
):

    if (
        df.empty
        or
        "finding_status"
        not in df.columns
    ):

        return 0

    return int(
        (
            df[
                "finding_status"
            ]
            .fillna("")
            ==
            status
        )
        .sum()
    )


def count_true(
    df,
    column
):

    if (
        df.empty
        or
        column
        not in df.columns
    ):

        return 0

    return int(
        df[
            column
        ]
        .apply(
            bool_value
        )
        .sum()
    )


def write_csv(
    dataframe,
    filename
):

    path = (
        OUTPUT_DIR
        /
        filename
    )

    dataframe.to_csv(
        path,
        index=False
    )

    print(
        path
    )

    return path


# ============================================================
# LOAD UNIFIED LIVE DATA
# ============================================================

def load_unified_files():

    files = sorted(
        UNIFIED_DIR.glob(
            "*__unified_findings.csv"
        )
    )

    records = []

    dataframes = []

    for file_path in files:

        try:

            df = pd.read_csv(
                file_path
            )

        except Exception as error:

            print()
            print(
                "WARNING:"
            )

            print(
                "Could not read:"
            )

            print(
                file_path
            )

            print(
                error
            )

            continue

        analysis_id = get_analysis_id(
            file_path,
            "__unified_findings.csv"
        )

        page_url = get_page_url(
            df
        )

        # ----------------------------------------------------
        # STATUS COUNTS
        # ----------------------------------------------------

        confirmed = status_count(
            df,
            "confirmed_by_both"
        )

        custom_only = status_count(
            df,
            "custom_only"
        )

        axe_only = status_count(
            df,
            "axe_only"
        )

        axe_incomplete = status_count(
            df,
            "axe_incomplete"
        )

        total = len(
            df
        )

        # ----------------------------------------------------
        # SOURCE INVOLVEMENT
        # ----------------------------------------------------

        custom_involved = count_true(
            df,
            "source_custom"
        )

        axe_involved = count_true(
            df,
            "source_axe"
        )

        # axe violation findings exclude incomplete findings.
        axe_violation_elements = (
            confirmed
            +
            axe_only
        )

        unique_violation_elements = (
            confirmed
            +
            custom_only
            +
            axe_only
        )

        # ----------------------------------------------------
        # OWNERSHIP
        # ----------------------------------------------------

        page_content = 0

        third_party = 0

        first_party_integration = 0

        if (
            "ownership_scope"
            in df.columns
        ):

            ownership = (
                df[
                    "ownership_scope"
                ]
                .fillna("")
            )

            page_content = int(
                (
                    ownership
                    ==
                    "page_content"
                )
                .sum()
            )

            third_party = int(
                (
                    ownership
                    ==
                    "third_party_embed"
                )
                .sum()
            )

            first_party_integration = int(
                (
                    ownership
                    ==
                    "first_party_integration"
                )
                .sum()
            )

        # ----------------------------------------------------
        # ACTIONABILITY
        # ----------------------------------------------------

        directly_fixable = 0

        directly_reviewable = 0

        review_integration = 0

        third_party_controlled = 0

        if (
            "actionability"
            in df.columns
        ):

            actionability = (
                df[
                    "actionability"
                ]
                .fillna("")
            )

            directly_fixable = int(
                (
                    actionability
                    ==
                    "directly_fixable"
                )
                .sum()
            )

            directly_reviewable = int(
                (
                    actionability
                    ==
                    "directly_reviewable"
                )
                .sum()
            )

            review_integration = int(
                (
                    actionability
                    ==
                    "review_integration"
                )
                .sum()
            )

            third_party_controlled = int(
                (
                    actionability
                    ==
                    "third_party_controlled"
                )
                .sum()
            )

        # ----------------------------------------------------
        # PAGE SUMMARY
        # ----------------------------------------------------

        records.append(
            {
                "analysis_id":
                    analysis_id,

                "page_url":
                    page_url,

                "total_unified_findings":
                    total,

                "confirmed_by_both":
                    confirmed,

                "custom_only":
                    custom_only,

                "axe_only":
                    axe_only,

                "axe_incomplete":
                    axe_incomplete,

                "custom_involved":
                    custom_involved,

                "axe_involved":
                    axe_involved,

                "axe_violation_elements":
                    axe_violation_elements,

                "unique_violation_elements":
                    unique_violation_elements,

                "confirmed_share_of_custom_pct":
                    safe_percent(
                        confirmed,
                        custom_involved
                    ),

                "confirmed_share_of_axe_violations_pct":
                    safe_percent(
                        confirmed,
                        axe_violation_elements
                    ),

                "overlap_share_of_unique_violations_pct":
                    safe_percent(
                        confirmed,
                        unique_violation_elements
                    ),

                "page_content_findings":
                    page_content,

                "third_party_embed_findings":
                    third_party,

                "first_party_integration_findings":
                    first_party_integration,

                "directly_fixable":
                    directly_fixable,

                "directly_reviewable":
                    directly_reviewable,

                "review_integration":
                    review_integration,

                "third_party_controlled":
                    third_party_controlled
            }
        )

        current = (
            df.copy()
        )

        current[
            "analysis_id"
        ] = (
            analysis_id
        )

        current[
            "source_file"
        ] = (
            file_path.name
        )

        dataframes.append(
            current
        )

    page_summary = pd.DataFrame(
        records
    )

    if dataframes:

        all_findings = pd.concat(
            dataframes,
            ignore_index=True,
            sort=False
        )

    else:

        all_findings = (
            pd.DataFrame()
        )

    return (
        files,
        page_summary,
        all_findings
    )


# ============================================================
# FUSION STATUS SUMMARY
# ============================================================

def build_fusion_summary(
    all_findings
):

    statuses = [

        "confirmed_by_both",

        "custom_only",

        "axe_only",

        "axe_incomplete"
    ]

    rows = []

    total = len(
        all_findings
    )

    for status in statuses:

        count = status_count(
            all_findings,
            status
        )

        rows.append(
            {
                "finding_status":
                    status,

                "count":
                    count,

                "percent_of_all_unified_findings":
                    safe_percent(
                        count,
                        total
                    )
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# RULE/SOURCE SUMMARY
# ============================================================

def build_rule_summary(
    all_findings
):

    if all_findings.empty:

        return pd.DataFrame(
            columns=[
                "rule",
                "source",
                "finding_status",
                "count"
            ]
        )

    rows = []

    for _, row in all_findings.iterrows():

        status = clean(
            row.get(
                "finding_status",
                ""
            )
        )

        custom_rule = clean(
            row.get(
                "custom_issue",
                ""
            )
        )

        axe_rule = clean(
            row.get(
                "axe_rule",
                ""
            )
        )

        if custom_rule:

            rows.append(
                {
                    "rule":
                        custom_rule,

                    "source":
                        "custom",

                    "finding_status":
                        status
                }
            )

        if axe_rule:

            rows.append(
                {
                    "rule":
                        axe_rule,

                    "source":
                        "axe",

                    "finding_status":
                        status
                }
            )

    if not rows:

        return pd.DataFrame(
            columns=[
                "rule",
                "source",
                "finding_status",
                "count"
            ]
        )

    detail = pd.DataFrame(
        rows
    )

    summary = (
        detail
        .groupby(
            [
                "rule",
                "source",
                "finding_status"
            ],
            dropna=False
        )
        .size()
        .reset_index(
            name="count"
        )
        .sort_values(
            [
                "count",
                "source",
                "rule"
            ],
            ascending=[
                False,
                True,
                True
            ]
        )
    )

    return summary


# ============================================================
# OWNERSHIP SUMMARY
# ============================================================

def build_ownership_summary(
    all_findings
):

    if (
        all_findings.empty
        or
        "ownership_scope"
        not in all_findings.columns
    ):

        return pd.DataFrame(
            columns=[
                "ownership_scope",
                "count",
                "percent"
            ]
        )

    series = (
        all_findings[
            "ownership_scope"
        ]
        .fillna("")
        .replace(
            "",
            "unknown"
        )
    )

    result = (
        series
        .value_counts()
        .rename_axis(
            "ownership_scope"
        )
        .reset_index(
            name="count"
        )
    )

    total = int(
        result[
            "count"
        ]
        .sum()
    )

    result[
        "percent"
    ] = (
        result[
            "count"
        ]
        .apply(
            lambda value:
                safe_percent(
                    value,
                    total
                )
        )
    )

    return result


# ============================================================
# ACTIONABILITY SUMMARY
# ============================================================

def build_actionability_summary(
    all_findings
):

    if (
        all_findings.empty
        or
        "actionability"
        not in all_findings.columns
    ):

        return pd.DataFrame(
            columns=[
                "actionability",
                "count",
                "percent"
            ]
        )

    series = (
        all_findings[
            "actionability"
        ]
        .fillna("")
        .replace(
            "",
            "unknown"
        )
    )

    result = (
        series
        .value_counts()
        .rename_axis(
            "actionability"
        )
        .reset_index(
            name="count"
        )
    )

    total = int(
        result[
            "count"
        ]
        .sum()
    )

    result[
        "percent"
    ] = (
        result[
            "count"
        ]
        .apply(
            lambda value:
                safe_percent(
                    value,
                    total
                )
        )
    )

    return result


# ============================================================
# LOAD CONTEXTUAL FILES
# ============================================================

def load_contextual_files():

    files = sorted(
        CONTEXTUAL_DIR.glob(
            "*__contextual_recommendations.csv"
        )
    )

    dataframes = []

    for file_path in files:

        try:

            df = pd.read_csv(
                file_path
            )

        except Exception as error:

            print()
            print(
                "WARNING:"
            )

            print(
                "Could not read:"
            )

            print(
                file_path
            )

            print(
                error
            )

            continue

        analysis_id = get_analysis_id(
            file_path,
            "__contextual_recommendations.csv"
        )

        df[
            "analysis_id"
        ] = analysis_id

        df[
            "source_file"
        ] = file_path.name

        dataframes.append(
            df
        )

    if dataframes:

        combined = pd.concat(
            dataframes,
            ignore_index=True,
            sort=False
        )

    else:

        combined = (
            pd.DataFrame()
        )

    return (
        files,
        combined
    )


# ============================================================
# CONTEXTUAL PROCESSED DATA
# ============================================================

def contextual_processed_rows(
    contextual
):

    if (
        contextual.empty
        or
        "contextual_processed"
        not in contextual.columns
    ):

        return pd.DataFrame()

    mask = (
        contextual[
            "contextual_processed"
        ]
        .apply(
            bool_value
        )
    )

    return contextual[
        mask
    ].copy()


# ============================================================
# CONTEXTUAL RULE SUMMARY
# ============================================================

def build_contextual_rule_summary(
    contextual
):

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    if (
        processed.empty
        or
        "custom_issue"
        not in processed.columns
    ):

        return pd.DataFrame(
            columns=[
                "custom_issue",
                "count",
                "percent"
            ]
        )

    result = (
        processed[
            "custom_issue"
        ]
        .fillna("")
        .replace(
            "",
            "unknown"
        )
        .value_counts()
        .rename_axis(
            "custom_issue"
        )
        .reset_index(
            name="count"
        )
    )

    total = int(
        result[
            "count"
        ]
        .sum()
    )

    result[
        "percent"
    ] = (
        result[
            "count"
        ]
        .apply(
            lambda value:
                safe_percent(
                    value,
                    total
                )
        )
    )

    return result


# ============================================================
# CONTEXTUAL DECISION SUMMARY
# ============================================================

def build_contextual_decision_summary(
    contextual
):

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    if (
        processed.empty
        or
        "contextual_decision_code"
        not in processed.columns
    ):

        return pd.DataFrame(
            columns=[
                "contextual_decision_code",
                "count",
                "percent"
            ]
        )

    result = (
        processed[
            "contextual_decision_code"
        ]
        .fillna("")
        .replace(
            "",
            "unknown"
        )
        .value_counts()
        .rename_axis(
            "contextual_decision_code"
        )
        .reset_index(
            name="count"
        )
    )

    total = int(
        result[
            "count"
        ]
        .sum()
    )

    result[
        "percent"
    ] = (
        result[
            "count"
        ]
        .apply(
            lambda value:
                safe_percent(
                    value,
                    total
                )
        )
    )

    return result


# ============================================================
# CONTEXT CONFIDENCE SUMMARY
# ============================================================

def build_context_confidence_summary(
    contextual
):

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    if (
        processed.empty
        or
        "contextual_confidence"
        not in processed.columns
    ):

        return pd.DataFrame(
            columns=[
                "contextual_confidence",
                "count",
                "percent"
            ]
        )

    result = (
        processed[
            "contextual_confidence"
        ]
        .fillna("")
        .replace(
            "",
            "unknown"
        )
        .value_counts()
        .rename_axis(
            "contextual_confidence"
        )
        .reset_index(
            name="count"
        )
    )

    total = int(
        result[
            "count"
        ]
        .sum()
    )

    result[
        "percent"
    ] = (
        result[
            "count"
        ]
        .apply(
            lambda value:
                safe_percent(
                    value,
                    total
                )
        )
    )

    return result


# ============================================================
# EVIDENCE SOURCE SUMMARY
# ============================================================

def build_evidence_summary(
    contextual
):

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    if (
        processed.empty
        or
        "contextual_evidence_source"
        not in processed.columns
    ):

        return pd.DataFrame(
            columns=[
                "contextual_evidence_source",
                "count",
                "percent"
            ]
        )

    result = (
        processed[
            "contextual_evidence_source"
        ]
        .fillna("")
        .replace(
            "",
            "none"
        )
        .value_counts()
        .rename_axis(
            "contextual_evidence_source"
        )
        .reset_index(
            name="count"
        )
    )

    total = int(
        result[
            "count"
        ]
        .sum()
    )

    result[
        "percent"
    ] = (
        result[
            "count"
        ]
        .apply(
            lambda value:
                safe_percent(
                    value,
                    total
                )
        )
    )

    return result


# ============================================================
# CONTEXTUAL PAGE SUMMARY
# ============================================================

def build_contextual_page_summary(
    contextual
):

    if contextual.empty:

        return pd.DataFrame()

    rows = []

    for analysis_id, group in contextual.groupby(
        "analysis_id"
    ):

        processed = (
            contextual_processed_rows(
                group
            )
        )

        visual_review = 0

        manual_review = 0

        if (
            not processed.empty
            and
            "contextual_visual_review_required"
            in processed.columns
        ):

            visual_review = int(
                processed[
                    "contextual_visual_review_required"
                ]
                .apply(
                    bool_value
                )
                .sum()
            )

        if (
            not processed.empty
            and
            "contextual_manual_review_required"
            in processed.columns
        ):

            manual_review = int(
                processed[
                    "contextual_manual_review_required"
                ]
                .apply(
                    bool_value
                )
                .sum()
            )

        rows.append(
            {
                "analysis_id":
                    analysis_id,

                "page_url":
                    get_page_url(
                        group
                    ),

                "total_unified_findings":
                    len(
                        group
                    ),

                "contextual_processed":
                    len(
                        processed
                    ),

                "contextual_processing_rate_pct":
                    safe_percent(
                        len(
                            processed
                        ),
                        len(
                            group
                        )
                    ),

                "visual_review_required":
                    visual_review,

                "manual_review_required":
                    manual_review
            }
        )

    return (
        pd.DataFrame(
            rows
        )
        .sort_values(
            "analysis_id"
        )
    )


# ============================================================
# TEXT SUMMARY
# ============================================================

def write_text_summary(
    unified_files,
    page_summary,
    all_findings,
    contextual_files,
    contextual
):

    path = (
        OUTPUT_DIR
        /
        "live_experimental_summary.txt"
    )

    total_pages = len(
        page_summary
    )

    total_findings = len(
        all_findings
    )

    confirmed = status_count(
        all_findings,
        "confirmed_by_both"
    )

    custom_only = status_count(
        all_findings,
        "custom_only"
    )

    axe_only = status_count(
        all_findings,
        "axe_only"
    )

    incomplete = status_count(
        all_findings,
        "axe_incomplete"
    )

    custom_involved = count_true(
        all_findings,
        "source_custom"
    )

    axe_violation_elements = (
        confirmed
        +
        axe_only
    )

    comparable_unique = (
        confirmed
        +
        custom_only
        +
        axe_only
    )

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    lines = []

    lines.append(
        "LIVE EXPERIMENTAL ACCESSIBILITY SUMMARY"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        ""
    )

    lines.append(
        "IMPORTANT METHODOLOGY NOTE"
    )

    lines.append(
        "-" * 70
    )

    lines.append(
        (
            "These results come only from the live experimental "
            "pipeline. They do NOT replace, modify, or recompute "
            "the frozen 63-site Bangladeshi website research dataset."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Finding overlap is based on normalized element-level "
            "fusion. Raw rule totals from the custom scanner and "
            "axe-core should not be compared directly."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "axe incomplete findings are retained separately because "
            "they require additional manual or contextual review."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Context confidence describes the strength of extracted "
            "contextual evidence. It is not a probability of WCAG "
            "conformance."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        "LIVE DATASET"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        f"Unified files analyzed: {len(unified_files)}"
    )

    lines.append(
        f"Pages represented: {total_pages}"
    )

    lines.append(
        f"Unified findings: {total_findings}"
    )

    lines.append(
        ""
    )

    lines.append(
        "Fusion status:"
    )

    lines.append(
        f"  Confirmed by both: {confirmed}"
    )

    lines.append(
        f"  Custom only: {custom_only}"
    )

    lines.append(
        f"  axe only: {axe_only}"
    )

    lines.append(
        f"  axe incomplete: {incomplete}"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Confirmed share of custom findings: "
            f"{safe_percent(confirmed, custom_involved):.2f}%"
        )
    )

    lines.append(
        (
            "Confirmed share of axe violation findings: "
            f"{safe_percent(confirmed, axe_violation_elements):.2f}%"
        )
    )

    lines.append(
        (
            "Confirmed overlap among unique comparable violation "
            f"findings: "
            f"{safe_percent(confirmed, comparable_unique):.2f}%"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        "CONTEXTUAL RECOMMENDATION ENGINE"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        (
            "Contextual result files: "
            f"{len(contextual_files)}"
        )
    )

    lines.append(
        (
            "Context-dependent findings processed: "
            f"{len(processed)}"
        )
    )

    if (
        not processed.empty
        and
        "contextual_visual_review_required"
        in processed.columns
    ):

        visual_review = int(
            processed[
                "contextual_visual_review_required"
            ]
            .apply(
                bool_value
            )
            .sum()
        )

    else:

        visual_review = 0

    lines.append(
        (
            "Contextual findings requiring visual review: "
            f"{visual_review}"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "Generated tables:"
    )

    lines.append(
        "  1. live_page_summary.csv"
    )

    lines.append(
        "  2. fusion_status_summary.csv"
    )

    lines.append(
        "  3. rule_source_summary.csv"
    )

    lines.append(
        "  4. ownership_summary.csv"
    )

    lines.append(
        "  5. actionability_summary.csv"
    )

    lines.append(
        "  6. contextual_page_summary.csv"
    )

    lines.append(
        "  7. contextual_rule_summary.csv"
    )

    lines.append(
        "  8. contextual_decision_summary.csv"
    )

    lines.append(
        "  9. contextual_confidence_summary.csv"
    )

    lines.append(
        "  10. contextual_evidence_summary.csv"
    )

    lines.append(
        ""
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        "INTERPRETATION CAUTIONS"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        (
            "1. confirmed_by_both means the fusion algorithm matched "
            "a compatible custom and axe finding at the element level."
        )
    )

    lines.append(
        (
            "2. custom_only does not automatically mean axe missed a "
            "WCAG failure; some custom rules are contextual or "
            "best-practice indicators."
        )
    )

    lines.append(
        (
            "3. axe_only does not automatically mean the custom "
            "scanner failed; axe analyzes the rendered DOM and covers "
            "many rules outside the custom scanner's scope."
        )
    )

    lines.append(
        (
            "4. axe_incomplete findings require review and should not "
            "be counted as confirmed violations."
        )
    )

    lines.append(
        (
            "5. Context-aware recommendations are deterministic "
            "decision-support outputs and require human/developer "
            "verification before implementation."
        )
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(
                lines
            )
        )

    print(
        path
    )

    return path


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 80
    )

    print(
        "LIVE RESEARCH RESULTS EXPORTER"
    )

    print(
        "=" * 80
    )

    print()

    print(
        "This script reads live experimental outputs only."
    )

    print(
        "The frozen historical research dataset is not modified."
    )

    print()

    # ========================================================
    # CREATE OUTPUT DIR
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # UNIFIED DATA
    # ========================================================

    (
        unified_files,
        page_summary,
        all_findings
    ) = load_unified_files()

    if not unified_files:

        print(
            "ERROR:"
        )

        print(
            "No live unified finding files were found in:"
        )

        print(
            UNIFIED_DIR
        )

        sys.exit(1)

    print(
        "Unified files found:",
        len(
            unified_files
        )
    )

    print(
        "Unified findings:",
        len(
            all_findings
        )
    )

    # ========================================================
    # BUILD FUSION TABLES
    # ========================================================

    fusion_summary = (
        build_fusion_summary(
            all_findings
        )
    )

    rule_summary = (
        build_rule_summary(
            all_findings
        )
    )

    ownership_summary = (
        build_ownership_summary(
            all_findings
        )
    )

    actionability_summary = (
        build_actionability_summary(
            all_findings
        )
    )

    # ========================================================
    # CONTEXTUAL DATA
    # ========================================================

    (
        contextual_files,
        contextual
    ) = load_contextual_files()

    print(
        "Contextual result files found:",
        len(
            contextual_files
        )
    )

    contextual_page_summary = (
        build_contextual_page_summary(
            contextual
        )
    )

    contextual_rule_summary = (
        build_contextual_rule_summary(
            contextual
        )
    )

    contextual_decision_summary = (
        build_contextual_decision_summary(
            contextual
        )
    )

    contextual_confidence_summary = (
        build_context_confidence_summary(
            contextual
        )
    )

    contextual_evidence_summary = (
        build_evidence_summary(
            contextual
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    print()
    print(
        "=" * 80
    )

    print(
        "FILES CREATED"
    )

    print(
        "=" * 80
    )

    print()

    write_csv(
        page_summary,
        "live_page_summary.csv"
    )

    write_csv(
        fusion_summary,
        "fusion_status_summary.csv"
    )

    write_csv(
        rule_summary,
        "rule_source_summary.csv"
    )

    write_csv(
        ownership_summary,
        "ownership_summary.csv"
    )

    write_csv(
        actionability_summary,
        "actionability_summary.csv"
    )

    write_csv(
        contextual_page_summary,
        "contextual_page_summary.csv"
    )

    write_csv(
        contextual_rule_summary,
        "contextual_rule_summary.csv"
    )

    write_csv(
        contextual_decision_summary,
        "contextual_decision_summary.csv"
    )

    write_csv(
        contextual_confidence_summary,
        "contextual_confidence_summary.csv"
    )

    write_csv(
        contextual_evidence_summary,
        "contextual_evidence_summary.csv"
    )

    write_text_summary(
        unified_files,
        page_summary,
        all_findings,
        contextual_files,
        contextual
    )

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    confirmed = status_count(
        all_findings,
        "confirmed_by_both"
    )

    custom_only = status_count(
        all_findings,
        "custom_only"
    )

    axe_only = status_count(
        all_findings,
        "axe_only"
    )

    incomplete = status_count(
        all_findings,
        "axe_incomplete"
    )

    contextual_processed = (
        contextual_processed_rows(
            contextual
        )
    )

    print()
    print(
        "=" * 80
    )

    print(
        "EXPERIMENTAL SUMMARY"
    )

    print(
        "=" * 80
    )

    print()

    print(
        "Pages:",
        len(
            page_summary
        )
    )

    print(
        "Unified findings:",
        len(
            all_findings
        )
    )

    print()

    print(
        "Confirmed by both:",
        confirmed
    )

    print(
        "Custom only:",
        custom_only
    )

    print(
        "axe only:",
        axe_only
    )

    print(
        "axe incomplete:",
        incomplete
    )

    print()

    print(
        "Context-dependent recommendations:",
        len(
            contextual_processed
        )
    )

    print()

    print(
        "Output directory:"
    )

    print(
        OUTPUT_DIR
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Keep these live experimental results separate "
        "from the frozen 63-site statistical dataset."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
