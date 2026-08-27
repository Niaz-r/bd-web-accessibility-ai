import pandas as pd


# =========================================================
# Configuration
# =========================================================

RESULTS_FILE = "data/accessibility_results_final.csv"
ISSUES_FILE = "data/accessibility_issues_final.csv"
OUTPUT_FILE = "data/page_accessibility_dataset_final.csv"


def main():

    # =====================================================
    # 1. Load data
    # =====================================================

    print("Loading scanner results...")

    results = pd.read_csv(RESULTS_FILE)

    print("Loading detailed accessibility issues...")

    issues = pd.read_csv(ISSUES_FILE)

    print(f"Raw scanned pages: {len(results)}")
    print(f"Raw websites: {results['website_id'].nunique()}")
    print(f"Detailed issues: {len(issues)}")

    # =====================================================
    # 2. Keep only successfully scanned pages
    # =====================================================

    results = results[
        results["status_code"] == 200
    ].copy()

    print()
    print("After removing non-200 pages:")
    print("Pages:", len(results))
    print("Websites:", results["website_id"].nunique())

    # =====================================================
    # 3. Normalize issue fields
    # =====================================================

    issues["severity"] = (
        issues["severity"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    issues["issue_category"] = (
        issues["issue_category"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Keep issues belonging only to valid pages
    valid_pages = results[
        ["website_id", "page_id"]
    ].drop_duplicates()

    issues = issues.merge(
        valid_pages,
        on=["website_id", "page_id"],
        how="inner"
    )

    # =====================================================
    # 4. Aggregate issue counts by page
    # =====================================================

    total_counts = (
        issues
        .groupby(["website_id", "page_id"])
        .size()
        .rename("total_issues")
        .reset_index()
    )

    # -----------------------------------------------------
    # Severity counts
    # -----------------------------------------------------

    severity_counts = (
        issues
        .groupby(
            ["website_id", "page_id", "severity"]
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    if "high" not in severity_counts.columns:
        severity_counts["high"] = 0

    if "medium" not in severity_counts.columns:
        severity_counts["medium"] = 0

    severity_counts = severity_counts.rename(
        columns={
            "high": "high_issues",
            "medium": "medium_issues"
        }
    )

    severity_counts = severity_counts[
        [
            "website_id",
            "page_id",
            "high_issues",
            "medium_issues"
        ]
    ]

    # -----------------------------------------------------
    # Category counts
    # -----------------------------------------------------

    category_counts = (
        issues
        .groupby(
            [
                "website_id",
                "page_id",
                "issue_category"
            ]
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for category in [
        "image",
        "heading",
        "link",
        "form"
    ]:
        if category not in category_counts.columns:
            category_counts[category] = 0

    category_counts = category_counts.rename(
        columns={
            "image": "image_issue_count",
            "heading": "heading_issue_count",
            "link": "link_issue_count",
            "form": "form_issue_count"
        }
    )

    category_counts = category_counts[
        [
            "website_id",
            "page_id",
            "image_issue_count",
            "heading_issue_count",
            "link_issue_count",
            "form_issue_count"
        ]
    ]

    # =====================================================
    # 5. Merge authoritative issue counts into page data
    # =====================================================

    df = results.merge(
        total_counts,
        on=["website_id", "page_id"],
        how="left"
    )

    df = df.merge(
        severity_counts,
        on=["website_id", "page_id"],
        how="left"
    )

    df = df.merge(
        category_counts,
        on=["website_id", "page_id"],
        how="left"
    )

    count_columns = [
        "total_issues",
        "high_issues",
        "medium_issues",
        "image_issue_count",
        "heading_issue_count",
        "link_issue_count",
        "form_issue_count"
    ]

    for column in count_columns:

        df[column] = (
            df[column]
            .fillna(0)
            .astype(int)
        )

    # =====================================================
    # 6. Missing H1 indicator
    # =====================================================

    df["missing_h1"] = (
        df["h1_count"].fillna(0) == 0
    ).astype(int)

    # =====================================================
    # 7. Issue rates
    # =====================================================

    df["image_issue_rate"] = (
        df["image_issue_count"]
        / df["total_images"].replace(0, pd.NA)
    ).fillna(0)

    df["heading_issue_rate"] = (
        df["heading_issue_count"]
        / df["total_headings"].replace(0, pd.NA)
    ).fillna(0)

    df["link_issue_rate"] = (
        df["link_issue_count"]
        / df["total_links"].replace(0, pd.NA)
    ).fillna(0)

    # =====================================================
    # 8. Accessibility score
    # =====================================================
    #
    # Current transparent heuristic:
    #
    # High severity   = 2 penalty points
    # Medium severity = 1 penalty point
    #
    # This is NOT WCAG's official scoring system.
    # It is a research-defined page-level indicator.
    # =====================================================

    penalty = (
        df["high_issues"] * 2
        + df["medium_issues"]
    )

    df["accessibility_score"] = (
        100 - penalty
    ).clip(
        lower=0,
        upper=100
    )

    # =====================================================
    # 9. Accessibility level
    # =====================================================

    def classify(score):

        if score >= 90:
            return "Excellent"

        elif score >= 75:
            return "Good"

        elif score >= 50:
            return "Needs Improvement"

        else:
            return "Poor"

    df["accessibility_level"] = (
        df["accessibility_score"]
        .apply(classify)
    )

    # =====================================================
    # 10. Select final columns
    # =====================================================

    columns = [

        # Identification
        "website_id",
        "page_id",
        "url",
        "page_title",

        # Images
        "total_images",
        "images_missing_alt",
        "images_empty_alt",
        "images_with_alt",

        # Headings
        "total_headings",
        "h1_count",
        "missing_h1",
        "heading_order_issues",

        # Links
        "total_links",
        "empty_link_text",
        "generic_link_text",

        # Forms
        "form_controls",
        "unlabeled_controls",

        # Category issue counts
        "image_issue_count",
        "heading_issue_count",
        "link_issue_count",
        "form_issue_count",

        # Overall issue counts
        "total_issues",
        "high_issues",
        "medium_issues",

        # Issue rates
        "image_issue_rate",
        "heading_issue_rate",
        "link_issue_rate",

        # Score
        "accessibility_score",
        "accessibility_level",

        # Technical
        "status_code"
    ]

    columns = [
        column
        for column in columns
        if column in df.columns
    ]

    dataset = df[columns].copy()

    # =====================================================
    # 11. Validation
    # =====================================================

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
            dataset["image_issue_count"]
            + dataset["heading_issue_count"]
            + dataset["link_issue_count"]
            + dataset["form_issue_count"]
        )
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
        "Non-200 pages:",
        len(
            dataset[
                dataset["status_code"] != 200
            ]
        )
    )

    # =====================================================
    # 12. Save
    # =====================================================

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # =====================================================
    # 13. Final report
    # =====================================================

    print()
    print("=" * 70)
    print("FINAL PAGE ACCESSIBILITY DATASET CREATED")
    print("=" * 70)

    print("Pages:", len(dataset))
    print(
        "Websites:",
        dataset["website_id"].nunique()
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
    print("Accessibility levels:")

    print(
        dataset[
            "accessibility_level"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
