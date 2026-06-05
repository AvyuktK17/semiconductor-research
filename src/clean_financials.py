"""
clean_financials.py
-------------------
Extracts quarterly financial data from a company's raw SEC EDGAR
company-facts JSON, including Q4 derivation.

Most companies do not publish a standalone Q4 10-Q. For duration metrics,
Q4 is derived as: full-year 10-K value minus 9-month YTD from the Q3 10-Q.
For cash-flow metrics, standalone Q2 and Q3 are also unavailable and
must be derived from cumulative YTD differences.

Reads company metadata from config/companies.csv and XBRL tag definitions
from config/xbrl_tags/<short_id>.json.

Usage:
    .venv/bin/python src/clean_financials.py QCOM
    .venv/bin/python src/clean_financials.py QCOM --test
"""

import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

from config_loader import (
    load_company, load_xbrl_tags, parse_ticker_arg, accession_to_url,
)

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


def is_test_mode() -> bool:
    """Check whether --test was passed on the command line."""
    return "--test" in sys.argv


def output_dirs(short_id: str) -> tuple[Path, Path]:
    """Return (processed_dir, manual_checks_dir) based on test mode."""
    if is_test_mode():
        base = PROJECT_ROOT / "data" / "test_outputs" / short_id
        return base, base
    return PROCESSED_DIR, MANUAL_CHECKS_DIR


# ---------------------------------------------------------------------------
# Load XBRL tag map from JSON config
# ---------------------------------------------------------------------------

def build_metric_map(tags_config: dict) -> dict:
    """
    Convert the JSON tag config into the tuple-based format the
    extraction functions expect.

    JSON format per metric:
        {"tag": "Revenues", "unit": "USD", "metric_type": "duration"}
    or for instant_sum:
        {"tag": ["LongTermDebt", "DebtCurrent"], "unit": "USD", ...}

    Returns:
        {"Revenue": ("Revenues", "USD", "duration"), ...}
    """
    metric_map = {}
    for metric_name, config in tags_config["metric_map"].items():
        tag = config["tag"]
        unit = config["unit"]
        metric_type = config["metric_type"]
        metric_map[metric_name] = (tag, unit, metric_type)
    return metric_map


