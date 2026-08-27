import os
import sys
import html
import pandas as pd


# ============================================================
# FILES
# ============================================================

RECOMMENDATION_FILE = (
    "final_pipeline/data/final/"
    "accessibility_recommendations.csv"
)

PAGE_FILE = (
    "final_pipeline/data/final/"
    "page_accessibility_dataset.csv"
)

WEBSITE_FILE = (
    "final_pipeline/data/final/"
    "website_accessibility_dataset.csv"
)

OUTPUT_DIR = (
    "final_pipeline/reports/html"
)


# ============================================================
# WCAG LINKS
# ============================================================

WCAG_LINKS = {

    "1.1.1 Non-text Content":
        "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",

    "2.4.4 Link Purpose (In Context)":
        "https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html",

    "2.4.6 Headings and Labels":
        "https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html",

    "1.3.1 Info and Relationships":
        "https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html",

    "1.3.1 / 2.4.6":
        "https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html"
}


# ============================================================
# HELPERS
# ============================================================

def safe(value):

    if pd.isna(value):
        return ""

    return html.escape(
        str(value)
    )


def code(value):

    if pd.isna(value):
        return ""

    return html.escape(
        str(value)
    )


def score_level(score):

    if pd.isna(score):
        return "Unknown"

    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Good"

    if score >= 50:
        return "Needs Improvement"

    return "Poor"


def wcag_link(wcag_sc):

    url = WCAG_LINKS.get(
        str(wcag_sc),
        ""
    )

    if not url:
        return safe(wcag_sc)

    return (
        f'<a href="{url}" '
        f'target="_blank">'
        f'{safe(wcag_sc)}</a>'
    )


# ============================================================
# CSS
# ============================================================

CSS = """
body {
    font-family: Arial, Helvetica, sans-serif;
    margin: 0;
    background: #f5f7fa;
    color: #202124;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: auto;
    padding: 30px;
}

.header {
    background: white;
    padding: 28px;
    border-radius: 10px;
    margin-bottom: 20px;
}

.header h1 {
    margin-top: 0;
}

.subtitle {
    color: #5f6368;
}

.cards {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(170px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
}

.card-number {
    font-size: 28px;
    font-weight: bold;
}

.card-label {
    color: #5f6368;
    font-size: 14px;
}

.section {
    background: white;
    padding: 25px;
    border-radius: 10px;
    margin-bottom: 20px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    text-align: left;
    background: #f1f3f4;
}

th, td {
    padding: 10px;
    border: 1px solid #ddd;
    vertical-align: top;
}

.issue {
    border-left: 5px solid #777;
}

.high {
    border-left-color: #b3261e;
}

.medium {
    border-left-color: #e37400;
}

.review {
    background: #fff8e1;
    padding: 12px;
    border-radius: 5px;
}

.warning {
    background: #fff4e5;
    padding: 15px;
    border-radius: 6px;
}

.note {
    background: #e8f0fe;
    padding: 15px;
    border-radius: 6px;
}

code, pre {
    font-family: monospace;
}

pre {
    background: #f6f8fa;
    padding: 12px;
    overflow-x: auto;
    border-radius: 5px;
}

.badge {
    display: inline-block;
    padding: 4px 8px;
    margin-right: 5px;
    background: #eee;
    border-radius: 12px;
    font-size: 12px;
}

a {
    color: #065fd4;
}

.evidence {
    margin-top: 15px;
}

.small {
    font-size: 13px;
    color: #5f6368;
}
"""


# ============================================================
# REPORT
# ============================================================

