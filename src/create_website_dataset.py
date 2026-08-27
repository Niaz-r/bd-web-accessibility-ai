import pandas as pd


PAGE_FILE = "data/page_accessibility_dataset_final.csv"
WEBSITE_FILE = "data/websites.xlsx"
OUTPUT_FILE = "data/website_accessibility_dataset.csv"


def main():

    # =========================================================
    # 1. Load data
    # =========================================================

    pages = pd.read_csv(PAGE_FILE)
    websites = pd.read_excel(WEBSITE_FILE)

    print("Page records:", len(pages))
    print("Websites in page dataset:", pages["website_id"].nunique())

    # =========================================================
    # 2. Clean website metadata
    # =========================================================

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

    # ---------------------------------------------------------
    # Organization type
    # ---------------------------------------------------------

    def get_organization_type(row):

        category = row["category"].lower()
        notes = row["notes"].lower()

        if category == "university":

            if "public" in notes:
                return "Public University"

            if "private" in notes or "priavate" in notes:
                return "Private University"

            return "University"

        if category == "news":
            return "News"

        if category == "government":
            return "Government"

        return row["category"]

    websites["organization_type"] = websites.apply(
        get_organization_type,
        axis=1
    )

    # =========================================================
    # 3. Page-level accessibility level counts
    # =========================================================

    level_counts = (
        pages
        .groupby(
            ["website_id", "accessibility_level"]
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    level_mapping = {
        "Excellent": "excellent_pages",
        "Good": "good_pages",
        "Needs Improvement": "needs_improvement_pages",
        "Poor": "poor_pages"
    }

    for old, new in level_mapping.items():

        if old not in level_counts.columns:
            level_counts[old] = 0

        level_counts = level_counts.rename(
            columns={old: new}
        )

    # =========================================================
    # 4. Website-level aggregation
    # =========================================================

    website_stats = (
        pages
        .groupby("website_id")
        .agg(

            pages_scanned=("page_id", "count"),

            total_issues=("total_issues", "sum"),
            high_issues=("high_issues", "sum"),
            medium_issues=("medium_issues", "sum"),

            image_issues=("image_issue_count", "sum"),
            heading_issues=("heading_issue_count", "sum"),
            link_issues=("link_issue_count", "sum"),
            form_issues=("form_issue_count", "sum"),

            mean_issues_per_page=("total_issues", "mean"),
            median_issues_per_page=("total_issues", "median"),

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

    # =========================================================
    # 5. Merge page-level classifications
    # =========================================================

    website_stats = website_stats.merge(
        level_counts,
        on="website_id",
        how="left"
    )

    # =========================================================
    # 6. Merge website metadata
    # =========================================================

    metadata_columns = [
        "website_id",
        "website_name",
        "url",
        "category",
        "organization_type",
        "language",
        "bilingual",
        "notes"
    ]

    metadata = websites[
        [
            col
            for col in metadata_columns
            if col in websites.columns
        ]
    ].copy()

    dataset = metadata.merge(
        website_stats,
        on="website_id",
        how="inner"
    )

    # =========================================================
    # 7. Additional normalized indicators
    # =========================================================

    dataset["high_issue_rate"] = (
        dataset["high_issues"]
        / dataset["total_issues"].replace(0, pd.NA)
    ).fillna(0)

    dataset["medium_issue_rate"] = (
        dataset["medium_issues"]
        / dataset["total_issues"].replace(0, pd.NA)
    ).fillna(0)

    dataset["image_issue_share"] = (
        dataset["image_issues"]
        / dataset["total_issues"].replace(0, pd.NA)
    ).fillna(0)

    dataset["heading_issue_share"] = (
        dataset["heading_issues"]
        / dataset["total_issues"].replace(0, pd.NA)
    ).fillna(0)

    dataset["link_issue_share"] = (
        dataset["link_issues"]
        / dataset["total_issues"].replace(0, pd.NA)
    ).fillna(0)

    # =========================================================
    # 8. Round continuous values
    # =========================================================

    round_columns = [
        "mean_issues_per_page",
        "median_issues_per_page",
        "mean_accessibility_score",
        "median_accessibility_score",
        "high_issue_rate",
        "medium_issue_rate",
        "image_issue_share",
        "heading_issue_share",
        "link_issue_share"
    ]

    for column in round_columns:

        if column in dataset.columns:
            dataset[column] = dataset[column].round(4)

    # =========================================================
    # 9. Validation
    # =========================================================

    print()
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    print("Website records:", len(dataset))

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

    print()

    print("Organization types:")

    print(
        dataset["organization_type"]
        .value_counts()
        .to_string()
    )

    # =========================================================
    # 10. Save
    # =========================================================

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 70)
    print("WEBSITE ACCESSIBILITY DATASET CREATED")
    print("=" * 70)

    print("Output:", OUTPUT_FILE)

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
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
