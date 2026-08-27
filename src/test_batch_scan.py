import pandas as pd
from accessibility_scanner import scan_page

# Load page dataset
pages = pd.read_csv("data/pages.csv")

# Take first 5 pages for testing
# Normalize URLs and remove duplicate pages
pages["normalized_url"] = (
    pages["page_url"]
    .astype(str)
    .str.strip()
    .str.rstrip("/")
)

test_pages = (
    pages
    .drop_duplicates(subset=["normalized_url"])
    .head(30)
)
results = []

for _, row in test_pages.iterrows():

    print(f"Scanning: {row['page_url']}")

  
    result = scan_page(row["normalized_url"])

    # Add information from our original dataset
    result["website_id"] = row["website_id"]
    result["page_id"] = row["page_id"]
    result["page_title"] = row["title"]

    results.append(result)

# Create DataFrame
results_df = pd.DataFrame(results)

# Save test results
results_df.to_csv(
    "data/test_accessibility_results.csv",
    index=False
)

print()
print("=" * 60)
print("TEST SCAN COMPLETE")
print("=" * 60)

print("Pages scanned:", len(results_df))
print("Output:", "data/test_accessibility_results.csv")

print()
print(results_df[
    [
        "website_id",
        "page_id",
        "total_images",
        "images_missing_alt",
        "images_empty_alt",
        "total_headings",
        "h1_count",
        "heading_order_issues",
        "total_links",
        "empty_link_text",
        "generic_link_text",
        "form_controls",
        "unlabeled_controls",
        "has_title",
        "has_lang",
        "status_code"
    ]
].to_string(index=False))
