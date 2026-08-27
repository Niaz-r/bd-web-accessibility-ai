import argparse
import json
import re
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path
from urllib.parse import (
    unquote,
    urlparse
)

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

SRC_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

FINAL_PIPELINE_DIR = (
    SRC_DIR.parent
)

PROJECT_ROOT = (
    FINAL_PIPELINE_DIR.parent
)


# ============================================================
# INPUT
# ============================================================

DEFAULT_INPUT_FILE = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "input"
    /
    "websites.xlsx"
)


# ============================================================
# ANALYZER
# ============================================================

ANALYZE_SCRIPT = (
    SRC_DIR
    /
    "analyze_url.py"
)


# ============================================================
# LIVE OUTPUT DIRECTORIES
# ============================================================

CUSTOM_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "intermediate"
    /
    "custom_live"
)

AXE_DIR = (
    FINAL_PIPELINE_DIR
    /
    "axe"
    /
    "results"
)

UNIFIED_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "intermediate"
    /
    "unified_live"
)

CONTEXT_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "intermediate"
    /
    "context_live"
)

CONTEXTUAL_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "final"
    /
    "contextual_recommendations"
)

RECOMMENDATION_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "final"
    /
    "live_recommendations"
)

REPORT_DIR = (
    FINAL_PIPELINE_DIR
    /
    "reports"
    /
    "live"
)


# ============================================================
# BATCH OUTPUT
# ============================================================

BATCH_DIR = (
    FINAL_PIPELINE_DIR
    /
    "reports"
    /
    "homepage_batch"
)

LOG_DIR = (
    BATCH_DIR
    /
    "logs"
)

STATUS_FILE = (
    BATCH_DIR
    /
    "homepage_batch_status.csv"
)

SUMMARY_FILE = (
    BATCH_DIR
    /
    "homepage_batch_summary.csv"
)


# ============================================================
# COLUMN CANDIDATES
# ============================================================

SITE_ID_COLUMNS = [
    "site_id",
    "site id",
    "website_id",
    "website id",
    "id",
    "code"
]

CATEGORY_COLUMNS = [
    "organization_type",
    "organization type",
    "organisation_type",
    "organisation type",
    "category",
    "type",
    "group",
    "organization",
    "organisation"
]

URL_COLUMNS = [
    "website_url",
    "website url",
    "url",
    "website",
    "homepage",
    "homepage_url",
    "homepage url",
    "site_url",
    "site url"
]

NAME_COLUMNS = [
    "website_name",
    "website name",
    "name",
    "organization_name",
    "organization name",
    "organisation_name",
    "organisation name"
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean(value):

    if pd.isna(value):
        return ""

    return str(
        value
    ).strip()


def normalize_column_name(value):

    value = clean(
        value
    ).lower()

    value = re.sub(
        r"[_\-]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def find_column(
    dataframe,
    candidates,
    required=True
):

    normalized_map = {
        normalize_column_name(column):
            column
        for column
        in dataframe.columns
    }

    for candidate in candidates:

        normalized_candidate = (
            normalize_column_name(
                candidate
            )
        )

        if (
            normalized_candidate
            in normalized_map
        ):

            return normalized_map[
                normalized_candidate
            ]

    if required:

        raise ValueError(
            (
                "Could not identify required column. "
                "Available columns: "
                +
                ", ".join(
                    str(column)
                    for column
                    in dataframe.columns
                )
            )
        )

    return None


# ============================================================
# URL HELPERS
# ============================================================

def normalize_url(
    value
):

    url = clean(
        value
    )

    if not url:
        return ""

    if not url.startswith(
        (
            "http://",
            "https://"
        )
    ):

        url = (
            "https://"
            +
            url
        )

    return url


def get_output_stem(
    url
):

    parsed = urlparse(
        url
    )

    host = (
        parsed.hostname
        or
        "unknown-host"
    ).strip().lower()

    path = unquote(
        parsed.path
        or
        ""
    )

    path = path.strip(
        "/"
    )

    if not path:

        return host

    path = path.replace(
        "/",
        "_"
    )

    path = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        path
    )

    path = re.sub(
        r"_+",
        "_",
        path
    )

    path = path.strip(
        "_"
    )

    if not path:
        return host

    return (
        host
        +
        "_"
        +
        path
    )


