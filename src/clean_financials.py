"""
clean_financials.py
-------------------
Extracts Qualcomm's quarterly financial data from the raw SEC EDGAR
company-facts JSON, including Q4 derivation.

SEC does not publish a standalone Q4 10-Q. For duration metrics, Q4 is
derived as: full-year 10-K value minus 9-month YTD from the Q3 10-Q.
For cash-flow metrics, standalone Q2 and Q3 are also unavailable and
must be derived from cumulative YTD differences.

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

TARGET_FISCAL_YEARS = 3

CSV_COLUMNS = [
    "company",
    "fiscal_year",
    "fiscal_quarter",
    "metric_name",
    "value",
    "unit",
    "filing_date",
    "form_type",
    "source_reference",
    "extraction_method",
    "derived_from",
    "requires_manual_review",
]

# ---------------------------------------------------------------------------
# XBRL tag mapping
#
# Each entry: (tag, unit, metric_type)
#   metric_type:
#     "duration"           — income/cash-flow, has start+end dates
#     "duration_cashflow"  — cash-flow only: SEC reports only cumulative YTD
#                            for Q2/Q3, so standalone must be derived
#     "instant"            — balance-sheet snapshot at period_end
#     "instant_sum"        — sum of multiple instant tags
#     "derived"            — computed from other extracted metrics
#     "eps"                — special handling: no Q4 subtraction
#
# Tag choices:
#   Revenues                                      — Qualcomm's top-line revenue
#   CostOfRevenue                                 — has standalone Q2/Q3
#   OperatingIncomeLoss                           — standard operating income
#   NetIncomeLoss                                 — net income to shareholders
#   EarningsPerShareDiluted                       — USD/shares, no subtraction
#   CashAndCashEquivalentsAtCarryingValue         — balance-sheet snapshot
#   LongTermDebt + DebtCurrent                    — total debt (instant sum)
#   NetCashProvidedByUsedInOperatingActivities    — only cumulative YTD
#   PaymentsToAcquireProductiveAssets             — Qualcomm's capex tag
#     (they don't use PaymentsToAcquirePropertyPlantAndEquipment)
#   ResearchAndDevelopmentExpense                 — standard R&D
# ---------------------------------------------------------------------------

METRIC_MAP = {
    "Revenue": ("Revenues", "USD", "duration"),
    "Cost of Revenue": ("CostOfRevenue", "USD", "duration"),
    "Operating Income": ("OperatingIncomeLoss", "USD", "duration"),
    "Net Income": ("NetIncomeLoss", "USD", "duration"),
    "Diluted EPS": ("EarningsPerShareDiluted", "USD/shares", "eps"),
    "R&D Expense": ("ResearchAndDevelopmentExpense", "USD", "duration"),
    "Operating Cash Flow": (
        "NetCashProvidedByUsedInOperatingActivities", "USD", "duration_cashflow"),
    "Capital Expenditure": (
        "PaymentsToAcquireProductiveAssets", "USD", "duration_cashflow"),
    "Cash and Cash Equivalents": (
        "CashAndCashEquivalentsAtCarryingValue", "USD", "instant"),
    "Total Debt": (["LongTermDebt", "DebtCurrent"], "USD", "instant_sum"),
}

# Gross Profit is derived after Revenue and Cost of Revenue are extracted.
DERIVED_METRICS = {
    "Gross Profit": {
        "formula": "Revenue minus Cost of Revenue",
        "plus": "Revenue",
        "minus": "Cost of Revenue",
        "unit": "USD",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_raw_file() -> Path:
    candidates = sorted(RAW_DIR.glob("qualcomm_CIK*.json"))
    if not candidates:
        sys.exit("ERROR: No raw Qualcomm JSON found in data/raw/. "
                 "Run fetch_sec_data.py first.")
    return candidates[-1]


def days_between(start_str: str, end_str: str) -> int:
    s = datetime.strptime(start_str, "%Y-%m-%d").date()
    e = datetime.strptime(end_str, "%Y-%m-%d").date()
    return (e - s).days


def accession_to_url(accn: str) -> str:
    clean = accn.replace("-", "")
    return (f"https://www.sec.gov/Archives/edgar/data/804328/"
            f"{clean}/{accn}-index.htm")


def best_entry(entries: list[dict]) -> dict | None:
    """From duplicate entries for the same period, keep the most recently filed."""
    if not entries:
        return None
    return max(entries, key=lambda e: e["filed"])


# ---------------------------------------------------------------------------
# Building a fiscal-year lookup of XBRL entries
# ---------------------------------------------------------------------------

def classify_entries(entries: list[dict]) -> dict:
    """
    Organize raw XBRL entries into a nested dict keyed by fiscal year:

        {fy: {"q1": entry, "ytd_q2": entry, "ytd_q3": entry, "fy": entry,
               "q2": entry_or_None, "q3": entry_or_None}}

    SEC filings tag prior-year comparison data with the SAME fy as the
    filing.  For example, fy=2025 may contain both the actual FY2025
    annual result AND the prior-year FY2024 result for comparison.

    To disambiguate, we first identify the correct FY entry (the one
    with the latest end date), then use its start date as the anchor.
    Only entries whose start date matches the FY anchor are accepted
    for YTD buckets (q1, ytd_q2, ytd_q3).  Standalone q2/q3 entries
    must fall within the FY date range.
    """
    # Step 1: bucket all entries by (fy, classification)
    raw_fy = {}

    for e in entries:
        fy = e.get("fy")
        fp = e.get("fp", "")
        if fy is None or "start" not in e:
            continue

        if fy not in raw_fy:
            raw_fy[fy] = {
                "q1": [], "q2": [], "q3": [],
                "ytd_q2": [], "ytd_q3": [], "fy": [],
            }

        days = days_between(e["start"], e["end"])

        if fp == "Q1" and 60 <= days <= 115:
            raw_fy[fy]["q1"].append(e)
        elif fp == "Q2" and 60 <= days <= 115:
            raw_fy[fy]["q2"].append(e)
        elif fp == "Q3" and 60 <= days <= 115:
            raw_fy[fy]["q3"].append(e)
        elif fp == "Q2" and 150 <= days <= 200:
            raw_fy[fy]["ytd_q2"].append(e)
        elif fp == "Q3" and 240 <= days <= 290:
            raw_fy[fy]["ytd_q3"].append(e)
        elif fp == "FY" and 340 <= days <= 400:
            raw_fy[fy]["fy"].append(e)

    # Step 2: for each fy, pick the FY entry with the latest end date
    # (the actual fiscal year, not the prior-year comparison), then
    # filter all other buckets to entries consistent with that anchor.
    by_fy = {}
    for fy, buckets in raw_fy.items():
        fy_candidates = buckets["fy"]
        if not fy_candidates:
            continue

        fy_entry = max(fy_candidates, key=lambda e: e["end"])
        anchor_start = fy_entry["start"]
        anchor_end = fy_entry["end"]

        by_fy[fy] = {"fy": fy_entry}

        # YTD entries (q1, ytd_q2, ytd_q3) must start on the anchor date
        for key in ("q1", "ytd_q2", "ytd_q3"):
            matching = [e for e in buckets[key] if e["start"] == anchor_start]
            by_fy[fy][key] = best_entry(matching)

        # Standalone q2/q3 must end within the FY range
        for key in ("q2", "q3"):
            matching = [e for e in buckets[key]
                        if anchor_start <= e["start"] and e["end"] <= anchor_end]
            by_fy[fy][key] = best_entry(matching)

    return by_fy


def classify_instant_entries(entries: list[dict]) -> dict:
    """
    Organize instant (balance-sheet) entries by fiscal year and quarter.

        {fy: {"q1": entry, "q2": entry, "q3": entry, "fy": entry}}

    Each SEC filing reports the current-period balance AND the prior-
    period comparison balance, both tagged with the same fy/fp.
    The current-period balance has the later end date, so we pick the
    entry with the LATEST end date per (fy, fp) bucket, then among
    ties keep the most recently filed.
    """
    by_fy = {}

    for e in entries:
        fy = e.get("fy")
        fp = e.get("fp", "")
        if fy is None:
            continue

        if fy not in by_fy:
            by_fy[fy] = {"q1": [], "q2": [], "q3": [], "fy": []}

        if fp == "Q1":
            by_fy[fy]["q1"].append(e)
        elif fp == "Q2":
            by_fy[fy]["q2"].append(e)
        elif fp == "Q3":
            by_fy[fy]["q3"].append(e)
        elif fp == "FY":
            by_fy[fy]["fy"].append(e)

    for fy in by_fy:
        for key in by_fy[fy]:
            candidates = by_fy[fy][key]
            if not candidates:
                by_fy[fy][key] = None
                continue
            # Pick latest end date first, then latest filing date as tiebreak
            by_fy[fy][key] = max(candidates,
                                  key=lambda e: (e["end"], e["filed"]))

    return by_fy


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def make_row(metric_name, unit, fy, quarter, value, filing_date, form_type,
             source_ref, extraction_method, derived_from="",
             requires_review=False):
    return {
        "company": "Qualcomm Incorporated",
        "fiscal_year": fy,
        "fiscal_quarter": quarter,
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "filing_date": filing_date,
        "form_type": form_type,
        "source_reference": source_ref,
        "extraction_method": extraction_method,
        "derived_from": derived_from,
        "requires_manual_review": "Yes" if requires_review else "",
    }


def make_missing_row(metric_name, unit, fy, quarter, reason):
    return {
        "company": "Qualcomm Incorporated",
        "fiscal_year": fy,
        "fiscal_quarter": quarter,
        "metric_name": metric_name,
        "value": "",
        "unit": unit,
        "filing_date": "",
        "form_type": "",
        "source_reference": "",
        "extraction_method": "missing_requires_review",
        "derived_from": reason,
        "requires_manual_review": "Yes",
    }


# ---------------------------------------------------------------------------
# Extraction per metric type
# ---------------------------------------------------------------------------

def extract_duration(metric_name: str, tag: str, unit: str, gaap: dict,
                     target_fys: list[int]) -> list[dict]:
    """
    Extract quarterly rows for a duration metric that has standalone
    Q2/Q3 entries (income-statement items like Revenue, CostOfRevenue).
    """
    if tag not in gaap or unit not in gaap[tag].get("units", {}):
        return []

    entries = gaap[tag]["units"][unit]
    by_fy = classify_entries(entries)
    rows = []

    for fy in target_fys:
        data = by_fy.get(fy, {})

        # Q1 — standalone
        e = data.get("q1")
        if e:
            rows.append(make_row(
                metric_name, unit, fy, "Q1", e["val"],
                e["filed"], e["form"], accession_to_url(e["accn"]),
                "reported_standalone"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q1",
                "No standalone Q1 entry found"))

        # Q2 — prefer standalone; fall back to YTD_Q2 - Q1
        e_q2 = data.get("q2")
        if e_q2:
            rows.append(make_row(
                metric_name, unit, fy, "Q2", e_q2["val"],
                e_q2["filed"], e_q2["form"], accession_to_url(e_q2["accn"]),
                "reported_standalone"))
        else:
            ytd2 = data.get("ytd_q2")
            q1 = data.get("q1")
            if ytd2 and q1:
                val = ytd2["val"] - q1["val"]
                rows.append(make_row(
                    metric_name, unit, fy, "Q2", val,
                    ytd2["filed"], ytd2["form"],
                    accession_to_url(ytd2["accn"]),
                    "derived_ytd_difference",
                    f"YTD_Q2({ytd2['val']:,}) minus Q1({q1['val']:,})"))
            else:
                rows.append(make_missing_row(
                    metric_name, unit, fy, "Q2",
                    "No standalone Q2 and insufficient YTD data"))

        # Q3 — prefer standalone; fall back to YTD_Q3 - YTD_Q2
        e_q3 = data.get("q3")
        if e_q3:
            rows.append(make_row(
                metric_name, unit, fy, "Q3", e_q3["val"],
                e_q3["filed"], e_q3["form"], accession_to_url(e_q3["accn"]),
                "reported_standalone"))
        else:
            ytd3 = data.get("ytd_q3")
            ytd2 = data.get("ytd_q2")
            if ytd3 and ytd2:
                val = ytd3["val"] - ytd2["val"]
                rows.append(make_row(
                    metric_name, unit, fy, "Q3", val,
                    ytd3["filed"], ytd3["form"],
                    accession_to_url(ytd3["accn"]),
                    "derived_ytd_difference",
                    f"YTD_Q3({ytd3['val']:,}) minus YTD_Q2({ytd2['val']:,})"))
            else:
                rows.append(make_missing_row(
                    metric_name, unit, fy, "Q3",
                    "No standalone Q3 and insufficient YTD data"))

        # Q4 — always derived: FY minus YTD_Q3
        fy_entry = data.get("fy")
        ytd3 = data.get("ytd_q3")
        if fy_entry and ytd3:
            val = fy_entry["val"] - ytd3["val"]
            rows.append(make_row(
                metric_name, unit, fy, "Q4", val,
                fy_entry["filed"], "10-K + 10-Q",
                accession_to_url(fy_entry["accn"]),
                "derived_ytd_difference",
                f"FY({fy_entry['val']:,}) minus YTD_Q3({ytd3['val']:,})"))
        elif fy_entry:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q4",
                "Have FY total but no Q3 YTD to subtract"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q4",
                "No FY total available for derivation"))

    return rows


def extract_duration_cashflow(metric_name: str, tag: str, unit: str,
                              gaap: dict, target_fys: list[int]) -> list[dict]:
    """
    Extract quarterly rows for a cash-flow metric where SEC only reports
    cumulative YTD for Q2/Q3 (no standalone Q2/Q3 entries exist).
    """
    if tag not in gaap or unit not in gaap[tag].get("units", {}):
        return []

    entries = gaap[tag]["units"][unit]
    by_fy = classify_entries(entries)
    rows = []

    for fy in target_fys:
        data = by_fy.get(fy, {})

        # Q1 — standalone (Q1 YTD = Q1 standalone)
        e = data.get("q1")
        if e:
            rows.append(make_row(
                metric_name, unit, fy, "Q1", e["val"],
                e["filed"], e["form"], accession_to_url(e["accn"]),
                "reported_standalone"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q1",
                "No Q1 entry found"))

        # Q2 — derived: YTD_Q2 - Q1
        ytd2 = data.get("ytd_q2")
        q1 = data.get("q1")
        if ytd2 and q1:
            val = ytd2["val"] - q1["val"]
            rows.append(make_row(
                metric_name, unit, fy, "Q2", val,
                ytd2["filed"], ytd2["form"],
                accession_to_url(ytd2["accn"]),
                "derived_ytd_difference",
                f"YTD_Q2({ytd2['val']:,}) minus Q1({q1['val']:,})"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q2",
                "Missing YTD_Q2 or Q1 for derivation"))

        # Q3 — derived: YTD_Q3 - YTD_Q2
        ytd3 = data.get("ytd_q3")
        if ytd3 and ytd2:
            val = ytd3["val"] - ytd2["val"]
            rows.append(make_row(
                metric_name, unit, fy, "Q3", val,
                ytd3["filed"], ytd3["form"],
                accession_to_url(ytd3["accn"]),
                "derived_ytd_difference",
                f"YTD_Q3({ytd3['val']:,}) minus YTD_Q2({ytd2['val']:,})"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q3",
                "Missing YTD_Q3 or YTD_Q2 for derivation"))

        # Q4 — derived: FY - YTD_Q3
        fy_entry = data.get("fy")
        if fy_entry and ytd3:
            val = fy_entry["val"] - ytd3["val"]
            rows.append(make_row(
                metric_name, unit, fy, "Q4", val,
                fy_entry["filed"], "10-K + 10-Q",
                accession_to_url(fy_entry["accn"]),
                "derived_ytd_difference",
                f"FY({fy_entry['val']:,}) minus YTD_Q3({ytd3['val']:,})"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q4",
                "Missing FY or YTD_Q3 for derivation"))

    return rows


def extract_eps(metric_name: str, tag: str, unit: str, gaap: dict,
                target_fys: list[int]) -> list[dict]:
    """
    Extract Diluted EPS. Uses standalone quarterly entries for Q1-Q3.
    Q4 EPS is NOT derived by subtraction (share counts change across
    quarters, making subtraction invalid). Q4 is flagged for manual review.
    """
    if tag not in gaap or unit not in gaap[tag].get("units", {}):
        return []

    entries = gaap[tag]["units"][unit]
    by_fy = classify_entries(entries)
    rows = []

    for fy in target_fys:
        data = by_fy.get(fy, {})

        for q_key, q_label in [("q1", "Q1"), ("q2", "Q2"), ("q3", "Q3")]:
            e = data.get(q_key)
            if e:
                rows.append(make_row(
                    metric_name, unit, fy, q_label, e["val"],
                    e["filed"], e["form"], accession_to_url(e["accn"]),
                    "reported_standalone"))
            else:
                rows.append(make_missing_row(
                    metric_name, unit, fy, q_label,
                    f"No standalone {q_label} EPS entry found"))

        # Q4 — never derived by subtraction
        rows.append(make_missing_row(
            metric_name, unit, fy, "Q4",
            "EPS cannot be derived by subtraction due to "
            "changing share counts across quarters"))

    return rows


def extract_instant(metric_name: str, tag: str, unit: str, gaap: dict,
                    target_fys: list[int]) -> list[dict]:
    """
    Extract a balance-sheet (instant) metric. Q4 uses the fiscal-year-end
    snapshot from the 10-K.
    """
    if tag not in gaap or unit not in gaap[tag].get("units", {}):
        return []

    entries = gaap[tag]["units"][unit]
    by_fy = classify_instant_entries(entries)
    rows = []

    for fy in target_fys:
        data = by_fy.get(fy, {})

        for q_key, q_label in [("q1", "Q1"), ("q2", "Q2"), ("q3", "Q3")]:
            e = data.get(q_key)
            if e:
                rows.append(make_row(
                    metric_name, unit, fy, q_label, e["val"],
                    e["filed"], e["form"], accession_to_url(e["accn"]),
                    "reported_standalone"))
            else:
                rows.append(make_missing_row(
                    metric_name, unit, fy, q_label,
                    f"No {q_label} balance-sheet snapshot found"))

        # Q4 — use fiscal-year-end balance from 10-K
        fy_entry = data.get("fy")
        if fy_entry:
            rows.append(make_row(
                metric_name, unit, fy, "Q4", fy_entry["val"],
                fy_entry["filed"], fy_entry["form"],
                accession_to_url(fy_entry["accn"]),
                "fiscal_year_end_balance"))
        else:
            rows.append(make_missing_row(
                metric_name, unit, fy, "Q4",
                "No fiscal-year-end balance found in 10-K"))

    return rows


def extract_instant_sum(metric_name: str, tags: list[str], unit: str,
                        gaap: dict, target_fys: list[int]) -> list[dict]:
    """
    Extract a metric that is the sum of multiple instant tags
    (e.g., Total Debt = LongTermDebt + DebtCurrent).
    """
    # Build classified entries for each component tag
    all_by_fy = {}
    available_tags = []
    for tag in tags:
        if tag in gaap and unit in gaap[tag].get("units", {}):
            all_by_fy[tag] = classify_instant_entries(gaap[tag]["units"][unit])
            available_tags.append(tag)

    if not available_tags:
        return []

    rows = []
    quarters = [("q1", "Q1"), ("q2", "Q2"), ("q3", "Q3"), ("fy", "Q4")]

    for fy in target_fys:
        for q_key, q_label in quarters:
            component_vals = []
            component_descs = []
            latest_filed = ""
            latest_form = ""
            latest_accn = ""
            all_found = True

            for tag in available_tags:
                data = all_by_fy[tag].get(fy, {})
                e = data.get(q_key)
                if e:
                    component_vals.append(e["val"])
                    component_descs.append(f"{tag}({e['val']:,})")
                    if e["filed"] > latest_filed:
                        latest_filed = e["filed"]
                        latest_form = e["form"]
                        latest_accn = e["accn"]
                else:
                    all_found = False

            if all_found and component_vals:
                total = sum(component_vals)
                method = ("fiscal_year_end_balance" if q_key == "fy"
                          else "reported_standalone")
                rows.append(make_row(
                    metric_name, unit, fy, q_label, total,
                    latest_filed, latest_form,
                    accession_to_url(latest_accn),
                    method,
                    " + ".join(component_descs)))
            else:
                missing_tags = [t for t in available_tags
                                if not all_by_fy[t].get(fy, {}).get(q_key)]
                rows.append(make_missing_row(
                    metric_name, unit, fy, q_label,
                    f"Missing component(s): {', '.join(missing_tags)}"))

    return rows


def derive_gross_profit(all_rows: list[dict], target_fys: list[int],
                        ) -> list[dict]:
    """
    Derive Gross Profit = Revenue - Cost of Revenue for each quarter.
    """
    rev_lookup = {}
    cor_lookup = {}
    for r in all_rows:
        key = (r["fiscal_year"], r["fiscal_quarter"])
        if r["metric_name"] == "Revenue" and r["value"] != "":
            rev_lookup[key] = r
        elif r["metric_name"] == "Cost of Revenue" and r["value"] != "":
            cor_lookup[key] = r

    rows = []
    for fy in target_fys:
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            key = (fy, q)
            rev = rev_lookup.get(key)
            cor = cor_lookup.get(key)

            if rev and cor:
                gp = float(rev["value"]) - float(cor["value"])
                sources = [rev["source_reference"], cor["source_reference"]]
                latest_filed = max(rev["filing_date"], cor["filing_date"])
                rows.append(make_row(
                    "Gross Profit", "USD", fy, q, gp,
                    latest_filed, rev["form_type"],
                    sources[0],
                    "derived_ytd_difference",
                    f"Revenue({float(rev['value']):,.0f}) minus "
                    f"CostOfRevenue({float(cor['value']):,.0f})"))
            else:
                missing = []
                if not rev:
                    missing.append("Revenue")
                if not cor:
                    missing.append("Cost of Revenue")
                rows.append(make_missing_row(
                    "Gross Profit", "USD", fy, q,
                    f"Cannot derive — missing: {', '.join(missing)}"))

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    raw_path = find_latest_raw_file()
    print(f"Reading raw data from: {raw_path.name}")

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    gaap = data["facts"].get("us-gaap", {})

    # Determine target fiscal years (most recent N with FY data available)
    # Look at Revenue to find which fiscal years have full-year entries
    rev_entries = gaap.get("Revenues", {}).get("units", {}).get("USD", [])
    available_fys = sorted(set(
        e["fy"] for e in rev_entries
        if e.get("fp") == "FY" and "start" in e
        and 340 <= days_between(e["start"], e["end"]) <= 400
    ), reverse=True)

    target_fys = available_fys[:TARGET_FISCAL_YEARS]
    print(f"Target fiscal years: {sorted(target_fys)}")

    all_rows = []
    missing_metrics = []

    for metric_name, config in METRIC_MAP.items():
        tag, unit, metric_type = config

        if metric_type == "duration":
            rows = extract_duration(metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "duration_cashflow":
            rows = extract_duration_cashflow(
                metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "eps":
            rows = extract_eps(metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "instant":
            rows = extract_instant(metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "instant_sum":
            rows = extract_instant_sum(
                metric_name, tag, unit, gaap, target_fys)
        else:
            missing_metrics.append({
                "metric": metric_name,
                "reason": f"Unknown metric_type: {metric_type}",
                "suggestion": "Check METRIC_MAP configuration",
            })
            continue

        if not rows:
            missing_metrics.append({
                "metric": metric_name,
                "reason": f"XBRL tag not found or no data",
                "suggestion": "Check tag name and unit in raw JSON",
            })
            print(f"  MISSING: {metric_name}")
            continue

        reported = sum(1 for r in rows if r["extraction_method"] == "reported_standalone")
        derived = sum(1 for r in rows
                      if r["extraction_method"] in ("derived_ytd_difference",
                                                     "fiscal_year_end_balance"))
        flagged = sum(1 for r in rows if r["requires_manual_review"] == "Yes")
        print(f"  {metric_name}: {reported} reported, {derived} derived, "
              f"{flagged} flagged")

        all_rows.extend(rows)

    # Derived metrics
    gp_rows = derive_gross_profit(all_rows, target_fys)
    reported = sum(1 for r in gp_rows if r["value"] != "")
    flagged = sum(1 for r in gp_rows if r["requires_manual_review"] == "Yes")
    print(f"  Gross Profit: {reported} derived, {flagged} flagged")
    all_rows.extend(gp_rows)

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
    flagged_rows = [r for r in all_rows if r["requires_manual_review"] == "Yes"]
    if flagged_rows or missing_metrics:
        MANUAL_CHECKS_DIR.mkdir(parents=True, exist_ok=True)
        flag_path = MANUAL_CHECKS_DIR / f"qualcomm_missing_metrics_{today}.csv"

        with open(flag_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "metric", "fiscal_year", "fiscal_quarter",
                "extraction_method", "reason"])
            writer.writeheader()

            for r in flagged_rows:
                writer.writerow({
                    "metric": r["metric_name"],
                    "fiscal_year": r["fiscal_year"],
                    "fiscal_quarter": r["fiscal_quarter"],
                    "extraction_method": r["extraction_method"],
                    "reason": r["derived_from"],
                })

            for m in missing_metrics:
                writer.writerow({
                    "metric": m["metric"],
                    "fiscal_year": "",
                    "fiscal_quarter": "",
                    "extraction_method": "not_available",
                    "reason": m["reason"],
                })

        print(f"Flagged {len(flagged_rows) + len(missing_metrics)} item(s) "
              f"in: {flag_path}")


if __name__ == "__main__":
    main()
