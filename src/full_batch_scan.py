import pandas as pd
from accessibility_scanner import scan_page



INPUT_FILE = "data/pages_full.csv"
OUTPUT_FILE = "data/accessibility_results_final.csv"


def main():

    pages = pd.read_csv(INPUT_FILE)

    # Normalize URLs
    pages["normalized_url"] = (
        pages["page_url"]
        .astype(str)
        .str.strip()
        .str.rstrip("/")
    )

    # Remove duplicate URLs
    pages = (
        pages
        .drop_duplicates(subset=["normalized_url"])
        .reset_index(drop=True)
    )

    print("=" * 60)
    print("FULL ACCESSIBILITY SCAN")
    print("=" * 60)
    print("Unique pages to scan:", len(pages))
    print()

    results = []

    for index, row in pages.iterrows():

        print(
            f"[{index + 1}/{len(pages)}] "
            f"{row['website_id']} - {row['normalized_url']}"
        )

        result = scan_page(
            row["normalized_url"]
        )

        # Add original dataset metadata
        result["website_id"] = row["website_id"]
        result["page_id"] = row["page_id"]
        result["page_title"] = row["title"]
        result["page_type"] = row["page_type"]

        results.append(result)

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 60)
    print("FULL SCAN COMPLETE")
    print("=" * 60)

    print("Pages scanned:", len(results_df))

    successful = (
        results_df["status_code"] == 200
    ).sum()

    print("HTTP 200 pages:", successful)

    errors = (
        results_df["error"]
        .fillna("")
        .str.len()
        .gt(0)
        .sum()
    )

    print("Pages with errors:", errors)

    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
