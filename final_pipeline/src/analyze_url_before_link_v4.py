import csv
import json
import re
import shutil
import subprocess
import sys
import time

from pathlib import Path
from urllib.parse import (
    unquote,
    urlparse
)


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
# SCRIPT PATHS
# ============================================================

CUSTOM_SCRIPT = (
    SRC_DIR
    /
    "export_custom_findings.py"
)

AXE_SCRIPT = (
    FINAL_PIPELINE_DIR
    /
    "axe"
    /
    "run_axe.js"
)

MERGE_SCRIPT = (
    SRC_DIR
    /
    "merge_findings.py"
)

CONTEXT_SCRIPT = (
    SRC_DIR
    /
    "context_extractor.py"
)

V3_SCRIPT = (
    SRC_DIR
    /
    "recommendation_engine_v3.py"
)

V2_SCRIPT = (
    SRC_DIR
    /
    "recommendation_engine_v2.py"
)

VLM_SCRIPT = (
    SRC_DIR
    /
    "vlm_alt_analyzer.py"
)

VLM_MODEL = (
    "qwen2.5vl:3b"
)


# ============================================================
# OUTPUT DIRECTORIES
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

V3_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "final"
    /
    "contextual_recommendations"
)

VLM_DIR = (
    FINAL_PIPELINE_DIR
    /
    "data"
    /
    "final"
    /
    "vlm_alt_reviews"
)

FINAL_RECOMMENDATION_DIR = (
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
# TERMINAL HELPERS
# ============================================================

def divider():

    print()
    print(
        "=" * 80
    )


def stage(
    number,
    title
):

    divider()

    print(
        f"STAGE {number}: {title}"
    )

    divider()

    print()


def warning(
    message
):

    print()
    print(
        "WARNING:"
    )

    print(
        message
    )

    print()


def error_message(
    message
):

    print()
    print(
        "ERROR:"
    )

    print(
        message
    )

    print()


# ============================================================
# COMMAND EXECUTION
# ============================================================

def run_command(
    command,
    fatal=True
):

    command = [
        str(part)
        for part
        in command
    ]

    print(
        "Running:"
    )

    print(
        " ".join(
            command
        )
    )

    print()

    try:

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False
        )

    except Exception as error:

        error_message(
            f"Could not execute command:\n{error}"
        )

        if fatal:

            sys.exit(1)

        return 1

    if (
        result.returncode != 0
        and
        fatal
    ):

        error_message(
            (
                "Command failed with exit code "
                f"{result.returncode}"
            )
        )

        sys.exit(
            result.returncode
        )

    return result.returncode


# ============================================================
# JSON READER
# ============================================================

def read_json_file(
    path
):

    if path is None:

        return {}

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

    except Exception as error:

        warning(
            (
                "Could not read JSON metadata:\n"
                f"{path}\n"
                f"{error}"
            )
        )

    return {}


# ============================================================
# VALUE HELPERS
# ============================================================

def bool_value(
    value
):

    if isinstance(
        value,
        bool
    ):

        return value

    return (
        str(
            value
        )
        .strip()
        .lower()
        in {
            "true",
            "1",
            "yes"
        }
    )


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
# URL HELPERS
# ============================================================

def normalize_url(
    raw_url
):

    url = str(
        raw_url
    ).strip()

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


def get_host(
    url
):

    parsed = urlparse(
        url
    )

    return (
        parsed.hostname
        or
        "unknown-host"
    ).strip().lower()


def get_output_stem(
    url
):
    """
    Build a filename-friendly identifier.

    Examples:

    https://www.du.ac.bd/
        -> www.du.ac.bd

    https://cu.ac.bd/vision-and-mission/
        -> cu.ac.bd_vision-and-mission

    https://example.com/about/team/
        -> example.com_about_team
    """

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


# ============================================================
# OUTPUT FILE DISCOVERY
# ============================================================

def file_modified_after(
    path,
    timestamp,
    tolerance=2.0
):

    try:

        return (
            path.exists()
            and
            path.stat().st_mtime
            >=
            (
                timestamp
                -
                tolerance
            )
        )

    except OSError:

        return False


