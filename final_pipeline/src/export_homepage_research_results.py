import re
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
# INPUT FILES
# ============================================================

WEBSITES_FILE = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "input"
    /
    "websites.xlsx"
)

BATCH_STATUS_FILE = (
    FINAL_PIPELINE_DIR
    /
    "reports"
    /
    "homepage_batch"
    /
    "homepage_batch_status.csv"
)


# ============================================================
# RESULT DIRECTORIES
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

REPORT_DIR = (
    FINAL_PIPELINE_DIR
    /
    "reports"
    /
    "live"
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = (
    FINAL_PIPELINE_DIR
    /
    "reports"
    /
    "homepage_research"
)


# ============================================================
# BASIC HELPERS
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
# ORGANIZATION GROUP
# ============================================================

def get_experiment_group(
    row
):

    category = clean(
        row.get(
            "category",
            ""
        )
    )

    notes = clean(
        row.get(
            "notes",
            ""
        )
    ).lower()

    category_lower = (
        category.lower()
    )

    # --------------------------------------------------------
    # UNIVERSITY SPLIT
    # --------------------------------------------------------

    if (
        category_lower
        ==
        "university"
    ):

        if (
            "public"
            in notes
        ):

            return (
                "Public University"
            )

        if (
            "private"
            in notes
        ):

            return (
                "Private University"
            )

        return (
            "University - Unknown"
        )

    # --------------------------------------------------------
    # GOVERNMENT
    # --------------------------------------------------------

    if (
        category_lower
        ==
        "government"
    ):

        return (
            "Government"
        )

    # --------------------------------------------------------
    # NEWS
    # --------------------------------------------------------

    if (
        category_lower
        ==
        "news"
    ):

        return (
            "News"
        )

    return (
        category
        or
        "Unknown"
    )


# ============================================================
# LOAD SAMPLING FRAME
# ============================================================

def load_sampling_frame():

    websites = pd.read_excel(
        WEBSITES_FILE
    )

    websites[
        "website_id"
    ] = (
        websites[
            "website_id"
        ]
        .astype(str)
        .str.strip()
    )

    websites[
        "experiment_group"
    ] = (
        websites.apply(
            get_experiment_group,
            axis=1
        )
    )

    return websites


# ============================================================
# LOAD BATCH STATUS
# ============================================================

def load_batch_status():

    status = pd.read_csv(
        BATCH_STATUS_FILE
    )

    status[
        "site_id"
    ] = (
        status[
            "site_id"
        ]
        .astype(str)
        .str.strip()
    )

    return status


# ============================================================
# MERGE SAMPLING FRAME + BATCH STATUS
# ============================================================

def build_experiment_index(
    websites,
    status
):

    selected_columns = [
        "website_id",
        "website_name",
        "url",
        "category",
        "notes",
        "experiment_group"
    ]

    site_info = websites[
        selected_columns
    ].copy()

    site_info = site_info.rename(
        columns={
            "website_id":
                "site_id",

            "website_name":
                "master_website_name",

            "url":
                "master_url"
        }
    )

    merged = status.merge(
        site_info,
        on="site_id",
        how="left"
    )

    # Prefer master spreadsheet name.
    merged[
        "website_name"
    ] = merged[
        "master_website_name"
    ].fillna(
        merged.get(
            "website_name",
            ""
        )
    )

    return merged


# ============================================================
# EXTRACT REAL OUTPUT STEM FROM LOG
# ============================================================

def extract_analysis_stem_from_log(
    log_file
):

    log_file = Path(
        clean(
            log_file
        )
    )

    if not log_file.exists():

        return ""

    try:

        text = log_file.read_text(
            encoding="utf-8",
            errors="replace"
        )

    except Exception:

        return ""

    # --------------------------------------------------------
    # BEST SOURCE:
    # final Analysis stem printed after ANALYSIS COMPLETE
    # --------------------------------------------------------

    matches = re.findall(
        r"Analysis stem:\s*\n([^\n]+)",
        text
    )

    if matches:

        return clean(
            matches[-1]
        )

    # --------------------------------------------------------
    # SECONDARY SOURCE:
    # unified findings filename
    # --------------------------------------------------------

    matches = re.findall(
        r"([A-Za-z0-9._-]+)__unified_findings\.csv",
        text
    )

    if matches:

        return clean(
            matches[-1]
        )

    # --------------------------------------------------------
    # AXE REDIRECT STEM
    # --------------------------------------------------------

    matches = re.findall(
        r"([A-Za-z0-9._-]+)__axe_nodes\.csv",
        text
    )

    if matches:

        return clean(
            matches[-1]
        )

    return ""


# ============================================================
# FIND OUTPUT FILE
# ============================================================

def find_exact_or_redirected_file(
    directory,
    stem,
    suffix
):

    directory = Path(
        directory
    )

    if not stem:

        return None

    exact = (
        directory
        /
        f"{stem}{suffix}"
    )

    if exact.exists():

        return exact

    return None


# ============================================================
# RESOLVE COMPLETED PAGE OUTPUTS
# ============================================================

def resolve_completed_outputs(
    experiment_index
):

    completed = experiment_index[
        experiment_index[
            "batch_status"
        ]
        ==
        "complete"
    ].copy()

    rows = []

    for _, row in completed.iterrows():

        actual_stem = (
            extract_analysis_stem_from_log(
                row.get(
                    "log_file",
                    ""
                )
            )
        )

        # Fallback to batch stem.
        if not actual_stem:

            actual_stem = clean(
                row.get(
                    "analysis_stem",
                    ""
                )
            )

        unified_file = (
            find_exact_or_redirected_file(
                UNIFIED_DIR,
                actual_stem,
                "__unified_findings.csv"
            )
        )

        contextual_file = (
            find_exact_or_redirected_file(
                CONTEXTUAL_DIR,
                actual_stem,
                "__contextual_recommendations.csv"
            )
        )

        report_file = (
            find_exact_or_redirected_file(
                REPORT_DIR,
                actual_stem,
                "__accessibility_report.html"
            )
        )

        rows.append(
            {
                "site_id":
                    clean(
                        row.get(
                            "site_id",
                            ""
                        )
                    ),

                "website_name":
                    clean(
                        row.get(
                            "website_name",
                            ""
                        )
                    ),

                "experiment_group":
                    clean(
                        row.get(
                            "experiment_group",
                            ""
                        )
                    ),

                "requested_url":
                    clean(
                        row.get(
                            "requested_url",
                            ""
                        )
                    ),

                "actual_analysis_stem":
                    actual_stem,

                "unified_file":
                    str(
                        unified_file
                    )
                    if unified_file
                    else "",

                "contextual_file":
                    str(
                        contextual_file
                    )
                    if contextual_file
                    else "",

                "report_file":
                    str(
                        report_file
                    )
                    if report_file
                    else "",

                "unified_exists":
                    bool(
                        unified_file
                    ),

                "contextual_exists":
                    bool(
                        contextual_file
                    ),

                "report_exists":
                    bool(
                        report_file
                    )
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# LOAD UNIFIED FINDINGS
# ============================================================

def load_completed_unified(
    resolved
):

    frames = []

    page_rows = []

    for _, row in resolved.iterrows():

        unified_file = clean(
            row.get(
                "unified_file",
                ""
            )
        )

        if not unified_file:

            continue

        path = Path(
            unified_file
        )

        if not path.exists():

            continue

        try:

            df = pd.read_csv(
                path
            )

        except Exception as error:

            print()
            print(
                "WARNING:"
            )
            print(
                "Could not read unified file:"
            )
            print(
                path
            )
            print(
                error
            )
            continue

        site_id = clean(
            row.get(
                "site_id",
                ""
            )
        )

        group = clean(
            row.get(
                "experiment_group",
                ""
            )
        )

        website_name = clean(
            row.get(
                "website_name",
                ""
            )
        )

        requested_url = clean(
            row.get(
                "requested_url",
                ""
            )
        )

        # ----------------------------------------------------
        # PAGE-LEVEL COUNTS
        # ----------------------------------------------------

        def status_count(
            status_name
        ):

            if (
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
                    status_name
                )
                .sum()
            )

        confirmed = status_count(
            "confirmed_by_both"
        )

        custom_only = status_count(
            "custom_only"
        )

        axe_only = status_count(
            "axe_only"
        )

        axe_incomplete = status_count(
            "axe_incomplete"
        )

        custom_involved = (
            confirmed
            +
            custom_only
        )

        axe_violation_findings = (
            confirmed
            +
            axe_only
        )

        comparable_findings = (
            confirmed
            +
            custom_only
            +
            axe_only
        )

        page_content = 0
        third_party = 0
        first_party = 0

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

            first_party = int(
                (
                    ownership
                    ==
                    "first_party_integration"
                )
                .sum()
            )

        page_rows.append(
            {
                "site_id":
                    site_id,

                "website_name":
                    website_name,

                "experiment_group":
                    group,

                "requested_url":
                    requested_url,

                "total_unified_findings":
                    len(
                        df
                    ),

                "confirmed_by_both":
                    confirmed,

                "custom_only":
                    custom_only,

                "axe_only":
                    axe_only,

                "axe_incomplete":
                    axe_incomplete,

                "custom_findings":
                    custom_involved,

                "axe_violation_findings":
                    axe_violation_findings,

                "comparable_violation_findings":
                    comparable_findings,

                "confirmed_share_of_custom_pct":
                    safe_percent(
                        confirmed,
                        custom_involved
                    ),

                "confirmed_share_of_axe_pct":
                    safe_percent(
                        confirmed,
                        axe_violation_findings
                    ),

                "overlap_share_of_comparable_pct":
                    safe_percent(
                        confirmed,
                        comparable_findings
                    ),

                "page_content_findings":
                    page_content,

                "third_party_embed_findings":
                    third_party,

                "first_party_integration_findings":
                    first_party
            }
        )

        current = df.copy()

        current[
            "site_id"
        ] = site_id

        current[
            "website_name"
        ] = website_name

        current[
            "experiment_group"
        ] = group

        current[
            "requested_url_original"
        ] = requested_url

        frames.append(
            current
        )

    if frames:

        all_findings = pd.concat(
            frames,
            ignore_index=True,
            sort=False
        )

    else:

        all_findings = (
            pd.DataFrame()
        )

    return (
        pd.DataFrame(
            page_rows
        ),
        all_findings
    )


# ============================================================
# LOAD CONTEXTUAL OUTPUTS
# ============================================================

def load_completed_contextual(
    resolved
):

    frames = []

    for _, row in resolved.iterrows():

        contextual_file = clean(
            row.get(
                "contextual_file",
                ""
            )
        )

        if not contextual_file:

            continue

        path = Path(
            contextual_file
        )

        if not path.exists():

            continue

        try:

            df = pd.read_csv(
                path
            )

        except Exception:
            continue

        df[
            "site_id"
        ] = clean(
            row.get(
                "site_id",
                ""
            )
        )

        df[
            "website_name"
        ] = clean(
            row.get(
                "website_name",
                ""
            )
        )

        df[
            "experiment_group"
        ] = clean(
            row.get(
                "experiment_group",
                ""
            )
        )

        frames.append(
            df
        )

    if frames:

        return pd.concat(
            frames,
            ignore_index=True,
            sort=False
        )

    return pd.DataFrame()


# ============================================================
# ATTEMPT SUMMARY
# ============================================================

def build_attempt_summary(
    experiment_index
):

    rows = []

    preferred_order = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    for group_name in preferred_order:

        group = experiment_index[
            experiment_index[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        rows.append(
            {
                "experiment_group":
                    group_name,

                "attempted":
                    len(
                        group
                    ),

                "complete":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "complete"
                        )
                        .sum()
                    ),

                "not_analyzable":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "not_analyzable"
                        )
                        .sum()
                    ),

                "failed":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "failed"
                        )
                        .sum()
                    ),

                "unreachable":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "unreachable"
                        )
                        .sum()
                    ),

                "incomplete":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "incomplete"
                        )
                        .sum()
                    ),

                "completion_rate_pct":
                    safe_percent(
                        int(
                            (
                                group[
                                    "batch_status"
                                ]
                                ==
                                "complete"
                            )
                            .sum()
                        ),
                        len(
                            group
                        )
                    )
            }
        )

    rows.append(
        {
            "experiment_group":
                "TOTAL",

            "attempted":
                len(
                    experiment_index
                ),

            "complete":
                int(
                    (
                        experiment_index[
                            "batch_status"
                        ]
                        ==
                        "complete"
                    )
                    .sum()
                ),

            "not_analyzable":
                int(
                    (
                        experiment_index[
                            "batch_status"
                        ]
                        ==
                        "not_analyzable"
                    )
                    .sum()
                ),

            "failed":
                int(
                    (
                        experiment_index[
                            "batch_status"
                        ]
                        ==
                        "failed"
                    )
                    .sum()
                ),

            "unreachable":
                int(
                    (
                        experiment_index[
                            "batch_status"
                        ]
                        ==
                        "unreachable"
                    )
                    .sum()
                ),

            "incomplete":
                int(
                    (
                        experiment_index[
                            "batch_status"
                        ]
                        ==
                        "incomplete"
                    )
                    .sum()
                ),

            "completion_rate_pct":
                safe_percent(
                    int(
                        (
                            experiment_index[
                                "batch_status"
                            ]
                            ==
                            "complete"
                        )
                        .sum()
                    ),
                    len(
                        experiment_index
                    )
                )
        }
    )

    return pd.DataFrame(
        rows
    )


