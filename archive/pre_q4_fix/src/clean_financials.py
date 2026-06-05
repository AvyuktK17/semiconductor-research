"""
clean_financials.py
-------------------
Extracts Qualcomm's most recent 12 reported quarters from the raw
SEC EDGAR company-facts JSON and writes a tidy CSV to data/processed/.

Reads from:  data/raw/qualcomm_CIK0000804328_<date>.json
Writes to:   data/processed/qualcomm_financials_<date>.csv
Flags:       data/manual_checks/qualcomm_missing_metrics_<date>.csv

Usage:
    .venv/bin/python src/clean_financials.py
"""

import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MANUAL_CHECKS_DIR = PROJECT_ROOT / "data" / "manual_checks"

TARGET_QUARTERS = 12

# Maps each metric we want to a tuple of:
#   (xbrl_tag, unit_key, metric_type)
#
# metric_type is either "duration" (income/cash-flow items with start+end)
# or "instant" (balance-sheet items with end only).
#
# Tag choices explained in the README and script header:
#   - Revenues: Qualcomm's top-line revenue tag.
#   - GrossProfit: NOT TAGGED by Qualcomm — flagged as missing.
#   - OperatingIncomeLoss: standard US-GAAP operating income.
#   - NetIncomeLoss: net income to Qualcomm shareholders.
#   - EarningsPerShareDiluted: per-share, so unit is USD/shares.
#   - CashAndCashEquivalentsAtCarryingValue: balance-sheet snapshot.
#   - NetCashProvidedByUsedInOperatingActivities: operating cash flow.
#   - PaymentsToAcquireProductiveAssets: Qualcomm's capex tag
#     (they don't use the more common PaymentsToAcquirePropertyPlantAndEquipment).
#   - ResearchAndDevelopmentExpense: standard R&D line item.
METRIC_MAP = {
    "Revenue": ("Revenues", "USD", "duration"),
    "Gross Profit": (None, None, None),  # not tagged by Qualcomm
    "Operating Income": ("OperatingIncomeLoss", "USD", "duration"),
    "Net Income": ("NetIncomeLoss", "USD", "duration"),
    "Diluted EPS": ("EarningsPerShareDiluted", "USD/shares", "duration"),
    "Cash and Cash Equivalents": ("CashAndCashEquivalentsAtCarryingValue", "USD", "instant"),
    "Operating Cash Flow": ("NetCashProvidedByUsedInOperatingActivities", "USD", "duration"),
    "Capital Expenditure": ("PaymentsToAcquireProductiveAssets", "USD", "duration"),
    "R&D Expense": ("ResearchAndDevelopmentExpense", "USD", "duration"),
}

