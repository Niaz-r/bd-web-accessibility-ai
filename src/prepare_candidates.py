import pandas as pd
import re

LINKS_FILE = "data/links_context.csv"
WEBSITES_FILE = "data/websites.xlsx"
OUTPUT_FILE = "data/candidate_samples.csv"

# Load data
links = pd.read_csv(LINKS_FILE)
websites = pd.read_excel(WEBSITES_FILE)

# Select useful website information
website_info = websites[
    [
        "website_id",
        "website_name",
        "category",
        "language",
        "bilingual"
    ]
]

# Extract website_id from page_id
links["website_id"] = (
    links["page_id"]
    .str.extract(r"(BD\d+)")
)

# Merge website information
df = links.merge(
    website_info,
    on="website_id",
    how="left"
)

# Clean text
df["link_text"] = (
    df["link_text"]
    .fillna("")
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

df["context"] = (
    df["context"]
    .fillna("")
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# ------------------------------------------------
# Candidate selection
# ------------------------------------------------

# Potentially ambiguous link text
ambiguous_terms = [
    "click here",
    "read more",
    "readmore",
    "more",
    "here",
    "click",
    "view",
    "details",
    "link",
    "learn more"
]

df["lower_text"] = (
    df["link_text"]
    .str.lower()
)

ambiguous = df[
    df["lower_text"].isin(
        ambiguous_terms
    )
].copy()

# Bengali / non-English candidates
bengali_pattern = r"[\u0980-\u09FF]"

bengali = df[
    df["link_text"].str.contains(
        bengali_pattern,
        regex=True,
        na=False
    )
].copy()

# Short links
short_links = df[
    df["link_text"].str.split().str.len() <= 2
].copy()

# Descriptive links
descriptive = df[
    df["link_text"].str.split().str.len() >= 3
].copy()

# Random sample from remaining links
remaining = df[
    ~df["sample_id"].isin(
        pd.concat([
            ambiguous,
            bengali,
            short_links
        ])["sample_id"]
    )
]

random_sample = remaining.sample(
    n=min(300, len(remaining)),
    random_state=42
)

# ------------------------------------------------
# Combine candidates
# ------------------------------------------------

candidate_parts = [
    ambiguous,
    bengali,
    short_links,
    descriptive.sample(
        n=min(400, len(descriptive)),
        random_state=42
    ),
    random_sample
]

candidates = pd.concat(
    candidate_parts,
    ignore_index=True
)

# Remove duplicate samples
candidates = candidates.drop_duplicates(
    subset=["sample_id"]
)

# Limit total candidates
if len(candidates) > 1500:
    candidates = candidates.sample(
        n=1500,
        random_state=42
    )

# Shuffle
candidates = candidates.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)

# Create annotation columns
candidates["label"] = ""
candidates["reason"] = ""
candidates["annotator"] = ""

# Keep useful columns
final_columns = [
    "sample_id",
    "website_id",
    "website_name",
    "category",
    "language",
    "bilingual",
    "page_id",
    "page_url",
    "page_title",
    "link_text",
    "context",
    "label",
    "reason",
    "annotator"
]

candidates = candidates[
    final_columns
]

candidates.to_csv(
    OUTPUT_FILE,
    index=False
)

print("=" * 60)
print("CANDIDATE DATASET CREATED")
print("=" * 60)

print(
    "Total candidates:",
    len(candidates)
)

print("\nCategory distribution:")
print(
    candidates["category"]
    .value_counts()
)

print("\nLanguage distribution:")
print(
    candidates["language"]
    .value_counts()
)

print("\nSample:")
print(
    candidates[
        [
            "link_text",
            "page_title",
            "context"
        ]
    ]
    .head(30)
    .to_string(index=False)
)
