import os
import itertools
import numpy as np
import pandas as pd

from scipy.stats import (
    shapiro,
    levene,
    kruskal,
    mannwhitneyu
)


# ============================================================
# FILES
# ============================================================

INPUT_FILE = (
    "final_pipeline/data/final/"
    "website_accessibility_dataset.csv"
)

REPORT_DIR = "final_pipeline/reports"

DESCRIPTIVE_FILE = (
    f"{REPORT_DIR}/descriptive_statistics.csv"
)

NORMALITY_FILE = (
    f"{REPORT_DIR}/normality_tests.csv"
)

KRUSKAL_FILE = (
    f"{REPORT_DIR}/kruskal_wallis_results.csv"
)

PAIRWISE_FILE = (
    f"{REPORT_DIR}/pairwise_comparisons.csv"
)

ISSUE_DISTRIBUTION_FILE = (
    f"{REPORT_DIR}/issue_distribution.csv"
)

GROUP_SUMMARY_FILE = (
    f"{REPORT_DIR}/organization_summary.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

ALPHA = 0.05

GROUP_COLUMN = "organization_type"

MAIN_VARIABLES = [
    "mean_accessibility_score",
    "mean_issues_per_page"
]

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


# ============================================================
# HOLM MULTIPLE-COMPARISON CORRECTION
# ============================================================

def holm_correction(p_values):

    p_values = np.array(
        p_values,
        dtype=float
    )

    m = len(p_values)

    order = np.argsort(p_values)

    adjusted = np.empty(
        m,
        dtype=float
    )

    running_max = 0

    for rank, index in enumerate(order):

        multiplier = (
            m - rank
        )

        corrected = (
            p_values[index]
            * multiplier
        )

        corrected = min(
            corrected,
            1.0
        )

        running_max = max(
            running_max,
            corrected
        )

        adjusted[index] = (
            running_max
        )

    return adjusted


# ============================================================
# EFFECT SIZE FOR MANN-WHITNEY
# ============================================================

def rank_biserial_from_u(
    u_statistic,
    n1,
    n2
):

    if n1 == 0 or n2 == 0:
        return np.nan

    return (
        1
        -
        (
            2 * u_statistic
            /
            (n1 * n2)
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )

    df = pd.read_csv(
        INPUT_FILE
    )

    print()
    print("=" * 75)
    print("STATISTICAL ACCESSIBILITY ANALYSIS")
    print("=" * 75)

    print(
        "Websites:",
        len(df)
    )

    print()

    print("Organization groups:")

    print(
        df[
            GROUP_COLUMN
        ]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # 1. ORGANIZATION SUMMARY
    # ========================================================

    organization_summary = (
        df
        .groupby(
            GROUP_COLUMN
        )
        .agg(

            websites=(
                "website_id",
                "count"
            ),

            pages=(
                "pages_scanned",
                "sum"
            ),

            total_issues=(
                "total_issues",
                "sum"
            ),

            high_issues=(
                "high_issues",
                "sum"
            ),

            medium_issues=(
                "medium_issues",
                "sum"
            ),

            mean_issues_per_page=(
                "mean_issues_per_page",
                "mean"
            ),

            median_issues_per_page=(
                "mean_issues_per_page",
                "median"
            ),

            mean_score=(
                "mean_accessibility_score",
                "mean"
            ),

            median_score=(
                "mean_accessibility_score",
                "median"
            ),

            min_score=(
                "mean_accessibility_score",
                "min"
            ),

            max_score=(
                "mean_accessibility_score",
                "max"
            )
        )
        .reset_index()
    )

    organization_summary.to_csv(
        GROUP_SUMMARY_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("ORGANIZATION SUMMARY")
    print("=" * 75)

    print(
        organization_summary
        .round(3)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 2. DESCRIPTIVE STATISTICS
    # ========================================================

    descriptive_rows = []

    for variable in MAIN_VARIABLES:

        for group_name, group in df.groupby(
            GROUP_COLUMN
        ):

            values = (
                group[variable]
                .dropna()
            )

            descriptive_rows.append(
                {
                    "variable": variable,
                    "organization_type":
                        group_name,

                    "n":
                        len(values),

                    "mean":
                        values.mean(),

                    "median":
                        values.median(),

                    "std":
                        values.std(
                            ddof=1
                        ),

                    "min":
                        values.min(),

                    "q1":
                        values.quantile(
                            0.25
                        ),

                    "q3":
                        values.quantile(
                            0.75
                        ),

                    "iqr":
                        (
                            values.quantile(
                                0.75
                            )
                            -
                            values.quantile(
                                0.25
                            )
                        ),

                    "max":
                        values.max()
                }
            )

    descriptive = pd.DataFrame(
        descriptive_rows
    )

    descriptive.to_csv(
        DESCRIPTIVE_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("DESCRIPTIVE STATISTICS")
    print("=" * 75)

    print(
        descriptive
        .round(4)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 3. NORMALITY CHECK — SHAPIRO-WILK
    # ========================================================

    normality_rows = []

    for variable in MAIN_VARIABLES:

        for group_name, group in df.groupby(
            GROUP_COLUMN
        ):

            values = (
                group[variable]
                .dropna()
            )

            if len(values) >= 3:

                statistic, p_value = (
                    shapiro(values)
                )

            else:

                statistic = np.nan
                p_value = np.nan

            normality_rows.append(
                {
                    "variable":
                        variable,

                    "organization_type":
                        group_name,

                    "n":
                        len(values),

                    "W_statistic":
                        statistic,

                    "p_value":
                        p_value,

                    "normal_at_0.05":
                        (
                            p_value >= ALPHA
                            if not np.isnan(
                                p_value
                            )
                            else False
                        )
                }
            )

    normality = pd.DataFrame(
        normality_rows
    )

    normality.to_csv(
        NORMALITY_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("SHAPIRO-WILK NORMALITY TEST")
    print("=" * 75)

    print(
        normality
        .round(6)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 4. LEVENE VARIANCE CHECK
    # ========================================================

    print()
    print("=" * 75)
    print("LEVENE VARIANCE TEST")
    print("=" * 75)

    for variable in MAIN_VARIABLES:

        groups = [
            group[
                variable
            ]
            .dropna()
            .values

            for _, group
            in df.groupby(
                GROUP_COLUMN
            )
        ]

        levene_stat, levene_p = (
            levene(
                *groups,
                center="median"
            )
        )

        print()
        print(
            f"Variable: {variable}"
        )

        print(
            f"Levene statistic: "
            f"{levene_stat:.6f}"
        )

        print(
            f"p-value: "
            f"{levene_p:.6f}"
        )

    # ========================================================
    # 5. KRUSKAL-WALLIS
    # ========================================================

    kruskal_rows = []

    for variable in MAIN_VARIABLES:

        groups = []

        group_names = []

        for group_name, group in df.groupby(
            GROUP_COLUMN
        ):

            values = (
                group[variable]
                .dropna()
                .values
            )

            groups.append(
                values
            )

            group_names.append(
                group_name
            )

        h_stat, p_value = (
            kruskal(
                *groups
            )
        )

        n = sum(
            len(values)
            for values in groups
        )

        k = len(
            groups
        )

        # ----------------------------------------------------
        # Epsilon-squared effect size
        # ----------------------------------------------------

        if n > k:

            epsilon_squared = (
                (
                    h_stat
                    - k
                    + 1
                )
                /
                (
                    n
                    - k
                )
            )

            epsilon_squared = max(
                0,
                epsilon_squared
            )

        else:

            epsilon_squared = (
                np.nan
            )

        kruskal_rows.append(
            {
                "variable":
                    variable,

                "groups":
                    k,

                "n":
                    n,

                "H_statistic":
                    h_stat,

                "p_value":
                    p_value,

                "epsilon_squared":
                    epsilon_squared,

                "significant_at_0.05":
                    p_value < ALPHA
            }
        )

    kruskal_results = (
        pd.DataFrame(
            kruskal_rows
        )
    )

    kruskal_results.to_csv(
        KRUSKAL_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("KRUSKAL-WALLIS RESULTS")
    print("=" * 75)

    print(
        kruskal_results
        .round(6)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 6. PAIRWISE MANN-WHITNEY U
    #
    # Run only when overall Kruskal-Wallis is significant.
    # Holm correction controls family-wise error.
    # ========================================================

    pairwise_rows = []

    unique_groups = sorted(
        df[
            GROUP_COLUMN
        ]
        .dropna()
        .unique()
    )

    for variable in MAIN_VARIABLES:

        kw_row = (
            kruskal_results[
                kruskal_results[
                    "variable"
                ] == variable
            ]
            .iloc[0]
        )

        if not kw_row[
            "significant_at_0.05"
        ]:
            continue

        temporary_rows = []

        for group1, group2 in itertools.combinations(
            unique_groups,
            2
        ):

            values1 = (
                df[
                    df[
                        GROUP_COLUMN
                    ] == group1
                ][variable]
                .dropna()
                .values
            )

            values2 = (
                df[
                    df[
                        GROUP_COLUMN
                    ] == group2
                ][variable]
                .dropna()
                .values
            )

            u_stat, p_value = (
                mannwhitneyu(
                    values1,
                    values2,
                    alternative="two-sided"
                )
            )

            effect = (
                rank_biserial_from_u(
                    u_stat,
                    len(values1),
                    len(values2)
                )
            )

            temporary_rows.append(
                {
                    "variable":
                        variable,

                    "group_1":
                        group1,

                    "group_2":
                        group2,

                    "n_1":
                        len(values1),

                    "n_2":
                        len(values2),

                    "median_1":
                        np.median(
                            values1
                        ),

                    "median_2":
                        np.median(
                            values2
                        ),

                    "U_statistic":
                        u_stat,

                    "raw_p_value":
                        p_value,

                    "rank_biserial_effect":
                        effect
                }
            )

        raw_p_values = [
            row[
                "raw_p_value"
            ]
            for row
            in temporary_rows
        ]

        adjusted_p_values = (
            holm_correction(
                raw_p_values
            )
        )

        for row, adjusted_p in zip(
            temporary_rows,
            adjusted_p_values
        ):

            row[
                "holm_adjusted_p"
            ] = adjusted_p

            row[
                "significant_after_holm"
            ] = (
                adjusted_p
                < ALPHA
            )

            pairwise_rows.append(
                row
            )

    pairwise = pd.DataFrame(
        pairwise_rows
    )

    pairwise.to_csv(
        PAIRWISE_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("PAIRWISE MANN-WHITNEY U TESTS")
    print("=" * 75)

    if len(pairwise) > 0:

        print(
            pairwise
            .round(6)
            .to_string(
                index=False
            )
        )

    else:

        print(
            "No pairwise tests were required "
            "because no overall Kruskal-Wallis "
            "test was statistically significant."
        )

    # ========================================================
    # 7. ISSUE DISTRIBUTION BY ORGANIZATION TYPE
    # ========================================================

    issue_rows = []

    for group_name, group in df.groupby(
        GROUP_COLUMN
    ):

        group_total = (
            group[
                "total_issues"
            ].sum()
        )

        for issue in ISSUE_COLUMNS:

            count = (
                group[
                    issue
                ].sum()
            )

            if group_total > 0:

                percentage = (
                    count
                    / group_total
                    * 100
                )

            else:

                percentage = 0

            issue_rows.append(
                {
                    "organization_type":
                        group_name,

                    "issue_type":
                        issue,

                    "count":
                        count,

                    "percentage_of_group_issues":
                        percentage
                }
            )

    issue_distribution = (
        pd.DataFrame(
            issue_rows
        )
    )

    issue_distribution.to_csv(
        ISSUE_DISTRIBUTION_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("ISSUE DISTRIBUTION")
    print("=" * 75)

    print(
        issue_distribution
        .round(3)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 8. FINAL OUTPUT SUMMARY
    # ========================================================

    print()
    print("=" * 75)
    print("FILES CREATED")
    print("=" * 75)

    print(
        GROUP_SUMMARY_FILE
    )

    print(
        DESCRIPTIVE_FILE
    )

    print(
        NORMALITY_FILE
    )

    print(
        KRUSKAL_FILE
    )

    print(
        PAIRWISE_FILE
    )

    print(
        ISSUE_DISTRIBUTION_FILE
    )

    print()

    print("=" * 75)
    print("IMPORTANT")
    print("=" * 75)

    print(
        "Statistical tests use WEBSITE-LEVEL "
        "observations, not individual pages."
    )

    print(
        "This avoids treating multiple pages "
        "from the same website as independent "
        "websites."
    )

    print(
        "Accessibility score is a "
        "research-defined heuristic and is not "
        "an official WCAG conformance score."
    )


if __name__ == "__main__":
    main()
