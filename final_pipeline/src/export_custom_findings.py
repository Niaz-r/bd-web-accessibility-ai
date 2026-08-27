import json
import os
import sys
import pandas as pd

from accessibility_scanner import scan_page


OUTPUT_DIR = (
    "final_pipeline/data/intermediate/"
    "custom_live"
)


OUTPUT_COLUMNS = [
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


def safe_filename(url):

    name = (
        url
        .replace("https://", "")
        .replace("http://", "")
    )

    for char in [
        "/",
        "\\",
        "?",
        "&",
        "=",
        ":",
        "#"
    ]:

        name = name.replace(
            char,
            "_"
        )

    return name[:180]


def main():

    if len(sys.argv) < 2:

        print(
            "Usage: "
            "python final_pipeline/src/"
            "export_custom_findings.py <URL>"
        )

        sys.exit(1)

    url = sys.argv[1]

    result = scan_page(
        url
    )

    rows = []

    status_code = result.get(
        "status_code"
    )

    scan_error = result.get(
        "error",
        ""
    )

    # ========================================================
    # DECIDE WHETHER PAGE IS ANALYZABLE
    # ========================================================

    analyzable = True

    if scan_error:
        analyzable = False

    if (
        status_code is None
        or
        status_code >= 400
    ):
        analyzable = False

    # ========================================================
    # ONLY EXPORT FINDINGS FROM A VALID PAGE
    # ========================================================

    if analyzable:

        categories = [

            (
                "image",
                "image_issues"
            ),

            (
                "heading",
                "heading_issues"
            ),

            (
                "link",
                "link_issues"
            ),

            (
                "form",
                "form_issues"
            )
        ]

        for category, key in categories:

            for issue in result.get(
                key,
                []
            ):

                row = {

                    "page_url":
                        result.get(
                            "url",
                            url
                        ),

                    "status_code":
                        status_code,

                    "source":
                        "custom",

                    "issue_category":
                        category
                }

                row.update(
                    issue
                )

                rows.append(
                    row
                )

    # ========================================================
    # IMPORTANT:
    # ALWAYS WRITE CSV HEADERS EVEN WITH ZERO FINDINGS
    # ========================================================

    df = pd.DataFrame(
        rows,
        columns=OUTPUT_COLUMNS
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    base_name = safe_filename(
        url
    )

    csv_path = os.path.join(
        OUTPUT_DIR,
        (
            base_name
            +
            "_custom_findings.csv"
        )
    )

    metadata_path = os.path.join(
        OUTPUT_DIR,
        (
            base_name
            +
            "_custom_meta.json"
        )
    )

    # ========================================================
    # SAVE CSV
    # ========================================================

    df.to_csv(
        csv_path,
        index=False
    )

    # ========================================================
    # SAVE SCAN METADATA
    # ========================================================

    metadata = {

        "requested_url":
            url,

        "status_code":
            status_code,

        "analyzable":
            analyzable,

        "error":
            scan_error,

        "finding_count":
            len(df)
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # TERMINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("CUSTOM FINDINGS EXPORTED")
    print("=" * 70)

    print(
        "URL:",
        url
    )

    print(
        "Status:",
        status_code
    )

    print(
        "Analyzable:",
        analyzable
    )

    if scan_error:

        print(
            "Scanner error:",
            scan_error
        )

    print(
        "Findings:",
        len(df)
    )

    if not analyzable:

        print()
        print(
            "WARNING:"
        )

        print(
            "The custom scanner did not treat this "
            "response as an analyzable target page."
        )

        print(
            "No accessibility findings were exported "
            "from the error response."
        )

    print()

    if len(df):

        print(
            df[
                [
                    "issue_category",
                    "issue",
                    "severity",
                    "selector"
                ]
            ]
            .head(20)
            .to_string(
                index=False
            )
        )

    else:

        print(
            "No custom findings exported."
        )

    print()

    print(
        "CSV:",
        csv_path
    )

    print(
        "Metadata:",
        metadata_path
    )


if __name__ == "__main__":
    main()