CSV_COLUMNS = [
    "company",
    "fiscal_year",
    "fiscal_quarter",
    "period_start",
    "period_end",
    "filing_date",
    "sec_form_type",
    "metric_name",
    "value",
    "unit",
    "source_reference",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_raw_file() -> Path:
    """Return the most recent Qualcomm raw JSON file in data/raw/."""
    candidates = sorted(RAW_DIR.glob("qualcomm_CIK*.json"))
    if not candidates:
        sys.exit("ERROR: No raw Qualcomm JSON found in data/raw/. Run fetch_sec_data.py first.")
    return candidates[-1]


def days_between(start_str: str, end_str: str) -> int:
    """Number of days between two YYYY-MM-DD date strings."""
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    return (end - start).days


def is_single_quarter(entry: dict) -> bool:
    """True if a duration entry covers roughly one fiscal quarter (60-115 days)."""
    if "start" not in entry:
        return False
    days = days_between(entry["start"], entry["end"])
    return 60 <= days <= 115


def is_full_year(entry: dict) -> bool:
    """True if a duration entry covers roughly one fiscal year (340-400 days)."""
    if "start" not in entry:
        return False
    days = days_between(entry["start"], entry["end"])
    return 340 <= days <= 400


def accession_to_url(accn: str) -> str:
    """Convert an SEC accession number to an EDGAR filing URL."""
    clean = accn.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/804328/{clean}/{accn}-index.htm"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_duration_quarters(entries: list[dict]) -> list[dict]:
    """
    From a list of XBRL fact entries for a duration metric,
    return standalone single-quarter entries, deduplicated to keep
    the most recently filed version of each period.
    """
    # Keep only entries that span a single quarter
    quarterly = [e for e in entries if is_single_quarter(e)]

    # Deduplicate: for each unique (start, end) period, keep the entry
    # with the latest filing date — this captures any restatements.
    best = {}
    for e in quarterly:
        key = (e["start"], e["end"])
        if key not in best or e["filed"] > best[key]["filed"]:
            best[key] = e

    # Sort by period end date, most recent first
    result = sorted(best.values(), key=lambda x: x["end"], reverse=True)
    return result[:TARGET_QUARTERS]


def extract_instant_quarters(entries: list[dict]) -> list[dict]:
    """
    From a list of XBRL fact entries for an instant (balance-sheet) metric,
    return one entry per reporting date, deduplicated by latest filing.
    """
    best = {}
    for e in entries:
        key = e["end"]
        if key not in best or e["filed"] > best[key]["filed"]:
            best[key] = e

    result = sorted(best.values(), key=lambda x: x["end"], reverse=True)
    return result[:TARGET_QUARTERS]


def entry_to_row(metric_name: str, unit: str, entry: dict) -> dict:
    """Convert one XBRL entry into a flat CSV row."""
    return {
        "company": "Qualcomm Incorporated",
        "fiscal_year": entry.get("fy", ""),
        "fiscal_quarter": entry.get("fp", ""),
        "period_start": entry.get("start", ""),
        "period_end": entry.get("end", ""),
        "filing_date": entry.get("filed", ""),
        "sec_form_type": entry.get("form", ""),
        "metric_name": metric_name,
        "value": entry.get("val", ""),
        "unit": unit,
        "source_reference": accession_to_url(entry["accn"]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    raw_path = find_latest_raw_file()
    print(f"Reading raw data from: {raw_path.name}")

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    gaap = data["facts"].get("us-gaap", {})

    all_rows = []
    missing_metrics = []

    for metric_name, (tag, unit, metric_type) in METRIC_MAP.items():
        # Handle metrics we already know are missing
        if tag is None:
            missing_metrics.append({
                "metric": metric_name,
                "reason": "Qualcomm does not file this as a standalone XBRL tag",
                "suggestion": "Can be derived from Revenue minus CostOfRevenue (for Gross Profit)",
            })
            print(f"  MISSING: {metric_name} — not tagged by Qualcomm")
            continue

        # Check if the tag exists in the data
        if tag not in gaap:
            missing_metrics.append({
                "metric": metric_name,
                "reason": f"XBRL tag '{tag}' not found in filing data",
                "suggestion": "Verify tag name or check for alternative tags",
            })
            print(f"  MISSING: {metric_name} — tag '{tag}' not in data")
            continue

        # Check if the expected unit exists
        if unit not in gaap[tag].get("units", {}):
            missing_metrics.append({
                "metric": metric_name,
                "reason": f"Unit '{unit}' not found for tag '{tag}'",
                "suggestion": f"Available units: {list(gaap[tag]['units'].keys())}",
            })
            print(f"  MISSING: {metric_name} — unit '{unit}' not available")
            continue

        entries = gaap[tag]["units"][unit]

        if metric_type == "duration":
            selected = extract_duration_quarters(entries)
        else:
            selected = extract_instant_quarters(entries)

        if not selected:
            missing_metrics.append({
                "metric": metric_name,
                "reason": "No quarterly entries found after filtering",
                "suggestion": "Check date-range filtering logic",
            })
            print(f"  MISSING: {metric_name} — no entries after filtering")
            continue

        for entry in selected:
            all_rows.append(entry_to_row(metric_name, unit, entry))

        print(f"  OK: {metric_name} — {len(selected)} quarters extracted")

    # --- Write processed CSV ---
    today = date.today().isoformat()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = PROCESSED_DIR / f"qualcomm_financials_{today}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} rows to: {csv_path}")

    # --- Write missing-metrics flag file ---
    if missing_metrics:
        MANUAL_CHECKS_DIR.mkdir(parents=True, exist_ok=True)
        flag_path = MANUAL_CHECKS_DIR / f"qualcomm_missing_metrics_{today}.csv"
        with open(flag_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metric", "reason", "suggestion"])
            writer.writeheader()
            writer.writerows(missing_metrics)
        print(f"Flagged {len(missing_metrics)} missing metric(s) in: {flag_path}")


if __name__ == "__main__":
    main()
