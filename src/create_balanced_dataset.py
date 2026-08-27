import pandas as pd
import numpy as np

INPUT_FILE = "data/annotation_dataset.csv"
WEBSITES_FILE = "data/websites.xlsx"
OUTPUT_FILE = "data/annotation_final.csv"

RANDOM_STATE = 42

# --------------------------------------------------
# Load data
# --------------------------------------------------

links = pd.read_csv(INPUT_FILE)
websites = pd.read_excel(WEBSITES_FILE)

# --------------------------------------------------
# Normalize university type
# --------------------------------------------------

websites["university_type"] = ""

websites.loc[
    websites["notes"]
    .fillna("")
    .str.lower()
    .str.contains("public"),
    "university_type"
] = "Public University"

websites.loc[
    websites["notes"]
    .fillna("")
    .str.lower()
    .str.contains("private|priavate"),
    "university_type"
] = "Private University"

# --------------------------------------------------
# Merge website information
# --------------------------------------------------

df = links.merge(
    websites[
        [
            "website_id",
            "university_type"
        ]
    ],
    on="website_id",
    how="left"
)

# --------------------------------------------------
# Create research group
# --------------------------------------------------

def get_group(row):

    if row["category"] == "University":
        return row["university_type"]

    if row["category"] == "News":
        return "News"

    if row["category"] == "Government":
        return "Government"

    return "Other"


df["research_group"] = df.apply(
    get_group,
    axis=1
)

# --------------------------------------------------
# Target number of samples
# --------------------------------------------------

targets = {
    "Public University": 250,
    "Private University": 200,
    "News": 200,
    "Government": 150
}

# --------------------------------------------------
# Sample approximately equally from each website
# --------------------------------------------------

selected_parts = []

for group, target in targets.items():

    group_df = df[
        df["research_group"] == group
    ].copy()

    print(
        f"\n{group}: "
        f"{len(group_df)} available samples"
    )

    website_ids = (
        group_df["website_id"]
        .dropna()
        .unique()
    )

    n_websites = len(website_ids)

    if n_websites == 0:
        continue

    # Base number per website
    base = target // n_websites

    remainder = target % n_websites

    for i, website_id in enumerate(
        website_ids
    ):

        website_df = group_df[
            group_df["website_id"] ==
            website_id
        ]

        n = base

        # Distribute remaining samples
        if i < remainder:
            n += 1

        # Don't request more than available
        n = min(
            n,
            len(website_df)
        )

        if n > 0:

            sampled = website_df.sample(
                n=n,
                random_state=(
                    RANDOM_STATE + i
                )
            )

            selected_parts.append(
                sampled
            )


# --------------------------------------------------
# Combine
# --------------------------------------------------

final_df = pd.concat(
    selected_parts,
    ignore_index=True
)

# Shuffle
final_df = final_df.sample(
    frac=1,
    random_state=RANDOM_STATE
).reset_index(drop=True)

# --------------------------------------------------
# Reset annotation fields
# --------------------------------------------------

final_df["label"] = ""
final_df["annotation_reason"] = ""
final_df["annotation_date"] = ""
final_df["review_status"] = "Not Reviewed"

# --------------------------------------------------
# Create annotation ID
# --------------------------------------------------

final_df["annotation_id"] = [
    f"A{i:04d}"
    for i in range(
        1,
        len(final_df) + 1
    )
]

# --------------------------------------------------
# Save
# --------------------------------------------------

final_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# --------------------------------------------------
# Report
# --------------------------------------------------

print("\n" + "=" * 60)
print("FINAL ANNOTATION DATASET")
print("=" * 60)

print(
    "Total samples:",
    len(final_df)
)

print("\nResearch group:")
print(
    final_df[
        "research_group"
    ].value_counts()
)

print("\nWebsite distribution:")
print(
    final_df.groupby(
        [
            "research_group",
            "website_id"
        ]
    ).size().to_string()
)

print("\nLink language:")
print(
    final_df[
        "link_language"
    ].value_counts()
)

print("\nSaved to:")
print(OUTPUT_FILE)