def build_derived_metrics(tags_config: dict) -> dict:
    """Load derived-metric definitions from the JSON config."""
    return tags_config.get("derived_metrics", {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_raw_file(short_id: str) -> Path:
    """Find the most recent raw JSON for a company."""
    candidates = sorted(RAW_DIR.glob(f"{short_id}_CIK*.json"))
    if not candidates:
        sys.exit(
            f"ERROR: No raw JSON found for '{short_id}' in {RAW_DIR}. "
            f"Run fetch_sec_data.py first."
        )
    return candidates[-1]


def days_between(start_str: str, end_str: str) -> int:
    s = datetime.strptime(start_str, "%Y-%m-%d").date()
    e = datetime.strptime(end_str, "%Y-%m-%d").date()
    return (e - s).days


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

    by_fy = {}
    for fy, buckets in raw_fy.items():
        fy_candidates = buckets["fy"]
        if not fy_candidates:
            continue

        fy_entry = max(fy_candidates, key=lambda e: e["end"])
        anchor_start = fy_entry["start"]
        anchor_end = fy_entry["end"]

        by_fy[fy] = {"fy": fy_entry}

        for key in ("q1", "ytd_q2", "ytd_q3"):
            matching = [e for e in buckets[key] if e["start"] == anchor_start]
            by_fy[fy][key] = best_entry(matching)

        for key in ("q2", "q3"):
            matching = [e for e in buckets[key]
                        if anchor_start <= e["start"] and e["end"] <= anchor_end]
            # Pick the entry with the latest end date first (actual quarter),
            # then latest filing date as tiebreaker.  This avoids selecting
            # prior-period comparison data that SEC re-tags with the current
            # filing's fp label (e.g. Q1 data re-reported in the Q3 10-Q
            # as fp=Q3 but with Q1's end date).
            if matching:
                by_fy[fy][key] = max(matching,
                                      key=lambda e: (e["end"], e["filed"]))
            else:
                by_fy[fy][key] = None

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
            by_fy[fy][key] = max(candidates,
                                  key=lambda e: (e["end"], e["filed"]))

    return by_fy


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def make_row(company_name, metric_name, unit, fy, quarter, value,
             filing_date, form_type, source_ref, extraction_method,
             derived_from="", requires_review=False):
    return {
        "company": company_name,
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


def make_missing_row(company_name, metric_name, unit, fy, quarter, reason):
    return {
        "company": company_name,
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

def extract_duration(company_name: str, cik: str, metric_name: str,
                     tag: str, unit: str, gaap: dict,
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
                company_name, metric_name, unit, fy, "Q1", e["val"],
                e["filed"], e["form"], accession_to_url(e["accn"], cik),
                "reported_standalone"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q1",
                "No standalone Q1 entry found"))

        # Q2 — prefer standalone; fall back to YTD_Q2 - Q1
        e_q2 = data.get("q2")
        if e_q2:
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q2", e_q2["val"],
                e_q2["filed"], e_q2["form"],
                accession_to_url(e_q2["accn"], cik),
                "reported_standalone"))
        else:
            ytd2 = data.get("ytd_q2")
            q1 = data.get("q1")
            if ytd2 and q1:
                val = ytd2["val"] - q1["val"]
                rows.append(make_row(
                    company_name, metric_name, unit, fy, "Q2", val,
                    ytd2["filed"], ytd2["form"],
                    accession_to_url(ytd2["accn"], cik),
                    "derived_ytd_difference",
                    f"YTD_Q2({ytd2['val']:,}) minus Q1({q1['val']:,})"))
            else:
                rows.append(make_missing_row(
                    company_name, metric_name, unit, fy, "Q2",
                    "No standalone Q2 and insufficient YTD data"))

        # Q3 — prefer standalone; fall back to YTD_Q3 - YTD_Q2
        e_q3 = data.get("q3")
        if e_q3:
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q3", e_q3["val"],
                e_q3["filed"], e_q3["form"],
                accession_to_url(e_q3["accn"], cik),
                "reported_standalone"))
        else:
            ytd3 = data.get("ytd_q3")
            ytd2 = data.get("ytd_q2")
            if ytd3 and ytd2:
                val = ytd3["val"] - ytd2["val"]
                rows.append(make_row(
                    company_name, metric_name, unit, fy, "Q3", val,
                    ytd3["filed"], ytd3["form"],
                    accession_to_url(ytd3["accn"], cik),
                    "derived_ytd_difference",
                    f"YTD_Q3({ytd3['val']:,}) minus YTD_Q2({ytd2['val']:,})"))
            else:
                rows.append(make_missing_row(
                    company_name, metric_name, unit, fy, "Q3",
                    "No standalone Q3 and insufficient YTD data"))

        # Q4 — always derived: FY minus YTD_Q3
        fy_entry = data.get("fy")
        ytd3 = data.get("ytd_q3")
        if fy_entry and ytd3:
            val = fy_entry["val"] - ytd3["val"]
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q4", val,
                fy_entry["filed"], "10-K + 10-Q",
                accession_to_url(fy_entry["accn"], cik),
                "derived_ytd_difference",
                f"FY({fy_entry['val']:,}) minus YTD_Q3({ytd3['val']:,})"))
        elif fy_entry:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q4",
                "Have FY total but no Q3 YTD to subtract"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q4",
                "No FY total available for derivation"))

    return rows


