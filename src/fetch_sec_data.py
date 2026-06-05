"""
fetch_sec_data.py
-----------------
Downloads Qualcomm's company-facts JSON from the SEC EDGAR XBRL API
and saves the untouched response to data/raw/.

SEC EDGAR endpoint documentation:
https://www.sec.gov/edgar/sec-api-documentation

Usage:
    .venv/bin/python src/fetch_sec_data.py
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Qualcomm's SEC Central Index Key (CIK), zero-padded to 10 digits.
QUALCOMM_CIK = "0000804328"

# SEC EDGAR company-facts endpoint.  Returns every XBRL fact the company
# has reported across all filings (10-K, 10-Q, etc.) in a single JSON.
ENDPOINT = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{QUALCOMM_CIK}.json"

# Where to save the raw download (relative to the project root).
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def load_user_agent() -> str:
    """Read SEC_USER_AGENT from the .env file at the project root."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    user_agent = os.getenv("SEC_USER_AGENT")
    if not user_agent:
        sys.exit(
            "ERROR: SEC_USER_AGENT is not set.\n"
            "Copy .env.example to .env and add your name and email.\n"
            "The SEC requires this header to identify who is making requests."
        )
    return user_agent


def build_output_path() -> Path:
    """Return the file path for today's raw download."""
    today = date.today().isoformat()  # e.g. 2026-06-04
    filename = f"qualcomm_CIK{QUALCOMM_CIK}_{today}.json"
    return RAW_DIR / filename


def fetch_company_facts(user_agent: str) -> dict:
    """GET the company-facts JSON from SEC EDGAR."""
    headers = {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
    }

    response = requests.get(ENDPOINT, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def save_raw_json(data: dict, path: Path) -> None:
    """Write the JSON response to disk without modification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    output_path = build_output_path()

    # Avoid redundant requests — if today's file already exists, skip.
    if output_path.exists():
        print(f"Already downloaded today: {output_path}")
        return

    user_agent = load_user_agent()

    print(f"Requesting Qualcomm company facts from SEC EDGAR ...")

    try:
        data = fetch_company_facts(user_agent)
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
