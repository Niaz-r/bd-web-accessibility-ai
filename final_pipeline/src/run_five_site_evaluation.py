#!/usr/bin/env python3

import argparse
import csv
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SITES = [
    {"site_id":"EVAL01","name":"Jahangirnagar University","category":"Public University","language":"English/Bangla","url":"https://juniv.edu/"},
    {"site_id":"EVAL02","name":"North South University","category":"Private University","language":"English","url":"https://www.northsouth.edu/"},
    {"site_id":"EVAL03","name":"The Daily Star","category":"News","language":"English","url":"https://www.thedailystar.net/"},
    {"site_id":"EVAL04","name":"Bangla Tribune","category":"News","language":"Bangla","url":"https://www.banglatribune.com/"},
    {"site_id":"EVAL05","name":"Bangladesh Land Portal","category":"Government","language":"Bangla/English","url":"https://land.gov.bd/"},
]

FIELDS = ["site_id","website_name","category","language","requested_url","host","status","return_code","started_at","finished_at","elapsed_seconds","recommendation_csv","html_report","log_file"]


def host_of(url):
    return (urlparse(url).netloc or "").lower().strip().removesuffix(":443")


def stem_variants(host):
    vals = [host, host[4:] if host.startswith("www.") else "www." + host]
    return list(dict.fromkeys(vals))


def find_output(directory, host, suffixes):
    directory = Path(directory)
    if not directory.exists():
        return ""
    stems = stem_variants(host)
    for stem in stems:
        for suffix in suffixes:
            p = directory / f"{stem}{suffix}"
            if p.exists():
                return str(p.resolve())
    candidates = []
    for p in directory.iterdir():
        if not p.is_file():
            continue
        low = p.name.lower()
        if any(s.lower() in low for s in stems) and any(low.endswith(x.lower()) for x in suffixes):
            candidates.append(p)
    if not candidates:
        return ""
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0].resolve())


def write_status(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def read_status(path):
    if not path.exists():
        return {}
    with path.open("r", newline="", encoding="utf-8") as f:
        return {r["site_id"]: r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser(description="Run the finalized accessibility pipeline on five evaluation websites.")
    ap.add_argument("--delay", type=float, default=3.0, help="Seconds between sites (default 3).")
    ap.add_argument("--resume", action="store_true", help="Skip sites already marked complete.")
    ap.add_argument("--site", action="append", default=[], help="Run only EVAL01..EVAL05; may be repeated.")
    args = ap.parse_args()

    root = Path.cwd().resolve()
    analyze = root / "final_pipeline" / "src" / "analyze_url.py"
    if not analyze.exists():
        print(f"ERROR: Could not find {analyze}")
        print("Run this script from ~/bd-web-accessibility-ai")
        sys.exit(2)

    outdir = root / "final_pipeline" / "evaluation" / "five_site_validation"
    logs = outdir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    status_csv = outdir / "five_site_pipeline_status.csv"

    existing = read_status(status_csv) if args.resume else {}
    rows = dict(existing)
    wanted = {x.upper() for x in args.site}
    valid = {s["site_id"] for s in SITES}
    bad = wanted - valid
    if bad:
        print("Unknown site ID(s):", ", ".join(sorted(bad)))
        sys.exit(2)
    selected = [s for s in SITES if not wanted or s["site_id"] in wanted]

    print("=" * 80)
    print("FIVE-SITE FINAL PIPELINE EVALUATION")
    print("=" * 80)
    print(f"Project root: {root}")
    print(f"Python: {sys.executable}")
    print(f"Selected sites: {len(selected)}")

    for n, site in enumerate(selected, 1):
        sid = site["site_id"]
        if args.resume and sid in rows and rows[sid].get("status") == "complete":
            print(f"[{n}/{len(selected)}] {sid} {site['name']}: already complete — skipped")
            continue

        host = host_of(site["url"])
        log_path = logs / f"{sid}_{host}.log"
        print("\n" + "-" * 80)
        print(f"[{n}/{len(selected)}] {sid} — {site['name']}")
        print(f"Category: {site['category']}")
        print(f"Language: {site['language']}")
        print(f"URL: {site['url']}")
        print("-" * 80)

        started = datetime.now()
        t0 = time.time()
        cmd = [sys.executable, str(analyze), site["url"]]
        with log_path.open("w", encoding="utf-8") as log:
            log.write("COMMAND:\n" + " ".join(cmd) + "\n\n")
            p = subprocess.Popen(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            assert p.stdout is not None
            for line in p.stdout:
                print(line, end="")
                log.write(line)
            rc = p.wait()

        finished = datetime.now()
        elapsed = round(time.time() - t0, 2)
        rec = find_output(root / "final_pipeline/data/final/live_recommendations", host, ["__recommendations.csv", "_recommendations.csv"])
        html = find_output(root / "final_pipeline/reports/live", host, ["__accessibility_report.html", "_accessibility_report.html"])
        status = "complete" if rc == 0 and rec and html else ("complete_output_not_located" if rc == 0 else "failed")

        rows[sid] = {
            "site_id": sid,
            "website_name": site["name"],
            "category": site["category"],
            "language": site["language"],
            "requested_url": site["url"],
            "host": host,
            "status": status,
            "return_code": rc,
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "elapsed_seconds": elapsed,
            "recommendation_csv": rec,
            "html_report": html,
            "log_file": str(log_path.resolve()),
        }
        write_status(status_csv, [rows[s["site_id"]] for s in SITES if s["site_id"] in rows])
        print(f"\nSTATUS: {status}")
        print(f"Return code: {rc}")
        if rec: print(f"Recommendations: {rec}")
        if html: print(f"HTML report: {html}")
        print(f"Log: {log_path.resolve()}")

        if n < len(selected) and args.delay > 0:
            time.sleep(args.delay)

    final_rows = [rows[s["site_id"]] for s in SITES if s["site_id"] in rows]
    write_status(status_csv, final_rows)
    complete = sum(r["status"] == "complete" for r in final_rows)
    print("\n" + "=" * 80)
    print("FINAL FIVE-SITE STATUS")
    print("=" * 80)
    for r in final_rows:
        print(f"{r['site_id']} | {r['website_name']} | {r['status']}")
    print(f"\nComplete: {complete}/{len(SITES)}")
    print(f"Status CSV: {status_csv.resolve()}")
    print("\nDo not calculate recommendation accuracy yet. First inspect the five reports.")


if __name__ == "__main__":
    main()