# ============================================================
# GROUP DETECTION/FUSION SUMMARY
# ============================================================

def build_group_fusion_summary(
    page_summary
):

    if page_summary.empty:

        return pd.DataFrame()

    numeric_columns = [
        "total_unified_findings",
        "confirmed_by_both",
        "custom_only",
        "axe_only",
        "axe_incomplete",
        "custom_findings",
        "axe_violation_findings",
        "comparable_violation_findings",
        "page_content_findings",
        "third_party_embed_findings",
        "first_party_integration_findings"
    ]

    rows = []

    preferred_order = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    for group_name in preferred_order:

        group = page_summary[
            page_summary[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        row = {
            "experiment_group":
                group_name,

            "completed_pages":
                len(
                    group
                )
        }

        for column in numeric_columns:

            row[
                column
            ] = int(
                group[
                    column
                ]
                .sum()
            )

            row[
                f"mean_{column}_per_page"
            ] = round(
                group[
                    column
                ]
                .mean(),
                2
            )

        row[
            "confirmed_share_of_custom_pct"
        ] = safe_percent(
            row[
                "confirmed_by_both"
            ],
            row[
                "custom_findings"
            ]
        )

        row[
            "confirmed_share_of_axe_pct"
        ] = safe_percent(
            row[
                "confirmed_by_both"
            ],
            row[
                "axe_violation_findings"
            ]
        )

        row[
            "overlap_share_of_comparable_pct"
        ] = safe_percent(
            row[
                "confirmed_by_both"
            ],
            row[
                "comparable_violation_findings"
            ]
        )

        rows.append(
            row
        )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total_row = {
        "experiment_group":
            "TOTAL",

        "completed_pages":
            len(
                page_summary
            )
    }

    for column in numeric_columns:

        total_row[
            column
        ] = int(
            page_summary[
                column
            ]
            .sum()
        )

        total_row[
            f"mean_{column}_per_page"
        ] = round(
            page_summary[
                column
            ]
            .mean(),
            2
        )

    total_row[
        "confirmed_share_of_custom_pct"
    ] = safe_percent(
        total_row[
            "confirmed_by_both"
        ],
        total_row[
            "custom_findings"
        ]
    )

    total_row[
        "confirmed_share_of_axe_pct"
    ] = safe_percent(
        total_row[
            "confirmed_by_both"
        ],
        total_row[
            "axe_violation_findings"
        ]
    )

    total_row[
        "overlap_share_of_comparable_pct"
    ] = safe_percent(
        total_row[
            "confirmed_by_both"
        ],
        total_row[
            "comparable_violation_findings"
        ]
    )

    rows.append(
        total_row
    )

    return pd.DataFrame(
        rows
    )


# ============================================================
# FUSION STATUS SUMMARY
# ============================================================

def build_fusion_status_summary(
    all_findings
):

    if all_findings.empty:

        return pd.DataFrame()

    statuses = [
        "confirmed_by_both",
        "custom_only",
        "axe_only",
        "axe_incomplete"
    ]

    rows = []

    for group_name in [
        "Public University",
        "Private University",
        "News",
        "Government",
        "TOTAL"
    ]:

        if group_name == "TOTAL":

            group = all_findings

        else:

            group = all_findings[
                all_findings[
                    "experiment_group"
                ]
                ==
                group_name
            ]

        if group.empty:
            continue

        for status in statuses:

            if (
                "finding_status"
                not in group.columns
            ):
                count = 0

            else:

                count = int(
                    (
                        group[
                            "finding_status"
                        ]
                        .fillna("")
                        ==
                        status
                    )
                    .sum()
                )

            rows.append(
                {
                    "experiment_group":
                        group_name,

                    "finding_status":
                        status,

                    "count":
                        count,

                    "percent_of_group_findings":
                        safe_percent(
                            count,
                            len(
                                group
                            )
                        )
                }
            )

    return pd.DataFrame(
        rows
    )


# ============================================================
# RULE SUMMARY
# ============================================================

def build_rule_summary(
    all_findings
):

    if all_findings.empty:

        return pd.DataFrame()

    rows = []

    for _, row in all_findings.iterrows():

        group = clean(
            row.get(
                "experiment_group",
                ""
            )
        )

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
                    "experiment_group":
                        group,

                    "source":
                        "custom",

                    "rule":
                        custom_rule,

                    "finding_status":
                        status
                }
            )

        if axe_rule:

            rows.append(
                {
                    "experiment_group":
                        group,

                    "source":
                        "axe",

                    "rule":
                        axe_rule,

                    "finding_status":
                        status
                }
            )

    if not rows:

        return pd.DataFrame()

    detail = pd.DataFrame(
        rows
    )

    return (
        detail
        .groupby(
            [
                "experiment_group",
                "source",
                "rule",
                "finding_status"
            ]
        )
        .size()
        .reset_index(
            name="count"
        )
        .sort_values(
            [
                "experiment_group",
                "count"
            ],
            ascending=[
                True,
                False
            ]
        )
    )


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

        return pd.DataFrame()

    rows = []

    groups = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    for group_name in groups:

        group = all_findings[
            all_findings[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        counts = (
            group[
                "ownership_scope"
            ]
            .fillna("")
            .replace(
                "",
                "unknown"
            )
            .value_counts()
        )

        for ownership, count in counts.items():

            rows.append(
                {
                    "experiment_group":
                        group_name,

                    "ownership_scope":
                        ownership,

                    "count":
                        int(
                            count
                        ),

                    "percent":
                        safe_percent(
                            int(
                                count
                            ),
                            len(
                                group
                            )
                        )
                }
            )

    return pd.DataFrame(
        rows
    )


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

        return pd.DataFrame()

    rows = []

    groups = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    for group_name in groups:

        group = all_findings[
            all_findings[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        counts = (
            group[
                "actionability"
            ]
            .fillna("")
            .replace(
                "",
                "unknown"
            )
            .value_counts()
        )

        for actionability, count in counts.items():

            rows.append(
                {
                    "experiment_group":
                        group_name,

                    "actionability":
                        actionability,

                    "count":
                        int(
                            count
                        ),

                    "percent":
                        safe_percent(
                            int(
                                count
                            ),
                            len(
                                group
                            )
                        )
                }
            )

    return pd.DataFrame(
        rows
    )


# ============================================================
# CONTEXTUAL PROCESSED ROWS
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
# CONTEXTUAL GROUP SUMMARY
# ============================================================

def build_contextual_group_summary(
    contextual
):

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    if processed.empty:

        return pd.DataFrame()

    rows = []

    groups = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    for group_name in groups:

        group = processed[
            processed[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        visual_review = 0

        manual_review = 0

        if (
            "contextual_visual_review_required"
            in group.columns
        ):

            visual_review = int(
                group[
                    "contextual_visual_review_required"
                ]
                .apply(
                    bool_value
                )
                .sum()
            )

        if (
            "contextual_manual_review_required"
            in group.columns
        ):

            manual_review = int(
                group[
                    "contextual_manual_review_required"
                ]
                .apply(
                    bool_value
                )
                .sum()
            )

        rows.append(
            {
                "experiment_group":
                    group_name,

                "contextual_findings":
                    len(
                        group
                    ),

                "visual_review_required":
                    visual_review,

                "manual_review_required":
                    manual_review
            }
        )

    rows.append(
        {
            "experiment_group":
                "TOTAL",

            "contextual_findings":
                len(
                    processed
                ),

            "visual_review_required":
                int(
                    processed[
                        "contextual_visual_review_required"
                    ]
                    .apply(
                        bool_value
                    )
                    .sum()
                )
                if
                "contextual_visual_review_required"
                in processed.columns
                else
                0,

            "manual_review_required":
                int(
                    processed[
                        "contextual_manual_review_required"
                    ]
                    .apply(
                        bool_value
                    )
                    .sum()
                )
                if
                "contextual_manual_review_required"
                in processed.columns
                else
                0
        }
    )

    return pd.DataFrame(
        rows
    )


# ============================================================
# GENERIC CONTEXT SUMMARY
# ============================================================

def build_context_value_summary(
    contextual,
    column
):

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    if (
        processed.empty
        or
        column
        not in processed.columns
    ):

        return pd.DataFrame()

    rows = []

    for group_name in [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]:

        group = processed[
            processed[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        counts = (
            group[
                column
            ]
            .fillna("")
            .replace(
                "",
                "unknown"
            )
            .value_counts()
        )

        for value, count in counts.items():

            rows.append(
                {
                    "experiment_group":
                        group_name,

                    column:
                        value,

                    "count":
                        int(
                            count
                        ),

                    "percent":
                        safe_percent(
                            int(
                                count
                            ),
                            len(
                                group
                            )
                        )
                }
            )

    return pd.DataFrame(
        rows
    )


# ============================================================
# TEXT SUMMARY
# ============================================================

def write_text_summary(
    experiment_index,
    resolved,
    page_summary,
    all_findings,
    contextual
):

    path = (
        OUTPUT_DIR
        /
        "homepage_experiment_summary.txt"
    )

    total_attempted = len(
        experiment_index
    )

    complete = int(
        (
            experiment_index[
                "batch_status"
            ]
            ==
            "complete"
        )
        .sum()
    )

    not_analyzable = int(
        (
            experiment_index[
                "batch_status"
            ]
            ==
            "not_analyzable"
        )
        .sum()
    )

    failed = int(
        (
            experiment_index[
                "batch_status"
            ]
            ==
            "failed"
        )
        .sum()
    )

    confirmed = 0
    custom_only = 0
    axe_only = 0
    incomplete = 0

    if (
        not all_findings.empty
        and
        "finding_status"
        in all_findings.columns
    ):

        confirmed = int(
            (
                all_findings[
                    "finding_status"
                ]
                ==
                "confirmed_by_both"
            )
            .sum()
        )

        custom_only = int(
            (
                all_findings[
                    "finding_status"
                ]
                ==
                "custom_only"
            )
            .sum()
        )

        axe_only = int(
            (
                all_findings[
                    "finding_status"
                ]
                ==
                "axe_only"
            )
            .sum()
        )

        incomplete = int(
            (
                all_findings[
                    "finding_status"
                ]
                ==
                "axe_incomplete"
            )
            .sum()
        )

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    lines = []

    lines.append(
        "HOMEPAGE-LEVEL EXPERIMENTAL EVALUATION"
    )

    lines.append(
        "=" * 72
    )

    lines.append(
        ""
    )

    lines.append(
        "Sampling frame:"
    )

    lines.append(
        f"Attempted homepages: {total_attempted}"
    )

    lines.append(
        f"Completed analyses: {complete}"
    )

    lines.append(
        f"Completion rate: {safe_percent(complete, total_attempted):.2f}%"
    )

    lines.append(
        f"Not analyzable: {not_analyzable}"
    )

    lines.append(
        f"Failed/excluded: {failed}"
    )

    lines.append(
        ""
    )

    lines.append(
        "Organization groups:"
    )

    for group_name in [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]:

        attempted = int(
            (
                experiment_index[
                    "experiment_group"
                ]
                ==
                group_name
            )
            .sum()
        )

        completed = int(
            (
                (
                    experiment_index[
                        "experiment_group"
                    ]
                    ==
                    group_name
                )
                &
                (
                    experiment_index[
                        "batch_status"
                    ]
                    ==
                    "complete"
                )
            )
            .sum()
        )

        lines.append(
            (
                f"  {group_name}: "
                f"{attempted} attempted, "
                f"{completed} completed"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "Unified finding results:"
    )

    lines.append(
        f"Total unified findings: {len(all_findings)}"
    )

    lines.append(
        f"Confirmed by both: {confirmed}"
    )

    lines.append(
        f"Custom only: {custom_only}"
    )

    lines.append(
        f"axe only: {axe_only}"
    )

    lines.append(
        f"axe incomplete: {incomplete}"
    )

    comparable = (
        confirmed
        +
        custom_only
        +
        axe_only
    )

    lines.append(
        (
            "Overlap among comparable violation findings: "
            f"{safe_percent(confirmed, comparable):.2f}%"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "Contextual remediation:"
    )

    lines.append(
        (
            "Context-dependent findings processed: "
            f"{len(processed)}"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "Methodology note:"
    )

    lines.append(
        (
            "This exporter includes only pages belonging to the "
            "80-homepage experimental sampling frame and only "
            "completed pipeline outputs. Earlier development and "
            "manual test pages are excluded."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The homepage experiment is separate from the frozen "
            "multi-page historical dataset and must not be used "
            "to recompute the original study statistics."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Homepage-level findings should not be interpreted "
            "as representing complete website-wide WCAG conformance."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "axe incomplete findings are retained separately and "
            "are not treated as confirmed violations."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Context confidence represents strength of extracted "
            "contextual evidence rather than WCAG conformance certainty."
        )
    )

    path.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8"
    )

    print(
        path
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 80
    )

    print(
        "BATCH-SCOPED HOMEPAGE RESEARCH EXPORTER"
    )

    print(
        "=" * 80
    )

    print()

    # ========================================================
    # CHECK INPUTS
    # ========================================================

    if not WEBSITES_FILE.exists():

        print(
            "ERROR: websites.xlsx not found:"
        )

        print(
            WEBSITES_FILE
        )

        return

    if not BATCH_STATUS_FILE.exists():

        print(
            "ERROR: homepage_batch_status.csv not found:"
        )

        print(
            BATCH_STATUS_FILE
        )

        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # LOAD
    # ========================================================

    websites = (
        load_sampling_frame()
    )

    status = (
        load_batch_status()
    )

    experiment_index = (
        build_experiment_index(
            websites,
            status
        )
    )

    # ========================================================
    # VERIFY SAMPLING FRAME
    # ========================================================

    print(
        "Homepage attempts:",
        len(
            experiment_index
        )
    )

    print()

    print(
        "Sampling groups:"
    )

    print(
        experiment_index[
            "experiment_group"
        ]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # RESOLVE OUTPUTS
    # ========================================================

    resolved = (
        resolve_completed_outputs(
            experiment_index
        )
    )

    # ========================================================
    # LOAD FINDINGS
    # ========================================================

    (
        page_summary,
        all_findings
    ) = load_completed_unified(
        resolved
    )

    contextual = (
        load_completed_contextual(
            resolved
        )
    )

    # ========================================================
    # SUMMARIES
    # ========================================================

    attempt_summary = (
        build_attempt_summary(
            experiment_index
        )
    )

    group_fusion_summary = (
        build_group_fusion_summary(
            page_summary
        )
    )

    fusion_status_summary = (
        build_fusion_status_summary(
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

    contextual_group_summary = (
        build_contextual_group_summary(
            contextual
        )
    )

    contextual_rule_summary = (
        build_context_value_summary(
            contextual,
            "custom_issue"
        )
    )

    contextual_decision_summary = (
        build_context_value_summary(
            contextual,
            "contextual_decision_code"
        )
    )

    contextual_confidence_summary = (
        build_context_value_summary(
            contextual,
            "contextual_confidence"
        )
    )

    contextual_evidence_summary = (
        build_context_value_summary(
            contextual,
            "contextual_evidence_source"
        )
    )

    # ========================================================
    # EXPORT
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
        experiment_index,
        "homepage_experiment_index.csv"
    )

    write_csv(
        resolved,
        "completed_output_resolution.csv"
    )

    write_csv(
        attempt_summary,
        "attempt_summary_by_group.csv"
    )

    write_csv(
        page_summary,
        "homepage_page_summary.csv"
    )

    write_csv(
        group_fusion_summary,
        "fusion_summary_by_group.csv"
    )

    write_csv(
        fusion_status_summary,
        "fusion_status_by_group.csv"
    )

    write_csv(
        rule_summary,
        "rule_summary_by_group.csv"
    )

    write_csv(
        ownership_summary,
        "ownership_summary_by_group.csv"
    )

    write_csv(
        actionability_summary,
        "actionability_summary_by_group.csv"
    )

    write_csv(
        contextual_group_summary,
        "contextual_summary_by_group.csv"
    )

    write_csv(
        contextual_rule_summary,
        "contextual_rule_summary_by_group.csv"
    )

    write_csv(
        contextual_decision_summary,
        "contextual_decision_summary_by_group.csv"
    )

    write_csv(
        contextual_confidence_summary,
        "contextual_confidence_summary_by_group.csv"
    )

    write_csv(
        contextual_evidence_summary,
        "contextual_evidence_summary_by_group.csv"
    )

    write_text_summary(
        experiment_index,
        resolved,
        page_summary,
        all_findings,
        contextual
    )

    # ========================================================
    # FINAL TERMINAL SUMMARY
    # ========================================================

    print()
    print(
        "=" * 80
    )

    print(
        "HOMEPAGE EXPERIMENT SUMMARY"
    )

    print(
        "=" * 80
    )

    print()

    print(
        attempt_summary.to_string(
            index=False
        )
    )

    print()

    print(
        "Completed pages with unified data:",
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

    processed = (
        contextual_processed_rows(
            contextual
        )
    )

    print(
        "Context-dependent recommendations:",
        len(
            processed
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
        "These results contain only the homepage batch "
        "experiment. Earlier manual/development pages are excluded."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
