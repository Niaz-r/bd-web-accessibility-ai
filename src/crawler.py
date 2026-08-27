import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os


# -----------------------------
# Configuration
# -----------------------------

INPUT_FILE = "data/websites.xlsx"
OUTPUT_FILE = "data/pages.csv"

MAX_PAGES_PER_SITE = 10
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/145.0 Safari/537.36"
    )
}


# -----------------------------
# Helper functions
# -----------------------------

def normalize_url(url):
    """Remove fragments and unnecessary trailing slash."""
    parsed = urlparse(url)

    clean = parsed._replace(fragment="").geturl()

    if clean.endswith("/") and parsed.path != "/":
        clean = clean[:-1]

    return clean


def is_internal_link(base_url, link):
    """Check whether a link belongs to the same domain."""
    base_domain = urlparse(base_url).netloc.lower()
    link_domain = urlparse(link).netloc.lower()

    return link_domain == base_domain


def guess_page_type(url, title):
    """Simple page-type classification."""
    text = (url + " " + title).lower()

    if any(x in text for x in ["admission", "apply"]):
        return "Admission"

    if any(x in text for x in ["notice", "notices", "circular"]):
        return "Notice"

    if any(x in text for x in ["contact"]):
        return "Contact"

    if any(x in text for x in ["about"]):
        return "About"

    if any(x in text for x in ["service", "services"]):
        return "Service"

    if any(x in text for x in ["news", "article"]):
        return "Article"

    return "Other"


def crawl_website(website_id, start_url):
    """Collect internal pages from one website."""

    pages = []
    visited = set()
    queue = [normalize_url(start_url)]

    while queue and len(pages) < MAX_PAGES_PER_SITE:

        current_url = queue.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)

        try:
            response = requests.get(
                current_url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            status = response.status_code

            # Only process successful HTML pages
            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if status != 200 or "text/html" not in content_type:
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # Page title
            title = ""

            if soup.title:
                title = soup.title.get_text(
                    strip=True
                )

            # Store page information
            page_id = f"PG{len(pages) + 1:04d}_{website_id}"

            pages.append({
                "page_id": page_id,
                "website_id": website_id,
                "page_url": current_url,
                "page_type": guess_page_type(
                    current_url,
                    title
                ),
                "title": title,
                "language": "",
                "status": status
            })

            print(
                f"    [{len(pages)}/{MAX_PAGES_PER_SITE}] "
                f"{current_url}"
            )

            # Find internal links
            for tag in soup.find_all("a", href=True):

                href = tag.get("href")

                if not href:
                    continue

                # Ignore special links
                if href.startswith(
                    ("mailto:", "tel:", "javascript:", "#")
                ):
                    continue

                absolute_url = urljoin(
                    current_url,
                    href
                )

                absolute_url = normalize_url(
                    absolute_url
                )

                # Only keep HTTP/HTTPS
                if not absolute_url.startswith(
                    ("http://", "https://")
                ):
                    continue

                # Same-domain links only
                if not is_internal_link(
                    start_url,
                    absolute_url
                ):
                    continue

                if absolute_url not in visited:
                    queue.append(absolute_url)

            time.sleep(0.5)

        except requests.RequestException as e:

            print(
                f"    ERROR: {current_url}"
            )
            print(
                f"    {type(e).__name__}: {e}"
            )

    return pages


# -----------------------------
# Main program
# -----------------------------

def main():

    print("\nLoading website list...")

    websites = pd.read_excel(INPUT_FILE)

    print(
        f"Found {len(websites)} websites.\n"
    )

    all_pages = []

    for index, row in websites.iterrows():

        website_id = str(
            row["website_id"]
        ).strip()

        website_name = str(
            row["website_name"]
        ).strip()

        start_url = str(
            row["url"]
        ).strip()

        print("\n" + "=" * 70)

        print(
            f"{index + 1}/{len(websites)} "
            f"{website_id} - {website_name}"
        )

        print(
            f"Starting URL: {start_url}"
        )

        print("=" * 70)

        pages = crawl_website(
            website_id,
            start_url
        )

        all_pages.extend(pages)

        print(
            f"Collected {len(pages)} pages."
        )

    # Create output directory
    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    # Save results
    df = pd.DataFrame(all_pages)

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 70)

    print("CRAWLING COMPLETE")

    print("=" * 70)

    print(
        f"Total pages collected: {len(df)}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