def extract_duration_cashflow(company_name: str, cik: str,
                              metric_name: str, tag: str, unit: str,
                              gaap: dict,
                              target_fys: list[int]) -> list[dict]:
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
                company_name, metric_name, unit, fy, "Q1", e["val"],
                e["filed"], e["form"], accession_to_url(e["accn"], cik),
                "reported_standalone"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q1",
                "No Q1 entry found"))

        # Q2 — derived: YTD_Q2 - Q1
        ytd2 = data.get("ytd_q2")
        q1 = data.get("q1")
        if ytd2 and q1:
            val = ytd2["val"] - q1["val"]
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q2", val,
                ytd2["filed"], ytd2["form"],
                accession_to_url(ytd2["accn"], cik),
                "derived_ytd_difference",
                f"YTD_Q2({ytd2['val']:,}) minus Q1({q1['val']:,})"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q2",
                "Missing YTD_Q2 or Q1 for derivation"))

        # Q3 — derived: YTD_Q3 - YTD_Q2
        ytd3 = data.get("ytd_q3")
        if ytd3 and ytd2:
            val = ytd3["val"] - ytd2["val"]
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q3", val,
                ytd3["filed"], ytd3["form"],
                accession_to_url(ytd3["accn"], cik),
                "derived_ytd_difference",
                f"YTD_Q3({ytd3['val']:,}) minus YTD_Q2({ytd2['val']:,})"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q3",
                "Missing YTD_Q3 or YTD_Q2 for derivation"))

        # Q4 — derived: FY - YTD_Q3
        fy_entry = data.get("fy")
        if fy_entry and ytd3:
            val = fy_entry["val"] - ytd3["val"]
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q4", val,
                fy_entry["filed"], "10-K + 10-Q",
                accession_to_url(fy_entry["accn"], cik),
                "derived_ytd_difference",
                f"FY({fy_entry['val']:,}) minus YTD_Q3({ytd3['val']:,})"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q4",
                "Missing FY or YTD_Q3 for derivation"))

    return rows


def extract_eps(company_name: str, cik: str, metric_name: str,
                tag: str, unit: str, gaap: dict,
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
                    company_name, metric_name, unit, fy, q_label, e["val"],
                    e["filed"], e["form"],
                    accession_to_url(e["accn"], cik),
                    "reported_standalone"))
            else:
                rows.append(make_missing_row(
                    company_name, metric_name, unit, fy, q_label,
                    f"No standalone {q_label} EPS entry found"))

        # Q4 — never derived by subtraction
        rows.append(make_missing_row(
            company_name, metric_name, unit, fy, "Q4",
            "EPS cannot be derived by subtraction due to "
            "changing share counts across quarters"))

    return rows


def extract_instant(company_name: str, cik: str, metric_name: str,
                    tag: str, unit: str, gaap: dict,
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
                    company_name, metric_name, unit, fy, q_label, e["val"],
                    e["filed"], e["form"],
                    accession_to_url(e["accn"], cik),
                    "reported_standalone"))
            else:
                rows.append(make_missing_row(
                    company_name, metric_name, unit, fy, q_label,
                    f"No {q_label} balance-sheet snapshot found"))

        # Q4 — use fiscal-year-end balance from 10-K
        fy_entry = data.get("fy")
        if fy_entry:
            rows.append(make_row(
                company_name, metric_name, unit, fy, "Q4", fy_entry["val"],
                fy_entry["filed"], fy_entry["form"],
                accession_to_url(fy_entry["accn"], cik),
                "fiscal_year_end_balance"))
        else:
            rows.append(make_missing_row(
                company_name, metric_name, unit, fy, "Q4",
                "No fiscal-year-end balance found in 10-K"))

    return rows


def extract_instant_sum(company_name: str, cik: str, metric_name: str,
                        tags: list[str], unit: str, gaap: dict,
                        target_fys: list[int]) -> list[dict]:
    """
    Extract a metric that is the sum of multiple instant tags
    (e.g., Total Debt = LongTermDebt + DebtCurrent).
    """
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
                    company_name, metric_name, unit, fy, q_label, total,
                    latest_filed, latest_form,
                    accession_to_url(latest_accn, cik),
                    method,
                    " + ".join(component_descs)))
            else:
                missing_tags = [t for t in available_tags
                                if not all_by_fy[t].get(fy, {}).get(q_key)]
                rows.append(make_missing_row(
                    company_name, metric_name, unit, fy, q_label,
                    f"Missing component(s): {', '.join(missing_tags)}"))

    return rows


