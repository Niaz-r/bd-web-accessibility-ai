import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

INPUT_FILE = "data/links_clean.csv"
OUTPUT_FILE = "data/links_context.csv"

df = pd.read_csv(INPUT_FILE)

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/145.0 Safari/537.36"
    )
})


def clean(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_local_context(link):

    parts = []

    # 1. Nearest heading
    heading = link.find_previous(
        ["h1", "h2", "h3", "h4"]
    )

    if heading:
        heading_text = clean(
            heading.get_text(" ", strip=True)
        )

        if heading_text:
            parts.append(heading_text)

    # 2. Nearest paragraph
    paragraph = link.find_previous("p")

    if paragraph:

        paragraph_text = clean(
            paragraph.get_text(
                " ",
                strip=True
            )
        )

        if paragraph_text:

            # Don't include huge blocks
            if len(paragraph_text) <= 300:
                parts.append(paragraph_text)

    # 3. Immediate parent if it is small
    parent = link.parent

    if parent:

        parent_text = clean(
            parent.get_text(
                " ",
                strip=True
            )
        )

        if (
            len(parent_text) >= 5
            and len(parent_text) <= 200
        ):
            parts.append(parent_text)

    # Remove duplicates
    unique_parts = []

    for part in parts:

        if part not in unique_parts:
            unique_parts.append(part)

    return " | ".join(unique_parts)[:500]


results = []

for index, row in df.iterrows():

    url = row["page_url"]
    target_text = clean(row["link_text"])

    context = ""

    try:

        response = session.get(
            url,
            timeout=15
        )

        if response.status_code != 200:
            raise Exception(
                f"HTTP {response.status_code}"
            )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Find matching link
        for link in soup.find_all("a"):

            current_text = clean(
                link.get_text(
                    " ",
                    strip=True
                )
            )

            if current_text != target_text:
                continue

            context = get_local_context(link)

            break

    except Exception:
        context = ""

    results.append({
        "sample_id": row["sample_id"],
        "page_id": row["page_id"],
        "page_url": row["page_url"],
        "page_title": row["page_title"],
        "link_text": row["link_text"],
        "context": context
    })

    if (index + 1) % 100 == 0:
        print(
            f"Processed {index + 1}/{len(df)}"
        )

    time.sleep(0.03)


result_df = pd.DataFrame(results)

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nContext extraction complete.")

print(
    "Total samples:",
    len(result_df)
)

print(
    "Non-empty contexts:",
    result_df["context"]
    .fillna("")
    .str.len()
    .gt(0)
    .sum()
)

print("\nSample results:")

print(
    result_df[
        [
            "link_text",
            "page_title",
            "context"
        ]
    ]
    .head(30)
    .to_string(index=False)
)