def safe_filename(
    value
):

    value = clean(
        value
    )

    value = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value
    )

    value = re.sub(
        r"_+",
        "_",
        value
    )

    return (
        value.strip(
            "_"
        )
        or
        "site"
    )


# ============================================================
# JSON HELPERS
# ============================================================

def read_json(
    path
):

    path = Path(
        path
    )

    if not path.exists():

        return {}

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            dict
        ):

            return data

    except Exception:
        pass

    return {}


def status_number(
    value
):

    if value is None:

        return None

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# OUTPUT FILE HELPERS
# ============================================================

def expected_files(
    url
):

    stem = get_output_stem(
        url
    )

    return {

        "stem":
            stem,

        "custom_csv":
            CUSTOM_DIR
            /
            f"{stem}__custom_findings.csv",

        "custom_meta":
            CUSTOM_DIR
            /
            f"{stem}__custom_meta.json",

        "axe_csv":
            AXE_DIR
            /
            f"{stem}__axe_nodes.csv",

        "axe_json":
            AXE_DIR
            /
            f"{stem}__axe.json",

        "unified_csv":
            UNIFIED_DIR
            /
            f"{stem}__unified_findings.csv",

        "context_csv":
            CONTEXT_DIR
            /
            f"{stem}__context_findings.csv",

        "contextual_csv":
            CONTEXTUAL_DIR
            /
            f"{stem}__contextual_recommendations.csv",

        "recommendation_csv":
            RECOMMENDATION_DIR
            /
            f"{stem}__recommendations.csv",

        "report_html":
            REPORT_DIR
            /
            f"{stem}__accessibility_report.html"
    }


# ============================================================
# RUN ANALYZER AND STREAM OUTPUT
# ============================================================

def run_analyzer(
    url,
    log_file
):

    command = [
        sys.executable,
        str(
            ANALYZE_SCRIPT
        ),
        url
    ]

    lines = []

    with open(
        log_file,
        "w",
        encoding="utf-8"
    ) as log:

        log.write(
            "COMMAND\n"
        )

        log.write(
            " ".join(
                command
            )
        )

        log.write(
            "\n\n"
        )

        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        if (
            process.stdout
            is not None
        ):

            for line in process.stdout:

                print(
                    line,
                    end=""
                )

                log.write(
                    line
                )

                lines.append(
                    line
                )

        return_code = (
            process.wait()
        )

    output_text = "".join(
        lines
    )

    return (
        return_code,
        output_text
    )


# ============================================================
# CLASSIFY RESULT
# ============================================================

def classify_result(
    return_code,
    output_text
):

    if (
        "ANALYSIS COMPLETE"
        in output_text
    ):

        return "complete"

    if (
        "TARGET NOT ANALYZABLE"
        in output_text
    ):

        return "not_analyzable"

    if (
        "TARGET UNREACHABLE"
        in output_text
    ):

        return "unreachable"

    if return_code != 0:

        return "failed"

    return "incomplete"


# ============================================================
# READ SCANNER STATUS
# ============================================================

