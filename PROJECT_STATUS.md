# Project Status — Semiconductor Research Terminal

Last updated: 2026-06-04

## Project objective

Build an auditable equity-research workflow for five public semiconductor companies. The system downloads financial data from SEC EDGAR, cleans and structures it, derives standard financial ratios, and exports analyst-ready Excel workbooks. Every metric carries a source reference, extraction method, and manual-review flag.

The user is a finance graduate learning Python. Code should be modular, clearly explained, and beginner-friendly.

## Completed work

| Stage | Description | Status |
|-------|-------------|--------|
| 1 | Project scaffolding — folders, .gitignore, .env, README | Done |
| 2 | SEC EDGAR download script for Qualcomm | Done |
| 3 | Initial quarterly financial extraction (Q1–Q3 only) | Done, then replaced |
| 4 | Excel workbook export (4 tabs) | Done, then updated |
| 5 | Q4 logic audit — identified missing Q4, cash-flow YTD issues, instant-entry bugs | Done |
| 6 | Backup of pre-Q4-fix scripts and outputs | Done |
| 7 | Full rewrite of cleaning script — Q4 derivation, YTD subtraction, new metrics, bug fixes | Done |
| 8 | Calculated metrics — margins, FCF, net debt, YoY growth, TTM aggregates | Done |

## Qualcomm pipeline

### Raw data source

SEC EDGAR XBRL company-facts API. One GET request returns every financial fact Qualcomm has filed across all 10-K and 10-Q filings as a single JSON (~8.4 MB).

- Endpoint: `https://data.sec.gov/api/xbrl/companyfacts/CIK0000804328.json`
- CIK: `0000804328` (Qualcomm Incorporated)
- Requires `User-Agent` header (stored in `.env`)

### Cleaning workflow

`src/clean_financials.py` reads the raw JSON and produces a structured CSV with one row per (metric, fiscal_year, quarter). The script handles three classes of metric differently:

- **Duration metrics with standalone quarters** (Revenue, Cost of Revenue, Operating Income, Net Income, R&D Expense): Q1–Q3 use standalone entries directly. Q4 = FY (10-K) minus 9M YTD (Q3 10-Q).
- **Duration metrics with cumulative-only reporting** (Operating Cash Flow, Capital Expenditure): SEC only reports cumulative YTD for Q2/Q3. Q1 is standalone. Q2 = YTD_Q2 minus Q1. Q3 = YTD_Q3 minus YTD_Q2. Q4 = FY minus YTD_Q3.
- **Instant (balance-sheet) metrics** (Cash and Cash Equivalents, Total Debt): Per-quarter snapshots from 10-Q filings. Q4 uses the fiscal-year-end balance from the 10-K.

Gross Profit is derived as Revenue minus Cost of Revenue each quarter.

Total Debt is the sum of `LongTermDebt` and `DebtCurrent` XBRL tags.

Diluted EPS Q4 is left blank and flagged — it cannot be derived by subtraction because diluted share counts change across quarters.

### Excel export workflow

`src/export_excel.py` reads the processed CSV and produces a multi-tab workbook:

1. **Quarterly Financials** — pivot grid, 11 metrics x 12 quarters. Derived cells shaded yellow, review cells shaded pink.
2. **Detail View** — full row-level data with all metadata columns visible.
3. **Missing Metrics** — flagged items plus not-yet-implemented ratios.
4. **Data Dictionary** — column definitions, extraction method meanings, metric-to-XBRL-tag mapping.
5. **Manual Checks** — 7 audit items documenting assumptions.

### Ratio calculation workflow

`src/calculate_metrics.py` reads the base financial CSV and calculates 10 derived metrics:

- Gross Margin, Operating Margin, FCF Margin, R&D as % of Revenue (all percentage ratios)
- Free Cash Flow, Net Cash (Debt) (USD values)
- YoY Revenue Growth (same-quarter comparison)
- TTM Revenue, TTM Operating Income, TTM Free Cash Flow (trailing 4-quarter sums)

Output is saved to `data/processed/qualcomm_metrics.csv` and appended as a "Calculated Metrics" tab in the Excel workbook.

### Validation workflow

`data/manual_checks/qualcomm_q4_validation.csv` contains a line-by-line reconciliation for FY2025 Q4: 10-K full-year value, Q3 YTD value, derived Q4 value, and whether they reconcile. All duration-metric derivations are arithmetically correct. No standalone Q4 values exist in XBRL to cross-check against.

## Important accounting logic

1. **Qualcomm does not file a separate Q4 10-Q.** The annual 10-K contains full-year totals but no standalone Q4 breakdown.

2. **Q4 duration metrics are derived:** Q4 = full-year 10-K value minus 9-month YTD from the Q3 10-Q filing. This applies to Revenue, Cost of Revenue, Operating Income, Net Income, R&D Expense, Operating Cash Flow, and Capital Expenditure.

3. **Q4 balance-sheet values use the fiscal-year-end snapshot** from the 10-K directly. Cash and Total Debt Q4 values are not derived by subtraction.

4. **EPS must not be derived by subtraction.** Diluted share counts change across quarters, making YTD subtraction invalid. Q4 EPS is flagged `missing_requires_review`.

5. **Prior-year comparison data must be filtered out.** SEC XBRL tags prior-year comparison figures with the same `fy` as the filing year. The cleaning script anchors on the FY entry with the latest end date and only accepts entries whose dates are consistent with that fiscal year.

6. **Cash-flow metrics only have cumulative YTD entries** for Q2 and Q3 in SEC XBRL. Standalone Q2 and Q3 must be derived by YTD subtraction.

