#!/usr/bin/env python3
"""
CSV Profiler Utility
Performs automated scale, data quality, null-check, and frequency profiling on tabular CSV files.
Usage: python profile_csv.py <path_to_csv> [--delimiter "|"]
"""

import sys
import os
import argparse
import pandas as pd

def profile_csv(file_path: str, delimiter: str = "|"):
    if not os.path.exists(file_path):
        print(f"[!] Error: File not found at {file_path}")
        return

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"=== CSV Data Profile: {file_path} ===")
    print(f"[*] File Size: {size_mb:.2f} MB")
    print(f"[*] Delimiter: {repr(delimiter)}")

    try:
        df = pd.read_csv(file_path, sep=delimiter, dtype=str, low_memory=False)
    except Exception as e:
        print(f"[!] Failed to read CSV: {e}")
        return

    print(f"[*] Row Count: {len(df):,}")
    print(f"[*] Column Count: {len(df.columns)}")
    print("\n--- Column Overview & Data Quality ---")
    
    col_summary = []
    for col in df.columns:
        null_count = df[col].isnull().sum() + (df[col] == "").sum()
        null_pct = (null_count / len(df)) * 100
        unique_count = df[col].nunique()
        col_summary.append({
            "Column": col,
            "Null / Empty Count": f"{null_count:,} ({null_pct:.1f}%)",
            "Unique Values": f"{unique_count:,}",
            "Sample Value": str(df[col].dropna().iloc[0])[:40] if not df[col].dropna().empty else "N/A"
        })

    summary_df = pd.DataFrame(col_summary)
    print(summary_df.to_string(index=False))
    print("\n=== End of Profile ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile a CSV file for data analysis.")
    parser.add_argument("file_path", help="Path to the CSV file")
    parser.add_argument("--delimiter", "-d", default="|", help="Field separator (default: '|')")
    args = parser.parse_args()
    profile_csv(args.file_path, args.delimiter)
