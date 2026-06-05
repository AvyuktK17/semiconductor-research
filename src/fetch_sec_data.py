"""
fetch_sec_data.py
-----------------
Downloads a company's company-facts JSON from the SEC EDGAR XBRL API
and saves the untouched response to data/raw/.

Reads company metadata (CIK, name, etc.) from config/companies.csv.

SEC EDGAR endpoint documentation:
https://www.sec.gov/edgar/sec-api-documentation

Usage:
    .venv/bin/python src/fetch_sec_data.py QCOM
    .venv/bin/python src/fetch_sec_data.py AVGO
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

from config_loader import load_company, parse_ticker_arg

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

EDGAR_ENDPOINT = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def load_user_agent() -> str:
    """Read SEC_USER_AGENT from the .env file at the project root."""
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(env_path)

    user_agent = os.getenv("SEC_USER_AGENT")
    if not user_agent:
        sys.exit(
            "ERROR: SEC_USER_AGENT is not set.\n"
            "Copy .env.example to .env and add your name and email.\n"
            "The SEC requires this header to identify who is making requests."
        )
    return user_agent


def build_output_path(short_id: str, cik: str) -> Path:
    """Return the file path for today's raw download."""
    today = date.today().isoformat()
    filename = f"{short_id}_CIK{cik}_{today}.json"
    return RAW_DIR / filename


def fetch_company_facts(cik: str, user_agent: str) -> dict:
    """GET the company-facts JSON from SEC EDGAR."""
    url = EDGAR_ENDPOINT.format(cik=cik)
    headers = {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def save_raw_json(data: dict, path: Path) -> None:
    """Write the JSON response to disk without modification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    ticker = parse_ticker_arg()
    company = load_company(ticker)

    short_id = company["short_identifier"]
    cik = company["cik"]
    name = company["company_name"]

    output_path = build_output_path(short_id, cik)

    if output_path.exists():
        print(f"Already downloaded today: {output_path}")
        return

    user_agent = load_user_agent()

    print(f"Requesting {name} ({ticker}) company facts from SEC EDGAR ...")

    try:
        data = fetch_company_facts(cik, user_agent)
    except requests.exceptions.HTTPError as e:
        sys.exit(f"HTTP error from SEC EDGAR: {e}")
    except requests.exceptions.ConnectionError:
        sys.exit("Connection error — check your internet connection.")
    except requests.exceptions.Timeout:
        sys.exit("Request timed out — SEC EDGAR may be slow. Try again later.")
    except requests.exceptions.RequestException as e:
        sys.exit(f"Request failed: {e}")

    save_raw_json(data, output_path)
    print(f"Saved raw JSON to: {output_path}")


if __name__ == "__main__":
    main()
