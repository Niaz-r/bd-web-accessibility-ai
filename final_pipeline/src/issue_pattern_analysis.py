import os
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# FILES
# ============================================================

WEBSITE_FILE = (
    "final_pipeline/data/final/"
    "website_accessibility_dataset.csv"
)

PAGE_FILE = (
    "final_pipeline/data/final/"
    "page_accessibility_dataset.csv"
)

REPORT_DIR = "final_pipeline/reports"

FIGURE_DIR = (
    "final_pipeline/reports/figures"
)


# ============================================================
# OUTPUT FILES
# ============================================================

OVERALL_ISSUES_FILE = (
    f"{REPORT_DIR}/overall_issue_distribution.csv"
)

ORG_ISSUES_FILE = (
    f"{REPORT_DIR}/organization_issue_distribution.csv"
)

NORMALIZED_ISSUES_FILE = (
    f"{REPORT_DIR}/organization_issue_rates.csv"
)

SEVERITY_FILE = (
    f"{REPORT_DIR}/severity_distribution.csv"
)


# ============================================================
# ISSUE TYPES
# ============================================================

ISSUE_COLUMNS = [
    "missing_alt",
    "empty_alt",
    "missing_h1",
    "multiple_h1",
    "empty_heading",
    "heading_order",
    "empty_link_text",
    "generic_link_text"
]


ISSUE_LABELS = {
    "missing_alt":
        "Missing image alt",

    "empty_alt":
        "Empty image alt",

    "missing_h1":
        "Missing H1",

    "multiple_h1":
        "Multiple H1",

    "empty_heading":
        "Empty heading",

    "heading_order":
        "Heading order",

    "empty_link_text":
        "Empty link text",

    "generic_link_text":
        "Generic link text"
}