7. **Reported and derived values are visibly distinguished** via the `extraction_method` column (`reported_standalone`, `derived_ytd_difference`, `fiscal_year_end_balance`, `missing_requires_review`) and yellow/pink shading in Excel.

## Existing scripts

### src/fetch_sec_data.py
- **Purpose:** Download Qualcomm's company-facts JSON from SEC EDGAR
- **Inputs:** `.env` (SEC_USER_AGENT)
- **Outputs:** `data/raw/qualcomm_CIK0000804328_<date>.json`
- **Notes:** Skips download if today's file already exists

### src/clean_financials.py
- **Purpose:** Extract and structure quarterly financial data with Q4 derivation
- **Inputs:** Latest file in `data/raw/qualcomm_CIK*.json`
- **Outputs:** `data/processed/qualcomm_financials_<date>.csv`, `data/manual_checks/qualcomm_missing_metrics_<date>.csv`
- **Notes:** 132 rows (11 metrics x 12 quarters across FY2023–FY2025)

### src/export_excel.py
- **Purpose:** Generate analyst-ready Excel workbook with 5 tabs
- **Inputs:** Latest files in `data/processed/qualcomm_financials_*.csv` and `data/manual_checks/qualcomm_missing_metrics_*.csv`
- **Outputs:** `output/qualcomm_financial_history.xlsx`

### src/calculate_metrics.py
- **Purpose:** Calculate financial ratios, margins, FCF, TTM aggregates
- **Inputs:** Latest file in `data/processed/qualcomm_financials_*.csv`
- **Outputs:** `data/processed/qualcomm_metrics.csv`, adds "Calculated Metrics" tab to `output/qualcomm_financial_history.xlsx`
- **Notes:** 120 rows (10 metrics x 12 quarters; 107 calculated, 13 missing due to insufficient prior-year data)

## Existing data files

### data/raw/
- `qualcomm_CIK0000804328_2026-06-04.json` (8.4 MB) — untouched SEC EDGAR response

### data/processed/
- `qualcomm_financials_2026-06-04.csv` (29 KB) — 132 rows, 11 base metrics, FY2023–FY2025
- `qualcomm_metrics.csv` (14 KB) — 120 rows, 10 calculated metrics

### data/manual_checks/
- `qualcomm_missing_metrics_2026-06-04.csv` — 3 items (Diluted EPS Q4 for each fiscal year)
- `qualcomm_q4_validation.csv` — FY2025 Q4 reconciliation checklist (7 metrics)

### output/
- `qualcomm_financial_history.xlsx` (20 KB) — 6-tab workbook (Quarterly Financials, Calculated Metrics, Detail View, Missing Metrics, Data Dictionary, Manual Checks)
- `q4_logic_audit.csv` (30 KB) — pre-fix audit of the old extraction logic (historical reference)

### archive/pre_q4_fix/
- Backup of scripts and outputs from before the Q4 derivation rewrite. Safe to delete once Stage 9 is stable.

## Validation status

### Completed
- FY2025 Q4 arithmetic reconciliation (all duration metrics sum to FY total)
- Balance-sheet Q4 values match 10-K fiscal-year-end snapshots
- Cash-flow YTD subtraction logic verified for FY2023–FY2025
- Prior-year comparison filtering verified (no cross-contamination of fiscal years)
- All calculated ratios produce reasonable values consistent with Qualcomm's public financials

### Flagged for manual review
- **Diluted EPS Q4** (3 instances) — cannot be derived; needs earnings press release
- **FY2025 Q4 Net Income = -$3.1B** — arithmetic is correct (FY $5.5B minus 9M $8.7B) but the large Q4 loss likely reflects a one-time charge; verify against 10-K notes
- **Capital Expenditure tag** — uses `PaymentsToAcquireProductiveAssets` which is broader than the typical `PaymentsToAcquirePropertyPlantAndEquipment`; Qualcomm doesn't file the narrower tag

### Known limitations
- Only 3 fiscal years of data (FY2023–FY2025); YoY growth and TTM metrics are unavailable for FY2023 Q1–Q3
- No Q4 standalone cross-check source in XBRL; earnings press releases would provide independent verification but are not in the SEC API
- Qualcomm's fiscal year ends in late September, not December; calendar-quarter comparisons with peers will require date alignment

## Stage 9 objective

Generalize the tested Qualcomm pipeline into a configurable multi-company system covering five semiconductor companies:

| Company | Ticker | CIK |
|---------|--------|-----|
| Qualcomm | QCOM | 0000804328 |
| Broadcom | AVGO | TBD — look up |
| AMD | AMD | TBD — look up |
| Nvidia | NVDA | TBD — look up |
| Intel | INTC | TBD — look up |

Key considerations for Stage 9:
- Each company may use different XBRL tags for the same concept (e.g., different revenue or capex tags)
- Fiscal year-end dates vary (Broadcom ends in October, others in December or January)
- The Q4 derivation logic applies to any company that does not file a standalone Q4 10-Q
- The existing Qualcomm output must be preserved as a regression benchmark — any refactored pipeline should produce identical Qualcomm results

## Non-negotiable rules

1. **Preserve raw source data unchanged.** Never modify files in `data/raw/`.
2. **Do not silently fill missing values.** Flag them with `missing_requires_review`.
3. **Maintain source references.** Every extracted value must carry an SEC filing URL.
4. **Distinguish reported, derived, and manually reviewed values** via the `extraction_method` column.
5. **Explain proposed changes before editing files.** The user is learning and needs to understand what will change and why.
6. **Run validation checks after refactoring.** Verify that Qualcomm output is unchanged before adding new companies.
7. **Preserve the working Qualcomm output as a regression benchmark.** Save current outputs before making structural changes.
