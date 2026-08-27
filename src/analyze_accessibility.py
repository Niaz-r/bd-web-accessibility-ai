import pandas as pd

INPUT_FILE = "data/website_accessibility_dataset.csv"


def main():

    df = pd.read_csv(INPUT_FILE)

    print("=" * 70)
    print("ACCESSIBILITY DATA ANALYSIS")
    print("=" * 70)

    # =========================================================
    # Overall statistics
    # =========================================================

    print("\nOVERALL DATASET\n")

    print("Websites:", len(df))
    print("Pages:", df["pages_scanned"].sum())
    print("Total issues:", df["total_issues"].sum())
    print("High issues:", df["high_issues"].sum())
    print("Medium issues:", df["medium_issues"].sum())

    print(
        "Overall mean website score:",
        round(df["mean_accessibility_score"].mean(), 2)
    )

    # =========================================================
    # Organization-level statistics
    # =========================================================

    group_stats = (
        df.groupby("organization_type")
        .agg(
            websites=("website_id", "count"),
            pages=("pages_scanned", "sum"),

            total_issues=("total_issues", "sum"),

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
        .round(2)
        .sort_values("mean_score")
    )

    print("\n" + "=" * 70)
    print("ORGANIZATION TYPE COMPARISON")
    print("=" * 70)

    print(group_stats.to_string())

    # =========================================================
    # Issue category analysis
    # =========================================================

    category_stats = (
        df.groupby("organization_type")
        [
            [
                "image_issues",
                "heading_issues",
                "link_issues",
                "form_issues"
            ]
        ]
        .sum()
    )

    category_stats["all_issues"] = (
        category_stats.sum(axis=1)
    )

    for category in [
        "image_issues",
        "heading_issues",
        "link_issues",
        "form_issues"
    ]:

        category_stats[
            category + "_pct"
        ] = (
            category_stats[category]
            / category_stats["all_issues"]
            * 100
        ).round(2)

    print("\n" + "=" * 70)
    print("ISSUE CATEGORY DISTRIBUTION")
    print("=" * 70)

    print(category_stats.to_string())

    # =========================================================
    # Severity analysis
    # =========================================================

    severity_stats = (
        df.groupby("organization_type")
        [
            [
                "high_issues",
                "medium_issues"
            ]
        ]
        .sum()
    )

    severity_stats["total"] = (
        severity_stats["high_issues"]
        + severity_stats["medium_issues"]
    )

    severity_stats["high_pct"] = (
        severity_stats["high_issues"]
        / severity_stats["total"]
        * 100
    ).round(2)

    severity_stats["medium_pct"] = (
        severity_stats["medium_issues"]
        / severity_stats["total"]
        * 100
    ).round(2)

    print("\n" + "=" * 70)
    print("SEVERITY DISTRIBUTION")
    print("=" * 70)

    print(severity_stats.to_string())

    # =========================================================
    # Website ranking
    # =========================================================

    ranking = df[
        [
            "website_id",
            "website_name",
            "organization_type",
            "pages_scanned",
            "mean_issues_per_page",
            "mean_accessibility_score"
        ]
    ].sort_values(
        "mean_accessibility_score",
        ascending=False
    )

    print("\n" + "=" * 70)
    print("WEBSITE ACCESSIBILITY RANKING")
    print("=" * 70)

    print(ranking.to_string(index=False))

    # =========================================================
    # Lowest scoring websites
    # =========================================================

    print("\n" + "=" * 70)
    print("LOWEST SCORING WEBSITES")
    print("=" * 70)

    print(
        ranking.tail(10)
        .sort_values("mean_accessibility_score")
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