GROUP_COLUMN = "organization_type"


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )

    os.makedirs(
        FIGURE_DIR,
        exist_ok=True
    )

    websites = pd.read_csv(
        WEBSITE_FILE
    )

    pages = pd.read_csv(
        PAGE_FILE
    )

    print()
    print("=" * 75)
    print("ACCESSIBILITY ISSUE PATTERN ANALYSIS")
    print("=" * 75)

    print(
        "Websites:",
        len(websites)
    )

    print(
        "Pages:",
        len(pages)
    )

    print(
        "Total issues:",
        websites["total_issues"].sum()
    )

    # ========================================================
    # 1. OVERALL ISSUE DISTRIBUTION
    # ========================================================

    total_issues = (
        websites[
            "total_issues"
        ].sum()
    )

    overall_rows = []

    for issue in ISSUE_COLUMNS:

        count = (
            websites[
                issue
            ].sum()
        )

        percentage = (
            count
            / total_issues
            * 100
        )

        overall_rows.append(
            {
                "issue_type":
                    issue,

                "issue_label":
                    ISSUE_LABELS[
                        issue
                    ],

                "count":
                    count,

                "percentage":
                    percentage
            }
        )

    overall = pd.DataFrame(
        overall_rows
    )

    overall = overall.sort_values(
        "count",
        ascending=False
    )

    overall.to_csv(
        OVERALL_ISSUES_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("OVERALL ISSUE DISTRIBUTION")
    print("=" * 75)

    print(
        overall
        .round(3)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 2. ISSUE DISTRIBUTION BY ORGANIZATION TYPE
    # ========================================================

    org_rows = []

    for org_type, group in websites.groupby(
        GROUP_COLUMN
    ):

        group_total = (
            group[
                "total_issues"
            ].sum()
        )

        pages_scanned = (
            group[
                "pages_scanned"
            ].sum()
        )

        for issue in ISSUE_COLUMNS:

            count = (
                group[
                    issue
                ].sum()
            )

            if group_total > 0:

                issue_share = (
                    count
                    / group_total
                    * 100
                )

            else:

                issue_share = 0

            if pages_scanned > 0:

                issues_per_page = (
                    count
                    / pages_scanned
                )

            else:

                issues_per_page = 0

            org_rows.append(
                {
                    "organization_type":
                        org_type,

                    "issue_type":
                        issue,

                    "issue_label":
                        ISSUE_LABELS[
                            issue
                        ],

                    "websites":
                        len(group),

                    "pages":
                        pages_scanned,

                    "count":
                        count,

                    "percentage_of_group_issues":
                        issue_share,

                    "issues_per_page":
                        issues_per_page
                }
            )

    organization_issues = (
        pd.DataFrame(
            org_rows
        )
    )

    organization_issues.to_csv(
        ORG_ISSUES_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("ISSUES BY ORGANIZATION TYPE")
    print("=" * 75)

    print(
        organization_issues
        .round(3)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 3. WEBSITE-NORMALIZED ISSUE RATES
    #
    # Each website receives equal statistical/descriptive
    # weight regardless of whether it has 1 or 10 pages.
    # ========================================================

    rate_data = websites[
        [
            "website_id",
            GROUP_COLUMN,
            "pages_scanned"
        ]
        + ISSUE_COLUMNS
    ].copy()

    for issue in ISSUE_COLUMNS:

        rate_data[
            f"{issue}_per_page"
        ] = (
            rate_data[
                issue
            ]
            /
            rate_data[
                "pages_scanned"
            ]
        )

    normalized_rows = []

    for org_type, group in rate_data.groupby(
        GROUP_COLUMN
    ):

        for issue in ISSUE_COLUMNS:

            variable = (
                f"{issue}_per_page"
            )

            values = (
                group[
                    variable
                ]
            )

            normalized_rows.append(
                {
                    "organization_type":
                        org_type,

                    "issue_type":
                        issue,

                    "issue_label":
                        ISSUE_LABELS[
                            issue
                        ],

                    "websites":
                        len(values),

                    "mean_per_page":
                        values.mean(),

                    "median_per_page":
                        values.median(),

                    "std_per_page":
                        values.std(
                            ddof=1
                        ),

                    "min_per_page":
                        values.min(),

                    "max_per_page":
                        values.max()
                }
            )

    normalized = pd.DataFrame(
        normalized_rows
    )

    normalized.to_csv(
        NORMALIZED_ISSUES_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("WEBSITE-NORMALIZED ISSUE RATES")
    print("=" * 75)

    print(
        normalized
        .round(4)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 4. SEVERITY DISTRIBUTION
    # ========================================================

    severity_rows = []

    # Overall
    overall_high = (
        websites[
            "high_issues"
        ].sum()
    )

    overall_medium = (
        websites[
            "medium_issues"
        ].sum()
    )

    overall_severity_total = (
        overall_high
        + overall_medium
    )

    severity_rows.append(
        {
            "organization_type":
                "Overall",

            "high_issues":
                overall_high,

            "medium_issues":
                overall_medium,

            "total_issues":
                overall_severity_total,

            "high_percentage":
                (
                    overall_high
                    / overall_severity_total
                    * 100
                ),

            "medium_percentage":
                (
                    overall_medium
                    / overall_severity_total
                    * 100
                )
        }
    )

    # By organization
    for org_type, group in websites.groupby(
        GROUP_COLUMN
    ):

        high = (
            group[
                "high_issues"
            ].sum()
        )

        medium = (
            group[
                "medium_issues"
            ].sum()
        )

        total = (
            high
            + medium
        )

        severity_rows.append(
            {
                "organization_type":
                    org_type,

                "high_issues":
                    high,

                "medium_issues":
                    medium,

                "total_issues":
                    total,

                "high_percentage":
                    (
                        high
                        / total
                        * 100
                        if total > 0
                        else 0
                    ),

                "medium_percentage":
                    (
                        medium
                        / total
                        * 100
                        if total > 0
                        else 0
                    )
            }
        )

    severity = pd.DataFrame(
        severity_rows
    )

    severity.to_csv(
        SEVERITY_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("SEVERITY DISTRIBUTION")
    print("=" * 75)

    print(
        severity
        .round(3)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # FIGURE 1
    # OVERALL ISSUE TYPE DISTRIBUTION
    # ========================================================

    plot_data = (
        overall
        .sort_values(
            "count",
            ascending=True
        )
    )

    plt.figure(
        figsize=(10, 6)
    )

    plt.barh(
        plot_data[
            "issue_label"
        ],
        plot_data[
            "count"
        ]
    )

    plt.xlabel(
        "Number of detected issues"
    )

    plt.ylabel(
        "Accessibility issue type"
    )

    plt.title(
        "Overall Distribution of "
        "Detected Accessibility Issues"
    )

    plt.tight_layout()

    plt.savefig(
        f"{FIGURE_DIR}/overall_issue_distribution.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    # ========================================================
    # FIGURE 2
    # MEAN ISSUES PER PAGE BY ORGANIZATION TYPE
    # ========================================================

    mean_issue_data = (
        websites
        .groupby(
            GROUP_COLUMN
        )[
            "mean_issues_per_page"
        ]
        .mean()
        .sort_values()
    )

    plt.figure(
        figsize=(9, 6)
    )

    plt.barh(
        mean_issue_data.index,
        mean_issue_data.values
    )

    plt.xlabel(
        "Mean detected issues per page"
    )

    plt.ylabel(
        "Organization type"
    )

    plt.title(
        "Mean Accessibility Issues per Page "
        "by Organization Type"
    )

    plt.tight_layout()

    plt.savefig(
        f"{FIGURE_DIR}/mean_issues_by_organization.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    # ========================================================
    # FIGURE 3
    # ACCESSIBILITY SCORE BOXPLOT
    # ========================================================

    organization_order = sorted(
        websites[
            GROUP_COLUMN
        ].unique()
    )

    score_data = [
        websites[
            websites[
                GROUP_COLUMN
            ] == org
        ][
            "mean_accessibility_score"
        ].dropna().values

        for org in organization_order
    ]

    plt.figure(
        figsize=(10, 6)
    )

    plt.boxplot(
        score_data,
        tick_labels=organization_order
    )

    plt.ylabel(
        "Mean accessibility score"
    )

    plt.xlabel(
        "Organization type"
    )

    plt.title(
        "Distribution of Website Accessibility Scores"
    )

    plt.xticks(
        rotation=20,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        f"{FIGURE_DIR}/accessibility_score_boxplot.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    # ========================================================
    # FIGURE 4
    # ISSUES PER PAGE BOXPLOT
    # ========================================================

    issue_page_data = [
        websites[
            websites[
                GROUP_COLUMN
            ] == org
        ][
            "mean_issues_per_page"
        ].dropna().values

        for org in organization_order
    ]

    plt.figure(
        figsize=(10, 6)
    )

    plt.boxplot(
        issue_page_data,
        tick_labels=organization_order
    )

    plt.ylabel(
        "Mean detected issues per page"
    )

    plt.xlabel(
        "Organization type"
    )

    plt.title(
        "Distribution of Accessibility Issues per Page"
    )

    plt.xticks(
        rotation=20,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        f"{FIGURE_DIR}/issues_per_page_boxplot.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    # ========================================================
    # FIGURE 5
    # HIGH VS MEDIUM SEVERITY
    # ========================================================

    severity_plot = (
        severity[
            severity[
                "organization_type"
            ] != "Overall"
        ]
        .set_index(
            "organization_type"
        )
    )

    severity_plot[
        [
            "high_percentage",
            "medium_percentage"
        ]
    ].plot(
        kind="bar",
        stacked=True,
        figsize=(10, 6)
    )

    plt.ylabel(
        "Percentage of detected issues"
    )

    plt.xlabel(
        "Organization type"
    )

    plt.title(
        "Severity Composition by Organization Type"
    )

    plt.legend(
        [
            "High",
            "Medium"
        ]
    )

    plt.xticks(
        rotation=20,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        f"{FIGURE_DIR}/severity_by_organization.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 75)
    print("FILES CREATED")
    print("=" * 75)

    print(
        OVERALL_ISSUES_FILE
    )

    print(
        ORG_ISSUES_FILE
    )

    print(
        NORMALIZED_ISSUES_FILE
    )

    print(
        SEVERITY_FILE
    )

    print()

    print("Figures:")

    print(
        f"{FIGURE_DIR}/"
        "overall_issue_distribution.png"
    )

    print(
        f"{FIGURE_DIR}/"
        "mean_issues_by_organization.png"
    )

    print(
        f"{FIGURE_DIR}/"
        "accessibility_score_boxplot.png"
    )

    print(
        f"{FIGURE_DIR}/"
        "issues_per_page_boxplot.png"
    )

    print(
        f"{FIGURE_DIR}/"
        "severity_by_organization.png"
    )

    print()
    print("=" * 75)
    print("IMPORTANT INTERPRETATION NOTE")
    print("=" * 75)

    print(
        "Raw issue counts are descriptive. "
        "Organization groups contain different "
        "numbers of websites and pages."
    )

    print(
        "Use website-normalized rates, medians, "
        "and statistical tests when comparing "
        "organization types."
    )


if __name__ == "__main__":
    main()
