"""Print a concise data-quality report. Does not modify the dataset."""

from __future__ import annotations

import pandas as pd

from src.data.load import load_cleaned_dataset
from src.utils.config import CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET_COLUMN


def print_data_quality_report(df: pd.DataFrame) -> None:
    print("=" * 60)
    print("RETENSA data quality report")
    print("=" * 60)

    print("\n[Shape]")
    print(f"rows={df.shape[0]}  columns={df.shape[1]}")

    print("\n[Column names]")
    print(list(df.columns))

    print("\n[Data types]")
    print(df.dtypes.to_string())

    print("\n[Missing values]")
    missing = df.isna().sum()
    print(missing.to_string())
    print(f"total_missing={int(missing.sum())}")

    print("\n[Duplicate rows]")
    print(f"duplicate_rows={int(df.duplicated().sum())}")

    print("\n[Target distribution]")
    if TARGET_COLUMN not in df.columns:
        print(f"{TARGET_COLUMN} column not found.")
    else:
        counts = df[TARGET_COLUMN].value_counts(dropna=False)
        percents = df[TARGET_COLUMN].value_counts(normalize=True, dropna=False) * 100
        for label in counts.index:
            print(f"{label}: {counts[label]} ({percents[label]:.2f}%)")

    print("\n[Unique values — categorical columns]")
    categorical_cols = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    extra_object_cols = [
        c
        for c in df.select_dtypes(include=["object", "category"]).columns
        if c not in categorical_cols and c != TARGET_COLUMN
    ]
    for col in categorical_cols + extra_object_cols:
        values = df[col].dropna().unique().tolist()
        print(f"{col} ({df[col].nunique(dropna=False)} unique): {values}")

    print("\n[Numeric statistics]")
    numeric_cols = [c for c in NUMERIC_FEATURES if c in df.columns]
    if numeric_cols:
        print(df[numeric_cols].describe().transpose().to_string())
    else:
        print("No expected numeric columns found.")

    print("\n" + "=" * 60)
    print("Report complete. Dataset was not modified.")
    print("=" * 60)


def main() -> None:
    df = load_cleaned_dataset()
    print_data_quality_report(df)


if __name__ == "__main__":
    main()