def find_generated_file(
    directory,
    expected_path,
    suffix,
    stage_start
):
    """
    Find a file created by the current pipeline stage while
    tolerating both live-output naming conventions:

        site_suffix.csv
        site__suffix.csv

    This also preserves redirect handling because the function
    falls back to the most recently generated matching file.
    """

    directory = Path(
        directory
    )

    expected_path = Path(
        expected_path
    )

    # --------------------------------------------------------
    # ACCEPT BOTH SINGLE- AND DOUBLE-UNDERSCORE SUFFIXES
    # --------------------------------------------------------

    suffix_candidates = {
        suffix
    }

    if suffix.startswith(
        "__"
    ):

        suffix_candidates.add(
            suffix[1:]
        )

    elif suffix.startswith(
        "_"
    ):

        suffix_candidates.add(
            "_" + suffix
        )

    # --------------------------------------------------------
    # EXPECTED PATH
    # --------------------------------------------------------

    if file_modified_after(
        expected_path,
        stage_start
    ):

        return expected_path

    # --------------------------------------------------------
    # TRY THE ALTERNATE EXPECTED FILENAME
    # --------------------------------------------------------

    expected_name = expected_path.name

    for candidate_suffix in sorted(
        suffix_candidates,
        key=len,
        reverse=True
    ):

        for source_suffix in sorted(
            suffix_candidates,
            key=len,
            reverse=True
        ):

            if expected_name.endswith(
                source_suffix
            ):

                alternate_name = (
                    expected_name[
                        :-len(
                            source_suffix
                        )
                    ]
                    +
                    candidate_suffix
                )

                alternate_path = (
                    expected_path.parent
                    /
                    alternate_name
                )

                if file_modified_after(
                    alternate_path,
                    stage_start
                ):

                    return alternate_path

    # --------------------------------------------------------
    # SEARCH RECENT OUTPUT FILES
    # --------------------------------------------------------

    candidates = []
    seen = set()

    if directory.exists():

        for candidate_suffix in sorted(
            suffix_candidates,
            key=len,
            reverse=True
        ):

            for path in directory.glob(
                f"*{candidate_suffix}"
            ):

                if (
                    path not in seen
                    and
                    file_modified_after(
                        path,
                        stage_start
                    )
                ):

                    candidates.append(
                        path
                    )

                    seen.add(
                        path
                    )

    if not candidates:

        return None

    candidates.sort(
        key=lambda path:
            path.stat().st_mtime,
        reverse=True
    )

    return candidates[0]


def get_stem_from_file(
    path,
    suffix
):
    """
    Return the analysis stem while tolerating both the newer
    single-underscore and older double-underscore live-output
    naming conventions.

    Examples:
        www.du.ac.bd_custom_findings.csv
            -> www.du.ac.bd

        www.du.ac.bd__custom_findings.csv
            -> www.du.ac.bd
    """

    if path is None:

        return ""

    name = Path(
        path
    ).name

    suffix_candidates = {
        suffix
    }

    # If the caller supplies a double-underscore suffix, also
    # accept the single-underscore form. If it supplies a
    # single-underscore suffix, also accept the double form.
    if suffix.startswith(
        "__"
    ):

        suffix_candidates.add(
            suffix[1:]
        )

    elif suffix.startswith(
        "_"
    ):

        suffix_candidates.add(
            "_" + suffix
        )

    # Longest first is important: __custom_findings.csv must
    # be stripped before _custom_findings.csv, otherwise an
    # unwanted trailing underscore would remain in the stem.
    for candidate_suffix in sorted(
        suffix_candidates,
        key=len,
        reverse=True
    ):

        if name.endswith(
            candidate_suffix
        ):

            return name[
                :-len(
                    candidate_suffix
                )
            ]

    return Path(
        path
    ).stem


# ============================================================
# EMPTY COMPATIBILITY FILES
#
# These files allow merge_findings.py to continue when only
# one real scanner succeeds.
# ============================================================

CUSTOM_COLUMNS = [
    "page_url",
    "status_code",
    "source",
    "issue_category",
    "element",
    "index",
    "src",
    "alt",
    "selector",
    "html_snippet",
    "element_id",
    "element_classes",
    "issue",
    "severity",
    "reason",
    "tag",
    "text",
    "href",
    "aria_label",
    "title",
    "accessible_name",
    "name_source"
]