def derive_gross_profit(company_name: str, all_rows: list[dict],
                        target_fys: list[int]) -> list[dict]:
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
                    company_name, "Gross Profit", "USD", fy, q, gp,
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
                    company_name, "Gross Profit", "USD", fy, q,
                    f"Cannot derive — missing: {', '.join(missing)}"))

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ticker = parse_ticker_arg()
    company = load_company(ticker)

    company_name = company["company_name"]
    short_id = company["short_identifier"]
    cik = company["cik"]

    tags_config = load_xbrl_tags(short_id)
    metric_map = build_metric_map(tags_config)
    derived_defs = build_derived_metrics(tags_config)

    raw_path = find_latest_raw_file(short_id)
    print(f"Reading raw data from: {raw_path.name}")

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    gaap = data["facts"].get("us-gaap", {})

    # Determine target fiscal years (most recent N with FY data available).
    # Use the first duration metric's tag to find which fiscal years exist.
    first_duration_tag = None
    for _, (tag, unit, mtype) in metric_map.items():
        if mtype == "duration":
            first_duration_tag = tag
            break

    if not first_duration_tag:
        sys.exit("ERROR: No duration metric found in tag config.")

    rev_entries = gaap.get(first_duration_tag, {}).get("units", {}).get("USD", [])
    available_fys = sorted(set(
        e["fy"] for e in rev_entries
        if e.get("fp") == "FY" and "start" in e
        and 340 <= days_between(e["start"], e["end"]) <= 400
    ), reverse=True)

    target_fys = available_fys[:TARGET_FISCAL_YEARS]
    print(f"Target fiscal years: {sorted(target_fys)}")

    all_rows = []
    missing_metrics = []

    for metric_name, (tag, unit, metric_type) in metric_map.items():

        if metric_type == "duration":
            rows = extract_duration(
                company_name, cik, metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "duration_cashflow":
            rows = extract_duration_cashflow(
                company_name, cik, metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "eps":
            rows = extract_eps(
                company_name, cik, metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "instant":
            rows = extract_instant(
                company_name, cik, metric_name, tag, unit, gaap, target_fys)
        elif metric_type == "instant_sum":
            rows = extract_instant_sum(
                company_name, cik, metric_name, tag, unit, gaap, target_fys)
        else:
            missing_metrics.append({
                "metric": metric_name,
                "reason": f"Unknown metric_type: {metric_type}",
                "suggestion": "Check XBRL tag configuration",
            })
            continue

        if not rows:
            missing_metrics.append({
                "metric": metric_name,
                "reason": "XBRL tag not found or no data",
                "suggestion": "Check tag name and unit in raw JSON",
            })
            print(f"  MISSING: {metric_name}")
            continue

        reported = sum(1 for r in rows
                       if r["extraction_method"] == "reported_standalone")
        derived = sum(1 for r in rows
                      if r["extraction_method"] in ("derived_ytd_difference",
                                                     "fiscal_year_end_balance"))
        flagged = sum(1 for r in rows
                      if r["requires_manual_review"] == "Yes")
        print(f"  {metric_name}: {reported} reported, {derived} derived, "
              f"{flagged} flagged")

        all_rows.extend(rows)

    # Derived metrics (e.g. Gross Profit)
    if "Gross Profit" in derived_defs:
        gp_rows = derive_gross_profit(company_name, all_rows, target_fys)
        reported = sum(1 for r in gp_rows if r["value"] != "")
        flagged = sum(1 for r in gp_rows
                      if r["requires_manual_review"] == "Yes")
        print(f"  Gross Profit: {reported} derived, {flagged} flagged")
        all_rows.extend(gp_rows)

    # --- Write processed CSV ---
    today = date.today().isoformat()
    proc_dir, checks_dir = output_dirs(short_id)
    proc_dir.mkdir(parents=True, exist_ok=True)
    checks_dir.mkdir(parents=True, exist_ok=True)

    csv_path = proc_dir / f"{short_id}_financials_{today}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} rows to: {csv_path}")

    # --- Write missing-metrics flag file ---
    flagged_rows = [r for r in all_rows if r["requires_manual_review"] == "Yes"]
    if flagged_rows or missing_metrics:
        flag_path = checks_dir / f"{short_id}_missing_metrics_{today}.csv"

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
