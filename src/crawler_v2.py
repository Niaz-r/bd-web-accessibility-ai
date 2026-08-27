import os
import time
import re
import pandas as pd
import requests

from bs4 import BeautifulSoup
from urllib.parse import (
    urljoin,
    urlparse,
    urlunparse
)


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "data/websites.xlsx"

OUTPUT_PAGES = "data/pages_recovered.csv"
OUTPUT_REPORT = "data/crawl_report.csv"

MAX_PAGES_PER_SITE = 10
REQUEST_TIMEOUT = 20
DELAY = 0.4


# Only recover websites missing from the original pages.csv
MISSING_IDS = {
    "BD002",
    "BD006",
    "BD012",
    "BD016",
    "BD017",
    "BD019",
    "BD022",
    "BD024",
    "BD026"
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    "Connection": "keep-alive"
}


# ============================================================
# URL FUNCTIONS
# ============================================================

def normalize_host(host):
    """
    Treat www.example.com and example.com as the same website.
    """

    host = (host or "").lower().strip()

    if host.startswith("www."):
        host = host[4:]

    return host


def normalize_url(url):
    """
    Normalize URLs for duplicate detection.
    """

    url = str(url).strip()

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()

    hostname = parsed.hostname or ""

    # Keep port if one exists
    netloc = hostname.lower()

    if parsed.port:
        netloc += f":{parsed.port}"

    path = re.sub(r"/+", "/", parsed.path)

    # Remove trailing slash except homepage
    if path != "/":
        path = path.rstrip("/")

    # Remove fragments.
    # Query parameters are retained because some real pages use them.
    normalized = urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            parsed.query,
            ""
        )
    )

    return normalized


def is_internal_link(base_url, candidate_url):
    """
    Allow www/non-www variation.
    """

    base_host = normalize_host(
        urlparse(base_url).hostname
    )

    candidate_host = normalize_host(
        urlparse(candidate_url).hostname
    )

    return base_host == candidate_host


def is_http_url(url):

    scheme = urlparse(url).scheme.lower()

    return scheme in {
        "http",
        "https"
    }


# ============================================================
# FILTERS
# ============================================================

SKIP_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".css",
    ".js",
    ".xml",
    ".zip",
    ".rar",
    ".7z",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx"
}


def should_skip_url(url):

    path = urlparse(url).path.lower()

    for extension in SKIP_EXTENSIONS:

        if path.endswith(extension):
            return True

    return False


# ============================================================
# PAGE TYPE
# ============================================================

def guess_page_type(url, title):

    text = f"{url} {title}".lower()

    if any(
        x in text
        for x in [
            "admission",
            "apply"
        ]
    ):
        return "Admission"

    if any(
        x in text
        for x in [
            "notice",
            "notices",
            "circular"
        ]
    ):
        return "Notice"

    if "contact" in text:
        return "Contact"

    if "about" in text:
        return "About"

    if any(
        x in text
        for x in [
            "service",
            "services"
        ]
    ):
        return "Service"

    if any(
        x in text
        for x in [
            "news",
            "article",
            "story"
        ]
    ):
        return "Article"

    return "Other"


# ============================================================
# HTML CHECK
# ============================================================

def looks_like_html(response):

    content_type = (
        response.headers
        .get("Content-Type", "")
        .lower()
    )

    if "text/html" in content_type:

        return True

    # Some servers return bad/missing Content-Type.
    beginning = response.text[:1000].lower()

    return (
        "<html" in beginning
        or "<!doctype html" in beginning
    )


# ============================================================
# CRAWLER
# ============================================================

