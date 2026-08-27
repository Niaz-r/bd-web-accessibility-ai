import pandas as pd
import numpy as np
from scipy.stats import kruskal

# ============================================================
# FILES
# ============================================================

INPUT_FILE = "data/website_accessibility_summary.csv"

OUTPUT_DESCRIPTIVE = "data/statistical_descriptive.csv"
OUTPUT_KRUSKAL = "data/kruskal_wallis_results.csv"


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("STATISTICAL ACCESSIBILITY ANALYSIS")
print("=" * 70)

print("\nWebsites:", len(df))

print("\nOrganization types:")
print(df["organization_type"].value_counts().to_string())


# ============================================================
# VARIABLES TO ANALYZE
# ============================================================

variables = [
    "mean_issues_per_page",
    "mean_accessibility_score"
]


# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

descriptive_rows = []

for variable in variables:

    for organization_type, group in df.groupby("organization_type"):

        values = group[variable].dropna()

        descriptive_rows.append({
            "variable": variable,
            "organization_type": organization_type,
            "n": len(values),
            "mean": values.mean(),
            "median": values.median(),
            "std": values.std(ddof=1),
            "min": values.min(),
            "max": values.max(),
            "q1": values.quantile(0.25),
            "q3": values.quantile(0.75),
            "iqr": (
                values.quantile(0.75)
                - values.quantile(0.25)
            )
        })


descriptive = pd.DataFrame(descriptive_rows)

descriptive.to_csv(
    OUTPUT_DESCRIPTIVE,
    index=False
)


print("\n" + "=" * 70)
print("DESCRIPTIVE STATISTICS")
print("=" * 70)

print(
    descriptive.round(4).to_string(index=False)
)


# ============================================================
# KRUSKAL-WALLIS TEST
# ============================================================

kruskal_rows = []

for variable in variables:

    groups = []

    group_names = []

    for organization_type, group in df.groupby("organization_type"):

        values = group[variable].dropna().values

        if len(values) > 0:
            groups.append(values)
            group_names.append(organization_type)

    statistic, p_value = kruskal(*groups)

    n = sum(len(group) for group in groups)
    k = len(groups)

    # --------------------------------------------------------
    # Epsilon-squared effect size
    #
    # epsilon^2 = (H - k + 1) / (n - k)
    # --------------------------------------------------------

    if n > k:
        epsilon_squared = (
            statistic - k + 1
        ) / (
            n - k
        )
    else:
        epsilon_squared = np.nan

    # Sampling can occasionally make the estimator negative.
    if not np.isnan(epsilon_squared):
        epsilon_squared = max(
            0,
            epsilon_squared
        )

    significant = p_value < 0.05

    kruskal_rows.append({
        "variable": variable,
        "groups": k,
        "n": n,
        "H_statistic": statistic,
        "p_value": p_value,
        "epsilon_squared": epsilon_squared,
        "significant_at_0.05": significant
    })


kruskal_results = pd.DataFrame(
    kruskal_rows
)

kruskal_results.to_csv(
    OUTPUT_KRUSKAL,
    index=False
)


print("\n" + "=" * 70)
print("KRUSKAL-WALLIS TEST")
print("=" * 70)

print(
    kruskal_results.round(6).to_string(index=False)
)


# ============================================================
# INTERPRETATION
# ============================================================

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)

for _, row in kruskal_results.iterrows():

    variable = row["variable"]
    p = row["p_value"]
    effect = row["epsilon_squared"]

    print(f"\nVariable: {variable}")
    print(f"H = {row['H_statistic']:.4f}")
    print(f"p = {p:.6f}")
    print(f"Epsilon squared = {effect:.4f}")

    if p < 0.05:

        print(
            "Result: statistically significant difference "
            "among organization types."
        )

    else:

        print(
            "Result: no statistically significant difference "
            "among organization types."
        )


print("\n" + "=" * 70)
print("FILES CREATED")
print("=" * 70)

print(OUTPUT_DESCRIPTIVE)
print(OUTPUT_KRUSKAL)