AXE_COLUMNS = [
    "page_url",
    "result_type",
    "rule_id",
    "impact",
    "description",
    "help",
    "help_url",
    "wcag_tags",
    "selector",
    "html",
    "failure_summary",
    "node_impact",
    "node_index"
]


def create_empty_csv(
    path,
    columns
):

    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            columns
        )

    return path


def create_empty_custom_csv(
    stem
):

    path = (
        CUSTOM_DIR
        /
        f"{stem}__custom_findings.csv"
    )

    return create_empty_csv(
        path,
        CUSTOM_COLUMNS
    )


def create_empty_axe_csv(
    stem
):

    path = (
        AXE_DIR
        /
        f"{stem}__axe_nodes.csv"
    )

    return create_empty_csv(
        path,
        AXE_COLUMNS
    )


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment():

    missing = []

    required_scripts = [
        CUSTOM_SCRIPT,
        AXE_SCRIPT,
        MERGE_SCRIPT,
        CONTEXT_SCRIPT,
        V3_SCRIPT,
        V2_SCRIPT
    ]

    for script in required_scripts:

        if not script.exists():

            missing.append(
                str(
                    script
                )
            )

    if shutil.which(
        "node"
    ) is None:

        error_message(
            (
                "Node.js was not found.\n\n"
                "Check with:\n"
                "node --version"
            )
        )

        sys.exit(1)

    if missing:

        print()
        print(
            "ERROR: Required project files are missing:"
        )

        for path in missing:

            print(
                " -",
                path
            )

        sys.exit(1)


# ============================================================
# OPTIONAL VLM ENVIRONMENT CHECK
# ============================================================

