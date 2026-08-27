import os
import pandas as pd


# ============================================================
# FILES
# ============================================================

INPUT_FILE = (
    "final_pipeline/data/intermediate/"
    "accessibility_issues_clean.csv"
)

OUTPUT_FILE = (
    "final_pipeline/data/final/"
    "accessibility_recommendations.csv"
)

SUMMARY_FILE = (
    "final_pipeline/reports/"
    "recommendation_summary.csv"
)

PAGE_SUMMARY_FILE = (
    "final_pipeline/reports/"
    "page_recommendation_summary.csv"
)


# ============================================================
# RECOMMENDATION KNOWLEDGE BASE
#
# IMPORTANT:
# These mappings do NOT claim that every scanner finding is a
# confirmed WCAG violation.
#
# Some findings require contextual/manual review.
# ============================================================

RECOMMENDATIONS = {

    # ========================================================
    # IMAGE ACCESSIBILITY
    # ========================================================

    "missing_alt": {

        "finding_class":
            "Likely accessibility failure",

        "confidence":
            "High",

        "wcag_sc":
            "1.1.1 Non-text Content",

        "wcag_level":
            "A",

        "wcag_relationship":
            "Directly related",

        "why_it_matters":
            (
                "Images without an appropriate text alternative "
                "may not communicate their purpose or information "
                "to users of screen readers and other assistive "
                "technologies."
            ),

        "recommendation":
            (
                "Determine whether the image is informative, "
                "functional, or decorative. Informative images "
                "should receive concise alternative text that "
                "communicates their purpose. Decorative images "
                "should normally use an empty alt attribute so "
                "assistive technology can ignore them."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "The scanner cannot reliably determine the purpose "
                "of the image from static HTML alone. Also verify "
                "whether another supported accessible-name mechanism "
                "already provides an equivalent alternative."
            ),

        "example_before":
            '<img src="campus.jpg">',

        "example_after":
            '<img src="campus.jpg" alt="Students entering the university library">',

        "alternative_fix":
            '<img src="decoration.png" alt="">',

        "reference_note":
            (
                "WCAG 2.2 SC 1.1.1; W3C HTML Technique H37 "
                "and Failure F65."
            )
    },


    "empty_alt": {

        "finding_class":
            "Manual review",

        "confidence":
            "Context dependent",

        "wcag_sc":
            "1.1.1 Non-text Content",

        "wcag_level":
            "A",

        "wcag_relationship":
            "Context dependent",

        "why_it_matters":
            (
                "An empty alt attribute is correct for a decorative "
                "image, but it is inappropriate when the image "
                "communicates meaningful information or performs "
                "a function."
            ),

        "recommendation":
            (
                "Review the purpose of the image. If the image is "
                "decorative, keep alt=\"\". If it communicates "
                "information, replace the empty alternative with "
                "concise text that conveys the same purpose."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "Empty alt text cannot be classified as a violation "
                "without knowing whether the image is decorative, "
                "informative, or functional."
            ),

        "example_before":
            '<img src="admission-chart.png" alt="">',

        "example_after":
            '<img src="admission-chart.png" alt="Undergraduate admission application timeline">',

        "alternative_fix":
            (
                'If the image is purely decorative, '
                'keep: <img src="decoration.png" alt="">'
            ),

        "reference_note":
            "WCAG 2.2 SC 1.1.1 Non-text Content."
    },


    # ========================================================
    # LINK ACCESSIBILITY
    # ========================================================

    "empty_link_text": {

        "finding_class":
            "Likely accessibility failure",

        "confidence":
            "High",

        "wcag_sc":
            "2.4.4 Link Purpose (In Context)",

        "wcag_level":
            "A",

        "wcag_relationship":
            "Directly related",

        "why_it_matters":
            (
                "A link without a meaningful accessible name may "
                "give screen-reader users little or no information "
                "about the link's purpose or destination."
            ),

        "recommendation":
            (
                "Provide a meaningful accessible name for the link. "
                "Prefer descriptive visible link text. When visible "
                "text is not appropriate, use a supported accessible "
                "naming mechanism and verify it with assistive "
                "technology."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "Verify the computed accessible name in the rendered "
                "page because JavaScript, ARIA, or nested content may "
                "affect the final accessible name."
            ),

        "example_before":
            '<a href="/admission"></a>',

        "example_after":
            '<a href="/admission">Undergraduate admission information</a>',

        "alternative_fix":
            (
                'For an icon-only link, provide an appropriate '
                'accessible name and test the rendered result.'
            ),

        "reference_note":
            "WCAG 2.2 SC 2.4.4 Link Purpose (In Context)."
    },


    "generic_link_text": {

        "finding_class":
            "Context review",

        "confidence":
            "Medium",

        "wcag_sc":
            "2.4.4 Link Purpose (In Context)",

        "wcag_level":
            "A",

        "wcag_relationship":
            "Context dependent",

        "why_it_matters":
            (
                "Generic text such as 'Read More', 'Click Here', "
                "or 'Learn More' may be difficult to understand "
                "when links are encountered outside their visual "
                "context."
            ),

        "recommendation":
            (
                "Prefer link text that communicates the purpose or "
                "destination. If short generic text is retained, "
                "verify that its purpose can be determined from "
                "programmatically associated context."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "WCAG allows link purpose to be determined from "
                "the link text together with programmatically "
                "determined context. Therefore generic wording "
                "alone is not sufficient evidence of failure."
            ),

        "example_before":
            '<a href="/admission">Read More</a>',

        "example_after":
            '<a href="/admission">Read more about undergraduate admission</a>',

        "alternative_fix":
            (
                "Retain concise wording only when sufficient "
                "programmatically determined context clearly "
                "identifies the link purpose."
            ),

        "reference_note":
            (
                "WCAG 2.2 SC 2.4.4; W3C Techniques G91, "
                "G53 and H78."
            )
    },


    # ========================================================
    # HEADING ACCESSIBILITY
    # ========================================================

    "missing_h1": {

        "finding_class":
            "Structural best-practice review",

        "confidence":
            "Advisory",

        "wcag_sc":
            "1.3.1 / 2.4.6",

        "wcag_level":
            "A / AA",

        "wcag_relationship":
            "Related guidance; not an automatic failure",

        "why_it_matters":
            (
                "A clear page-level heading can help users understand "
                "the topic of the page and navigate its structure, "
                "particularly when using assistive technology."
            ),

        "recommendation":
            (
                "Review the page structure and provide a meaningful "
                "top-level heading when appropriate. The heading "
                "should describe the page's primary content or purpose."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "WCAG does not simply require exactly one h1 on every "
                "page. The complete heading structure and content "
                "organization must be evaluated."
            ),

        "example_before":
            '<main><p>Admission information...</p></main>',

        "example_after":
            '<main><h1>Undergraduate Admission</h1><p>Admission information...</p></main>',

        "alternative_fix":
            (
                "Use heading levels according to the logical document "
                "structure rather than visual size alone."
            ),

        "reference_note":
            (
                "Related to WCAG 2.2 SC 1.3.1 and SC 2.4.6 "
                "and W3C page-structure guidance."
            )
    },


    "multiple_h1": {

        "finding_class":
            "Structural best-practice review",

        "confidence":
            "Advisory",

        "wcag_sc":
            "1.3.1 / 2.4.6",

        "wcag_level":
            "A / AA",

        "wcag_relationship":
            "Related guidance; not an automatic failure",

        "why_it_matters":
            (
                "Multiple top-level headings may make the document "
                "hierarchy harder to understand when they do not "
                "reflect the logical structure of the content."
            ),

        "recommendation":
            (
                "Review the heading hierarchy. Keep heading levels "
                "consistent with the logical organization of the page. "
                "Do not change headings solely to satisfy a numerical "
                "one-h1 rule."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "The presence of multiple h1 elements alone does not "
                "prove WCAG non-conformance. Their semantic role and "
                "document structure must be reviewed."
            ),

        "example_before":
            '<h1>University</h1><h1>Admission</h1>',

        "example_after":
            '<h1>University Admission</h1><h2>Application Requirements</h2>',

        "alternative_fix":
            (
                "If multiple top-level headings correctly represent "
                "the document structure, do not alter them merely "
                "because the scanner counted more than one h1."
            ),

        "reference_note":
            (
                "Related to WCAG 2.2 SC 1.3.1, SC 2.4.6 "
                "and W3C heading-structure guidance."
            )
    },


    "empty_heading": {

        "finding_class":
            "Potential accessibility failure",

        "confidence":
            "Medium",

        "wcag_sc":
            "2.4.6 Headings and Labels",

        "wcag_level":
            "AA",

        "wcag_relationship":
            "Directly related",

        "why_it_matters":
            (
                "An empty heading can create an unhelpful navigation "
                "stop for users who navigate pages by headings and "
                "does not describe a topic or purpose."
            ),

        "recommendation":
            (
                "Remove the heading element if no heading is required, "
                "or provide concise meaningful heading text describing "
                "the associated section."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "Confirm the rendered heading content and whether "
                "CSS, JavaScript, or assistive naming affects what "
                "users actually encounter."
            ),

        "example_before":
            '<h2></h2>',

        "example_after":
            '<h2>Admission Requirements</h2>',

        "alternative_fix":
            (
                "Remove the empty heading if it has no semantic "
                "purpose."
            ),

        "reference_note":
            "Related to WCAG 2.2 SC 2.4.6 Headings and Labels."
    },


    "heading_order": {

        "finding_class":
            "Structural review",

        "confidence":
            "Advisory",

        "wcag_sc":
            "1.3.1 Info and Relationships",

        "wcag_level":
            "A",

        "wcag_relationship":
            "Related/advisory",

        "why_it_matters":
            (
                "Unexpected heading-level jumps can make the "
                "relationship between page sections harder to "
                "understand for users navigating by headings."
            ),

        "recommendation":
            (
                "Review the logical hierarchy of the page. Nest "
                "headings according to section relationships and "
                "avoid skipping levels when the skipped level would "
                "represent a missing structural relationship."
            ),

        "manual_review_required":
            "Yes",

        "review_reason":
            (
                "A numerical heading-level jump is not always a WCAG "
                "failure. For example, moving back from an h4 to an h2 "
                "can correctly close subsections. Human review of the "
                "document outline is required."
            ),

        "example_before":
            '<h2>Programs</h2><h4>Computer Science</h4>',

        "example_after":
            '<h2>Programs</h2><h3>Computer Science</h3>',

        "alternative_fix":
            (
                "Choose heading levels according to semantic "
                "hierarchy, not visual appearance."
            ),

        "reference_note":
            (
                "Related to WCAG 2.2 SC 1.3.1 and W3C "
                "Technique G141/page-structure guidance."
            )
    }
}


