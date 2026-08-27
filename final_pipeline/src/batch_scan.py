import os
import pandas as pd

from accessibility_scanner import scan_page


# ============================================================
# FILES
# ============================================================

INPUT_FILE = (
    "final_pipeline/data/intermediate/pages_final.csv"
)

OUTPUT_FILE = (
    "final_pipeline/data/intermediate/accessibility_results.csv"
)


# ============================================================
# MAIN
# ============================================================

def main():

    pages = pd.read_csv(
        INPUT_FILE
    )

    print()
    print("=" * 70)
    print("FINAL ACCESSIBILITY BATCH SCAN")
    print("=" * 70)

    print(
        "Pages to scan:",
        len(pages)
    )

    print(
        "Websites:",
        pages["website_id"].nunique()
    )

    print()

    results = []

    for index, row in pages.iterrows():

        url = str(
            row["page_url"]
        ).strip()

        website_id = str(
            row["website_id"]
        ).strip()

        page_id = str(
            row["page_id"]
        ).strip()

        print(
            f"[{index + 1}/{len(pages)}] "
            f"{website_id} | {page_id}"
        )

        print(
            f"    {url}"
        )

        result = scan_page(
            url
        )

        # ----------------------------------------------------
        # Add page metadata
        # ----------------------------------------------------

        result["website_id"] = (
            website_id
        )

        result["page_id"] = (
            page_id
        )

        result["page_title"] = (
            row.get(
                "title",
                ""
            )
        )

        result["page_type"] = (
            row.get(
                "page_type",
                ""
            )
        )

        result["crawler_language"] = (
            row.get(
                "language",
                ""
            )
        )

        result["crawler_status"] = (
            row.get(
                "status",
                ""
            )
        )

        results.append(
            result
        )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_df = pd.DataFrame(
        results
    )

    os.makedirs(
        "final_pipeline/data/intermediate",
        exist_ok=True
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("ACCESSIBILITY SCAN COMPLETE")
    print("=" * 70)

    print(
        "Pages processed:",
        len(results_df)
    )

    print(
        "Websites:",
        results_df[
            "website_id"
        ].nunique()
    )

    print()

    print("HTTP status:")

    print(
        results_df[
            "status_code"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()

    error_count = (
        results_df[
            "error"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )

    print(
        "Pages with scanner errors:",
        error_count
    )

    # --------------------------------------------------------
    # Successfully scanned pages
    # --------------------------------------------------------

    successful = results_df[
        results_df[
            "status_code"
        ] == 200
    ]

    print(
        "HTTP 200 pages:",
        len(successful)
    )

    print(
        "HTTP 200 websites:",
        successful[
            "website_id"
        ].nunique()
    )

    # --------------------------------------------------------
    # Basic issue totals
    # --------------------------------------------------------

    if len(successful) > 0:

        print()

        print(
            "Missing alt:",
            successful[
                "images_missing_alt"
            ].sum()
        )

        print(
            "Empty alt:",
            successful[
                "images_empty_alt"
            ].sum()
        )

        print(
            "Heading order issues:",
            successful[
                "heading_order_issues"
            ].sum()
        )

        print(
            "Empty links:",
            successful[
                "empty_link_text"
            ].sum()
        )

        print(
            "Generic links:",
            successful[
                "generic_link_text"
            ].sum()
        )

    print()

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
