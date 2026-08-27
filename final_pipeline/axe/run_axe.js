const { chromium } = require("playwright");
const AxeBuilder = require("@axe-core/playwright").default;
const fs = require("fs");
const path = require("path");


function sanitizeFilename(url) {
    return url
        .replace(/^https?:\/\//, "")
        .replace(/[^a-zA-Z0-9._-]/g, "_")
        .slice(0, 180);
}


function extractWcagTags(tags = []) {
    return tags.filter(tag =>
        tag.startsWith("wcag") ||
        tag.startsWith("EN-") ||
        tag.startsWith("best-practice")
    );
}


function flattenResults(items, resultType, pageUrl) {

    const rows = [];

    for (const rule of items) {

        const wcagTags = extractWcagTags(
            rule.tags || []
        );

        for (let i = 0; i < rule.nodes.length; i++) {

            const node = rule.nodes[i];

            const target = Array.isArray(node.target)
                ? node.target.join(" ")
                : String(node.target || "");

            rows.push({
                page_url: pageUrl,

                result_type: resultType,

                rule_id: rule.id,

                impact: rule.impact || "",

                description: rule.description || "",

                help: rule.help || "",

                help_url: rule.helpUrl || "",

                wcag_tags: wcagTags.join("|"),

                selector: target,

                html: node.html || "",

                failure_summary:
                    node.failureSummary || "",

                node_impact:
                    node.impact || "",

                node_index: i + 1
            });
        }
    }

    return rows;
}


function escapeCsv(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    const text = String(value);

    if (
        text.includes(",") ||
        text.includes("\"") ||
        text.includes("\n") ||
        text.includes("\r")
    ) {
        return `"${text.replace(/"/g, "\"\"")}"`;
    }

    return text;
}


function writeCsv(rows, filePath) {

    const columns = [
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
    ];

    const lines = [];

    // Always write the CSV header.
    lines.push(
        columns.join(",")
    );

    for (const row of rows) {

        lines.push(
            columns
                .map(column =>
                    escapeCsv(
                        row[column]
                    )
                )
                .join(",")
        );
    }

    fs.writeFileSync(
        filePath,
        lines.join("\n"),
        "utf8"
    );
}


async function main() {

    const url = process.argv[2];

    if (!url) {

        console.log();
        console.log(
            "Usage:"
        );

        console.log(
            "node final_pipeline/axe/run_axe.js <URL>"
        );

        console.log();

        process.exit(1);
    }

    const outputDir = path.join(
        __dirname,
        "results"
    );

    fs.mkdirSync(
        outputDir,
        {
            recursive: true
        }
    );

    console.log();
    console.log("=".repeat(80));
    console.log("AXE-CORE RENDERED PAGE SCAN");
    console.log("=".repeat(80));

    console.log(
        "URL:",
        url
    );

    const browser = await chromium.launch({
        headless: true
    });

    const context = await browser.newContext({
        viewport: {
            width: 1440,
            height: 1000
        },

        locale: "en-US"
    });

    const page = await context.newPage();

    let response = null;

    try {

    response = await page.goto(
        url,
        {
            waitUntil:
                "domcontentloaded",

            timeout:
                60000
        }
    );

} catch (error) {

    console.error();
    console.error(
        "Navigation failed:"
    );

    console.error(
        error.message
    );

    // ========================================================
    // SAVE FAILURE OUTPUT
    //
    // Even when navigation fails, create valid output files
    // so the Python pipeline can handle the failure safely.
    // ========================================================

    const safeName = sanitizeFilename(
        url
    );

    const jsonPath = path.join(
        outputDir,
        `${safeName}_axe.json`
    );

    const csvPath = path.join(
        outputDir,
        `${safeName}_axe_nodes.csv`
    );

    const failureJson = {

        page_url:
            url,

        page_title:
            "",

        status_code:
            null,

        timestamp:
            new Date().toISOString(),

        navigation_error:
            error.message,

        summary: {

            violation_rules:
                0,

            violation_nodes:
                0,

            incomplete_rules:
                0,

            incomplete_nodes:
                0,

            passed_rules:
                0,

            inapplicable_rules:
                0
        },

        violations:
            [],

        incomplete:
            [],

        passes:
            []
    };

    fs.writeFileSync(
        jsonPath,
        JSON.stringify(
            failureJson,
            null,
            2
        ),
        "utf8"
    );

    writeCsv(
        [],
        csvPath
    );

    console.log();
    console.log("=".repeat(80));
    console.log("AXE NAVIGATION FAILURE");
    console.log("=".repeat(80));

    console.log(
        "Empty node CSV created:"
    );

    console.log(
        csvPath
    );

    console.log(
        "Failure metadata created:"
    );

    console.log(
        jsonPath
    );

    await browser.close();

    process.exit(2);
}

    const statusCode = response
        ? response.status()
        : null;

    console.log(
        "HTTP status:",
        statusCode
    );

    // Give JS-driven components time to render.
    await page.waitForTimeout(
        2500
    );

    // Optional second wait.
    try {

        await page.waitForLoadState(
            "networkidle",
            {
                timeout: 10000
            }
        );

    } catch (_) {

        console.log(
            "Network remained active; continuing."
        );
    }

    const finalUrl = page.url();

    const title = await page.title();

    console.log(
        "Final URL:",
        finalUrl
    );

    console.log(
        "Page title:",
        title
    );

    // ========================================================
    // AXE ANALYSIS
    // ========================================================

    const results = await new AxeBuilder({
        page
    }).analyze();

    // ========================================================
    // FLATTEN NODE-LEVEL FINDINGS
    // ========================================================

    const violationRows = flattenResults(
        results.violations,
        "violation",
        finalUrl
    );

    const incompleteRows = flattenResults(
        results.incomplete,
        "incomplete",
        finalUrl
    );

    const allRows = [
        ...violationRows,
        ...incompleteRows
    ];

    // ========================================================
    // FILE NAMES
    // ========================================================

    const safeName = sanitizeFilename(
        finalUrl
    );

    const jsonPath = path.join(
        outputDir,
        `${safeName}_axe.json`
    );

    const csvPath = path.join(
        outputDir,
        `${safeName}_axe_nodes.csv`
    );

    // ========================================================
    // SAVE FULL JSON
    // ========================================================

    const outputJson = {

        page_url:
            finalUrl,

        page_title:
            title,

        status_code:
            statusCode,

        timestamp:
            new Date().toISOString(),

        summary: {

            violation_rules:
                results.violations.length,

            violation_nodes:
                violationRows.length,

            incomplete_rules:
                results.incomplete.length,

            incomplete_nodes:
                incompleteRows.length,

            passed_rules:
                results.passes.length,

            inapplicable_rules:
                results.inapplicable.length
        },

        violations:
            results.violations,

        incomplete:
            results.incomplete,

        passes:
            results.passes
    };

    fs.writeFileSync(
        jsonPath,
        JSON.stringify(
            outputJson,
            null,
            2
        ),
        "utf8"
    );

    writeCsv(
        allRows,
        csvPath
    );

    // ========================================================
    // TERMINAL REPORT
    // ========================================================

    console.log();
    console.log("=".repeat(80));
    console.log("AXE SUMMARY");
    console.log("=".repeat(80));

    console.log(
        "Violation rules:",
        results.violations.length
    );

    console.log(
        "Violation nodes:",
        violationRows.length
    );

    console.log(
        "Incomplete rules:",
        results.incomplete.length
    );

    console.log(
        "Incomplete nodes:",
        incompleteRows.length
    );

    console.log(
        "Passed rules:",
        results.passes.length
    );

    console.log();

    console.log(
        "VIOLATIONS"
    );

    console.log("-".repeat(80));

    if (
        results.violations.length === 0
    ) {

        console.log(
            "No axe violations detected."
        );

    } else {

        for (
            const violation
            of results.violations
        ) {

            console.log();

            console.log(
                violation.id,
                "| impact:",
                violation.impact,
                "| nodes:",
                violation.nodes.length
            );

            console.log(
                "  Help:",
                violation.help
            );

            console.log(
                "  Tags:",
                (
                    violation.tags || []
                ).join(", ")
            );

            for (
                const node
                of violation.nodes.slice(
                    0,
                    3
                )
            ) {

                console.log(
                    "  Selector:",
                    Array.isArray(
                        node.target
                    )
                        ? node.target.join(" ")
                        : node.target
                );

                console.log(
                    "  HTML:",
                    (
                        node.html || ""
                    ).replace(
                        /\s+/g,
                        " "
                    ).slice(
                        0,
                        250
                    )
                );
            }
        }
    }

    console.log();
    console.log("=".repeat(80));
    console.log("FILES CREATED");
    console.log("=".repeat(80));

    console.log(
        jsonPath
    );

    console.log(
        csvPath
    );

    await browser.close();
}


main().catch(
    error => {

        console.error(
            error
        );

        process.exit(1);
    }
);
