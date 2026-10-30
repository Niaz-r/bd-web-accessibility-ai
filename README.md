# AI-Assisted Web Accessibility Analysis and Recommendation System for Bangladeshi Websites

An AI-assisted research project for analyzing web accessibility issues on Bangladeshi websites, interpreting findings in context, and generating actionable recommendations to improve accessibility.

## Overview

Web accessibility helps ensure that people with different abilities can access and use websites effectively. However, identifying accessibility barriers requires more than simply detecting technical violations: understanding the surrounding content and providing useful remediation guidance are also important.

This project develops a modular pipeline that combines automated accessibility testing, website crawling, contextual analysis, AI-assisted interpretation, and recommendation generation.

The research focuses on evaluating Bangladeshi websites and organizing accessibility findings at issue, page, and website levels.

## Key Features

- **Automated Accessibility Scanning:** Uses axe-core to identify potential accessibility violations.
- **Website Crawling:** Collects website pages for systematic accessibility analysis.
- **Context Extraction:** Extracts relevant page context to support better interpretation of accessibility issues.
- **AI-Assisted Analysis:** Includes a vision-language-model (VLM) analysis component.
- **Recommendation Generation:** Produces recommendations based on accessibility findings and contextual information.
- **Link-Level Recommendations:** Includes a dedicated component for analyzing and recommending improvements related to links.
- **Dataset Preparation:** Creates issue-level, page-level, and website-level research datasets.
- **Research Evaluation:** Includes manual-validation preparation, statistical analysis, and evaluation utilities.
- **Report Generation:** Exports accessibility findings and research reports.

## Research Pipeline

The project is organized into several connected stages:

1. **Website Collection and Crawling**  
   Collects target websites and relevant pages for analysis.

2. **Automated Accessibility Testing**  
   Runs accessibility checks using axe-core and collects potential violations.

3. **Contextual Analysis**  
   Extracts page information and contextual details associated with detected issues.

4. **Finding Processing**  
   Merges and organizes accessibility findings for further analysis.

5. **AI-Assisted Interpretation**  
   Uses the VLM analysis component to support the interpretation of accessibility-related content.

6. **Recommendation Generation**  
   Generates issue-related and link-specific recommendations.

7. **Dataset and Report Generation**  
   Exports structured research datasets and accessibility reports.

8. **Evaluation and Statistical Analysis**  
   Provides utilities for manual validation, evaluation metrics, issue-pattern analysis, and statistical testing.

## Project Structure

```text
bd-web-accessibility-ai/
│
├── final_pipeline/
│   │
│   ├── axe/
│   │   ├── run_axe.js
│   │   ├── package.json
│   │   ├── package-lock.json
│   │   └── results/
│   │
│   ├── src/
│   │   ├── analyze_url.py
│   │   ├── accessibility_scanner.py
│   │   ├── crawler.py
│   │   ├── context_extractor.py
│   │   ├── merge_findings.py
│   │   ├── recommendation_engine_v2.py
│   │   ├── recommendation_engine_v3.py
│   │   ├── link_recommendation_engine_v4.py
│   │   ├── vlm_alt_analyzer.py
│   │   ├── generate_accessibility_report.py
│   │   ├── statistical_analysis.py
│   │   └── ...
│   │
│   ├── data/
│   │   ├── intermediate/
│   │   └── final/
│   │
│   └── reports/
│       └── live/
│
├── README.md
└── .gitignore
```

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main research pipeline and data processing |
| JavaScript / Node.js | Accessibility scanning execution |
| axe-core | Automated accessibility testing |
| Playwright | Browser automation support |
| Pandas / NumPy | Research data processing |
| SciPy | Statistical analysis |
| Vision-Language Model (VLM) | AI-assisted accessibility analysis |
| Git / GitHub | Version control and project management |

## Getting Started

### Prerequisites

- Python 3
- Node.js and npm
- Git
- A compatible Python environment with the packages required by the research scripts

### 1. Clone the Repository

```bash
git clone https://github.com/Niaz-r/bd-web-accessibility-ai.git

cd bd-web-accessibility-ai
```

### 2. Set Up the Python Environment

```bash
python3 -m venv .venv

source .venv/bin/activate
```

Install the Python dependencies required by the pipeline scripts.

### 3. Install Node.js Dependencies

```bash
cd final_pipeline/axe

npm ci
```

### 4. Explore the Main Pipeline

The main pipeline controller is:

```text
final_pipeline/src/analyze_url.py
```

Supporting modules for scanning, crawling, contextual analysis, recommendation generation, and evaluation are located in:

```text
final_pipeline/src/
```

Check the script's configuration and accepted arguments before running an analysis.

## Validation

The following commands can be used to check Python and JavaScript syntax:

```bash
python3 -m compileall -q final_pipeline/src

node --check final_pipeline/axe/run_axe.js
```

## Research and Evaluation

The repository includes scripts supporting different stages of the research process, including:

- Issue-level, page-level, and website-level dataset creation.
- Homepage and live research-result exports.
- Accessibility issue-pattern analysis.
- Preparation of data for manual validation.
- Five-site evaluation and validation metrics.
- Statistical tests and analysis.
- Accessibility report generation.

The corresponding scripts are available under `final_pipeline/src/`.

## Limitations

- Automated accessibility tools cannot identify every accessibility barrier.
- Some accessibility issues require human judgment and manual testing.
- AI-generated interpretations and recommendations should be reviewed before implementation.
- Automated scan results should not be treated as formal certification of WCAG compliance.
- Results may vary depending on website structure, page content, and the availability of scanned pages.

## Responsible Use

This project is intended for academic research and accessibility improvement.

Only analyze websites where you have permission to conduct testing. Respect website terms, rate limits, privacy requirements, and applicable data-protection rules. Review collected screenshots, page content, and research datasets before publishing them.

## Project Status

**Academic Research Prototype — MSc Thesis Project**

The repository contains the research pipeline, analysis modules, dataset-generation utilities, recommendation components, and evaluation scripts.

## Author

**Md. Niaz Rahaman**  
GitHub: [@Niaz-r](https://github.com/Niaz-r)

## Acknowledgements

This project builds on open-source accessibility testing and browser automation technologies, particularly axe-core and Playwright.

---

*Research focus: AI-assisted web accessibility analysis and recommendation generation for Bangladeshi websites.*
