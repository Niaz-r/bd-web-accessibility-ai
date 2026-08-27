import pandas as pd
import ast
from pathlib import Path


INPUT_FILE = "data/accessibility_results_final.csv"
OUTPUT_FILE = "data/accessibility_issues_final.csv"


def parse_issues(value):
    """
    Convert the CSV string representation of a Python list
    into an actual list of dictionaries.
    """
    if pd.isna(value):
        return []

    if isinstance(value, list):
        return value

    try:
        parsed = ast.literal_eval(value)

        if isinstance(parsed, list):
            return parsed

    except (ValueError, SyntaxError):
        pass

    return []


def main():

    df = pd.read_csv(INPUT_FILE)

    issue_columns = [
        "image_issues",
        "heading_issues",
        "link_issues",
        "form_issues"
    ]

    rows = []

    for _, page in df.iterrows():

        for column in issue_columns:

            if column not in df.columns:
                continue

            issues = parse_issues(page[column])

            for issue in issues:

                if not isinstance(issue, dict):
                    continue

                rows.append({
                    "website_id": page.get("website_id", ""),
                    "page_id": page.get("page_id", ""),
                    "url": page.get("url", ""),
                    "page_title": page.get("page_title", ""),

                    "issue_category":
                        column.replace("_issues", ""),

                    "element":
                        issue.get("element", ""),

                    "index":
                        issue.get("index", ""),

                    "issue":
                        issue.get("issue", ""),

                    "severity":
                        issue.get("severity", ""),

                    "reason":
                        issue.get("reason", ""),

                    "text":
                        issue.get("text", ""),

                    "href":
                        issue.get("href", ""),

                    "src":
                        issue.get("src", ""),

                    "alt":
                        issue.get("alt", ""),

                    "aria_label":
                        issue.get("aria_label", ""),

                    "title":
                        issue.get("title", ""),

                    "accessible_name":
                        issue.get("accessible_name", ""),

                    "name_source":
                        issue.get("name_source", "")
                })

    columns = [
        "website_id",
        "page_id",
        "url",
        "page_title",
        "issue_category",
        "element",
        "index",
        "issue",
        "severity",
        "reason",
        "text",
        "href",
        "src",
        "alt",
        "aria_label",
        "title",
        "accessible_name",
        "name_source"
    ]

    issues_df = pd.DataFrame(
        rows,
        columns=columns
    )

    Path("data").mkdir(exist_ok=True)

    issues_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 60)
    print("ACCESSIBILITY ISSUE DATASET CREATED")
    print("=" * 60)

    print("Pages processed :", len(df))
    print("Issues extracted:", len(issues_df))
    print("Output          :", OUTPUT_FILE)

    print()

    if len(issues_df) > 0:

        print("Issues by category:")
        print(
            issues_df[
                "issue_category"
            ].value_counts().to_string()
        )

        print()

        print("Issues by severity:")
        print(
            issues_df[
                "severity"
            ].value_counts().to_string()
        )

        print()

        print("Issue types:")
        print(
            issues_df[
                "issue"
            ].value_counts().to_string()
        )


if __name__ == "__main__":
    main()
