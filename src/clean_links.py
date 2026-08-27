import pandas as pd
import re

INPUT_FILE = "data/links_raw.csv"
OUTPUT_FILE = "data/links_clean.csv"

df = pd.read_csv(INPUT_FILE)

# Clean link text
df["link_text"] = (
    df["link_text"]
    .fillna("")
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# Clean page title
df["page_title"] = (
    df["page_title"]
    .fillna("")
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# Remove empty links
df = df[df["link_text"].str.len() >= 2]

# Remove exact duplicates from the same page
df = df.drop_duplicates(
    subset=["page_url", "link_text"]
)

# Remove extremely long navigation/text blocks
df = df[df["link_text"].str.len() <= 200]

# Remove obvious non-content links
bad_patterns = [
    r"^javascript",
    r"^mailto:",
    r"^tel:",
]

pattern = "|".join(bad_patterns)

df = df[
    ~df["link_text"].str.lower().str.contains(
        pattern,
        regex=True,
        na=False
    )
]

# Recreate sample IDs
df = df.reset_index(drop=True)

df["sample_id"] = [
    f"S{i:05d}"
    for i in range(1, len(df) + 1)
]

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("Clean dataset created.")
print("Total samples:", len(df))
print("\nFirst 20 samples:")
print(df.head(20).to_string(index=False))
