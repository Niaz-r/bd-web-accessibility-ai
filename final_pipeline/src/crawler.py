import os
import re
import time
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

INPUT_FILE = "final_pipeline/data/input/websites.xlsx"

OUTPUT_PAGES = (
    "final_pipeline/data/intermediate/pages.csv"
)

OUTPUT_REPORT = (
    "final_pipeline/data/intermediate/crawl_report.csv"
)

MAX_PAGES_PER_SITE = 10
REQUEST_TIMEOUT = 20
REQUEST_DELAY = 0.4


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": (
        "en-US,en;q=0.9,bn;q=0.8"
    ),
    "Connection": "keep-alive"
}


# ============================================================
# URL HELPERS
# ============================================================

def normalize_host(host):
    host = (host or "").lower().strip()

    if host.startswith("www."):
        host = host[4:]

    return host


def normalize_url(url):
    """
    Normalize URL for duplicate detection.

    - remove fragment
    - normalize duplicate slashes
    - remove unnecessary trailing slash
    """

    url = str(url).strip()

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()

    hostname = parsed.hostname or ""

    netloc = hostname.lower()

    if parsed.port:
        netloc += f":{parsed.port}"

    path = re.sub(
        r"/+",
        "/",
        parsed.path
    )

    if path != "/":
        path = path.rstrip("/")

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            parsed.query,
            ""
        )
    )


def is_http_url(url):
    return (
        urlparse(url)
        .scheme
        .lower()
        in {"http", "https"}
    )


def is_internal_link(
    original_url,
    final_url,
    candidate_url
):

    candidate_host = normalize_host(
        urlparse(candidate_url).hostname
    )

    original_host = normalize_host(
        urlparse(original_url).hostname
    )

    final_host = normalize_host(
        urlparse(final_url).hostname
    )

    return candidate_host in {
        original_host,
        final_host
    }


# ============================================================
# FILE FILTER
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

    path = (
        urlparse(url)
        .path
        .lower()
    )

    return any(
        path.endswith(ext)
        for ext in SKIP_EXTENSIONS
    )


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

    beginning = (
        response.text[:1500]
        .lower()
    )

    return (
        "<html" in beginning
        or "<!doctype html" in beginning
    )


# ============================================================
# PAGE TYPE
# ============================================================