def crawl_website(
    website_id,
    website_name,
    start_url,
    session
):

    pages = []

    visited = set()
    queued = set()

    start_url = normalize_url(start_url)

    queue = [start_url]
    queued.add(start_url)

    report = {
        "website_id": website_id,
        "website_name": website_name,
        "start_url": start_url,
        "homepage_status": None,
        "final_homepage_url": "",
        "pages_collected": 0,
        "failure_reason": "",
        "possible_javascript_site": False
    }

    while (
        queue
        and len(pages) < MAX_PAGES_PER_SITE
    ):

        current_url = queue.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)

        print(
            f"    Requesting: {current_url}"
        )

        try:

            response = session.get(
                current_url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

        except requests.RequestException as e:

            print(
                f"    ERROR: "
                f"{type(e).__name__}: {e}"
            )

            if not pages:

                report["failure_reason"] = (
                    f"{type(e).__name__}: {e}"
                )

            continue

        status = response.status_code

        final_url = normalize_url(
            response.url
        )

        # Record homepage request information
        if report["homepage_status"] is None:

            report["homepage_status"] = status

            report["final_homepage_url"] = (
                final_url
            )

        print(
            f"    Status: {status}"
        )

        if status != 200:

            if not pages:

                report["failure_reason"] = (
                    f"HTTP {status}"
                )

            continue

        if not looks_like_html(response):

            print(
                "    Skipped: response does "
                "not appear to be HTML."
            )

            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = ""

        if soup.title:

            title = soup.title.get_text(
                " ",
                strip=True
            )

        # Avoid duplicate page caused by redirect
        already_saved = any(
            normalize_url(
                page["page_url"]
            )
            == final_url
            for page in pages
        )

        if not already_saved:

            page_id = (
                f"PG{len(pages) + 1:04d}_"
                f"{website_id}"
            )

            pages.append(
                {
                    "page_id": page_id,
                    "website_id": website_id,
                    "page_url": final_url,
                    "page_type": guess_page_type(
                        final_url,
                        title
                    ),
                    "title": title,
                    "language": "",
                    "status": status
                }
            )

            print(
                f"    [{len(pages)}/"
                f"{MAX_PAGES_PER_SITE}] "
                f"Saved: {final_url}"
            )

        # --------------------------------------------
        # Extract links
        # --------------------------------------------

        links_found = 0

        for tag in soup.find_all(
            "a",
            href=True
        ):

            href = (
                tag.get("href")
                or ""
            ).strip()

            if not href:

                continue

            if href.lower().startswith(
                (
                    "mailto:",
                    "tel:",
                    "javascript:",
                    "data:"
                )
            ):
                continue

            # Ignore fragment-only links
            if href.startswith("#"):

                continue

            absolute_url = urljoin(
                final_url,
                href
            )

            absolute_url = normalize_url(
                absolute_url
            )

            if not is_http_url(
                absolute_url
            ):
                continue

            # Use the redirected/final host as well as
            # original site for internal-link validation.
            if not (
                is_internal_link(
                    start_url,
                    absolute_url
                )
                or
                is_internal_link(
                    final_url,
                    absolute_url
                )
            ):
                continue

            if should_skip_url(
                absolute_url
            ):
                continue

            if (
                absolute_url not in visited
                and absolute_url not in queued
            ):

                queue.append(
                    absolute_url
                )

                queued.add(
                    absolute_url
                )

                links_found += 1

        # --------------------------------------------
        # Detect likely JS-only site
        # --------------------------------------------

        if (
            len(pages) == 1
            and links_found == 0
        ):

            scripts = soup.find_all(
                "script"
            )

            root_text = soup.get_text(
                " ",
                strip=True
            )

            if (
                len(scripts) >= 5
                and len(root_text) < 500
            ):

                report[
                    "possible_javascript_site"
                ] = True

        time.sleep(DELAY)

    report["pages_collected"] = (
        len(pages)
    )

    if (
        len(pages) == 0
        and not report["failure_reason"]
    ):

        report["failure_reason"] = (
            "No usable HTML pages found"
        )

    elif (
        len(pages) == 1
        and report[
            "possible_javascript_site"
        ]
    ):

        report["failure_reason"] = (
            "Only one HTML shell page found; "
            "site may require JavaScript rendering"
        )

    return pages, report


# ============================================================
# MAIN
# ============================================================

def main():

    websites = pd.read_excel(
        INPUT_FILE
    )

    # Only websites missing from pages.csv
    websites = websites[
        websites["website_id"].isin(
            MISSING_IDS
        )
    ].copy()

    print()
    print("=" * 70)
    print("RECOVERY CRAWL")
    print("=" * 70)

    print(
        "Websites to retry:",
        len(websites)
    )

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    all_pages = []
    reports = []

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

        print()
        print("=" * 70)

        print(
            f"{website_id} - "
            f"{website_name}"
        )

        print(
            f"Start: {start_url}"
        )

        print("=" * 70)

        pages, report = crawl_website(
            website_id,
            website_name,
            start_url,
            session
        )

        all_pages.extend(
            pages
        )

        reports.append(
            report
        )

        print(
            f"Collected: {len(pages)}"
        )

    os.makedirs(
        "data",
        exist_ok=True
    )

    pages_df = pd.DataFrame(
        all_pages
    )

    report_df = pd.DataFrame(
        reports
    )

    pages_df.to_csv(
        OUTPUT_PAGES,
        index=False
    )

    report_df.to_csv(
        OUTPUT_REPORT,
        index=False
    )

    print()
    print("=" * 70)
    print("RECOVERY COMPLETE")
    print("=" * 70)

    print(
        "Recovered pages:",
        len(pages_df)
    )

    print(
        "Recovered websites:",
        (
            pages_df["website_id"].nunique()
            if len(pages_df)
            else 0
        )
    )

    print()
    print(
        report_df[
            [
                "website_id",
                "homepage_status",
                "pages_collected",
                "possible_javascript_site",
                "failure_reason"
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print(
        "Pages output:",
        OUTPUT_PAGES
    )

    print(
        "Report output:",
        OUTPUT_REPORT
    )


if __name__ == "__main__":
    main()
