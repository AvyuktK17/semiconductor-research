"""
regression_check.py
-------------------
Compares test-output CSVs against the immutable benchmark files to
verify that the refactored pipeline produces identical Qualcomm results.

Compares:
    1. qualcomm_financials_*.csv  (base financial data, 132 rows)
    2. qualcomm_missing_metrics_*.csv  (flagged items)
    3. qualcomm_metrics.csv  (calculated metrics, 120 rows)

Usage:
    .venv/bin/python src/regression_check.py QCOM
"""

import csv
import sys
from pathlib import Path

from config_loader import load_company, parse_ticker_arg

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_latest_file(directory: Path, pattern: str) -> Path | None:
    candidates = sorted(directory.glob(pattern))
    return candidates[-1] if candidates else None


def load_csv_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compare_csvs(benchmark_path: Path, test_path: Path,
                 label: str) -> list[str]:
    """
    Compare two CSV files row-by-row.
    Returns a list of difference descriptions (empty = identical).
    """
    diffs = []

    if not benchmark_path.exists():
        diffs.append(f"  Benchmark file missing: {benchmark_path}")
        return diffs
    if not test_path.exists():
        diffs.append(f"  Test output file missing: {test_path}")
        return diffs

    bench_rows = load_csv_rows(benchmark_path)
    test_rows = load_csv_rows(test_path)

    if len(bench_rows) != len(test_rows):
        diffs.append(
            f"  Row count: benchmark={len(bench_rows)}, "
            f"test={len(test_rows)}")

    # Compare headers
    if bench_rows and test_rows:
        bench_cols = list(bench_rows[0].keys())
        test_cols = list(test_rows[0].keys())
        if bench_cols != test_cols:
            diffs.append(
                f"  Column mismatch:\n"
                f"    benchmark: {bench_cols}\n"
                f"    test:      {test_cols}")
            return diffs

    # Compare row-by-row
    max_diffs = 10
    diff_count = 0
    for i, (b, t) in enumerate(zip(bench_rows, test_rows)):
        if b != t:
            diff_count += 1
            if diff_count <= max_diffs:
                for col in b:
                    if b.get(col) != t.get(col):
                        diffs.append(
                            f"  Row {i+1}, column '{col}':\n"
                            f"    benchmark: {b.get(col)!r}\n"
                            f"    test:      {t.get(col)!r}")

    if diff_count > max_diffs:
        diffs.append(f"  ... and {diff_count - max_diffs} more row differences")

    return diffs


def main():
    ticker = parse_ticker_arg()
    company = load_company(ticker)
    short_id = company["short_identifier"]

    bench_dir = PROJECT_ROOT / "data" / "benchmarks" / short_id
    test_dir = PROJECT_ROOT / "data" / "test_outputs" / short_id

    print(f"Regression check for {company['company_name']} ({ticker})")
    print(f"  Benchmark dir: {bench_dir}")
    print(f"  Test dir:      {test_dir}")
    print()

    all_pass = True

    # --- 1. Financials CSV ---
    bench_fin = find_latest_file(bench_dir,
                                 f"{short_id}_financials_*.csv")
    test_fin = find_latest_file(test_dir,
                                f"{short_id}_financials_*.csv")

    print("1. Financials CSV")
    if bench_fin and test_fin:
        diffs = compare_csvs(bench_fin, test_fin, "financials")
        if diffs:
            all_pass = False
            print("   FAIL")
            for d in diffs:
                print(d)
        else:
            print(f"   PASS — {len(load_csv_rows(bench_fin))} rows match")
    else:
        all_pass = False
        if not bench_fin:
            print(f"   FAIL — benchmark file not found in {bench_dir}")
        if not test_fin:
            print(f"   FAIL — test output file not found in {test_dir}")

    # --- 2. Missing metrics CSV ---
    bench_miss = find_latest_file(bench_dir,
                                  f"{short_id}_missing_metrics_*.csv")
    test_miss = find_latest_file(test_dir,
                                 f"{short_id}_missing_metrics_*.csv")

    print("\n2. Missing Metrics CSV")
    if bench_miss and test_miss:
        diffs = compare_csvs(bench_miss, test_miss, "missing_metrics")
        if diffs:
            all_pass = False
            print("   FAIL")
            for d in diffs:
                print(d)
        else:
            print(f"   PASS — {len(load_csv_rows(bench_miss))} rows match")
    else:
        all_pass = False
        if not bench_miss:
            print(f"   FAIL — benchmark file not found in {bench_dir}")
        if not test_miss:
            print(f"   FAIL — test output file not found in {test_dir}")

    # --- 3. Calculated metrics CSV ---
    bench_met = bench_dir / f"{short_id}_metrics.csv"
    test_met = test_dir / f"{short_id}_metrics.csv"

    print("\n3. Calculated Metrics CSV")
    if bench_met.exists() and test_met.exists():
        diffs = compare_csvs(bench_met, test_met, "metrics")
        if diffs:
            all_pass = False
            print("   FAIL")
            for d in diffs:
                print(d)
        else:
            print(f"   PASS — {len(load_csv_rows(bench_met))} rows match")
    else:
        all_pass = False
        if not bench_met.exists():
            print(f"   FAIL — benchmark file not found: {bench_met}")
        if not test_met.exists():
            print(f"   FAIL — test output file not found: {test_met}")

    # --- Summary ---
    print("\n" + "=" * 50)
    if all_pass:
        print("REGRESSION CHECK: ALL PASS")
        print("The refactored pipeline produces identical Qualcomm output.")
    else:
        print("REGRESSION CHECK: FAILED")
        print("The refactored pipeline does NOT match the benchmark.")
        sys.exit(1)


if __name__ == "__main__":
    main()