def guess_page_type(url, title):

    text = (
        f"{url} {title}"
        .lower()
    )

    if any(
        word in text
        for word in [
            "admission",
            "apply"
        ]
    ):
        return "Admission"

    if any(
        word in text
        for word in [
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
        word in text
        for word in [
            "service",
            "services"
        ]
    ):
        return "Service"

    if any(
        word in text
        for word in [
            "news",
            "article",
            "story"
        ]
    ):
        return "Article"

    return "Other"


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

    original_start_url = start_url

    start_url = normalize_url(
        start_url
    )

    queue = [start_url]
    queued.add(start_url)

    report = {
        "website_id": website_id,
        "website_name": website_name,
        "start_url": original_start_url,
        "homepage_status": None,
        "final_homepage_url": "",
        "pages_collected": 0,
        "requests_attempted": 0,
        "http_403_count": 0,
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

        visited.add(
            current_url
        )

        report[
            "requests_attempted"
        ] += 1

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
                "    ERROR:",
                type(e).__name__,
                str(e)
            )

            if len(pages) == 0:
                report["failure_reason"] = (
                    f"{type(e).__name__}: {e}"
                )

            continue

        status = response.status_code

        final_url = normalize_url(
            response.url
        )

        if (
            report["homepage_status"]
            is None
        ):

            report[
                "homepage_status"
            ] = status

            report[
                "final_homepage_url"
            ] = final_url

        print(
            f"    Status: {status}"
        )

        if status == 403:
            report[
                "http_403_count"
            ] += 1

        if status != 200:

            if len(pages) == 0:
                report[
                    "failure_reason"
                ] = f"HTTP {status}"

            continue

        if not looks_like_html(
            response
        ):

            print(
                "    Skipped: non-HTML response"
            )

            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # ----------------------------------------------------
        # PAGE TITLE
        # ----------------------------------------------------

        title = ""

        if soup.title:
            title = soup.title.get_text(
                " ",
                strip=True
            )

        # ----------------------------------------------------
        # LANGUAGE
        # ----------------------------------------------------

        html_tag = soup.find("html")

        page_language = ""

        if html_tag:
            page_language = (
                html_tag.get("lang")
                or ""
            ).strip()

        # ----------------------------------------------------
        # SAVE PAGE
        # ----------------------------------------------------

        already_saved = any(
            normalize_url(
                item["page_url"]
            ) == final_url
            for item in pages
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
                    "language": page_language,
                    "status": status
                }
            )

            print(
                f"    [{len(pages)}/"
                f"{MAX_PAGES_PER_SITE}] "
                f"Saved: {final_url}"
            )

        # ----------------------------------------------------
        # EXTRACT INTERNAL LINKS
        # ----------------------------------------------------

        new_links = 0

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

            if href.startswith("#"):
                continue

            absolute_url = urljoin(
                final_url,
                href
            )

            absolute_url = (
                normalize_url(
                    absolute_url
                )
            )

            if not is_http_url(
                absolute_url
            ):
                continue

            if not is_internal_link(
                start_url,
                final_url,
                absolute_url
            ):
                continue

            if should_skip_url(
                absolute_url
            ):
                continue

            if (
                absolute_url
                not in visited
                and
                absolute_url
                not in queued
            ):

                queue.append(
                    absolute_url
                )

                queued.add(
                    absolute_url
                )

                new_links += 1

        # ----------------------------------------------------
        # POSSIBLE JAVASCRIPT SITE
        # ----------------------------------------------------

        if (
            len(pages) == 1
            and new_links == 0
        ):

            scripts = soup.find_all(
                "script"
            )

            visible_text = (
                soup.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                len(scripts) >= 5
                and len(visible_text) < 500
            ):

                report[
                    "possible_javascript_site"
                ] = True

        time.sleep(
            REQUEST_DELAY
        )

    # ========================================================
    # REPORT FINAL STATUS
    # ========================================================

    report[
        "pages_collected"
    ] = len(pages)

    if (
        len(pages) == 0
        and not report["failure_reason"]
    ):

        report[
            "failure_reason"
        ] = "No usable HTML pages found"

    elif (
        len(pages) == 1
        and report[
            "possible_javascript_site"
        ]
    ):

        report[
            "failure_reason"
        ] = (
            "Only one HTML shell page found; "
            "possible JavaScript-rendered site"
        )

    return pages, report


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("FINAL WEBSITE CRAWLER")
    print("=" * 70)

    websites = pd.read_excel(
        INPUT_FILE
    )

    print(
        "Websites in input:",
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
            f"[{index + 1}/{len(websites)}] "
            f"{website_id} - {website_name}"
        )

        print(
            f"Start URL: {start_url}"
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
            f"Collected pages: {len(pages)}"
        )

    # ========================================================
    # SAVE
    # ========================================================

    os.makedirs(
        "final_pipeline/data/intermediate",
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
    print("CRAWLING COMPLETE")
    print("=" * 70)

    print(
        "Selected websites:",
        len(websites)
    )

    print(
        "Websites with pages:",
        (
            pages_df[
                "website_id"
            ].nunique()
            if len(pages_df)
            else 0
        )
    )

    print(
        "Total pages:",
        len(pages_df)
    )

    print()
    print("Crawler report:")

    print(
        report_df[
            [
                "website_id",
                "homepage_status",
                "pages_collected",
                "requests_attempted",
                "http_403_count",
                "possible_javascript_site",
                "failure_reason"
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print(
        "Pages:",
        OUTPUT_PAGES
    )

    print(
        "Report:",
        OUTPUT_REPORT
    )


if __name__ == "__main__":
    main()