def generate_report(
    website_id,
    page_id=None
):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    recommendations = pd.read_csv(
        RECOMMENDATION_FILE
    )

    pages = pd.read_csv(
        PAGE_FILE
    )

    websites = pd.read_csv(
        WEBSITE_FILE
    )

    # ========================================================
    # FILTER WEBSITE
    # ========================================================

    recommendations = recommendations[
        recommendations[
            "website_id"
        ].astype(str) == str(website_id)
    ].copy()

    pages = pages[
        pages[
            "website_id"
        ].astype(str) == str(website_id)
    ].copy()

    website = websites[
        websites[
            "website_id"
        ].astype(str) == str(website_id)
    ].copy()

    if len(website) == 0:

        print(
            f"ERROR: Website ID not found: "
            f"{website_id}"
        )

        return

    # ========================================================
    # OPTIONAL PAGE FILTER
    # ========================================================

    if page_id:

        recommendations = recommendations[
            recommendations[
                "page_id"
            ].astype(str) == str(page_id)
        ].copy()

        pages = pages[
            pages[
                "page_id"
            ].astype(str) == str(page_id)
        ].copy()

        if len(pages) == 0:

            print(
                f"ERROR: Page ID not found: "
                f"{page_id}"
            )

            return

    meta = website.iloc[0]

    # ========================================================
    # SUMMARY VALUES
    # ========================================================

    if page_id:

        page_row = pages.iloc[0]

        pages_scanned = 1

        total_issues = int(
            page_row[
                "total_issues"
            ]
        )

        high_issues = int(
            page_row[
                "high_issues"
            ]
        )

        medium_issues = int(
            page_row[
                "medium_issues"
            ]
        )

        score = float(
            page_row[
                "accessibility_score"
            ]
        )

        report_title = (
            f"Accessibility Report — "
            f"{page_id}"
        )

    else:

        pages_scanned = len(pages)

        total_issues = int(
            pages[
                "total_issues"
            ].sum()
        )

        high_issues = int(
            pages[
                "high_issues"
            ].sum()
        )

        medium_issues = int(
            pages[
                "medium_issues"
            ].sum()
        )

        score = float(
            pages[
                "accessibility_score"
            ].mean()
        )

        report_title = (
            "Website Accessibility Report"
        )

    pages_with_findings = (
        recommendations[
            "page_id"
        ].nunique()
        if len(recommendations)
        else 0
    )

    level = score_level(
        score
    )

    # ========================================================
    # ISSUE COUNTS
    # ========================================================

    if len(recommendations):

        issue_summary = (
            recommendations
            .groupby(
                [
                    "issue",
                    "severity",
                    "finding_class",
                    "wcag_sc"
                ]
            )
            .size()
            .reset_index(
                name="count"
            )
            .sort_values(
                "count",
                ascending=False
            )
        )

    else:

        issue_summary = pd.DataFrame()

    # ========================================================
    # BUILD HTML
    # ========================================================

    content = []

    content.append(
        "<!DOCTYPE html>"
    )

    content.append(
        "<html lang='en'>"
    )

    content.append(
        "<head>"
    )

    content.append(
        "<meta charset='UTF-8'>"
    )

    content.append(
        "<meta name='viewport' "
        "content='width=device-width, initial-scale=1'>"
    )

    content.append(
        f"<title>{safe(report_title)}</title>"
    )

    content.append(
        f"<style>{CSS}</style>"
    )

    content.append(
        "</head>"
    )

    content.append(
        "<body>"
    )

    content.append(
        "<div class='container'>"
    )

    # ========================================================
    # HEADER
    # ========================================================

    content.append(
        "<div class='header'>"
    )

    content.append(
        f"<h1>{safe(report_title)}</h1>"
    )

    content.append(
        f"<h2>{safe(meta['website_name'])}</h2>"
    )

    content.append(
        "<div class='subtitle'>"
    )

    content.append(
        f"Website ID: {safe(website_id)}"
    )

    content.append(
        "<br>"
    )

    content.append(
        f"Organization: "
        f"{safe(meta['organization_type'])}"
    )

    content.append(
        "<br>"
    )

    content.append(
        f"Website: "
        f"<a href='{safe(meta['url'])}' "
        f"target='_blank'>"
        f"{safe(meta['url'])}</a>"
    )

    if page_id:

        content.append(
            "<br>"
        )

        content.append(
            f"Page ID: {safe(page_id)}"
        )

        content.append(
            "<br>"
        )

        content.append(
            f"Page URL: "
            f"<a href='{safe(pages.iloc[0]['url'])}' "
            f"target='_blank'>"
            f"{safe(pages.iloc[0]['url'])}</a>"
        )

    content.append(
        "</div>"
    )

    content.append(
        "</div>"
    )

    # ========================================================
    # CARDS
    # ========================================================

    content.append(
        "<div class='cards'>"
    )

    card_values = [

        (
            pages_scanned,
            "Pages analyzed"
        ),

        (
            total_issues,
            "Detected findings"
        ),

        (
            high_issues,
            "High severity"
        ),

        (
            medium_issues,
            "Medium severity"
        ),

        (
            pages_with_findings,
            "Pages with findings"
        ),

        (
            f"{score:.1f}",
            "Research-defined score"
        ),

        (
            level,
            "Research-defined level"
        )
    ]

    for value, label in card_values:

        content.append(
            "<div class='card'>"
        )

        content.append(
            f"<div class='card-number'>"
            f"{safe(value)}</div>"
        )

        content.append(
            f"<div class='card-label'>"
            f"{safe(label)}</div>"
        )

        content.append(
            "</div>"
        )

    content.append(
        "</div>"
    )

    # ========================================================
    # IMPORTANT DISCLAIMER
    # ========================================================

    content.append(
        "<div class='section'>"
    )

    content.append(
        "<h2>Interpretation</h2>"
    )

    content.append(
        "<div class='warning'>"
    )

    content.append(
        "<strong>Important:</strong> "
        "This report contains automated accessibility findings "
        "from static HTML analysis. It does not constitute an "
        "official WCAG conformance evaluation. Some findings "
        "require inspection of the rendered page, user interface, "
        "JavaScript-generated content, assistive-technology "
        "behavior, and human judgment."
    )

    content.append(
        "</div>"
    )

    content.append(
        "</div>"
    )

    # ========================================================
    # ISSUE SUMMARY TABLE
    # ========================================================

    content.append(
        "<div class='section'>"
    )

    content.append(
        "<h2>Detected Issue Summary</h2>"
    )

    if len(issue_summary):

        content.append(
            "<table>"
        )

        content.append(
            "<tr>"
            "<th>Issue</th>"
            "<th>Count</th>"
            "<th>Severity</th>"
            "<th>Finding class</th>"
            "<th>WCAG relationship</th>"
            "</tr>"
        )

        for _, row in issue_summary.iterrows():

            content.append(
                "<tr>"
            )

            content.append(
                f"<td>{safe(row['issue'])}</td>"
            )

            content.append(
                f"<td>{safe(row['count'])}</td>"
            )

            content.append(
                f"<td>{safe(row['severity'])}</td>"
            )

            content.append(
                f"<td>{safe(row['finding_class'])}</td>"
            )

            content.append(
                f"<td>{wcag_link(row['wcag_sc'])}</td>"
            )

            content.append(
                "</tr>"
            )

        content.append(
            "</table>"
        )

    else:

        content.append(
            "<p>No findings were recorded for this selection.</p>"
        )

    content.append(
        "</div>"
    )

    # ========================================================
    # DETAILED RECOMMENDATIONS
    # ========================================================

    content.append(
        "<div class='section'>"
    )

    content.append(
        "<h2>Recommendations</h2>"
    )

    if len(recommendations):

        issue_order = (
            recommendations[
                "issue"
            ]
            .value_counts()
            .index
        )

        for issue in issue_order:

            issue_rows = recommendations[
                recommendations[
                    "issue"
                ] == issue
            ].copy()

            first = issue_rows.iloc[0]

            severity_class = (
                str(
                    first[
                        "severity"
                    ]
                )
                .strip()
                .lower()
            )

            content.append(
                f"<div class='section issue "
                f"{safe(severity_class)}'>"
            )

            content.append(
                f"<h3>{safe(issue)}</h3>"
            )

            content.append(
                f"<span class='badge'>"
                f"{len(issue_rows)} occurrence(s)"
                f"</span>"
            )

            content.append(
                f"<span class='badge'>"
                f"Severity: "
                f"{safe(first['severity'])}"
                f"</span>"
            )

            content.append(
                f"<span class='badge'>"
                f"{safe(first['finding_class'])}"
                f"</span>"
            )

            content.append(
                f"<span class='badge'>"
                f"Confidence: "
                f"{safe(first['confidence'])}"
                f"</span>"
            )

            content.append(
                "<h4>WCAG relationship</h4>"
            )

            content.append(
                f"<p>{wcag_link(first['wcag_sc'])} "
                f"— Level {safe(first['wcag_level'])}</p>"
            )

            content.append(
                "<h4>Why this matters</h4>"
            )

            content.append(
                f"<p>{safe(first['why_it_matters'])}</p>"
            )

            content.append(
                "<h4>Recommendation</h4>"
            )

            content.append(
                f"<p>{safe(first['recommendation'])}</p>"
            )

            content.append(
                "<div class='review'>"
            )

            content.append(
                "<strong>Manual review:</strong> "
                f"{safe(first['manual_review_required'])}"
                "<br>"
                f"{safe(first['review_reason'])}"
            )

            content.append(
                "</div>"
            )

            content.append(
                "<h4>Example</h4>"
            )

            content.append(
                "<strong>Before</strong>"
            )

            content.append(
                f"<pre>{code(first['example_before'])}</pre>"
            )

            content.append(
                "<strong>After</strong>"
            )

            content.append(
                f"<pre>{code(first['example_after'])}</pre>"
            )

            if safe(
                first[
                    "alternative_fix"
                ]
            ):

                content.append(
                    "<strong>Alternative/context-dependent fix</strong>"
                )

                content.append(
                    f"<pre>{code(first['alternative_fix'])}</pre>"
                )

            # =================================================
            # EVIDENCE
            # =================================================

            content.append(
                "<div class='evidence'>"
            )

            content.append(
                "<h4>Sample detected occurrences</h4>"
            )

            content.append(
                "<table>"
            )

            content.append(
                "<tr>"
                "<th>Page</th>"
                "<th>Evidence</th>"
                "<th>Context</th>"
                "</tr>"
            )

            # Limit evidence to 10 examples per issue
            for _, evidence in issue_rows.head(
                10
            ).iterrows():

                evidence_parts = []

                for column, label in [

                    (
                        "text",
                        "Text"
                    ),

                    (
                        "href",
                        "Href"
                    ),

                    (
                        "src",
                        "Image"
                    ),

                    (
                        "alt",
                        "Alt"
                    ),

                    (
                        "accessible_name",
                        "Accessible name"
                    )
                ]:

                    if (
                        column
                        in evidence.index
                        and not pd.isna(
                            evidence[
                                column
                            ]
                        )
                        and str(
                            evidence[
                                column
                            ]
                        ).strip()
                    ):

                        evidence_parts.append(
                            f"<strong>{label}:</strong> "
                            f"{safe(evidence[column])}"
                        )

                content.append(
                    "<tr>"
                )

                content.append(
                    "<td>"
                    f"{safe(evidence['page_id'])}"
                    "<br>"
                    f"<a href='{safe(evidence['url'])}' "
                    f"target='_blank'>Open page</a>"
                    "</td>"
                )

                content.append(
                    "<td>"
                    + "<br>".join(
                        evidence_parts
                    )
                    + "</td>"
                )

                content.append(
                    f"<td>{safe(evidence['context_note'])}</td>"
                )

                content.append(
                    "</tr>"
                )

            content.append(
                "</table>"
            )

            if len(issue_rows) > 10:

                content.append(
                    f"<p class='small'>Showing 10 of "
                    f"{len(issue_rows)} occurrences.</p>"
                )

            content.append(
                "</div>"
            )

            content.append(
                "</div>"
            )

    content.append(
        "</div>"
    )

    # ========================================================
    # METHODOLOGY
    # ========================================================

    content.append(
        "<div class='section'>"
    )

    content.append(
        "<h2>Methodology and Limitations</h2>"
    )

    content.append(
        "<ul>"
    )

    content.append(
        "<li>"
        "The scanner analyzes static HTML obtained by the research crawler."
        "</li>"
    )

    content.append(
        "<li>"
        "JavaScript-generated content may not be represented."
        "</li>"
    )

    content.append(
        "<li>"
        "Automated findings are accessibility indicators, "
        "not complete WCAG conformance decisions."
        "</li>"
    )

    content.append(
        "<li>"
        "Empty alternative text may be correct for decorative images."
        "</li>"
    )

    content.append(
        "<li>"
        "Generic link text must be interpreted together with "
        "programmatically determined context."
        "</li>"
    )

    content.append(
        "<li>"
        "Heading hierarchy findings require examination of "
        "the complete page structure."
        "</li>"
    )

    content.append(
        "<li>"
        "The accessibility score shown in this report is a "
        "research-defined heuristic, not an official WCAG score."
        "</li>"
    )

    content.append(
        "</ul>"
    )

    content.append(
        "</div>"
    )

    # ========================================================
    # CLOSE
    # ========================================================

    content.append(
        "</div>"
    )

    content.append(
        "</body>"
    )

    content.append(
        "</html>"
    )

    # ========================================================
    # OUTPUT PATH
    # ========================================================

    if page_id:

        output_name = (
            f"{website_id}_{page_id}_"
            "accessibility_report.html"
        )

    else:

        output_name = (
            f"{website_id}_"
            "accessibility_report.html"
        )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_name
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(
                content
            )
        )

    print()
    print("=" * 80)
    print("ACCESSIBILITY REPORT GENERATED")
    print("=" * 80)

    print(
        "Website:",
        meta["website_name"]
    )

    print(
        "Website ID:",
        website_id
    )

    if page_id:

        print(
            "Page ID:",
            page_id
        )

    print(
        "Pages analyzed:",
        pages_scanned
    )

    print(
        "Detected findings:",
        total_issues
    )

    print(
        "High:",
        high_issues
    )

    print(
        "Medium:",
        medium_issues
    )

    print(
        "Research-defined score:",
        round(
            score,
            2
        )
    )

    print(
        "Level:",
        level
    )

    print()
    print(
        "Report:",
        output_path
    )


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )

        print(
            "Website report:"
        )

        print(
            "python final_pipeline/src/"
            "generate_accessibility_report.py "
            "BD001"
        )

        print()

        print(
            "Single-page report:"
        )

        print(
            "python final_pipeline/src/"
            "generate_accessibility_report.py "
            "BD001 PG0001_BD001"
        )

        sys.exit()

    website_id = (
        sys.argv[1]
    )

    page_id = (
        sys.argv[2]
        if len(sys.argv) >= 3
        else None
    )

    generate_report(
        website_id,
        page_id
    )
