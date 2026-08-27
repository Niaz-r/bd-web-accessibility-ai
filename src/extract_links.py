import pandas as pd
import requests
from bs4 import BeautifulSoup

pages = pd.read_csv("data/pages.csv")

rows = []

sample_counter = 1

for _, page in pages.iterrows():

    page_url = page["page_url"]
    page_id = page["page_id"]

    try:
        r = requests.get(
            page_url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        title = ""

        if soup.title:
            title = soup.title.get_text(
                strip=True
            )

        for a in soup.find_all("a"):

            text = a.get_text(
                strip=True
            )

            if len(text) < 2:
                continue

            rows.append({
                "sample_id":
                    f"S{sample_counter:05d}",
                "page_id":
                    page_id,
                "page_url":
                    page_url,
                "page_title":
                    title,
                "link_text":
                    text
            })

            sample_counter += 1

    except Exception:
        pass

df = pd.DataFrame(rows)

df.drop_duplicates(
    subset=["page_url", "link_text"],
    inplace=True
)

df.to_csv(
    "data/links_raw.csv",
    index=False
)

print(
    "Total links:",
    len(df)
)
