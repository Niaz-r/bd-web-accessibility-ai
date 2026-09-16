#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

VALID = {"correct", "partially correct", "incorrect"}


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def summarize(df, title):
    labels = df["human_label"].apply(clean).str.lower()
    evaluated = labels.isin(VALID)
    work = df[evaluated].copy()
    labels = work["human_label"].apply(clean).str.lower()

    n = len(work)
    c = int((labels == "correct").sum())
    p = int((labels == "partially correct").sum())
    i = int((labels == "incorrect").sum())

    strict = (c / n * 100) if n else 0.0
    acceptable = ((c + p) / n * 100) if n else 0.0
    weighted = ((c + 0.5 * p) / n * 100) if n else 0.0

    return {
        "group": title,
        "evaluated": n,
        "correct": c,
        "partially_correct": p,
        "incorrect": i,
        "strict_accuracy_pct": round(strict, 2),
        "acceptable_rate_pct": round(acceptable, 2),
        "weighted_quality_pct": round(weighted, 2),
    }


def main():
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python final_pipeline/src/calculate_five_site_validation_metrics.py "
            "<five_site_manual_validation_all.csv>"
        )
        sys.exit(2)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"ERROR: file not found: {path}")
        sys.exit(2)

    df = pd.read_csv(path)

    required = {"validation_type", "human_label", "site_id"}
    missing = required - set(df.columns)
    if missing:
        print("ERROR: missing columns:", ", ".join(sorted(missing)))
        sys.exit(2)

    results = []

    results.append(
        summarize(
            df[df["validation_type"] == "link_recommendation"],
            "Link V4 recommendations",
        )
    )

    results.append(
        summarize(
            df[df["validation_type"] == "link_abstention"],
            "Link V4 abstention decisions",
        )
    )

    results.append(
        summarize(
            df[df["validation_type"] == "vlm_recommendation"],
            "VLM recommendations",
        )
    )

    # Per-site metrics for primary recommendation components.
    for site_id in sorted(df["site_id"].dropna().astype(str).unique()):
        site_df = df[df["site_id"].astype(str) == site_id]

        for validation_type, label in [
            ("link_recommendation", "Link"),
            ("vlm_recommendation", "VLM"),
        ]:
            subset = site_df[site_df["validation_type"] == validation_type]
            if len(subset):
                results.append(
                    summarize(
                        subset,
                        f"{site_id} {label}",
                    )
                )

    result_df = pd.DataFrame(results)

    out_path = path.with_name(
        path.stem + "__metrics.csv"
    )
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("=" * 110)
    print("FIVE-SITE HUMAN VALIDATION RESULTS")
    print("=" * 110)
    print()

    display = result_df[
        [
            "group",
            "evaluated",
            "correct",
            "partially_correct",
            "incorrect",
            "strict_accuracy_pct",
            "acceptable_rate_pct",
            "weighted_quality_pct",
        ]
    ]

    print(display.to_string(index=False))
    print()
    print(f"Metrics CSV: {out_path.resolve()}")
    print()
    print("Interpretation:")
    print("- Strict accuracy = Correct / Evaluated")
    print("- Acceptable rate = (Correct + Partially Correct) / Evaluated")
    print("- Weighted quality = (Correct + 0.5*Partially Correct) / Evaluated")
    print("- Abstention accuracy is reported separately from recommendation accuracy.")


if __name__ == "__main__":
    main()