def get_http_metadata(
    files
):

    custom_data = read_json(
        files[
            "custom_meta"
        ]
    )

    axe_data = read_json(
        files[
            "axe_json"
        ]
    )

    custom_status = status_number(
        custom_data.get(
            "status_code"
        )
    )

    rendered_status = status_number(
        axe_data.get(
            "status"
        )
    )

    if rendered_status is None:

        rendered_status = status_number(
            axe_data.get(
                "status_code"
            )
        )

    if rendered_status is None:

        rendered_status = status_number(
            axe_data.get(
                "http_status"
            )
        )

    rendered_url = clean(
        axe_data.get(
            "final_url"
        )
        or
        axe_data.get(
            "page_url"
        )
        or
        axe_data.get(
            "url"
        )
    )

    custom_analyzable = (
        str(
            custom_data.get(
                "analyzable",
                ""
            )
        )
        .lower()
        ==
        "true"
    )

    return {
        "custom_status":
            custom_status,

        "custom_analyzable":
            custom_analyzable,

        "rendered_status":
            rendered_status,

        "rendered_url":
            rendered_url
    }


# ============================================================
# LOAD EXISTING STATUS FOR RESUME
# ============================================================

def load_previous_status():

    if not STATUS_FILE.exists():

        return {}

    try:

        df = pd.read_csv(
            STATUS_FILE
        )

    except Exception:

        return {}

    result = {}

    for _, row in df.iterrows():

        site_id = clean(
            row.get(
                "site_id",
                ""
            )
        )

        if site_id:

            result[
                site_id
            ] = row.to_dict()

    return result


# ============================================================
# WRITE STATUS
# ============================================================

STATUS_COLUMNS = [

    "attempt_number",

    "site_id",

    "organization_type",

    "website_name",

    "input_url",

    "requested_url",

    "rendered_url",

    "analysis_stem",

    "batch_status",

    "return_code",

    "custom_status",

    "custom_analyzable",

    "rendered_status",

    "unified_created",

    "context_created",

    "contextual_created",

    "report_created",

    "started_at",

    "finished_at",

    "duration_seconds",

    "log_file"
]


def write_status(
    records
):

    dataframe = pd.DataFrame(
        records
    )

    for column in STATUS_COLUMNS:

        if (
            column
            not in dataframe.columns
        ):

            dataframe[
                column
            ] = ""

    dataframe = dataframe[
        STATUS_COLUMNS
    ]

    dataframe.to_csv(
        STATUS_FILE,
        index=False
    )


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    status_df
):

    if status_df.empty:

        return pd.DataFrame()

    rows = []

    categories = sorted(
        status_df[
            "organization_type"
        ]
        .fillna(
            "Unknown"
        )
        .astype(str)
        .unique()
    )

    # --------------------------------------------------------
    # Per organization type
    # --------------------------------------------------------

    for category in categories:

        group = status_df[
            status_df[
                "organization_type"
            ].astype(str)
            ==
            str(
                category
            )
        ]

        rows.append(
            {
                "organization_type":
                    category,

                "attempted":
                    len(
                        group
                    ),

                "complete":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "complete"
                        ).sum()
                    ),

                "not_analyzable":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "not_analyzable"
                        ).sum()
                    ),

                "unreachable":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "unreachable"
                        ).sum()
                    ),

                "failed":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "failed"
                        ).sum()
                    ),

                "incomplete":
                    int(
                        (
                            group[
                                "batch_status"
                            ]
                            ==
                            "incomplete"
                        ).sum()
                    ),

                "reports_created":
                    int(
                        group[
                            "report_created"
                        ]
                        .astype(str)
                        .str.lower()
                        .eq(
                            "true"
                        )
                        .sum()
                    )
            }
        )

    # --------------------------------------------------------
    # Overall row
    # --------------------------------------------------------

    rows.append(
        {
            "organization_type":
                "TOTAL",

            "attempted":
                len(
                    status_df
                ),

            "complete":
                int(
                    (
                        status_df[
                            "batch_status"
                        ]
                        ==
                        "complete"
                    ).sum()
                ),

            "not_analyzable":
                int(
                    (
                        status_df[
                            "batch_status"
                        ]
                        ==
                        "not_analyzable"
                    ).sum()
                ),

            "unreachable":
                int(
                    (
                        status_df[
                            "batch_status"
                        ]
                        ==
                        "unreachable"
                    ).sum()
                ),

            "failed":
                int(
                    (
                        status_df[
                            "batch_status"
                        ]
                        ==
                        "failed"
                    ).sum()
                ),

            "incomplete":
                int(
                    (
                        status_df[
                            "batch_status"
                        ]
                        ==
                        "incomplete"
                    ).sum()
                ),

            "reports_created":
                int(
                    status_df[
                        "report_created"
                    ]
                    .astype(str)
                    .str.lower()
                    .eq(
                        "true"
                    )
                    .sum()
                )
        }
    )

    return pd.DataFrame(
        rows
    )


