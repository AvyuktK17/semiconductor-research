# Semiconductor Research Terminal

Auditable equity-research workflow for public semiconductor companies.

## Current scope

Qualcomm Incorporated — financial data sourced from SEC EDGAR filings.

## Project structure

```
data/raw/            # Original SEC filings, never modified
data/processed/      # Cleaned and structured financial data
data/manual_checks/  # Flagged items needing human review
src/                 # Python scripts (download, parse, clean, analyze)
output/              # Final tables, charts, and exports
notebooks/           # Jupyter notebooks for exploration
memo/                # Research memos and interpretation
```

## Raw data

Raw SEC EDGAR JSON files (`data/raw/*.json`) are downloaded locally by the pipeline and are intentionally not committed to Git. They are large (~8 MB each) and fully reproducible by running `src/fetch_sec_data.py`.

## Setup

1. Copy `.env.example` to `.env` and fill in your SEC User-Agent.
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
