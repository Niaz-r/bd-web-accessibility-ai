import pandas as pd
import re

INPUT_FILE = "data/candidate_samples.csv"
OUTPUT_FILE = "data/annotation_dataset.csv"

df = pd.read_csv(INPUT_FILE)

# --------------------------------------------------
# Detect language of individual link text
# --------------------------------------------------

def detect_link_language(text):

    if pd.isna(text):
        return "Unknown"

    text = str(text)

    bengali = bool(
        re.search(r"[\u0980-\u09FF]", text)
    )

    english = bool(
        re.search(r"[A-Za-z]", text)
    )

    if bengali and english:
        return "Mixed"

    if bengali:
        return "Bengali"

    if english:
        return "English"

    return "Other"


df["link_language"] = (
    df["link_text"]
    .apply(detect_link_language)
)

# --------------------------------------------------
# Annotation columns
# --------------------------------------------------

df["label"] = ""

df["annotation_reason"] = ""

df["annotator"] = "Niaz"

df["annotation_date"] = ""

# --------------------------------------------------
# Add annotation guideline columns
# --------------------------------------------------

df["review_status"] = "Not Reviewed"

# --------------------------------------------------
# Save
# --------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("=" * 60)
print("ANNOTATION DATASET CREATED")
print("=" * 60)

print("Total samples:", len(df))

print("\nWebsite category:")
print(
    df["category"].value_counts()
)

print("\nLink language:")
print(
    df["link_language"].value_counts()
)

print("\nColumns:")
print(
    df.columns.tolist()
)

print("\nFirst 20 samples:")
print(
    df[
        [
            "sample_id",
            "category",
            "link_language",
            "link_text",
            "context",
            "label"
        ]
    ]
    .head(20)
    .to_string(index=False)
)
