import os
import time
import pandas as pd
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Reuse the tested crawler helpers
from crawler import (
    normalize_url,
    is_http_url,
    is_internal_link,
    should_skip_url,
    looks_like_html,
    guess_page_type,
    HEADERS,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    MAX_PAGES_PER_SITE
)


# ============================================================
# FILES
# ============================================================

WEBSITE_FILE = "final_pipeline/data/input/websites.xlsx"

EXISTING_PAGES_FILE = (
    "final_pipeline/data/intermediate/pages.csv"
)

CRAWL_REPORT_FILE = (
    "final_pipeline/data/intermediate/crawl_report.csv"
)

OUTPUT_PAGES_FILE = (
    "final_pipeline/data/intermediate/pages_final.csv"
)

OUTPUT_RECOVERY_REPORT = (
    "final_pipeline/data/intermediate/recovery_report.csv"
)


# ============================================================
# RETRY POLICY
# ============================================================
#
# Retry transient / potentially recoverable failures only.
#
# We intentionally DO NOT retry HTTP 403 websites because
# those servers explicitly rejected automated access.
# ============================================================

RETRY_WEBSITE_IDS = {
    "BD005",   # DNS
    "BD006",   # DNS
    "BD021",   # DNS
    "BD052",   # DNS
    "BD058",   # HTTP 522
    "BD061",   # DNS
    "BD062",   # DNS

    # SSL failures: one controlled retry only
    "BD071",
    "BD073",
    "BD076",
    "BD077",
    "BD080"
}

MAX_RETRY_ATTEMPTS = 2
RETRY_WAIT_SECONDS = 2


# ============================================================
# CRAWL ONE WEBSITE
# ============================================================

