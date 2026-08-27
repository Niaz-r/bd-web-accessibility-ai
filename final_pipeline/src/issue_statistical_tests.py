import itertools
import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu


INPUT_FILE = (
    "final_pipeline/data/final/"
    "website_accessibility_dataset.csv"
)

OUTPUT_FILE = (
    "final_pipeline/reports/"
    "issue_kruskal_wallis_results.csv"
)

PAIRWISE_FILE = (
    "final_pipeline/reports/"
    "issue_pairwise_comparisons.csv"
)

ALPHA = 0.05

GROUP = "organization_type"

ISSUES = [
    "missing_alt",
    "empty_alt",
    "missing_h1",
    "multiple_h1",
    "empty_heading",
    "heading_order",
    "empty_link_text",
    "generic_link_text"
]


def holm_correction(p_values):

    p_values = np.asarray(
        p_values,
        dtype=float
    )

    m = len(p_values)

    order = np.argsort(p_values)

    adjusted = np.zeros(
        m,
        dtype=float
    )

    previous = 0

    for rank, index in enumerate(order):

        value = (
            p_values[index]
            * (m - rank)
        )

        value = min(
            value,
            1.0
        )

        value = max(
            value,
            previous
        )

        adjusted[index] = value

        previous = value

    return adjusted


def main():

    df = pd.read_csv(
        INPUT_FILE
    )

    print()
    print("=" * 75)
    print("ISSUE-SPECIFIC STATISTICAL TESTS")
    print("=" * 75)

    # ========================================================
    # 1. NORMALIZE EACH ISSUE BY PAGES SCANNED
    # ========================================================

    for issue in ISSUES:

        df[
            f"{issue}_per_page"
        ] = (
            df[issue]
            /
            df["pages_scanned"]
        )

    # ========================================================
    # 2. KRUSKAL-WALLIS FOR EACH ISSUE TYPE
    # ========================================================

    results = []

    for issue in ISSUES:

        variable = (
            f"{issue}_per_page"
        )

        groups = []

        for _, group in df.groupby(
            GROUP
        ):

            groups.append(
                group[
                    variable
                ]
                .dropna()
                .values
            )

        H, p = kruskal(
            *groups
        )

        n = sum(
            len(x)
            for x in groups
        )

        k = len(groups)

        if n > k:

            epsilon_squared = (
                H - k + 1
            ) / (
                n - k
            )

            epsilon_squared = max(
                0,
                epsilon_squared
            )

        else:

            epsilon_squared = np.nan

        results.append(
            {
                "issue_type":
                    issue,

                "H_statistic":
                    H,

                "raw_p_value":
                    p,

                "epsilon_squared":
                    epsilon_squared
            }
        )

    results_df = pd.DataFrame(
        results
    )

    # ========================================================
    # 3. HOLM CORRECTION ACROSS 8 ISSUE TESTS
    # ========================================================

    results_df[
        "holm_adjusted_p"
    ] = holm_correction(
        results_df[
            "raw_p_value"
        ].values
    )

    results_df[
        "significant_after_holm"
    ] = (
        results_df[
            "holm_adjusted_p"
        ] < ALPHA
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("KRUSKAL-WALLIS ISSUE RESULTS")
    print("=" * 75)

    print(
        results_df
        .sort_values(
            "raw_p_value"
        )
        .round(6)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 4. PAIRWISE TESTS ONLY FOR SIGNIFICANT ISSUE TYPES
    # ========================================================

    pairwise_results = []

    organizations = sorted(
        df[
            GROUP
        ]
        .dropna()
        .unique()
    )

    significant_issues = (
        results_df[
            results_df[
                "significant_after_holm"
            ]
        ][
            "issue_type"
        ]
        .tolist()
    )

    for issue in significant_issues:

        variable = (
            f"{issue}_per_page"
        )

        temporary = []

        for group1, group2 in itertools.combinations(
            organizations,
            2
        ):

            x = (
                df[
                    df[GROUP] == group1
                ][variable]
                .dropna()
                .values
            )

            y = (
                df[
                    df[GROUP] == group2
                ][variable]
                .dropna()
                .values
            )

            U, p = mannwhitneyu(
                x,
                y,
                alternative="two-sided"
            )

            temporary.append(
                {
                    "issue_type":
                        issue,

                    "group_1":
                        group1,

                    "group_2":
                        group2,

                    "n_1":
                        len(x),

                    "n_2":
                        len(y),

                    "median_1":
                        np.median(x),

                    "median_2":
                        np.median(y),

                    "U_statistic":
                        U,

                    "raw_p_value":
                        p
                }
            )

        adjusted = holm_correction(
            [
                row["raw_p_value"]
                for row in temporary
            ]
        )

        for row, adjusted_p in zip(
            temporary,
            adjusted
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

            pairwise_results.append(
                row
            )

    pairwise_df = pd.DataFrame(
        pairwise_results
    )

    pairwise_df.to_csv(
        PAIRWISE_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("PAIRWISE RESULTS")
    print("=" * 75)

    if len(pairwise_df) == 0:

        print(
            "No issue types remained statistically "
            "significant after Holm correction."
        )

    else:

        print(
            pairwise_df
            .round(6)
            .to_string(
                index=False
            )
        )

    print()
    print("=" * 75)
    print("FILES CREATED")
    print("=" * 75)

    print(OUTPUT_FILE)
    print(PAIRWISE_FILE)


if __name__ == "__main__":
    main()
