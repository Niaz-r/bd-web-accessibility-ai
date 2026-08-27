import pandas as pd


# ============================================================
# FILES
# ============================================================

PAGE_FILE = (
    "final_pipeline/data/final/page_accessibility_dataset.csv"
)

WEBSITE_FILE = (
    "final_pipeline/data/input/websites.xlsx"
)

OUTPUT_FILE = (
    "final_pipeline/data/final/website_accessibility_dataset.csv"
)


# ============================================================
# MAIN
# ============================================================

def main():

    pages = pd.read_csv(PAGE_FILE)
    websites = pd.read_excel(WEBSITE_FILE)

    print()
    print("=" * 70)
    print("CREATE WEBSITE ACCESSIBILITY DATASET")
    print("=" * 70)

    print("Page records:", len(pages))
    print(
        "Websites in page dataset:",
        pages["website_id"].nunique()
    )

    # ========================================================
    # 1. CLEAN WEBSITE METADATA
    # ========================================================

    websites["category"] = (
        websites["category"]
        .astype(str)
        .str.strip()
    )

    websites["notes"] = (
        websites["notes"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    websites["language"] = (
        websites["language"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    websites["bilingual"] = (
        websites["bilingual"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # ========================================================
    # 2. ORGANIZATION TYPE
    # ========================================================

    def get_organization_type(row):

        category = str(
            row["category"]
        ).strip().lower()

        notes = str(
            row["notes"]
        ).strip().lower()

        if category == "university":

            if "public" in notes:
                return "Public University"

            if "private" in notes:
                return "Private University"

            return "University"

        if category == "news":
            return "News"

        if category == "government":
            return "Government"

        return row["category"]

    websites["organization_type"] = (
        websites.apply(
            get_organization_type,
            axis=1
        )
    )

    # ========================================================
    # 3. PAGE ACCESSIBILITY LEVEL COUNTS
    # ========================================================

    level_counts = (
        pages
        .groupby(
            [
                "website_id",
                "accessibility_level"
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
        .reset_index()
    )

    expected_levels = [
        "Excellent",
        "Good",
        "Needs Improvement",
        "Poor"
    ]

    for level in expected_levels:

        if level not in level_counts.columns:
            level_counts[level] = 0

    level_counts = level_counts.rename(
        columns={
            "Excellent": "excellent_pages",
            "Good": "good_pages",
            "Needs Improvement":
                "needs_improvement_pages",
            "Poor": "poor_pages"
        }
    )

    # ========================================================
    # 4. WEBSITE-LEVEL AGGREGATION
    # ========================================================

    website_stats = (
        pages
        .groupby("website_id")
        .agg(

            pages_scanned=(
                "page_id",
                "count"
            ),

            # -----------------------------------------------
            # Overall issues
            # -----------------------------------------------

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

            # -----------------------------------------------
            # Issue categories
            # -----------------------------------------------

            image_issues=(
                "image_issue_count",
                "sum"
            ),

            heading_issues=(
                "heading_issue_count",
                "sum"
            ),

            link_issues=(
                "link_issue_count",
                "sum"
            ),

            form_issues=(
                "form_issue_count",
                "sum"
            ),

            # -----------------------------------------------
            # Specific issues
            # -----------------------------------------------

            missing_alt=(
                "issue_missing_alt",
                "sum"
            ),

            empty_alt=(
                "issue_empty_alt",
                "sum"
            ),

            missing_h1=(
                "issue_missing_h1",
                "sum"
            ),

            multiple_h1=(
                "issue_multiple_h1",
                "sum"
            ),

            empty_heading=(
                "issue_empty_heading",
                "sum"
            ),

            heading_order=(
                "issue_heading_order",
                "sum"
            ),

            empty_link_text=(
                "issue_empty_link_text",
                "sum"
            ),

            generic_link_text=(
                "issue_generic_link_text",
                "sum"
            ),

            # -----------------------------------------------
            # Issues per page
            # -----------------------------------------------

            mean_issues_per_page=(
                "total_issues",
                "mean"
            ),

            median_issues_per_page=(
                "total_issues",
                "median"
            ),

            # -----------------------------------------------
            # Accessibility score
            # -----------------------------------------------

            mean_accessibility_score=(
                "accessibility_score",
                "mean"
            ),

            median_accessibility_score=(
                "accessibility_score",
                "median"
            ),

            min_accessibility_score=(
                "accessibility_score",
                "min"
            ),

            max_accessibility_score=(
                "accessibility_score",
                "max"
            )

        )
        .reset_index()
    )

    # ========================================================
    # 5. MERGE ACCESSIBILITY LEVEL COUNTS
    # ========================================================

    website_stats = website_stats.merge(
        level_counts[
            [
                "website_id",
                "excellent_pages",
                "good_pages",
                "needs_improvement_pages",
                "poor_pages"
            ]
        ],
        on="website_id",
        how="left"
    )

    # ========================================================
    # 6. MERGE WEBSITE METADATA
    # ========================================================

    metadata = websites[
        [
            "website_id",
            "website_name",
            "url",
            "category",
            "organization_type",
            "language",
            "bilingual",
            "notes"
        ]
    ].copy()

    dataset = metadata.merge(
        website_stats,
        on="website_id",
        how="inner"
    )

    # ========================================================
    # 7. NORMALIZED INDICATORS
    # ========================================================

    dataset["high_issue_share"] = (
        dataset["high_issues"]
        / dataset["total_issues"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    dataset["medium_issue_share"] = (
        dataset["medium_issues"]
        / dataset["total_issues"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    dataset["image_issue_share"] = (
        dataset["image_issues"]
        / dataset["total_issues"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    dataset["heading_issue_share"] = (
        dataset["heading_issues"]
        / dataset["total_issues"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    dataset["link_issue_share"] = (
        dataset["link_issues"]
        / dataset["total_issues"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    # ========================================================
    # 8. ROUND CONTINUOUS VALUES
    # ========================================================

    round_columns = [
        "mean_issues_per_page",
        "median_issues_per_page",
        "mean_accessibility_score",
        "median_accessibility_score",
        "high_issue_share",
        "medium_issue_share",
        "image_issue_share",
        "heading_issue_share",
        "link_issue_share"
    ]

    for column in round_columns:

        dataset[column] = (
            dataset[column]
            .round(4)
        )

    # ========================================================
    # 9. VALIDATION
    # ========================================================

    severity_mismatch = dataset[
        dataset["total_issues"]
        !=
        (
            dataset["high_issues"]
            + dataset["medium_issues"]
        )
    ]

    category_mismatch = dataset[
        dataset["total_issues"]
        !=
        (
            dataset["image_issues"]
            + dataset["heading_issues"]
            + dataset["link_issues"]
            + dataset["form_issues"]
        )
    ]

    specific_issue_total = (
        dataset["missing_alt"]
        + dataset["empty_alt"]
        + dataset["missing_h1"]
        + dataset["multiple_h1"]
        + dataset["empty_heading"]
        + dataset["heading_order"]
        + dataset["empty_link_text"]
        + dataset["generic_link_text"]
    )

    specific_issue_mismatch = dataset[
        dataset["total_issues"]
        != specific_issue_total
    ]

    print()
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    print(
        "Severity mismatches:",
        len(severity_mismatch)
    )

    print(
        "Category mismatches:",
        len(category_mismatch)
    )

    print(
        "Specific-issue mismatches:",
        len(specific_issue_mismatch)
    )

    print()

    print(
        "Pages represented:",
        dataset["pages_scanned"].sum()
    )

    print(
        "Total issues:",
        dataset["total_issues"].sum()
    )

    print(
        "High issues:",
        dataset["high_issues"].sum()
    )

    print(
        "Medium issues:",
        dataset["medium_issues"].sum()
    )

    # ========================================================
    # 10. SAVE
    # ========================================================

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # 11. REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("WEBSITE ACCESSIBILITY DATASET CREATED")
    print("=" * 70)

    print(
        "Websites:",
        len(dataset)
    )

    print(
        "Pages:",
        dataset["pages_scanned"].sum()
    )

    print()

    print("Organization types:")

    print(
        dataset[
            "organization_type"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        dataset[
            [
                "website_id",
                "website_name",
                "organization_type",
                "pages_scanned",
                "total_issues",
                "mean_issues_per_page",
                "mean_accessibility_score"
            ]
        ]
        .sort_values(
            "mean_accessibility_score"
        )
        .to_string(
            index=False
        )
    )

    print()

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
