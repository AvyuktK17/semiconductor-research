# Semiconductor Research Terminal

An auditable equity-research workflow that extracts, cleans, validates, and analyzes quarterly financial data for five public semiconductor companies using SEC EDGAR filings as the sole data source.

> **Disclaimer:** This is a portfolio project demonstrating financial data engineering and analysis skills. It is not investment advice. All data is sourced from public SEC filings and may contain errors. See [Key Limitations](#key-limitations).

<!-- ![Dashboard screenshot placeholder](docs/screenshots/dashboard.png) -->

---

## Why I Built This

Equity research depends on clean, traceable financial data. Most freely available datasets either lack source references, silently impute missing values, or obscure the difference between reported and derived figures.

I wanted to build a system where every number can be traced back to a specific SEC filing, every derivation is labeled, and every gap is flagged for human review rather than quietly filled in. The project also gave me an opportunity to work through real-world accounting edge cases — different fiscal year-ends, 53-week years, acquisition-year distortions, and inconsistent XBRL tagging across companies.

---

## Companies Covered

| Company | Ticker | Fiscal Year-End | Business Model | Coverage |
|---------|--------|-----------------|----------------|----------|
| Qualcomm | QCOM | Late September | Fabless + Licensing | FY2023–FY2025 |
| AMD | AMD | Late December | Fabless | FY2023–FY2025 |
| Nvidia | NVDA | Late January | Fabless | FY2024–FY2026 |
| Intel | INTC | Late December | IDM (owns fabs) | FY2023–FY2025 |
| Broadcom | AVGO | Early November | Fabless + Software | FY2023–FY2025 |

Each company covers 12 quarters (3 fiscal years) across 11 financial metrics and 10 calculated ratios.

---

## Data Source

All financial data comes from the **SEC EDGAR XBRL API** — the same structured data that companies file with the Securities and Exchange Commission. No third-party data providers, no scraped web pages, no manually typed numbers.

Every extracted value carries:
- An SEC filing URL linking to the specific filing
- The filing date and reporting period
- An extraction method label (`reported_standalone`, `derived_ytd_difference`, `fiscal_year_end_balance`, or `missing_requires_review`)

---

## Methodology

The pipeline runs in four stages per company:

1. **Download** — Fetch the company-facts JSON from SEC EDGAR (`fetch_sec_data.py`)
2. **Clean** — Extract quarterly financials from XBRL data, derive Q4 values, flag gaps (`clean_financials.py`)
3. **Calculate** — Compute margins, free cash flow, YoY growth rates, and trailing-twelve-month aggregates (`calculate_metrics.py`)
4. **Export** — Generate a multi-tab Excel workbook with color-coded sourcing (`export_excel.py`)

A fifth script (`build_peer_comparison.py`) consolidates all five companies into a peer comparison model, and a sixth (`add_valuation_layer.py`) adds market-data-based valuation multiples.

Each company has its own XBRL tag configuration file (`config/xbrl_tags/*.json`) because companies use different XBRL tags for the same financial concept (for example, three different tags are used for "Revenue" across these five companies).

---

## Q4 Derivation Logic

None of these companies file a separate Q4 10-Q. The pipeline handles this by:

- **Income statement and cash-flow metrics:** Q4 = full-year value from the 10-K minus the nine-month year-to-date value from the Q3 10-Q. Both source values and the derivation method are recorded.
- **Balance sheet metrics:** Q4 uses the fiscal year-end snapshot directly from the 10-K.
- **Diluted EPS:** Not derived by subtraction (diluted share counts change across quarters, making subtraction mathematically invalid). Flagged as `missing_requires_review` for all five companies.

Every derived value is labeled and shaded differently in the Excel output so a reviewer can distinguish it from directly reported data.

---

## Validation Framework

Each company has a validation checklist (`data/manual_checks/*_validation_checklist.csv`) that documents:

- **FY total reconciliation** — quarterly sums are compared against reported full-year totals
- **Cross-tag verification** — derived values (like Gross Profit = Revenue − Cost of Revenue) are compared against independently reported XBRL tags where available
- **Debt component reconciliation** — total debt figures are compared against the sum of their components
- **Rounding tolerance rules** — small discrepancies (≤$1M) caused by XBRL data artifacts are documented and tolerated, not hidden

The Qualcomm pipeline serves as an immutable regression benchmark. After every code change, automated checks confirm that Qualcomm's output is unchanged.

**Missing data is never silently filled.** The pipeline produces 15 flagged items for Q4 EPS alone, plus company-specific gaps (AMD Q1 debt, Intel Q2/Q3 cash). These are documented, not papered over.

---

## Valuation Methodology

The valuation layer adds market data (share prices and shares outstanding from SEC cover pages) to compute:

- Market capitalization
- Enterprise value (Market Cap + Total Debt − Cash)
- EV / TTM Revenue
- Price / TTM Free Cash Flow
- FCF Yield

P/E ratio and EV/EBITDA are intentionally omitted because Q4 EPS is missing for all companies and EBITDA is not derived from the available data.

All market data inputs are stored in a separate file (`data/manual_inputs/valuation_inputs.csv`) with a `manually_reviewed = Yes` flag.

---

## Key Limitations

These are disclosed throughout the pipeline outputs and documented in full in `PROJECT_STATUS.md`:

1. **Fiscal year-ends differ** — direct period-over-period comparison across companies requires calendar-quarter alignment, which is not yet implemented
2. **Q4 diluted EPS is missing** for all five companies (15 instances) — would require earnings press releases as an independent source
3. **Intel is an IDM** — its CapEx ($14–26B/year) is 10–20× larger than fabless peers, making FCF comparison structurally misleading without business-model adjustment
4. **Intel cash includes ~$447M restricted cash** (~3%) — inconsistent with the other four companies
5. **Intel FY2024 includes ~$16B in non-recurring charges** — GAAP margins are not comparable to peers without non-GAAP adjustments
6. **Broadcom's total debt is gross principal** (~$2B / 3% above carrying value used by the other four companies)
7. **Broadcom FY2024 was a 53-week VMware transition year** — revenue jumped 44%, primarily from the acquisition, making YoY comparison unreliable
8. **All analysis is GAAP only** — no non-GAAP adjustments are applied

---

## Key Analytical Findings

Selected observations from the peer comparison (full analysis in `memo/semiconductor_sector_memo.md`):

- **Nvidia's revenue scale dominates the peer group** — $130B TTM revenue is 3–4× larger than the next-largest peer, driven by data-center AI demand
- **Fabless margins cluster in a band** — QCOM, AMD, and NVDA gross margins range 50–75%; Intel's IDM model produces 28–46% gross margins
- **Broadcom's operating margin collapsed from 45% to 26% in FY2024** due to ~$8–10B/year in acquired intangible amortization from VMware — this is a GAAP accounting artifact, not an operational deterioration
- **Intel generated negative free cash flow** across recent periods due to fab construction investment — this is structural, not cyclical
- **All five companies have material AI-related revenue exposure**, but the nature differs: Nvidia (GPUs), Broadcom (custom accelerators and networking), AMD (GPUs and CPUs), Qualcomm (edge AI), Intel (different approach via foundry and Gaudi)

---

## Claude's Role vs. My Role

This project was built collaboratively with Claude (Anthropic's AI assistant). Here is how the work was divided:

**Claude wrote:**
- Python scripts for data extraction, cleaning, calculation, and export
- XBRL tag configurations after I identified the correct tags through SEC filing review
- Validation logic and regression testing framework
- Excel formatting and peer comparison model structure

**I did:**
- All accounting judgment calls (which XBRL tags to use, how to handle edge cases, when a derivation is valid)
- Manual review of every flagged item and validation checklist
- Cross-referencing derived values against SEC filings
- Qualitative claims sourcing and review (reading 10-K/10-Q filings, selecting relevant excerpts)
- Valuation input verification (share prices, shares outstanding)
- Final sign-off on all outputs

**Neither of us should be trusted blindly.** The validation checklists exist so a third party can independently verify the data.

---

## Repository Structure

```
src/                          # Pipeline scripts (8 files)
  config_loader.py            #   Shared config reader and SEC URL builder
  fetch_sec_data.py           #   Downloads company-facts JSON from SEC EDGAR
  clean_financials.py         #   Extracts quarterly financials, derives Q4
  calculate_metrics.py        #   Margins, FCF, YoY growth, TTM aggregates
  export_excel.py             #   Multi-tab Excel workbook with color coding
  build_peer_comparison.py    #   Five-company consolidated peer model
  add_valuation_layer.py      #   Market data, EV, valuation multiples
  regression_check.py         #   Compares output against Qualcomm benchmarks

config/
  companies.csv               # Company registry (ticker, CIK, FY-end dates)
  xbrl_tags/*.json            # Per-company XBRL tag configurations

data/
  raw/                        # Original SEC EDGAR JSON (not committed, reproducible)
  processed/                  # Cleaned CSVs — financials and calculated metrics
  manual_checks/              # Validation checklists and flagged items
  manual_inputs/              # Valuation inputs (prices, shares outstanding)
  benchmarks/qualcomm/        # Immutable regression benchmarks

output/
  *.xlsx                      # 5 individual workbooks + 1 peer comparison workbook

memo/
  semiconductor_sector_memo.md  # Analyst-style peer comparison memo
```

---

## How to Run the Pipeline

**Prerequisites:** Python 3.10+, a SEC EDGAR User-Agent string (your name and email, per SEC fair-use policy).

```bash
# 1. Set up the environment
cp .env.example .env          # Add your SEC User-Agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run for a single company
python src/fetch_sec_data.py QCOM
python src/clean_financials.py QCOM
python src/calculate_metrics.py QCOM
python src/export_excel.py QCOM

# 3. Repeat for all five companies (QCOM, AMD, NVDA, INTC, AVGO)

# 4. Build the peer comparison
python src/build_peer_comparison.py

# 5. Add valuation layer
python src/add_valuation_layer.py

# 6. Verify Qualcomm regression (after any code changes)
python src/regression_check.py
```

Use the `--test` flag on any script to write output to `data/test_outputs/` and `output/test_outputs/` instead of production directories.

---

## Interactive Dashboard

<!-- TODO: Replace with published Claude Artifact URL -->
**[View the interactive peer comparison dashboard →](#)**

<!-- ![Dashboard detail screenshot placeholder](docs/screenshots/dashboard-detail.png) -->

---

## License

This project is for educational and portfolio purposes. SEC EDGAR data is in the public domain. See [SEC EDGAR fair access policies](https://www.sec.gov/os/accessing-edgar-data).