def check_vlm_environment(
    model=VLM_MODEL
):
    """
    Check whether the optional local Ollama VLM layer is ready.

    VLM is intentionally NON-FATAL.  If any dependency is
    unavailable, the normal deterministic accessibility pipeline
    continues without visual alt-text enrichment.
    """

    if not VLM_SCRIPT.exists():

        return (
            False,
            (
                "VLM analyzer script was not found:\n"
                f"{VLM_SCRIPT}"
            )
        )

    if shutil.which(
        "ollama"
    ) is None:

        return (
            False,
            "Ollama CLI was not found in PATH."
        )

    try:

        service_check = subprocess.run(
            [
                "ollama",
                "list"
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10
        )

    except Exception as error:

        return (
            False,
            (
                "Could not contact the Ollama service: "
                f"{error}"
            )
        )

    if service_check.returncode != 0:

        service_error = (
            service_check.stderr
            or
            service_check.stdout
            or
            "Ollama service check failed."
        ).strip()

        return (
            False,
            service_error
        )

    try:

        model_check = subprocess.run(
            [
                "ollama",
                "show",
                model
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10
        )

    except Exception as error:

        return (
            False,
            (
                "Could not verify the configured VLM model: "
                f"{error}"
            )
        )

    if model_check.returncode != 0:

        return (
            False,
            (
                f"Ollama model {model!r} is not available. "
                f"Install it with: ollama pull {model}"
            )
        )

    # Verify that the current Python environment can import
    # the local Ollama client used by vlm_alt_analyzer.py.
    package_check = subprocess.run(
        [
            sys.executable,
            "-c",
            "import ollama, PIL, pydantic"
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True
    )

    if package_check.returncode != 0:

        package_error = (
            package_check.stderr
            or
            package_check.stdout
            or
            "Required VLM Python packages are unavailable."
        ).strip()

        return (
            False,
            package_error
        )

    return (
        True,
        ""
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # URL ARGUMENT
    # ========================================================

    if len(
        sys.argv
    ) < 2:

        print()

        print(
            "Usage:"
        )

        print()

        print(
            "python final_pipeline/src/"
            "analyze_url.py "
            "https://example.com"
        )

        print()

        sys.exit(1)

    requested_url = normalize_url(
        sys.argv[1]
    )

    if not requested_url:

        error_message(
            "URL is empty."
        )

        sys.exit(1)

    host = get_host(
        requested_url
    )

    predicted_stem = get_output_stem(
        requested_url
    )

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    check_environment()

    # ========================================================
    # CREATE DIRECTORIES
    # ========================================================

    for directory in [
        CUSTOM_DIR,
        AXE_DIR,
        UNIFIED_DIR,
        CONTEXT_DIR,
        V3_DIR,
        VLM_DIR,
        FINAL_RECOMMENDATION_DIR,
        REPORT_DIR
    ]:

        directory.mkdir(
            parents=True,
            exist_ok=True
        )

    # ========================================================
    # HEADER
    # ========================================================

    divider()

    print(
        "AI-ASSISTED WEB ACCESSIBILITY ANALYZER"
    )

    divider()

    print()

    print(
        "Requested URL:"
    )

    print(
        requested_url
    )

    print()

    print(
        "Host:"
    )

    print(
        host
    )

    print()

    print(
        "Output stem:"
    )

    print(
        predicted_stem
    )

    # ========================================================
    # STAGE 1
    # CUSTOM STATIC SCANNER
    # ========================================================

    stage(
        1,
        "CUSTOM STATIC ACCESSIBILITY SCAN"
    )

    expected_custom_csv = (
        CUSTOM_DIR
        /
        (
            predicted_stem
            +
            "_custom_findings.csv"
        )
    )

    expected_custom_meta = (
        CUSTOM_DIR
        /
        (
            predicted_stem
            +
            "_custom_meta.json"
        )
    )

    custom_stage_start = (
        time.time()
    )

    custom_exit_code = run_command(
        [
            sys.executable,
            CUSTOM_SCRIPT,
            requested_url
        ],
        fatal=False
    )

    # ========================================================
    # DISCOVER ACTUAL CUSTOM OUTPUT
    # ========================================================

    custom_csv = find_generated_file(
        CUSTOM_DIR,
        expected_custom_csv,
        "_custom_findings.csv",
        custom_stage_start
    )

    custom_meta = find_generated_file(
        CUSTOM_DIR,
        expected_custom_meta,
        "_custom_meta.json",
        custom_stage_start
    )

    custom_data = read_json_file(
        custom_meta
    )

    custom_status = status_number(
        custom_data.get(
            "status_code"
        )
    )

    custom_analyzable = bool_value(
        custom_data.get(
            "analyzable",
            False
        )
    )

    custom_error = (
        custom_data.get(
            "error"
        )
        or
        ""
    )

    print()

    print(
        "Custom scanner exit code:",
        custom_exit_code
    )

    print(
        "Custom findings file:",
        custom_csv
        if custom_csv
        else
        "NOT FOUND"
    )

    print(
        "Custom metadata file:",
        custom_meta
        if custom_meta
        else
        "NOT FOUND"
    )

    print(
        "Custom HTTP status:",
        custom_status
    )

    print(
        "Custom analyzable:",
        custom_analyzable
    )

    if custom_error:

        print()

        print(
            "Custom scanner message:"
        )

        print(
            custom_error
        )

    # ========================================================
    # INITIAL ACTUAL STEM
    # ========================================================

    if custom_csv:

        actual_stem = get_stem_from_file(
            custom_csv,
            "__custom_findings.csv"
        )

    else:

        actual_stem = (
            predicted_stem
        )

    print()

    print(
        "Actual analysis stem:"
    )

    print(
        actual_stem
    )

    # ========================================================
    # STAGE 2
    # PLAYWRIGHT + AXE-CORE
    # ========================================================

    stage(
        2,
        "PLAYWRIGHT + AXE-CORE RENDERED-DOM SCAN"
    )

    expected_axe_csv = (
        AXE_DIR
        /
        (
            actual_stem
            +
            "__axe_nodes.csv"
        )
    )

    expected_axe_json = (
        AXE_DIR
        /
        (
            actual_stem
            +
            "__axe.json"
        )
    )

    axe_stage_start = (
        time.time()
    )

    axe_exit_code = run_command(
        [
            "node",
            AXE_SCRIPT,
            requested_url
        ],
        fatal=False
    )

    # ========================================================
    # DISCOVER ACTUAL AXE OUTPUT
    # ========================================================

    axe_csv = find_generated_file(
        AXE_DIR,
        expected_axe_csv,
        "__axe_nodes.csv",
        axe_stage_start
    )

    axe_json = find_generated_file(
        AXE_DIR,
        expected_axe_json,
        "__axe.json",
        axe_stage_start
    )

    axe_data = read_json_file(
        axe_json
    )

    # ========================================================
    # RENDERED STATUS
    # ========================================================

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

    navigation_error = (
        axe_data.get(
            "navigation_error"
        )
        or
        ""
    )

    rendered_url = (
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
        or
        requested_url
    )

    rendered_valid = (
        rendered_status is not None
        and
        200 <= rendered_status < 400
        and
        not navigation_error
    )

    print()

    print(
        "axe exit code:",
        axe_exit_code
    )

    print(
        "axe node file:",
        axe_csv
        if axe_csv
        else
        "NOT FOUND"
    )

    print(
        "axe JSON file:",
        axe_json
        if axe_json
        else
        "NOT FOUND"
    )

    print(
        "Rendered URL:",
        rendered_url
    )

    print(
        "Rendered HTTP status:",
        rendered_status
    )

    if navigation_error:

        print()

        print(
            "Navigation error:"
        )

        print(
            navigation_error
        )

    # ========================================================
    # HTTP ERROR TARGET
    # ========================================================

    if (
        rendered_status is not None
        and
        rendered_status >= 400
        and
        not custom_analyzable
    ):

        divider()

        print(
            "TARGET NOT ANALYZABLE"
        )

        divider()

        print()

        print(
            "Requested URL:"
        )

        print(
            requested_url
        )

        print()

        print(
            "Rendered URL:"
        )

        print(
            rendered_url
        )

        print()

        print(
            "Custom HTTP status:",
            custom_status
        )

        print(
            "Rendered HTTP status:",
            rendered_status
        )

        print()

        print(
            "The rendered page returned an HTTP error "
            "response and the static scanner did not "
            "produce an analyzable page."
        )

        print()

        print(
            "Fusion, context extraction, contextual "
            "recommendations, and report generation "
            "were skipped."
        )

        return

    # ========================================================
    # BOTH NAVIGATION METHODS FAILED
    # ========================================================

    if (
        not rendered_valid
        and
        navigation_error
        and
        not custom_analyzable
    ):

        divider()

        print(
            "TARGET UNREACHABLE"
        )

        divider()

        print()

        print(
            "Requested URL:"
        )

        print(
            requested_url
        )

        print()

        print(
            "The static scanner could not obtain an "
            "analyzable response and Playwright could "
            "not successfully navigate to the page."
        )

        print()

        print(
            "Remaining analysis stages were skipped."
        )

        return

    # ========================================================
    # DETERMINE REAL ENGINE AVAILABILITY
    # ========================================================

    real_custom_available = (
        custom_csv is not None
        and
        custom_analyzable
    )

    real_axe_available = (
        axe_csv is not None
        and
        rendered_valid
    )

    # ========================================================
    # PARTIAL ANALYSIS SUPPORT
    # ========================================================

    # --------------------------------------------------------
    # AXE-ONLY MODE
    # --------------------------------------------------------

    if (
        not real_custom_available
        and
        real_axe_available
    ):

        # Use the actual axe output stem.
        #
        # This is important when the requested site redirects:
        #
        # bonikbarta.net
        # -> www.bonikbarta.com
        #
        # bida.gov.bd
        # -> investbangladesh.gov.bd

        actual_stem = get_stem_from_file(
            axe_csv,
            "__axe_nodes.csv"
        )

        warning(
            (
                "The custom static scanner did not produce "
                "an analyzable findings dataset, but axe-core "
                "successfully analyzed the rendered page.\n\n"
                "Continuing in AXE-ONLY mode."
            )
        )

        custom_csv = create_empty_custom_csv(
            actual_stem
        )

        print(
            "Created empty custom compatibility CSV:"
        )

        print(
            custom_csv
        )

    # --------------------------------------------------------
    # CUSTOM-ONLY MODE
    # --------------------------------------------------------

    elif (
        real_custom_available
        and
        not real_axe_available
    ):

        actual_stem = get_stem_from_file(
            custom_csv,
            "__custom_findings.csv"
        )

        warning(
            (
                "The custom static scanner successfully "
                "analyzed the page, but a usable rendered-DOM "
                "axe result was not available.\n\n"
                "Continuing in CUSTOM-ONLY mode."
            )
        )

        if axe_csv is None:

            axe_csv = create_empty_axe_csv(
                actual_stem
            )

            print(
                "Created empty axe compatibility CSV:"
            )

            print(
                axe_csv
            )

    # --------------------------------------------------------
    # BOTH REAL ENGINES SUCCEEDED
    # --------------------------------------------------------

    elif (
        real_custom_available
        and
        real_axe_available
    ):

        actual_stem = get_stem_from_file(
            custom_csv,
            "__custom_findings.csv"
        )

    # --------------------------------------------------------
    # NEITHER ENGINE PRODUCED USABLE ANALYSIS
    # --------------------------------------------------------

    else:

        divider()

        print(
            "ANALYSIS COULD NOT CONTINUE"
        )

        divider()

        print()

        print(
            "Requested URL:"
        )

        print(
            requested_url
        )

        print()

        print(
            "Custom analyzable:"
        )

        print(
            custom_analyzable
        )

        print()

        print(
            "Custom findings file:"
        )

        print(
            custom_csv
            if custom_csv
            else
            "NOT CREATED"
        )

        print()

        print(
            "Rendered HTTP status:"
        )

        print(
            rendered_status
        )

        print()

        print(
            "axe findings file:"
        )

        print(
            axe_csv
            if axe_csv
            else
            "NOT CREATED"
        )

        print()

        print(
            "Neither analysis engine produced a usable "
            "dataset for fusion."
        )

        print()

        # Non-zero exit code so the batch runner records
        # this as failed instead of incomplete.
        sys.exit(2)

    # ========================================================
    # ANALYSIS SOURCE SUMMARY
    # ========================================================

    print()

    print(
        "Analysis sources:"
    )

    print(
        "  Real custom scanner:",
        real_custom_available
    )

    print(
        "  Real axe-core:",
        real_axe_available
    )

    print(
        "  Fusion stem:",
        actual_stem
    )

    # ========================================================
    # STAGE 3
    # ELEMENT-LEVEL FUSION
    # ========================================================

    stage(
        3,
        "ELEMENT-LEVEL FINDING FUSION"
    )

    expected_unified_csv = (
        UNIFIED_DIR
        /
        (
            actual_stem
            +
            "__unified_findings.csv"
        )
    )

    merge_stage_start = (
        time.time()
    )

    merge_exit_code = run_command(
        [
            sys.executable,
            MERGE_SCRIPT,
            custom_csv,
            axe_csv
        ],
        fatal=False
    )

    unified_csv = find_generated_file(
        UNIFIED_DIR,
        expected_unified_csv,
        "__unified_findings.csv",
        merge_stage_start
    )

    if (
        merge_exit_code != 0
        or
        unified_csv is None
    ):

        error_message(
            (
                "Fusion stage could not produce the "
                "unified findings dataset."
            )
        )

        sys.exit(3)

    actual_stem = get_stem_from_file(
        unified_csv,
        "__unified_findings.csv"
    )

    print()

    print(
        "Unified findings:"
    )

    print(
        unified_csv
    )

    # ========================================================
    # STAGE 4
    # CONTEXT EXTRACTION
    # ========================================================

    stage(
        4,
        "CONTEXT EXTRACTION"
    )

    expected_context_csv = (
        CONTEXT_DIR
        /
        (
            actual_stem
            +
            "__context_findings.csv"
        )
    )

    context_stage_start = (
        time.time()
    )

    context_exit_code = run_command(
        [
            sys.executable,
            CONTEXT_SCRIPT,
            unified_csv
        ],
        fatal=False
    )

    context_csv = find_generated_file(
        CONTEXT_DIR,
        expected_context_csv,
        "__context_findings.csv",
        context_stage_start
    )

    context_available = (
        context_exit_code == 0
        and
        context_csv is not None
    )

    if context_available:

        print()

        print(
            "Context dataset:"
        )

        print(
            context_csv
        )

    else:

        context_csv = None

        warning(
            (
                "Context extraction was unavailable "
                "for this page.\n\n"
                "The analyzer will continue with the "
                "standard unified findings."
            )
        )

    # ========================================================
    # STAGE 5
    # CONTEXTUAL RECOMMENDATION ENGINE V3
    # ========================================================

    contextual_available = False
    contextual_csv = None

    stage(
        5,
        "CONTEXT-AWARE RECOMMENDATION ENGINE V3"
    )

    if context_available:

        expected_contextual_csv = (
            V3_DIR
            /
            (
                actual_stem
                +
                "__contextual_recommendations.csv"
            )
        )

        v3_stage_start = (
            time.time()
        )

        v3_exit_code = run_command(
            [
                sys.executable,
                V3_SCRIPT,
                context_csv
            ],
            fatal=False
        )

        contextual_csv = find_generated_file(
            V3_DIR,
            expected_contextual_csv,
            "__contextual_recommendations.csv",
            v3_stage_start
        )

        contextual_available = (
            v3_exit_code == 0
            and
            contextual_csv is not None
        )

        if contextual_available:

            print()

            print(
                "Contextual recommendation dataset:"
            )

            print(
                contextual_csv
            )

        else:

            contextual_csv = None

            warning(
                (
                    "Context-aware Recommendation Engine "
                    "V3 could not complete.\n\n"
                    "The standard recommendation/report "
                    "stage will still continue."
                )
            )

    else:

        print(
            "Skipped because no context dataset "
            "was available."
        )

    # ========================================================
    # CHOOSE BEST INPUT FOR FINAL REPORT
    # ========================================================

    if contextual_available:

        final_input = (
            contextual_csv
        )

        final_input_type = (
            "V3 contextual recommendations"
        )

    elif context_available:

        final_input = (
            context_csv
        )

        final_input_type = (
            "Context-enriched unified findings"
        )

    else:

        final_input = (
            unified_csv
        )

        final_input_type = (
            "Unified findings"
        )

    # ========================================================
    # STAGE 6
    # OPTIONAL VLM IMAGE-ALT ANALYSIS
    # ========================================================

    vlm_available = False
    vlm_review_csv = None
    vlm_summary_csv = None

    stage(
        6,
        "OPTIONAL VLM IMAGE-ALT ANALYSIS"
    )

    # The VLM module is driven by custom image findings.
    # In axe-only mode, the custom CSV is only a compatibility
    # header and contains no real image evidence, so VLM is skipped.
    if not real_custom_available:

        print(
            "Skipped because no real custom-scanner "
            "image findings were available."
        )

    else:

        vlm_environment_ready, vlm_environment_message = (
            check_vlm_environment(
                VLM_MODEL
            )
        )

        if not vlm_environment_ready:

            warning(
                (
                    "Optional VLM image analysis is unavailable.\n\n"
                    f"{vlm_environment_message}\n\n"
                    "Continuing with the deterministic "
                    "recommendation pipeline."
                )
            )

        else:

            expected_vlm_review_csv = (
                VLM_DIR
                /
                (
                    actual_stem
                    +
                    "__custom_findings__vlm_alt_reviews.csv"
                )
            )

            expected_vlm_summary_csv = (
                VLM_DIR
                /
                (
                    actual_stem
                    +
                    "__custom_findings__vlm_alt_summary.csv"
                )
            )

            vlm_stage_start = (
                time.time()
            )

            vlm_exit_code = run_command(
                [
                    sys.executable,
                    VLM_SCRIPT,
                    custom_csv,
                    VLM_MODEL
                ],
                fatal=False
            )

            vlm_review_csv = find_generated_file(
                VLM_DIR,
                expected_vlm_review_csv,
                "__vlm_alt_reviews.csv",
                vlm_stage_start
            )

            vlm_summary_csv = find_generated_file(
                VLM_DIR,
                expected_vlm_summary_csv,
                "__vlm_alt_summary.csv",
                vlm_stage_start
            )

            vlm_available = (
                vlm_exit_code == 0
                and
                vlm_review_csv is not None
            )

            if vlm_available:

                print()

                print(
                    "VLM image-alt review dataset:"
                )

                print(
                    vlm_review_csv
                )

                if vlm_summary_csv:

                    print()

                    print(
                        "VLM image-alt summary:"
                    )

                    print(
                        vlm_summary_csv
                    )

            elif vlm_exit_code == 0:

                print(
                    "No eligible image-alt findings required "
                    "VLM processing for this page."
                )

                vlm_review_csv = None
                vlm_summary_csv = None

            else:

                vlm_review_csv = None
                vlm_summary_csv = None

                warning(
                    (
                        "Optional VLM image analysis could not "
                        "complete.\n\n"
                        "The deterministic recommendation/report "
                        "stage will still continue."
                    )
                )

    # ========================================================
    # STAGE 7
    # FINAL RECOMMENDATION + HTML REPORT
    # ========================================================

    stage(
        7,
        "FINAL RECOMMENDATIONS + INTERACTIVE REPORT"
    )

    print(
        "Final recommendation input:"
    )

    print(
        final_input
    )

    print()

    print(
        "Input type:"
    )

    print(
        final_input_type
    )

    print()

    expected_recommendation_csv = (
        FINAL_RECOMMENDATION_DIR
        /
        (
            actual_stem
            +
            "__recommendations.csv"
        )
    )

    expected_report_html = (
        REPORT_DIR
        /
        (
            actual_stem
            +
            "__accessibility_report.html"
        )
    )

    final_stage_start = (
        time.time()
    )

    final_exit_code = run_command(
        [
            sys.executable,
            V2_SCRIPT,
            final_input
        ],
        fatal=False
    )

    recommendation_csv = find_generated_file(
        FINAL_RECOMMENDATION_DIR,
        expected_recommendation_csv,
        "__recommendations.csv",
        final_stage_start
    )

    report_html = find_generated_file(
        REPORT_DIR,
        expected_report_html,
        "__accessibility_report.html",
        final_stage_start
    )

    if final_exit_code != 0:

        error_message(
            (
                "Final recommendation/report stage failed."
            )
        )

        sys.exit(4)

    if report_html is None:

        error_message(
            (
                "The final HTML report was not created."
            )
        )

        sys.exit(5)

    # ========================================================
    # DETERMINE FINAL ANALYSIS MODE
    # ========================================================

    if (
        real_custom_available
        and
        real_axe_available
    ):

        source_mode = (
            "Custom + axe"
        )

    elif real_axe_available:

        source_mode = (
            "axe-only partial analysis"
        )

    elif real_custom_available:

        source_mode = (
            "custom-only partial analysis"
        )

    else:

        source_mode = (
            "no usable analysis source"
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    divider()

    print(
        "ANALYSIS COMPLETE"
    )

    divider()

    print()

    print(
        "Requested URL:"
    )

    print(
        requested_url
    )

    print()

    print(
        "Rendered URL:"
    )

    print(
        rendered_url
    )

    print()

    print(
        "Analysis stem:"
    )

    print(
        actual_stem
    )

    print()

    print(
        "Analysis mode:"
    )

    if contextual_available:

        analysis_mode_text = (
            source_mode
            +
            " + fusion + context extraction "
            "+ deterministic contextual recommendations"
        )

    elif context_available:

        analysis_mode_text = (
            source_mode
            +
            " + fusion + context extraction"
        )

    else:

        analysis_mode_text = (
            source_mode
            +
            " + fusion"
        )

    if vlm_available:

        analysis_mode_text += (
            " + VLM visual alt analysis"
        )

    print(
        analysis_mode_text
    )

    # ========================================================
    # OUTPUT FILES
    # ========================================================

    print()

    print(
        "Unified findings:"
    )

    print(
        unified_csv
    )

    if context_csv:

        print()

        print(
            "Context findings:"
        )

        print(
            context_csv
        )

    if contextual_csv:

        print()

        print(
            "Contextual recommendations:"
        )

        print(
            contextual_csv
        )

    if vlm_review_csv:

        print()

        print(
            "VLM image-alt reviews:"
        )

        print(
            vlm_review_csv
        )

    if vlm_summary_csv:

        print()

        print(
            "VLM image-alt summary:"
        )

        print(
            vlm_summary_csv
        )

    if recommendation_csv:

        print()

        print(
            "Final recommendations:"
        )

        print(
            recommendation_csv
        )

    print()

    print(
        "Interactive HTML report:"
    )

    print(
        report_html
    )

    # ========================================================
    # FINAL METHODOLOGY NOTE
    # ========================================================

    print()

    print(
        "Reminder:"
    )

    print(
        "Automated findings, context-aware recommendations, "
        "and VLM-generated visual suggestions are "
        "decision-support evidence requiring appropriate human "
        "review. They do not constitute a declaration of "
        "complete WCAG conformance."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