# ============================================================
# ARGUMENTS
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description=(
            "Run the complete live accessibility "
            "pipeline on homepage URLs from websites.xlsx."
        )
    )

    parser.add_argument(
        "--input",
        default=str(
            DEFAULT_INPUT_FILE
        ),
        help=(
            "Input Excel file. "
            "Default: final_pipeline/data/input/websites.xlsx"
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Analyze only the first N websites."
        )
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Skip websites already recorded as complete, "
            "not_analyzable, or unreachable."
        )
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help=(
            "Delay in seconds between websites. "
            "Default: 1 second."
        )
    )

    parser.add_argument(
        "--category",
        default=None,
        help=(
            "Optional organization category filter."
        )
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    input_file = Path(
        args.input
    )

    # ========================================================
    # CHECK FILES
    # ========================================================

    if not input_file.exists():

        print(
            "ERROR: Input file not found:"
        )

        print(
            input_file
        )

        sys.exit(1)

    if not ANALYZE_SCRIPT.exists():

        print(
            "ERROR: analyze_url.py not found:"
        )

        print(
            ANALYZE_SCRIPT
        )

        sys.exit(1)

    # ========================================================
    # CREATE OUTPUT DIRS
    # ========================================================

    BATCH_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # READ EXCEL
    # ========================================================

    df = pd.read_excel(
        input_file
    )

    if df.empty:

        print(
            "ERROR: Input spreadsheet is empty."
        )

        sys.exit(1)

    # ========================================================
    # IDENTIFY COLUMNS
    # ========================================================

    url_column = find_column(
        df,
        URL_COLUMNS,
        required=True
    )

    category_column = find_column(
        df,
        CATEGORY_COLUMNS,
        required=True
    )

    site_id_column = find_column(
        df,
        SITE_ID_COLUMNS,
        required=False
    )

    name_column = find_column(
        df,
        NAME_COLUMNS,
        required=False
    )

    print()
    print(
        "=" * 80
    )

    print(
        "HOMEPAGE BATCH ACCESSIBILITY ANALYSIS"
    )

    print(
        "=" * 80
    )

    print()

    print(
        "Input:"
    )

    print(
        input_file
    )

    print()

    print(
        "Rows:",
        len(
            df
        )
    )

    print()

    print(
        "Detected columns:"
    )

    print(
        "  URL:",
        url_column
    )

    print(
        "  Organization type:",
        category_column
    )

    print(
        "  Site ID:",
        site_id_column
        or
        "generated"
    )

    print(
        "  Website name:",
        name_column
        or
        "not available"
    )

    # ========================================================
    # OPTIONAL CATEGORY FILTER
    # ========================================================

    if args.category:

        requested_category = (
            args.category
            .strip()
            .lower()
        )

        df = df[
            df[
                category_column
            ]
            .astype(str)
            .str.strip()
            .str.lower()
            ==
            requested_category
        ].copy()

        print()

        print(
            "Category filter:",
            args.category
        )

        print(
            "Rows after filter:",
            len(
                df
            )
        )

    # ========================================================
    # LIMIT
    # ========================================================

    if (
        args.limit is not None
        and
        args.limit >= 0
    ):

        df = df.head(
            args.limit
        ).copy()

        print()

        print(
            "Limit:",
            args.limit
        )

    # ========================================================
    # EXISTING STATUS
    # ========================================================

    previous = (
        load_previous_status()
        if args.resume
        else {}
    )

    final_statuses = {
        "complete",
        "not_analyzable",
        "unreachable"
    }

    records = []

    # If resuming, preserve existing rows first.
    if (
        args.resume
        and
        STATUS_FILE.exists()
    ):

        try:

            existing_df = pd.read_csv(
                STATUS_FILE
            )

            records = (
                existing_df.to_dict(
                    orient="records"
                )
            )

        except Exception:

            records = []

    # ========================================================
    # ANALYSIS LOOP
    # ========================================================

    attempted_now = 0

    total_selected = len(
        df
    )

    for position, (
        original_index,
        row
    ) in enumerate(
        df.iterrows(),
        start=1
    ):

        raw_url = clean(
            row.get(
                url_column,
                ""
            )
        )

        organization_type = clean(
            row.get(
                category_column,
                ""
            )
        )

        if site_id_column:

            site_id = clean(
                row.get(
                    site_id_column,
                    ""
                )
            )

        else:

            site_id = (
                f"SITE{position:03d}"
            )

        if not site_id:

            site_id = (
                f"SITE{position:03d}"
            )

        website_name = ""

        if name_column:

            website_name = clean(
                row.get(
                    name_column,
                    ""
                )
            )

        url = normalize_url(
            raw_url
        )

        # ----------------------------------------------------
        # RESUME
        # ----------------------------------------------------

        if args.resume:

            existing = previous.get(
                site_id
            )

            if existing:

                existing_status = clean(
                    existing.get(
                        "batch_status",
                        ""
                    )
                )

                if (
                    existing_status
                    in final_statuses
                ):

                    print()
                    print(
                        "=" * 80
                    )

                    print(
                        f"[{position}/{total_selected}] "
                        f"{site_id} — SKIPPED"
                    )

                    print(
                        "=" * 80
                    )

                    print(
                        "Previous status:",
                        existing_status
                    )

                    continue

        # ----------------------------------------------------
        # EMPTY URL
        # ----------------------------------------------------

        if not url:

            print()
            print(
                f"[{position}/{total_selected}] "
                f"{site_id}: EMPTY URL"
            )

            record = {

                "attempt_number":
                    position,

                "site_id":
                    site_id,

                "organization_type":
                    organization_type,

                "website_name":
                    website_name,

                "input_url":
                    raw_url,

                "requested_url":
                    "",

                "rendered_url":
                    "",

                "analysis_stem":
                    "",

                "batch_status":
                    "failed",

                "return_code":
                    "",

                "custom_status":
                    "",

                "custom_analyzable":
                    False,

                "rendered_status":
                    "",

                "unified_created":
                    False,

                "context_created":
                    False,

                "contextual_created":
                    False,

                "report_created":
                    False,

                "started_at":
                    "",

                "finished_at":
                    "",

                "duration_seconds":
                    0,

                "log_file":
                    ""
            }

            records.append(
                record
            )

            write_status(
                records
            )

            continue

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        attempted_now += 1

        files = expected_files(
            url
        )

        log_name = (
            safe_filename(
                site_id
            )
            +
            "__"
            +
            safe_filename(
                files[
                    "stem"
                ]
            )
            +
            ".log"
        )

        log_file = (
            LOG_DIR
            /
            log_name
        )

        print()
        print()
        print(
            "#" * 80
        )

        print(
            f"HOMEPAGE {position}/{total_selected}"
        )

        print(
            "#" * 80
        )

        print(
            "Site ID:",
            site_id
        )

        print(
            "Organization:",
            organization_type
        )

        if website_name:

            print(
                "Name:",
                website_name
            )

        print(
            "URL:",
            url
        )

        print(
            "Log:",
            log_file
        )

        print()

        start_time = (
            time.time()
        )

        started_at = (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        )

        # ----------------------------------------------------
        # RUN ANALYSIS
        # ----------------------------------------------------

        return_code, output_text = (
            run_analyzer(
                url,
                log_file
            )
        )

        end_time = (
            time.time()
        )

        finished_at = (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        )

        duration = round(
            end_time
            -
            start_time,
            2
        )

        batch_status = (
            classify_result(
                return_code,
                output_text
            )
        )

        metadata = (
            get_http_metadata(
                files
            )
        )

        record = {

            "attempt_number":
                position,

            "site_id":
                site_id,

            "organization_type":
                organization_type,

            "website_name":
                website_name,

            "input_url":
                raw_url,

            "requested_url":
                url,

            "rendered_url":
                metadata[
                    "rendered_url"
                ],

            "analysis_stem":
                files[
                    "stem"
                ],

            "batch_status":
                batch_status,

            "return_code":
                return_code,

            "custom_status":
                metadata[
                    "custom_status"
                ],

            "custom_analyzable":
                metadata[
                    "custom_analyzable"
                ],

            "rendered_status":
                metadata[
                    "rendered_status"
                ],

            "unified_created":
                files[
                    "unified_csv"
                ].exists(),

            "context_created":
                files[
                    "context_csv"
                ].exists(),

            "contextual_created":
                files[
                    "contextual_csv"
                ].exists(),

            "report_created":
                files[
                    "report_html"
                ].exists(),

            "started_at":
                started_at,

            "finished_at":
                finished_at,

            "duration_seconds":
                duration,

            "log_file":
                str(
                    log_file
                )
        }

        # ----------------------------------------------------
        # REMOVE OLD RECORD FOR SAME SITE DURING RESUME
        # ----------------------------------------------------

        records = [
            existing
            for existing
            in records
            if clean(
                existing.get(
                    "site_id",
                    ""
                )
            )
            !=
            site_id
        ]

        records.append(
            record
        )

        # ----------------------------------------------------
        # SAVE AFTER EVERY WEBSITE
        # ----------------------------------------------------

        write_status(
            records
        )

        print()
        print(
            "-" * 80
        )

        print(
            "BATCH RESULT"
        )

        print(
            "-" * 80
        )

        print(
            "Site:",
            site_id
        )

        print(
            "Status:",
            batch_status
        )

        print(
            "Custom HTTP:",
            metadata[
                "custom_status"
            ]
        )

        print(
            "Rendered HTTP:",
            metadata[
                "rendered_status"
            ]
        )

        print(
            "Report created:",
            files[
                "report_html"
            ].exists()
        )

        print(
            "Duration:",
            duration,
            "seconds"
        )

        # ----------------------------------------------------
        # DELAY
        # ----------------------------------------------------

        if (
            args.delay > 0
            and
            position < total_selected
        ):

            time.sleep(
                args.delay
            )

    # ========================================================
    # FINAL STATUS DATA
    # ========================================================

    if STATUS_FILE.exists():

        final_df = pd.read_csv(
            STATUS_FILE
        )

    else:

        final_df = pd.DataFrame(
            records
        )

    # ========================================================
    # CREATE SUMMARY
    # ========================================================

    summary = create_summary(
        final_df
    )

    if not summary.empty:

        summary.to_csv(
            SUMMARY_FILE,
            index=False
        )

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print()
    print()
    print(
        "=" * 80
    )

    print(
        "HOMEPAGE BATCH SUMMARY"
    )

    print(
        "=" * 80
    )

    print()

    if not summary.empty:

        print(
            summary.to_string(
                index=False
            )
        )

    else:

        print(
            "No results available."
        )

    print()

    print(
        "Websites processed in this run:",
        attempted_now
    )

    print()

    print(
        "Status file:"
    )

    print(
        STATUS_FILE
    )

    print()

    print(
        "Summary file:"
    )

    print(
        SUMMARY_FILE
    )

    print()

    print(
        "Individual logs:"
    )

    print(
        LOG_DIR
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This homepage batch is a separate live experimental "
        "evaluation. It does not modify the frozen historical "
        "multi-page research dataset."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
