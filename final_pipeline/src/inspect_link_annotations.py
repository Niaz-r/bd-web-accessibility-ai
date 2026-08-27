import os
import sys
import pandas as pd


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

REPORT_DIR = "final_pipeline/reports/ai"

os.makedirs(
    REPORT_DIR,
    exist_ok=True
)


# ============================================================
# HELPER
# ============================================================

def find_first_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) < 2:

        print()
        print("Usage:")
        print(
            "python final_pipeline/src/"
            "inspect_link_annotations.py "
            "<annotation_csv>"
        )

        print()

        print("Example:")
        print(
            "python final_pipeline/src/"
            "inspect_link_annotations.py "
            "data/annotation_final.csv"
        )

        return

    input_file = sys.argv[1]

    if not os.path.exists(input_file):

        print(
            f"ERROR: File not found: "
            f"{input_file}"
        )

        return

    # ========================================================
    # 1. LOAD
    # ========================================================

    df = pd.read_csv(
        input_file
    )

    print()
    print("=" * 80)
    print("AI LINK ANNOTATION DATASET INSPECTION")
    print("=" * 80)

    print(
        "File:",
        input_file
    )

    print(
        "Rows:",
        len(df)
    )

    print(
        "Columns:",
        len(df.columns)
    )

    print()

    print("Column names:")

    for column in df.columns:
        print(
            f"  - {column}"
        )

    # ========================================================
    # 2. DETECT IMPORTANT COLUMNS
    # ========================================================

    label_col = find_first_column(
        df,
        [
            "label",
            "annotation_label",
            "accessibility_label",
            "class",
            "target"
        ]
    )

    link_col = find_first_column(
        df,
        [
            "link_text",
            "text",
            "anchor_text"
        ]
    )

    context_col = find_first_column(
        df,
        [
            "context",
            "link_context",
            "surrounding_context",
            "surrounding_text"
        ]
    )

    title_col = find_first_column(
        df,
        [
            "page_title",
            "title"
        ]
    )

    organization_col = find_first_column(
        df,
        [
            "organization_type",
            "org_type",
            "category",
            "website_type"
        ]
    )

    language_col = find_first_column(
        df,
        [
            "link_language",
            "language",
            "lang"
        ]
    )

    reason_col = find_first_column(
        df,
        [
            "annotation_reason",
            "reason"
        ]
    )

    print()
    print("=" * 80)
    print("DETECTED IMPORTANT COLUMNS")
    print("=" * 80)

    print(
        "Label:",
        label_col
    )

    print(
        "Link text:",
        link_col
    )

    print(
        "Context:",
        context_col
    )

    print(
        "Page title:",
        title_col
    )

    print(
        "Organization:",
        organization_col
    )

    print(
        "Language:",
        language_col
    )

    print(
        "Reason:",
        reason_col
    )

    # ========================================================
    # 3. MISSING VALUES
    # ========================================================

    missing = pd.DataFrame(
        {
            "column":
                df.columns,

            "missing_count":
                [
                    df[column]
                    .isna()
                    .sum()

                    for column
                    in df.columns
                ]
        }
    )

    missing[
        "missing_percentage"
    ] = (
        missing[
            "missing_count"
        ]
        / len(df)
        * 100
    )

    missing = (
        missing
        .sort_values(
            "missing_count",
            ascending=False
        )
    )

    missing.to_csv(
        f"{REPORT_DIR}/"
        "annotation_missing_values.csv",
        index=False
    )

    print()
    print("=" * 80)
    print("MISSING VALUES")
    print("=" * 80)

    print(
        missing[
            missing[
                "missing_count"
            ] > 0
        ]
        .round(2)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # 4. LABEL DISTRIBUTION
    # ========================================================

    if label_col is not None:

        label_distribution = (
            df[
                label_col
            ]
            .fillna(
                "<MISSING>"
            )
            .astype(str)
            .str.strip()
            .value_counts(
                dropna=False
            )
            .rename_axis(
                "label"
            )
            .reset_index(
                name="count"
            )
        )

        label_distribution[
            "percentage"
        ] = (
            label_distribution[
                "count"
            ]
            / len(df)
            * 100
        )

        label_distribution.to_csv(
            f"{REPORT_DIR}/"
            "annotation_label_distribution.csv",
            index=False
        )

        print()
        print("=" * 80)
        print("LABEL DISTRIBUTION")
        print("=" * 80)

        print(
            label_distribution
            .round(3)
            .to_string(
                index=False
            )
        )

    else:

        print()
        print(
            "WARNING: No label column "
            "was automatically detected."
        )

    # ========================================================
    # 5. EXACT DUPLICATE ROWS
    # ========================================================

    exact_duplicate_count = (
        df.duplicated()
        .sum()
    )

    print()
    print("=" * 80)
    print("DUPLICATE CHECK")
    print("=" * 80)

    print(
        "Exact duplicate rows:",
        exact_duplicate_count
    )

    # ========================================================
    # 6. SEMANTIC DUPLICATES
    # ========================================================

    semantic_columns = []

    for column in [
        link_col,
        context_col,
        title_col
    ]:

        if (
            column is not None
            and column not in semantic_columns
        ):

            semantic_columns.append(
                column
            )

    if len(semantic_columns) > 0:

        temp = df.copy()

        for column in semantic_columns:

            temp[
                f"__norm_{column}"
            ] = (
                temp[column]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(
                    r"\s+",
                    " ",
                    regex=True
                )
            )

        duplicate_keys = [
            f"__norm_{column}"
            for column
            in semantic_columns
        ]

        semantic_duplicate_mask = (
            temp.duplicated(
                subset=duplicate_keys,
                keep=False
            )
        )

        semantic_duplicates = (
            df[
                semantic_duplicate_mask
            ]
            .copy()
        )

        print(
            "Rows participating in "
            "semantic duplicates:",
            len(
                semantic_duplicates
            )
        )

        semantic_duplicates.to_csv(
            f"{REPORT_DIR}/"
            "annotation_semantic_duplicates.csv",
            index=False
        )

        # ====================================================
        # 7. CONFLICTING LABELS
        # ====================================================

        if label_col is not None:

            conflict_source = (
                temp[
                    semantic_duplicate_mask
                ]
                .copy()
            )

            if len(conflict_source) > 0:

                conflict_counts = (
                    conflict_source
                    .groupby(
                        duplicate_keys
                    )[
                        label_col
                    ]
                    .nunique(
                        dropna=True
                    )
                )

                conflict_keys = (
                    conflict_counts[
                        conflict_counts > 1
                    ]
                    .reset_index()
                )

                if len(
                    conflict_keys
                ) > 0:

                    conflicts = (
                        conflict_source
                        .merge(
                            conflict_keys[
                                duplicate_keys
                            ],
                            on=duplicate_keys,
                            how="inner"
                        )
                    )

                    original_columns = [
                        column
                        for column
                        in df.columns
                        if column
                        in conflicts.columns
                    ]

                    conflicts = conflicts[
                        original_columns
                    ]

                else:

                    conflicts = (
                        pd.DataFrame(
                            columns=df.columns
                        )
                    )

                conflicts.to_csv(
                    f"{REPORT_DIR}/"
                    "annotation_label_conflicts.csv",
                    index=False
                )

                print(
                    "Rows with conflicting "
                    "labels:",
                    len(conflicts)
                )

            else:

                print(
                    "Rows with conflicting "
                    "labels: 0"
                )

    # ========================================================
    # 8. TEXT QUALITY
    # ========================================================

    print()
    print("=" * 80)
    print("TEXT FIELD QUALITY")
    print("=" * 80)

    text_quality_rows = []

    for field_name, column in [
        (
            "link_text",
            link_col
        ),
        (
            "context",
            context_col
        ),
        (
            "page_title",
            title_col
        )
    ]:

        if column is None:
            continue

        text = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        empty_count = (
            text.eq("")
            .sum()
        )

        lengths = (
            text.str.len()
        )

        words = (
            text
            .str.split()
            .str.len()
        )

        row = {
            "field":
                field_name,

            "source_column":
                column,

            "empty_count":
                empty_count,

            "empty_percentage":
                empty_count
                / len(df)
                * 100,

            "mean_characters":
                lengths.mean(),

            "median_characters":
                lengths.median(),

            "mean_words":
                words.mean(),

            "median_words":
                words.median()
        }

        text_quality_rows.append(
            row
        )

    text_quality = (
        pd.DataFrame(
            text_quality_rows
        )
    )

    text_quality.to_csv(
        f"{REPORT_DIR}/"
        "annotation_text_quality.csv",
        index=False
    )

    if len(text_quality) > 0:

        print(
            text_quality
            .round(3)
            .to_string(
                index=False
            )
        )

    # ========================================================
    # 9. ORGANIZATION DISTRIBUTION
    # ========================================================

    if organization_col is not None:

        org_distribution = (
            df[
                organization_col
            ]
            .fillna(
                "<MISSING>"
            )
            .astype(str)
            .str.strip()
            .value_counts()
            .rename_axis(
                "organization_type"
            )
            .reset_index(
                name="count"
            )
        )

        org_distribution[
            "percentage"
        ] = (
            org_distribution[
                "count"
            ]
            / len(df)
            * 100
        )

        org_distribution.to_csv(
            f"{REPORT_DIR}/"
            "annotation_organization_distribution.csv",
            index=False
        )

        print()
        print("=" * 80)
        print("ORGANIZATION DISTRIBUTION")
        print("=" * 80)

        print(
            org_distribution
            .round(3)
            .to_string(
                index=False
            )
        )

    # ========================================================
    # 10. LANGUAGE DISTRIBUTION
    # ========================================================

    if language_col is not None:

        language_distribution = (
            df[
                language_col
            ]
            .fillna(
                "<MISSING>"
            )
            .astype(str)
            .str.strip()
            .value_counts()
            .rename_axis(
                "language"
            )
            .reset_index(
                name="count"
            )
        )

        language_distribution[
            "percentage"
        ] = (
            language_distribution[
                "count"
            ]
            / len(df)
            * 100
        )

        language_distribution.to_csv(
            f"{REPORT_DIR}/"
            "annotation_language_distribution.csv",
            index=False
        )

        print()
        print("=" * 80)
        print("LANGUAGE DISTRIBUTION")
        print("=" * 80)

        print(
            language_distribution
            .round(3)
            .to_string(
                index=False
            )
        )

    # ========================================================
    # 11. LABEL x ORGANIZATION
    # ========================================================

    if (
        label_col is not None
        and organization_col is not None
    ):

        label_org = pd.crosstab(
            df[
                organization_col
            ],
            df[
                label_col
            ],
            margins=True
        )

        label_org.to_csv(
            f"{REPORT_DIR}/"
            "annotation_label_by_organization.csv"
        )

        print()
        print("=" * 80)
        print("LABEL BY ORGANIZATION")
        print("=" * 80)

        print(
            label_org.to_string()
        )

    # ========================================================
    # 12. LABEL x LANGUAGE
    # ========================================================

    if (
        label_col is not None
        and language_col is not None
    ):

        label_language = pd.crosstab(
            df[
                language_col
            ],
            df[
                label_col
            ],
            margins=True
        )

        label_language.to_csv(
            f"{REPORT_DIR}/"
            "annotation_label_by_language.csv"
        )

        print()
        print("=" * 80)
        print("LABEL BY LANGUAGE")
        print("=" * 80)

        print(
            label_language.to_string()
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)

    print(
        "Reports saved in:",
        REPORT_DIR
    )

    print()

    print(
        "Do NOT train the AI model yet."
    )

    print(
        "First inspect label balance, "
        "duplicates, conflicts, missing text, "
        "and organization/language coverage."
    )


if __name__ == "__main__":
    main()