# ============================================================
# SAFE STRING
# ============================================================

def safe_text(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


# ============================================================
# CONTEXT NOTE
# ============================================================

def create_context_note(row):

    issue = safe_text(
        row.get("issue")
    ).lower()

    text = safe_text(
        row.get("text")
    )

    href = safe_text(
        row.get("href")
    )

    src = safe_text(
        row.get("src")
    )

    alt = safe_text(
        row.get("alt")
    )

    accessible_name = safe_text(
        row.get("accessible_name")
    )

    notes = []

    if issue in {
        "empty_link_text",
        "generic_link_text"
    }:

        if text:
            notes.append(
                f"Detected link text: {text}"
            )

        if href:
            notes.append(
                f"Destination: {href}"
            )

        if accessible_name:
            notes.append(
                f"Recorded accessible name: {accessible_name}"
            )

    if issue in {
        "missing_alt",
        "empty_alt"
    }:

        if src:
            notes.append(
                f"Image source: {src}"
            )

        if alt:
            notes.append(
                f"Recorded alt text: {alt}"
            )

    if not notes:

        return (
            "Review the affected element in the "
            "rendered page context."
        )

    return " | ".join(notes)


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )

    os.makedirs(
        os.path.dirname(
            SUMMARY_FILE
        ),
        exist_ok=True
    )

    issues = pd.read_csv(
        INPUT_FILE
    )

    print()
    print("=" * 80)
    print("ACCESSIBILITY RECOMMENDATION ENGINE")
    print("=" * 80)

    print(
        "Input issues:",
        len(issues)
    )

    print(
        "Websites:",
        issues["website_id"].nunique()
    )

    print(
        "Pages with issues:",
        issues["page_id"].nunique()
    )

    # ========================================================
    # NORMALIZE ISSUE NAME
    # ========================================================

    issues["issue"] = (
        issues["issue"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    unknown_issues = sorted(
        set(
            issues["issue"].unique()
        )
        -
        set(
            RECOMMENDATIONS.keys()
        )
    )

    if unknown_issues:

        print()
        print(
            "WARNING - unknown issue types:"
        )

        for issue in unknown_issues:
            print(
                f"  - {issue}"
            )

    # ========================================================
    # APPLY RECOMMENDATIONS
    # ========================================================

    output_rows = []

    for index, row in issues.iterrows():

        issue = row["issue"]

        knowledge = (
            RECOMMENDATIONS.get(
                issue
            )
        )

        if knowledge is None:
            continue

        output = row.to_dict()

        output[
            "recommendation_id"
        ] = (
            f"REC-{index + 1:06d}"
        )

        output[
            "finding_class"
        ] = knowledge[
            "finding_class"
        ]

        output[
            "confidence"
        ] = knowledge[
            "confidence"
        ]

        output[
            "wcag_sc"
        ] = knowledge[
            "wcag_sc"
        ]

        output[
            "wcag_level"
        ] = knowledge[
            "wcag_level"
        ]

        output[
            "wcag_relationship"
        ] = knowledge[
            "wcag_relationship"
        ]

        output[
            "why_it_matters"
        ] = knowledge[
            "why_it_matters"
        ]

        output[
            "recommendation"
        ] = knowledge[
            "recommendation"
        ]

        output[
            "manual_review_required"
        ] = knowledge[
            "manual_review_required"
        ]

        output[
            "review_reason"
        ] = knowledge[
            "review_reason"
        ]

        output[
            "example_before"
        ] = knowledge[
            "example_before"
        ]

        output[
            "example_after"
        ] = knowledge[
            "example_after"
        ]

        output[
            "alternative_fix"
        ] = knowledge[
            "alternative_fix"
        ]

        output[
            "reference_note"
        ] = knowledge[
            "reference_note"
        ]

        output[
            "context_note"
        ] = create_context_note(
            row
        )

        output_rows.append(
            output
        )

    recommendations = pd.DataFrame(
        output_rows
    )

    # ========================================================
    # COLUMN ORDER
    # ========================================================

    preferred_columns = [

        "recommendation_id",

        "website_id",
        "page_id",
        "url",
        "page_title",

        "issue_category",
        "issue",
        "severity",

        "element",
        "index",

        "text",
        "href",
        "src",
        "alt",
        "aria_label",
        "title",
        "accessible_name",
        "name_source",

        "finding_class",
        "confidence",

        "wcag_sc",
        "wcag_level",
        "wcag_relationship",

        "why_it_matters",
        "recommendation",

        "manual_review_required",
        "review_reason",

        "example_before",
        "example_after",
        "alternative_fix",

        "context_note",

        "reference_note"
    ]

    available_columns = [
        column
        for column
        in preferred_columns
        if column
        in recommendations.columns
    ]

    recommendations = (
        recommendations[
            available_columns
        ]
    )

    # ========================================================
    # SAVE FULL RECOMMENDATION DATASET
    # ========================================================

    recommendations.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # ISSUE-TYPE SUMMARY
    # ========================================================

    summary = (
        recommendations
        .groupby(
            [
                "issue_category",
                "issue",
                "severity",
                "finding_class",
                "confidence",
                "wcag_sc",
                "wcag_level",
                "manual_review_required"
            ],
            dropna=False
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

    summary[
        "percentage"
    ] = (
        summary["count"]
        / len(recommendations)
        * 100
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False
    )

    # ========================================================
    # PAGE-LEVEL RECOMMENDATION SUMMARY
    # ========================================================

    page_summary = (
        recommendations
        .groupby(
            [
                "website_id",
                "page_id",
                "url"
            ]
        )
        .agg(

            total_findings=(
                "recommendation_id",
                "count"
            ),

            high_findings=(
                "severity",
                lambda x:
                (
                    x.astype(str)
                    .str.lower()
                    .eq("high")
                    .sum()
                )
            ),

            medium_findings=(
                "severity",
                lambda x:
                (
                    x.astype(str)
                    .str.lower()
                    .eq("medium")
                    .sum()
                )
            ),

            manual_review_findings=(
                "manual_review_required",
                lambda x:
                (
                    x.astype(str)
                    .str.lower()
                    .eq("yes")
                    .sum()
                )
            )
        )
        .reset_index()
    )

    page_summary.to_csv(
        PAGE_SUMMARY_FILE,
        index=False
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print()
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)

    print(
        "Input issue rows:",
        len(issues)
    )

    print(
        "Recommendation rows:",
        len(recommendations)
    )

    print(
        "Unmapped rows:",
        len(issues)
        - len(recommendations)
    )

    print()

    print(
        "Recommendation counts by issue:"
    )

    print(
        recommendations[
            "issue"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "Finding classes:"
    )

    print(
        recommendations[
            "finding_class"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "WCAG mappings:"
    )

    print(
        recommendations[
            "wcag_sc"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "Manual review:"
    )

    print(
        recommendations[
            "manual_review_required"
        ]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # SAMPLE OUTPUT
    # ========================================================

    print()
    print("=" * 80)
    print("SAMPLE RECOMMENDATIONS")
    print("=" * 80)

    sample_columns = [
        "website_id",
        "page_id",
        "issue",
        "severity",
        "finding_class",
        "wcag_sc",
        "recommendation"
    ]

    print(
        recommendations[
            sample_columns
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print()
    print("=" * 80)
    print("FILES CREATED")
    print("=" * 80)

    print(
        OUTPUT_FILE
    )

    print(
        SUMMARY_FILE
    )

    print(
        PAGE_SUMMARY_FILE
    )


if __name__ == "__main__":
    main()
