"""
config_loader.py
----------------
Shared utility for reading company configuration and XBRL tag maps.

All four pipeline scripts import this module instead of hardcoding
company-specific values.

Usage from another script:
    from config_loader import load_company, load_xbrl_tags, parse_ticker_arg
"""

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
COMPANIES_CSV = CONFIG_DIR / "companies.csv"
XBRL_TAGS_DIR = CONFIG_DIR / "xbrl_tags"


def load_all_companies() -> dict:
    """
    Read config/companies.csv and return a dict keyed by ticker.

    Each value is a dict with keys:
        company_name, ticker, cik, short_identifier,
        fiscal_year_end_month (int), fiscal_year_end_day (int)
    """
    companies = {}
    with open(COMPANIES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["fiscal_year_end_month"] = int(row["fiscal_year_end_month"])
            row["fiscal_year_end_day"] = int(row["fiscal_year_end_day"])
            companies[row["ticker"]] = row
    return companies


def load_company(ticker: str) -> dict:
    """Load metadata for a single company by ticker. Exits on unknown ticker."""
    companies = load_all_companies()
    if ticker not in companies:
        valid = ", ".join(sorted(companies.keys()))
        sys.exit(f"ERROR: Unknown ticker '{ticker}'. Valid tickers: {valid}")
    return companies[ticker]


def load_xbrl_tags(short_identifier: str) -> dict:
    """
    Load the XBRL tag map for a company from config/xbrl_tags/<short_id>.json.

    Returns a dict with keys "metric_map" and "derived_metrics".
    """
    path = XBRL_TAGS_DIR / f"{short_identifier}.json"
    if not path.exists():
        sys.exit(
            f"ERROR: No XBRL tag file found at {path}.\n"
            f"Create it before running the pipeline for this company."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_ticker_arg() -> str:
    """
    Read the company ticker from sys.argv[1].
    Defaults to QCOM if no argument is given.
    """
    if len(sys.argv) < 2:
        return "QCOM"
    return sys.argv[1].upper()


def cik_numeric(cik: str) -> str:
    """Strip leading zeros from a CIK for use in EDGAR URLs."""
    return str(int(cik))


def accession_to_url(accession: str, cik: str) -> str:
    """Build a SEC EDGAR filing URL from an accession number and CIK."""
    clean = accession.replace("-", "")
    numeric = cik_numeric(cik)
    return (f"https://www.sec.gov/Archives/edgar/data/{numeric}/"
            f"{clean}/{accession}-index.htm")