def crawl_retry(
    website_id,
    website_name,
    start_url,
    session
):

    pages = []

    visited = set()
    queued = set()

    start_url = normalize_url(
        start_url
    )

    queue = [start_url]

    queued.add(
        start_url
    )

    report = {
        "website_id": website_id,
        "website_name": website_name,
        "start_url": start_url,
        "success": False,
        "homepage_status": None,
        "pages_recovered": 0,
        "requests_attempted": 0,
        "failure_reason": ""
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

        response = None
        last_error = ""

        # ----------------------------------------------------
        # Controlled retry for request failures
        # ----------------------------------------------------

        for attempt in range(
            1,
            MAX_RETRY_ATTEMPTS + 1
        ):

            report[
                "requests_attempted"
            ] += 1

            print(
                f"    Attempt {attempt}/"
                f"{MAX_RETRY_ATTEMPTS}: "
                f"{current_url}"
            )

            try:

                response = session.get(
                    current_url,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True
                )

                break

            except requests.RequestException as e:

                last_error = (
                    f"{type(e).__name__}: {e}"
                )

                print(
                    f"    ERROR: {last_error}"
                )

                if attempt < MAX_RETRY_ATTEMPTS:

                    time.sleep(
                        RETRY_WAIT_SECONDS
                    )

        if response is None:

            if len(pages) == 0:

                report[
                    "failure_reason"
                ] = last_error

            continue

        status = response.status_code

        if (
            report["homepage_status"]
            is None
        ):

            report[
                "homepage_status"
            ] = status

        print(
            f"    Status: {status}"
        )

        # ----------------------------------------------------
        # Do not bypass 403
        # ----------------------------------------------------

        if status == 403:

            if len(pages) == 0:

                report[
                    "failure_reason"
                ] = "HTTP 403"

            continue

        # ----------------------------------------------------
        # Retry server-side temporary errors
        # ----------------------------------------------------

        if status in {
            408,
            429,
            500,
            502,
            503,
            504,
            520,
            521,
            522,
            523,
            524
        }:

            print(
                f"    Temporary/server error: "
                f"HTTP {status}"
            )

            if len(pages) == 0:

                report[
                    "failure_reason"
                ] = f"HTTP {status}"

            continue

        if status != 200:

            if len(pages) == 0:

                report[
                    "failure_reason"
                ] = f"HTTP {status}"

            continue

        if not looks_like_html(
            response
        ):

            if len(pages) == 0:

                report[
                    "failure_reason"
                ] = (
                    "Response was not HTML"
                )

            continue

        final_url = normalize_url(
            response.url
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title = ""

        if soup.title:

            title = soup.title.get_text(
                " ",
                strip=True
            )

        # ----------------------------------------------------
        # Language
        # ----------------------------------------------------

        page_language = ""

        html = soup.find("html")

        if html:

            page_language = (
                html.get("lang")
                or ""
            ).strip()

        # ----------------------------------------------------
        # Save recovered page
        # ----------------------------------------------------

        duplicate = any(
            normalize_url(
                page["page_url"]
            )
            == final_url

            for page in pages
        )

        if not duplicate:

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
                f"Recovered: {final_url}"
            )

        # ----------------------------------------------------
        # Internal links
        # ----------------------------------------------------

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

            absolute_url = normalize_url(
                absolute_url
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
                and absolute_url
                not in queued
            ):

                queue.append(
                    absolute_url
                )

                queued.add(
                    absolute_url
                )

        time.sleep(
            REQUEST_DELAY
        )

    report[
        "pages_recovered"
    ] = len(pages)

    report[
        "success"
    ] = len(pages) > 0

    if (
        not pages
        and not report["failure_reason"]
    ):

        report[
            "failure_reason"
        ] = "No usable pages recovered"

    return pages, report


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("FAILED WEBSITE RECOVERY")
    print("=" * 70)

    websites = pd.read_excel(
        WEBSITE_FILE
    )

    existing_pages = pd.read_csv(
        EXISTING_PAGES_FILE
    )

    crawl_report = pd.read_csv(
        CRAWL_REPORT_FILE
    )

    # --------------------------------------------------------
    # Only retry selected failed IDs
    # --------------------------------------------------------

    candidates = websites[
        websites["website_id"]
        .astype(str)
        .isin(RETRY_WEBSITE_IDS)
    ].copy()

    successful_existing_ids = set(
        existing_pages[
            "website_id"
        ].astype(str)
    )

    # Do not retry something that somehow already has pages
    candidates = candidates[
        ~candidates[
            "website_id"
        ].astype(str)
        .isin(successful_existing_ids)
    ]

    print(
        "Recovery candidates:",
        len(candidates)
    )

    print()

    if len(candidates) == 0:

        print(
            "No retry candidates remain."
        )

        existing_pages.to_csv(
            OUTPUT_PAGES_FILE,
            index=False
        )

        return

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    recovered_pages = []
    recovery_reports = []

    for _, row in candidates.iterrows():

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
            f"Start URL: {start_url}"
        )

        print("=" * 70)

        pages, report = crawl_retry(
            website_id,
            website_name,
            start_url,
            session
        )

        recovered_pages.extend(
            pages
        )

        recovery_reports.append(
            report
        )

    # ========================================================
    # BUILD FINAL PAGE LIST
    # ========================================================

    recovered_df = pd.DataFrame(
        recovered_pages
    )

    if len(recovered_df) > 0:

        combined = pd.concat(
            [
                existing_pages,
                recovered_df
            ],
            ignore_index=True
        )

    else:

        combined = (
            existing_pages.copy()
        )

    # --------------------------------------------------------
    # Normalize URLs and remove duplicates
    # --------------------------------------------------------

    combined[
        "_normalized_url"
    ] = (
        combined["page_url"]
        .astype(str)
        .apply(normalize_url)
    )

    combined = (
        combined
        .drop_duplicates(
            subset=[
                "website_id",
                "_normalized_url"
            ]
        )
        .drop(
            columns=[
                "_normalized_url"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    os.makedirs(
        "final_pipeline/data/intermediate",
        exist_ok=True
    )

    combined.to_csv(
        OUTPUT_PAGES_FILE,
        index=False
    )

    recovery_df = pd.DataFrame(
        recovery_reports
    )

    recovery_df.to_csv(
        OUTPUT_RECOVERY_REPORT,
        index=False
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("RECOVERY COMPLETE")
    print("=" * 70)

    print(
        "Original pages:",
        len(existing_pages)
    )

    print(
        "Recovered pages:",
        len(recovered_df)
    )

    print(
        "Final pages:",
        len(combined)
    )

    print(
        "Original websites:",
        existing_pages[
            "website_id"
        ].nunique()
    )

    print(
        "Final websites:",
        combined[
            "website_id"
        ].nunique()
    )

    print()

    if len(recovery_df) > 0:

        print(
            recovery_df[
                [
                    "website_id",
                    "success",
                    "homepage_status",
                    "pages_recovered",
                    "requests_attempted",
                    "failure_reason"
                ]
            ].to_string(
                index=False
            )
        )

    print()

    print(
        "Final pages file:",
        OUTPUT_PAGES_FILE
    )

    print(
        "Recovery report:",
        OUTPUT_RECOVERY_REPORT
    )


if __name__ == "__main__":
    main()
