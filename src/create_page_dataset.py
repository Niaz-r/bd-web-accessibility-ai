import pandas as pd


INPUT_FILE = "data/test_accessibility_results.csv"
ISSUES_FILE = "data/accessibility_issues.csv"
OUTPUT_FILE = "data/page_accessibility_dataset.csv"


def main():

    # =========================================================
    # 1. LOAD DATA
    # =========================================================

    df = pd.read_csv(INPUT_FILE)

    issues_df = pd.read_csv(ISSUES_FILE)

    # =========================================================
    # 2. BASIC ISSUE COUNTS
    # =========================================================

    # -------------------------
    # Images
    # -------------------------

    df["image_issue_count"] = (
        df["images_missing_alt"].fillna(0)
        + df["images_empty_alt"].fillna(0)
    )

    # -------------------------
    # Missing H1
    # -------------------------

    df["missing_h1"] = (
        df["h1_count"].fillna(0) == 0
    ).astype(int)

    # -------------------------
    # Empty headings
    #
    # This information exists in accessibility_issues.csv,
    # not directly in test_accessibility_results.csv.
    # -------------------------

    empty_heading_counts = (
        issues_df[
            issues_df["issue"] == "empty_heading"
        ]
        .groupby(
            ["website_id", "page_id"]
        )
        .size()
        .rename("empty_heading")
        .reset_index()
    )

    df = df.merge(
        empty_heading_counts,
        on=["website_id", "page_id"],
        how="left"
    )

    df["empty_heading"] = (
        df["empty_heading"]
        .fillna(0)
        .astype(int)
    )

    # -------------------------
    # Heading issues
    # -------------------------

    df["heading_issue_count"] = (
        df["missing_h1"]
        + df["heading_order_issues"].fillna(0)
        + df["empty_heading"]
    )

    # -------------------------
    # Link issues
    # -------------------------

    df["link_issue_count"] = (
        df["empty_link_text"].fillna(0)
        + df["generic_link_text"].fillna(0)
    )

    # -------------------------
    # Form issues
    # -------------------------

    df["form_issue_count"] = (
        df["unlabeled_controls"].fillna(0)
    )

    # =========================================================
    # 3. TOTAL ISSUES
    # =========================================================

    df["total_issues"] = (
        df["image_issue_count"]
        + df["heading_issue_count"]
        + df["link_issue_count"]
        + df["form_issue_count"]
    )

    # =========================================================
    # 4. SEVERITY COUNTS
    #
    # Severity comes directly from accessibility_issues.csv.
    # This avoids inconsistent manual reconstruction.
    # =========================================================

    severity_counts = (
        issues_df
        .groupby(
            ["website_id", "page_id", "severity"]
        )
        .size()
        .unstack(
            fill_value=0
        )
        .reset_index()
    )

    # Make sure required severity columns exist
    if "high" not in severity_counts.columns:
        severity_counts["high"] = 0

    if "medium" not in severity_counts.columns:
        severity_counts["medium"] = 0

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

    # Remove any old severity columns
    df = df.drop(
        columns=[
            "high_issues",
            "medium_issues"
        ],
        errors="ignore"
    )

    # Merge severity counts
    df = df.merge(
        severity_counts,
        on=["website_id", "page_id"],
        how="left"
    )

    df["high_issues"] = (
        df["high_issues"]
        .fillna(0)
        .astype(int)
    )

    df["medium_issues"] = (
        df["medium_issues"]
        .fillna(0)
        .astype(int)
    )

    # =========================================================
    # 5. VALIDATE ISSUE COUNTS
    # =========================================================

    df["severity_total"] = (
        df["high_issues"]
        + df["medium_issues"]
    )

    mismatches = df[
        df["total_issues"]
        != df["severity_total"]
    ]

    print()

    if len(mismatches) == 0:

        print("Severity validation: PASSED")
        print(
            "total_issues = high_issues + medium_issues"
        )

    else:

        print(
            "WARNING: Severity count mismatch detected"
        )

        print(
            mismatches[
                [
                    "website_id",
                    "page_id",
                    "total_issues",
                    "high_issues",
                    "medium_issues",
                    "severity_total"
                ]
            ].to_string(
                index=False
            )
        )

    # =========================================================
    # 6. ACCESSIBILITY SCORE
    #
    # Initial transparent scoring baseline:
    #
    # High issue   = 2 penalty points
    # Medium issue = 1 penalty point
    #
    # This is NOT an official WCAG score.
    # =========================================================

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

    # =========================================================
    # 7. ISSUE RATES
    # =========================================================

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

    df["form_issue_rate"] = (
        df["form_issue_count"]
        / df["form_controls"].replace(
            0,
            pd.NA
        )
    ).fillna(0)

    # =========================================================
    # 8. ACCESSIBILITY LEVEL
    # =========================================================

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

    # =========================================================
    # 9. SELECT FINAL COLUMNS
    # =========================================================

    columns = [

        # -------------------------
        # Identification
        # -------------------------

        "website_id",
        "page_id",
        "url",
        "page_title",

        # -------------------------
        # Images
        # -------------------------

        "total_images",
        "images_missing_alt",
        "images_empty_alt",
        "images_with_alt",
        "image_issue_count",

        # -------------------------
        # Headings
        # -------------------------

        "total_headings",
        "h1_count",
        "missing_h1",
        "empty_heading",
        "heading_order_issues",
        "heading_issue_count",

        # -------------------------
        # Links
        # -------------------------

        "total_links",
        "empty_link_text",
        "generic_link_text",
        "link_issue_count",

        # -------------------------
        # Forms
        # -------------------------

        "form_controls",
        "unlabeled_controls",
        "form_issue_count",

        # -------------------------
        # Total issues
        # -------------------------

        "total_issues",

        # -------------------------
        # Severity
        # -------------------------

        "high_issues",
        "medium_issues",

        # -------------------------
        # Issue rates
        # -------------------------

        "image_issue_rate",
        "heading_issue_rate",
        "link_issue_rate",
        "form_issue_rate",

        # -------------------------
        # Score
        # -------------------------

        "accessibility_score",
        "accessibility_level",

        # -------------------------
        # Technical
        # -------------------------

        "status_code"
    ]

    # Only keep columns that actually exist
    columns = [
        column
        for column in columns
        if column in df.columns
    ]

    dataset = df[
        columns
    ].copy()

    # =========================================================
    # 10. SAVE DATASET
    # =========================================================

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # =========================================================
    # 11. REPORT
    # =========================================================

    print()
    print("=" * 60)
    print("PAGE ACCESSIBILITY DATASET CREATED")
    print("=" * 60)

    print(
        "Pages:",
        len(dataset)
    )

    print(
        "Columns:",
        len(dataset.columns)
    )

    print(
        "Output:",
        OUTPUT_FILE
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

    print("Issue totals:")

    print(
        dataset[
            [
                "website_id",
                "page_id",
                "total_issues",
                "high_issues",
                "medium_issues",
                "accessibility_score",
                "accessibility_level"
            ]
        ]
        .sort_values(
            "accessibility_score"
        )
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
