import pandas as pd


# ============================================================
# FILES
# ============================================================

RESULTS_FILE = (
    "final_pipeline/data/intermediate/accessibility_results.csv"
)

ISSUES_FILE = (
    "final_pipeline/data/intermediate/accessibility_issues_clean.csv"
)

OUTPUT_FILE = (
    "final_pipeline/data/final/page_accessibility_dataset.csv"
)


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # 1. LOAD DATA
    # ========================================================

    results = pd.read_csv(
        RESULTS_FILE
    )

    issues = pd.read_csv(
        ISSUES_FILE
    )

    print()
    print("=" * 70)
    print("CREATE PAGE ACCESSIBILITY DATASET")
    print("=" * 70)

    print(
        "Raw scanner pages:",
        len(results)
    )

    print(
        "Raw scanner websites:",
        results["website_id"].nunique()
    )

    print(
        "Detailed issues:",
        len(issues)
    )

    # ========================================================
    # 2. KEEP ONLY SUCCESSFUL SCANS
    # ========================================================

    results = results[
        results["status_code"] == 200
    ].copy()

    print()
    print("After HTTP 200 filter:")

    print(
        "Pages:",
        len(results)
    )

    print(
        "Websites:",
        results["website_id"].nunique()
    )

    # ========================================================
    # 3. NORMALIZE ISSUE FIELDS
    # ========================================================

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

    issues["issue"] = (
        issues["issue"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # ========================================================
    # 4. KEEP ISSUES BELONGING TO VALID PAGES
    # ========================================================

    valid_pages = (
        results[
            [
                "website_id",
                "page_id"
            ]
        ]
        .drop_duplicates()
    )

    issues = issues.merge(
        valid_pages,
        on=[
            "website_id",
            "page_id"
        ],
        how="inner"
    )

    # ========================================================
    # 5. TOTAL ISSUE COUNT PER PAGE
    # ========================================================

    total_counts = (
        issues
        .groupby(
            [
                "website_id",
                "page_id"
            ]
        )
        .size()
        .rename(
            "total_issues"
        )
        .reset_index()
    )

    # ========================================================
    # 6. SEVERITY COUNTS
    # ========================================================

    severity_counts = (
        issues
        .groupby(
            [
                "website_id",
                "page_id",
                "severity"
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
        .reset_index()
    )

    for severity in [
        "high",
        "medium"
    ]:

        if severity not in severity_counts.columns:

            severity_counts[
                severity
            ] = 0

    severity_counts = (
        severity_counts[
            [
                "website_id",
                "page_id",
                "high",
                "medium"
            ]
        ]
        .rename(
            columns={
                "high": "high_issues",
                "medium": "medium_issues"
            }
        )
    )

    # ========================================================
    # 7. CATEGORY COUNTS
    # ========================================================

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
        .unstack(
            fill_value=0
        )
        .reset_index()
    )

    for category in [
        "image",
        "heading",
        "link",
        "form"
    ]:

        if category not in category_counts.columns:

            category_counts[
                category
            ] = 0

    category_counts = (
        category_counts[
            [
                "website_id",
                "page_id",
                "image",
                "heading",
                "link",
                "form"
            ]
        ]
        .rename(
            columns={
                "image": "image_issue_count",
                "heading": "heading_issue_count",
                "link": "link_issue_count",
                "form": "form_issue_count"
            }
        )
    )

    # ========================================================
    # 8. SPECIFIC ISSUE TYPE COUNTS
    # ========================================================

    issue_type_counts = (
        issues
        .groupby(
            [
                "website_id",
                "page_id",
                "issue"
            ]
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    expected_issue_types = [
        "missing_alt",
        "empty_alt",
        "missing_h1",
        "multiple_h1",
        "empty_heading",
        "heading_order",
        "empty_link_text",
        "generic_link_text"
    ]

    for issue_type in expected_issue_types:

        if issue_type not in issue_type_counts.columns:
            issue_type_counts[issue_type] = 0

    # Rename issue-level columns so they do not collide
    # with scanner summary columns.
    rename_issue_columns = {
        issue_type: f"issue_{issue_type}"
        for issue_type in expected_issue_types
    }

    issue_type_counts = issue_type_counts.rename(
        columns=rename_issue_columns
    )

    issue_type_counts = issue_type_counts[
        [
            "website_id",
            "page_id"
        ]
        + [
            f"issue_{issue_type}"
            for issue_type in expected_issue_types
        ]
    ]

    # ========================================================
    # 9. MERGE EVERYTHING
    # ========================================================

    df = results.copy()

    df = df.merge(
        total_counts,
        on=[
            "website_id",
            "page_id"
        ],
        how="left"
    )

    df = df.merge(
        severity_counts,
        on=[
            "website_id",
            "page_id"
        ],
        how="left"
    )

    df = df.merge(
        category_counts,
        on=[
            "website_id",
            "page_id"
        ],
        how="left"
    )

    df = df.merge(
        issue_type_counts,
        on=[
            "website_id",
            "page_id"
        ],
        how="left"
    )

    # ========================================================
    # 10. FILL ZERO-ISSUE PAGES
    # ========================================================

    count_columns = [
        "total_issues",
        "high_issues",
        "medium_issues",

        "image_issue_count",
        "heading_issue_count",
        "link_issue_count",
        "form_issue_count",

        "issue_missing_alt",
        "issue_empty_alt",
        "issue_missing_h1",
        "issue_multiple_h1",
        "issue_empty_heading",
        "issue_heading_order",
        "issue_empty_link_text",
        "issue_generic_link_text"
    ]
    for column in count_columns:

        df[column] = (
            df[column]
            .fillna(0)
            .astype(int)
        )

    # ========================================================
    # 11. ISSUE RATES
    # ========================================================

    df["image_issue_rate"] = (
        df["image_issue_count"]
        / df["total_images"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    df["heading_issue_rate"] = (
        df["heading_issue_count"]
        / df["total_headings"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    df["link_issue_rate"] = (
        df["link_issue_count"]
        / df["total_links"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    # ========================================================
    # 12. ACCESSIBILITY SCORE
    # ========================================================
    #
    # Research-defined transparent heuristic:
    #
    # High issue   = 2 penalty points
    # Medium issue = 1 penalty point
    #
    # This is NOT an official WCAG conformance score.
    # ========================================================

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

    # ========================================================
    # 13. ACCESSIBILITY LEVEL
    # ========================================================

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

    # ========================================================
    # 14. SELECT FINAL COLUMNS
    # ========================================================

    columns = [

        # Identification
        "website_id",
        "page_id",
        "url",
        "page_title",
        "page_type",

        # Technical
        "status_code",

        # Images
        "total_images",
        "images_missing_alt",
        "images_empty_alt",
        "images_with_alt",

        # Headings
        "total_headings",
        "h1_count",
        "heading_order_issues",

        # Links
        "total_links",
        "empty_link_text",
        "generic_link_text",

        # Forms
        "form_controls",
        "unlabeled_controls",

        # Specific issue types
        # Specific issue types from detailed issue dataset
        "issue_missing_alt",
        "issue_empty_alt",
        "issue_missing_h1",
        "issue_multiple_h1",
        "issue_empty_heading",
        "issue_heading_order",
        "issue_empty_link_text",
        "issue_generic_link_text",

        # Category totals
        "image_issue_count",
        "heading_issue_count",
        "link_issue_count",
        "form_issue_count",

        # Overall
        "total_issues",
        "high_issues",
        "medium_issues",

        # Rates
        "image_issue_rate",
        "heading_issue_rate",
        "link_issue_rate",

        # Research score
        "accessibility_score",
        "accessibility_level"
    ]

    columns = [
        column
        for column in columns
        if column in df.columns
    ]

    dataset = (
        df[
            columns
        ]
        .copy()
    )

    # ========================================================
    # 15. VALIDATION
    # ========================================================

    severity_mismatch = dataset[
        dataset[
            "total_issues"
        ]
        !=
        (
            dataset[
                "high_issues"
            ]
            +
            dataset[
                "medium_issues"
            ]
        )
    ]

    category_mismatch = dataset[
        dataset[
            "total_issues"
        ]
        !=
        (
            dataset[
                "image_issue_count"
            ]
            +
            dataset[
                "heading_issue_count"
            ]
            +
            dataset[
                "link_issue_count"
            ]
            +
            dataset[
                "form_issue_count"
            ]
        )
    ]

    issue_type_total = (
        dataset["issue_missing_alt"]
        + dataset["issue_empty_alt"]
        + dataset["issue_missing_h1"]
        + dataset["issue_multiple_h1"]
        + dataset["issue_empty_heading"]
        + dataset["issue_heading_order"]
        + dataset["issue_empty_link_text"]
        + dataset["issue_generic_link_text"]
    )

    issue_type_mismatch = dataset[
        dataset[
            "total_issues"
        ]
        != issue_type_total
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
        "Issue-type mismatches:",
        len(issue_type_mismatch)
    )

    print(
        "Non-200 pages:",
        len(
            dataset[
                dataset[
                    "status_code"
                ] != 200
            ]
        )
    )

    # ========================================================
    # 16. SAVE
    # ========================================================

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # 17. FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("PAGE ACCESSIBILITY DATASET CREATED")
    print("=" * 70)

    print(
        "Pages:",
        len(dataset)
    )

    print(
        "Websites:",
        dataset[
            "website_id"
        ].nunique()
    )

    print(
        "Total issues:",
        dataset[
            "total_issues"
        ].sum()
    )

    print(
        "High issues:",
        dataset[
            "high_issues"
        ].sum()
    )

    print(
        "Medium issues:",
        dataset[
            "medium_issues"
        ].sum()
    )

    print()

    print(
        "Accessibility levels:"
    )

    print(
        dataset[
            "accessibility_level"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
