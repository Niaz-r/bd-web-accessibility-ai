import re
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
FINAL_PIPELINE_DIR = SRC_DIR.parent


# ============================================================
# INPUT FILES
# ============================================================

WEBSITES_FILE = (
    FINAL_PIPELINE_DIR
    / "data"
    / "input"
    / "websites.xlsx"
)

BATCH_STATUS_FILE = (
    FINAL_PIPELINE_DIR
    / "reports"
    / "homepage_batch"
    / "homepage_batch_status.csv"
)

PAGE_SUMMARY_FILE = (
    FINAL_PIPELINE_DIR
    / "reports"
    / "homepage_research"
    / "homepage_page_summary.csv"
)

CONTEXTUAL_FILE_DIR = (
    FINAL_PIPELINE_DIR
    / "data"
    / "final"
    / "contextual_recommendations"
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = (
    FINAL_PIPELINE_DIR
    / "reports"
    / "homepage_analysis_sets"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def bool_value(value):

    if isinstance(value, bool):
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
        numerator / denominator * 100,
        2
    )


# ============================================================
# ORGANIZATION GROUP
# ============================================================

def get_experiment_group(row):

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

    category_lower = category.lower()

    if category_lower == "university":

        if "public" in notes:
            return "Public University"

        if "private" in notes:
            return "Private University"

        return "University - Unknown"

    if category_lower == "news":
        return "News"

    if category_lower == "government":
        return "Government"

    return category or "Unknown"


# ============================================================
# ANALYSIS MODE FROM LOG
# ============================================================

def get_analysis_mode(
    log_file
):

    log_file = Path(
        clean(
            log_file
        )
    )

    if not log_file.exists():

        return "unknown"

    try:

        text = log_file.read_text(
            encoding="utf-8",
            errors="replace"
        )

    except Exception:

        return "unknown"

    matches = re.findall(
        r"Analysis mode:\s*\n([^\n]+)",
        text
    )

    if not matches:

        return "unknown"

    mode = clean(
        matches[-1]
    ).lower()

    if mode.startswith(
        "custom + axe"
    ):

        return "custom_and_axe"

    if mode.startswith(
        "axe-only partial analysis"
    ):

        return "axe_only"

    if mode.startswith(
        "custom-only partial analysis"
    ):

        return "custom_only"

    return "unknown"


# ============================================================
# ANALYSIS STEM FROM LOG
# ============================================================

def get_analysis_stem(
    log_file,
    fallback=""
):

    log_file = Path(
        clean(
            log_file
        )
    )

    if log_file.exists():

        try:

            text = log_file.read_text(
                encoding="utf-8",
                errors="replace"
            )

            matches = re.findall(
                r"Analysis stem:\s*\n([^\n]+)",
                text
            )

            if matches:

                return clean(
                    matches[-1]
                )

        except Exception:

            pass

    return clean(
        fallback
    )


# ============================================================
# LOAD MASTER SAMPLE
# ============================================================

def load_master_sample():

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
    ] = websites.apply(
        get_experiment_group,
        axis=1
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
# BUILD COMPLETED PAGE INDEX
# ============================================================

def build_completed_index(
    websites,
    status
):

    site_info = websites[
        [
            "website_id",
            "website_name",
            "url",
            "category",
            "notes",
            "experiment_group"
        ]
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

    completed = merged[
        merged[
            "batch_status"
        ]
        ==
        "complete"
    ].copy()

    completed[
        "analysis_mode"
    ] = completed[
        "log_file"
    ].apply(
        get_analysis_mode
    )

    completed[
        "actual_analysis_stem"
    ] = completed.apply(
        lambda row:
            get_analysis_stem(
                row.get(
                    "log_file",
                    ""
                ),
                row.get(
                    "analysis_stem",
                    ""
                )
            ),
        axis=1
    )

    return completed


# ============================================================
# LOAD PAGE SUMMARY
# ============================================================

def load_page_summary():

    page_summary = pd.read_csv(
        PAGE_SUMMARY_FILE
    )

    page_summary[
        "site_id"
    ] = (
        page_summary[
            "site_id"
        ]
        .astype(str)
        .str.strip()
    )

    return page_summary


# ============================================================
# MERGE PAGE METRICS
# ============================================================

def attach_page_metrics(
    completed,
    page_summary
):

    page_columns = [
        "site_id",
        "total_unified_findings",
        "confirmed_by_both",
        "custom_only",
        "axe_only",
        "axe_incomplete",
        "custom_findings",
        "axe_violation_findings",
        "comparable_violation_findings",
        "confirmed_share_of_custom_pct",
        "confirmed_share_of_axe_pct",
        "overlap_share_of_comparable_pct",
        "page_content_findings",
        "third_party_embed_findings",
        "first_party_integration_findings"
    ]

    available_columns = [
        column
        for column
        in page_columns
        if column
        in page_summary.columns
    ]

    metrics = page_summary[
        available_columns
    ].copy()

    merged = completed.merge(
        metrics,
        on="site_id",
        how="left"
    )

    return merged


# ============================================================
# BUILD ALL-COMPLETED SUMMARY
# ============================================================

def build_all_completed_summary(
    dataframe
):

    rows = []

    groups = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    for group_name in groups:

        group = dataframe[
            dataframe[
                "experiment_group"
            ]
            ==
            group_name
        ]

        if group.empty:
            continue

        axe_only_pages = int(
            (
                group[
                    "analysis_mode"
                ]
                ==
                "axe_only"
            )
            .sum()
        )

        dual_pages = int(
            (
                group[
                    "analysis_mode"
                ]
                ==
                "custom_and_axe"
            )
            .sum()
        )

        rows.append(
            {
                "experiment_group":
                    group_name,

                "completed_pages":
                    len(
                        group
                    ),

                "dual_engine_pages":
                    dual_pages,

                "axe_only_pages":
                    axe_only_pages,

                "dual_engine_coverage_pct":
                    safe_percent(
                        dual_pages,
                        len(group)
                    ),

                "axe_only_coverage_pct":
                    safe_percent(
                        axe_only_pages,
                        len(group)
                    ),

                "axe_violation_findings":
                    int(
                        group[
                            "axe_violation_findings"
                        ]
                        .fillna(0)
                        .sum()
                    ),

                "mean_axe_violation_findings_per_page":
                    round(
                        group[
                            "axe_violation_findings"
                        ]
                        .fillna(0)
                        .mean(),
                        2
                    ),

                "median_axe_violation_findings_per_page":
                    round(
                        group[
                            "axe_violation_findings"
                        ]
                        .fillna(0)
                        .median(),
                        2
                    ),

                "axe_incomplete":
                    int(
                        group[
                            "axe_incomplete"
                        ]
                        .fillna(0)
                        .sum()
                    ),

                "mean_axe_incomplete_per_page":
                    round(
                        group[
                            "axe_incomplete"
                        ]
                        .fillna(0)
                        .mean(),
                        2
                    ),

                "median_axe_incomplete_per_page":
                    round(
                        group[
                            "axe_incomplete"
                        ]
                        .fillna(0)
                        .median(),
                        2
                    )
            }
        )

    total = dataframe

    rows.append(
        {
            "experiment_group":
                "TOTAL",

            "completed_pages":
                len(total),

            "dual_engine_pages":
                int(
                    (
                        total[
                            "analysis_mode"
                        ]
                        ==
                        "custom_and_axe"
                    )
                    .sum()
                ),

            "axe_only_pages":
                int(
                    (
                        total[
                            "analysis_mode"
                        ]
                        ==
                        "axe_only"
                    )
                    .sum()
                ),

            "dual_engine_coverage_pct":
                safe_percent(
                    int(
                        (
                            total[
                                "analysis_mode"
                            ]
                            ==
                            "custom_and_axe"
                        )
                        .sum()
                    ),
                    len(total)
                ),

            "axe_only_coverage_pct":
                safe_percent(
                    int(
                        (
                            total[
                                "analysis_mode"
                            ]
                            ==
                            "axe_only"
                        )
                        .sum()
                    ),
                    len(total)
                ),

            "axe_violation_findings":
                int(
                    total[
                        "axe_violation_findings"
                    ]
                    .fillna(0)
                    .sum()
                ),

            "mean_axe_violation_findings_per_page":
                round(
                    total[
                        "axe_violation_findings"
                    ]
                    .fillna(0)
                    .mean(),
                    2
                ),

            "median_axe_violation_findings_per_page":
                round(
                    total[
                        "axe_violation_findings"
                    ]
                    .fillna(0)
                    .median(),
                    2
                ),

            "axe_incomplete":
                int(
                    total[
                        "axe_incomplete"
                    ]
                    .fillna(0)
                    .sum()
                ),

            "mean_axe_incomplete_per_page":
                round(
                    total[
                        "axe_incomplete"
                    ]
                    .fillna(0)
                    .mean(),
                    2
                ),

            "median_axe_incomplete_per_page":
                round(
                    total[
                        "axe_incomplete"
                    ]
                    .fillna(0)
                    .median(),
                    2
                )
        }
    )

    return pd.DataFrame(
        rows
    )


# ============================================================
# BUILD DUAL-ENGINE SUMMARY
# ============================================================

def build_dual_engine_summary(
    dataframe
):

    dual = dataframe[
        dataframe[
            "analysis_mode"
        ]
        ==
        "custom_and_axe"
    ].copy()

    rows = []

    groups = [
        "Public University",
        "Private University",
        "News",
        "Government"
    ]

    numeric_columns = [
        "total_unified_findings",
        "confirmed_by_both",
        "custom_only",
        "axe_only",
        "axe_incomplete",
        "custom_findings",
        "axe_violation_findings",
        "comparable_violation_findings"
    ]

    for group_name in groups:

        group = dual[
            dual[
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

            "dual_engine_pages":
                len(
                    group
                )
        }

        for column in numeric_columns:

            values = (
                group[
                    column
                ]
                .fillna(0)
            )

            row[
                column
            ] = int(
                values.sum()
            )

            row[
                f"mean_{column}_per_page"
            ] = round(
                values.mean(),
                2
            )

            row[
                f"median_{column}_per_page"
            ] = round(
                values.median(),
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

        "dual_engine_pages":
            len(
                dual
            )
    }

    for column in numeric_columns:

        values = (
            dual[
                column
            ]
            .fillna(0)
        )

        total_row[
            column
        ] = int(
            values.sum()
        )

        total_row[
            f"mean_{column}_per_page"
        ] = round(
            values.mean(),
            2
        )

        total_row[
            f"median_{column}_per_page"
        ] = round(
            values.median(),
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
# LOAD CONTEXTUAL DATA FOR DUAL-ENGINE PAGES
# ============================================================

def load_dual_contextual(
    dual_dataframe
):

    frames = []

    for _, row in dual_dataframe.iterrows():

        stem = clean(
            row.get(
                "actual_analysis_stem",
                ""
            )
        )

        if not stem:
            continue

        file_path = (
            CONTEXTUAL_FILE_DIR
            /
            f"{stem}__contextual_recommendations.csv"
        )

        if not file_path.exists():
            continue

        try:

            df = pd.read_csv(
                file_path
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
# CONTEXTUAL SUMMARY
# ============================================================

def build_contextual_summary(
    contextual
):

    if (
        contextual.empty
        or
        "contextual_processed"
        not in contextual.columns
    ):

        return pd.DataFrame()

    processed = contextual[
        contextual[
            "contextual_processed"
        ]
        .apply(
            bool_value
        )
    ].copy()

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

        site_count = (
            group[
                "site_id"
            ]
            .nunique()
        )

        visual = 0
        manual = 0

        if (
            "contextual_visual_review_required"
            in group.columns
        ):

            visual = int(
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

            manual = int(
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

                "dual_engine_pages_with_context":
                    site_count,

                "contextual_findings":
                    len(
                        group
                    ),

                "mean_contextual_findings_per_page":
                    round(
                        len(group)
                        /
                        site_count,
                        2
                    )
                    if site_count
                    else 0.0,

                "visual_review_required":
                    visual,

                "visual_review_pct":
                    safe_percent(
                        visual,
                        len(group)
                    ),

                "manual_review_required":
                    manual,

                "manual_review_pct":
                    safe_percent(
                        manual,
                        len(group)
                    )
            }
        )

    total_sites = (
        processed[
            "site_id"
        ]
        .nunique()
        if not processed.empty
        else 0
    )

    visual_total = 0
    manual_total = 0

    if (
        "contextual_visual_review_required"
        in processed.columns
    ):

        visual_total = int(
            processed[
                "contextual_visual_review_required"
            ]
            .apply(
                bool_value
            )
            .sum()
        )

    if (
        "contextual_manual_review_required"
        in processed.columns
    ):

        manual_total = int(
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
            "experiment_group":
                "TOTAL",

            "dual_engine_pages_with_context":
                total_sites,

            "contextual_findings":
                len(
                    processed
                ),

            "mean_contextual_findings_per_page":
                round(
                    len(processed)
                    /
                    total_sites,
                    2
                )
                if total_sites
                else 0.0,

            "visual_review_required":
                visual_total,

            "visual_review_pct":
                safe_percent(
                    visual_total,
                    len(processed)
                ),

            "manual_review_required":
                manual_total,

            "manual_review_pct":
                safe_percent(
                    manual_total,
                    len(processed)
                )
        }
    )

    return pd.DataFrame(
        rows
    )


# ============================================================
# SOURCE MODE SUMMARY
# ============================================================

def build_source_mode_summary(
    completed
):

    summary = (
        completed
        .groupby(
            [
                "experiment_group",
                "analysis_mode"
            ]
        )
        .size()
        .reset_index(
            name="pages"
        )
    )

    return summary


# ============================================================
# WRITE METHODOLOGY NOTE
# ============================================================

def write_methodology_note(
    completed,
    dual
):

    path = (
        OUTPUT_DIR
        /
        "analysis_set_methodology.txt"
    )

    lines = []

    lines.append(
        "HOMEPAGE EXPERIMENT ANALYSIS SETS"
    )

    lines.append(
        "=" * 72
    )

    lines.append(
        ""
    )

    lines.append(
        (
            f"All completed homepage analyses: "
            f"{len(completed)}"
        )
    )

    lines.append(
        (
            f"Dual-engine analyses "
            f"(custom scanner + axe-core): "
            f"{len(dual)}"
        )
    )

    lines.append(
        (
            f"axe-only completed analyses: "
            f"{int((completed['analysis_mode'] == 'axe_only').sum())}"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "Analysis Set A — All completed pages"
    )

    lines.append(
        "-" * 72
    )

    lines.append(
        (
            "This set contains all successfully completed "
            "homepage analyses. It is appropriate for "
            "rendered-DOM/axe-core analyses because axe-core "
            "was available for all included pages."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "Analysis Set B — Dual-engine pages"
    )

    lines.append(
        "-" * 72
    )

    lines.append(
        (
            "This set contains only pages for which both the "
            "custom static scanner and axe-core produced usable "
            "analysis. Fusion overlap, custom-only findings, "
            "cross-tool comparison, and contextual-remediation "
            "results should be evaluated using this set."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "This separation avoids confounding organization "
            "type with scanner availability."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Because subgroup sizes in the dual-engine set are "
            "unequal and small for several categories, raw totals "
            "should not be interpreted as direct cross-group "
            "comparisons. Per-page means and medians should be "
            "reported, and strong inferential claims should be "
            "avoided."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "axe incomplete findings remain separate from "
            "confirmed violation findings."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Homepage-level results should not be interpreted "
            "as full website WCAG conformance assessments."
        )
    )

    path.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8"
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
        "HOMEPAGE ANALYSIS SET EXPORTER"
    )
    print(
        "=" * 80
    )
    print()

    # --------------------------------------------------------
    # CHECK FILES
    # --------------------------------------------------------

    required_files = [
        WEBSITES_FILE,
        BATCH_STATUS_FILE,
        PAGE_SUMMARY_FILE
    ]

    for file_path in required_files:

        if not file_path.exists():

            print(
                "ERROR: Required file not found:"
            )

            print(
                file_path
            )

            return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    websites = load_master_sample()

    status = load_batch_status()

    completed = build_completed_index(
        websites,
        status
    )

    page_summary = load_page_summary()

    completed = attach_page_metrics(
        completed,
        page_summary
    )

    dual = completed[
        completed[
            "analysis_mode"
        ]
        ==
        "custom_and_axe"
    ].copy()

    axe_only = completed[
        completed[
            "analysis_mode"
        ]
        ==
        "axe_only"
    ].copy()

    # --------------------------------------------------------
    # BUILD SUMMARIES
    # --------------------------------------------------------

    source_mode_summary = (
        build_source_mode_summary(
            completed
        )
    )

    all_completed_summary = (
        build_all_completed_summary(
            completed
        )
    )

    dual_engine_summary = (
        build_dual_engine_summary(
            completed
        )
    )

    contextual = (
        load_dual_contextual(
            dual
        )
    )

    contextual_summary = (
        build_contextual_summary(
            contextual
        )
    )

    # --------------------------------------------------------
    # EXPORT DATASETS
    # --------------------------------------------------------

    all_completed_path = (
        OUTPUT_DIR
        /
        "homepage_all_completed.csv"
    )

    dual_path = (
        OUTPUT_DIR
        /
        "homepage_dual_engine.csv"
    )

    axe_only_path = (
        OUTPUT_DIR
        /
        "homepage_axe_only.csv"
    )

    completed.to_csv(
        all_completed_path,
        index=False
    )

    dual.to_csv(
        dual_path,
        index=False
    )

    axe_only.to_csv(
        axe_only_path,
        index=False
    )

    source_mode_summary.to_csv(
        OUTPUT_DIR
        /
        "source_mode_by_group.csv",
        index=False
    )

    all_completed_summary.to_csv(
        OUTPUT_DIR
        /
        "axe_summary_all_completed.csv",
        index=False
    )

    dual_engine_summary.to_csv(
        OUTPUT_DIR
        /
        "fusion_summary_dual_engine.csv",
        index=False
    )

    contextual_summary.to_csv(
        OUTPUT_DIR
        /
        "contextual_summary_dual_engine.csv",
        index=False
    )

    methodology_path = (
        write_methodology_note(
            completed,
            dual
        )
    )

    # --------------------------------------------------------
    # TERMINAL SUMMARY
    # --------------------------------------------------------

    print(
        "All completed pages:",
        len(
            completed
        )
    )

    print(
        "Dual-engine pages:",
        len(
            dual
        )
    )

    print(
        "axe-only pages:",
        len(
            axe_only
        )
    )

    print()

    print(
        "Dual-engine pages by group:"
    )

    print(
        dual[
            "experiment_group"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "=" * 80
    )

    print(
        "ALL-COMPLETED AXE SUMMARY"
    )

    print(
        "=" * 80
    )

    print()

    print(
        all_completed_summary.to_string(
            index=False
        )
    )

    print()

    print(
        "=" * 80
    )

    print(
        "DUAL-ENGINE FUSION SUMMARY"
    )

    print(
        "=" * 80
    )

    print()

    print(
        dual_engine_summary.to_string(
            index=False
        )
    )

    print()

    print(
        "=" * 80
    )

    print(
        "DUAL-ENGINE CONTEXTUAL SUMMARY"
    )

    print(
        "=" * 80
    )

    print()

    if contextual_summary.empty:

        print(
            "No contextual data available."
        )

    else:

        print(
            contextual_summary.to_string(
                index=False
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
        "Methodology note:"
    )

    print(
        methodology_path
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
