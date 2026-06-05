# Project Status — Semiconductor Research Terminal

Last updated: 2026-06-05 (all five pipelines complete — checkpoint)

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
| 9A | Multi-company refactor — config system, parameterized scripts, regression testing | Done |
| 9B | AMD pipeline — tag discovery, cleaning, metrics, Excel export, validation | Done |
| 9C | Nvidia pipeline — tag discovery, cleaning, metrics, Excel export, validation | Done |
| 9D | Intel pipeline — tag discovery, cleaning, metrics, Excel export, validation | Done |
| 9E | Broadcom pipeline — tag discovery, cleaning, metrics, Excel export, validation | Done |
| 9F | Bug fix — classify_entries() standalone Q2/Q3 selection used latest end date instead of latest filing date | Done |
| 10 | Five-company peer comparison model — consolidated CSV, 9-tab Excel workbook | Done |

## Stage 9 architecture

### Configuration system

All scripts read company metadata from `config/companies.csv` and XBRL tag definitions from `config/xbrl_tags/<short_id>.json`. Each script accepts a ticker argument:

```
.venv/bin/python src/fetch_sec_data.py QCOM
.venv/bin/python src/clean_financials.py AMD
.venv/bin/python src/export_excel.py NVDA
.venv/bin/python src/calculate_metrics.py QCOM
```

A `--test` flag writes output to `data/test_outputs/` and `output/test_outputs/` instead of production directories.

### Company registry

| Company | Ticker | CIK | Short ID | FY-End Month | FY-End Day (approx) | Status |
|---------|--------|-----|----------|--------------|---------------------|--------|
| Qualcomm Incorporated | QCOM | 0000804328 | qualcomm | 9 | 29 | Complete, regression-tested |
| Advanced Micro Devices Inc. | AMD | 0000002488 | amd | 12 | 28 | Complete |
| Nvidia Corp. | NVDA | 0001045810 | nvidia | 1 | 26 | Complete |
| Intel Corp. | INTC | 0000050863 | intel | 12 | 28 | Complete |
| Broadcom Inc. | AVGO | 0001730168 | broadcom | 11 | 3 | Complete |

### Scripts (6 files in `src/`)

| Script | Purpose |
|--------|---------|
| `src/config_loader.py` | Shared utility — reads company config, XBRL tag maps, parses ticker args, builds SEC filing URLs |
| `src/fetch_sec_data.py` | Downloads a company's company-facts JSON from SEC EDGAR |
| `src/clean_financials.py` | Extracts and structures quarterly financial data with Q4 derivation |
| `src/export_excel.py` | Generates analyst-ready multi-tab Excel workbook |
| `src/calculate_metrics.py` | Calculates financial ratios, margins, FCF, TTM aggregates |
| `src/regression_check.py` | Compares test outputs against immutable Qualcomm benchmarks |
| `src/build_peer_comparison.py` | Consolidates five-company data into peer comparison CSV and 9-tab Excel workbook |

### Tag-map files

| File | Notes |
|------|-------|
| `config/xbrl_tags/qualcomm.json` | Uses `Revenues`, `CostOfRevenue`, `PaymentsToAcquireProductiveAssets`; Total Debt = `LongTermDebt` + `DebtCurrent` (instant_sum) |
| `config/xbrl_tags/amd.json` | Uses `RevenueFromContractWithCustomerExcludingAssessedTax`, `CostOfGoodsAndServicesSold`, `PaymentsToAcquirePropertyPlantAndEquipment`; Total Debt = `DebtLongtermAndShorttermCombinedAmount` (single instant) |
| `config/xbrl_tags/nvidia.json` | Uses `Revenues`, `CostOfRevenue`, `PaymentsToAcquireProductiveAssets`; Total Debt = `LongTermDebt` (single instant, includes noncurrent + current portion) |
| `config/xbrl_tags/intel.json` | Uses `RevenueFromContractWithCustomerExcludingAssessedTax`, `CostOfGoodsAndServicesSold`, `PaymentsToAcquirePropertyPlantAndEquipment`; Cash = `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` (includes restricted cash); Total Debt = `LongTermDebtNoncurrent` + `DebtCurrent` (instant_sum) |
| `config/xbrl_tags/broadcom.json` | Uses `RevenueFromContractWithCustomerExcludingAssessedTax`, `CostOfRevenue`, `PaymentsToAcquirePropertyPlantAndEquipment`; Net Income = `ProfitLoss` (NCI=0; `NetIncomeLoss` has FY-only data); Total Debt = `DebtInstrumentCarryingAmount` (gross principal, ~$2B above carrying value) |

## Qualcomm pipeline

### Refactor and regression test

The original Qualcomm-only scripts were refactored into the multi-company architecture. Immutable benchmark copies of the validated Qualcomm output are stored in `data/benchmarks/qualcomm/` and `output/benchmarks/qualcomm/`. The regression checker (`src/regression_check.py`) confirmed that the refactored pipeline produces **identical** output:

- Financials CSV: 132 rows match
- Missing Metrics CSV: 3 rows match
- Calculated Metrics CSV: 120 rows match

### Data summary

- **Raw:** `data/raw/qualcomm_CIK0000804328_2026-06-04.json` (8.4 MB)
- **Processed:** `data/processed/qualcomm_financials_2026-06-04.csv` (132 rows, 11 metrics, FY2023–FY2025)
- **Metrics:** `data/processed/qualcomm_metrics.csv` (120 rows; 107 calculated, 13 missing)
- **Workbook:** `output/qualcomm_financial_history.xlsx` (6 tabs)
- **Flagged:** 3 items (Diluted EPS Q4 × 3)

### Qualcomm-specific notes

- Fiscal year ends last Sunday of September (~Sep 29)
- FY2025 Q4 Net Income = −$3.1B — arithmetic correct but likely one-time charge
- CapEx uses broader `PaymentsToAcquireProductiveAssets` tag (Qualcomm does not file the narrower PP&E tag)
- Total Debt = `LongTermDebt` + `DebtCurrent` (instant_sum approach)

## AMD pipeline

### Data summary

- **Raw:** `data/raw/amd_CIK0000002488_2026-06-04.json` (4.0 MB)
- **Processed:** `data/processed/amd_financials_2026-06-04.csv` (132 rows, 11 metrics, FY2023–FY2025)
- **Metrics:** `data/processed/amd_metrics.csv` (120 rows; 106 calculated, 14 missing)
- **Workbook:** `output/amd_financial_history.xlsx` (6 tabs)
- **Validation:** `data/manual_checks/amd_validation_checklist.csv` (20 checks)
- **Flagged:** 4 items

### AMD validation results

- All 24 FY total reconciliations pass (8 duration metrics × 3 fiscal years)
- Derived Gross Profit matches reported `GrossProfit` XBRL tag exactly for all 3 FYs
- Total Debt cross-check: `DebtLongtermAndShorttermCombinedAmount` matches `LongTermDebtNoncurrent` + `LongTermDebtCurrent` sum

### AMD manual-review items

1. **Total Debt FY2023 Q1** — `DebtLongtermAndShorttermCombinedAmount` has no Q1 entry for fy=2023 (tag coverage begins Q2 FY2023, after Xilinx acquisition accounting settled)
2. **Diluted EPS Q4** (×3) — cannot derive by subtraction
3. **Gross Profit cross-check** — AMD reports `GrossProfit` directly; derived values match exactly but should be re-verified if tag map changes

### AMD-specific notes

- Fiscal year ends last Saturday of December (~Dec 28); 52/53-week calendar (FY2022 was 370 days)
- Uses ASC 606 revenue tag (`RevenueFromContractWithCustomerExcludingAssessedTax`)
- Uses narrower PP&E CapEx tag (`PaymentsToAcquirePropertyPlantAndEquipment`)
- Total Debt uses single combined tag (not a sum of components)

## Nvidia pipeline

### Data summary

- **Raw:** `data/raw/nvidia_CIK0001045810_2026-06-05.json`
- **Processed:** `data/processed/nvidia_financials_2026-06-05.csv` (132 rows, 11 metrics, FY2024–FY2026)
- **Metrics:** `data/processed/nvidia_metrics.csv` (120 rows; 98 calculated, 22 missing)
- **Workbook:** `output/nvidia_financial_history.xlsx` (6 tabs)
- **Validation:** `data/manual_checks/nvidia_validation_checklist.csv` (23 checks)
- **Flagged:** 3 items (Diluted EPS Q4 × 3) + 3 pending manual confirmation (CapEx FY2024 Q1–Q3 from earnings releases)

### Nvidia validation results

- Revenue: all 3 FY totals reconcile exactly
- Capital Expenditure FY2024: all 4 quarters now present. Q1–Q3 sourced from earnings press releases (8-K filings); Q4 derived from XBRL. Quarterly sum ($1,069M) matches FY total exactly. Pending manual confirmation of press-release source.
- 5 metrics have $1M rounding gaps between quarterly sums and FY totals (Cost of Revenue FY2025, Operating Income FY2024/FY2025, Net Income FY2024, R&D FY2024). These are XBRL data artifacts, not pipeline errors. A validation tolerance rule (absolute difference ≤ $1,000,000) is applied; these cases are labeled `validation_status = rounding_tolerance` and are not treated as extraction failures.
- Derived Gross Profit matches reported `GrossProfit` tag (FY2024 exact, FY2025 ±$1M within rounding tolerance, FY2026 exact)
- Total Debt cross-check: `LongTermDebt` $8,468M = `LongTermDebtNoncurrent` $7,469M + `LongTermDebtCurrent` $999M for FY2026

### Nvidia manual-review items

1. **Capital Expenditure FY2024 Q1–Q3 (pending confirmation)** — XBRL tag `PaymentsToAcquireProductiveAssets` has no Q1/Q2 YTD entries for fy=2024. Values sourced from Nvidia quarterly earnings press releases (8-K filings): Q1=$248M (2023-05-24), Q2=$289M (2023-08-23), Q3=$278M (2023-11-21). Line item: "Purchase related to property and equipment and intangible assets". Cross-validates: Q1+Q2+Q3=$815M = XBRL YTD_Q3; full FY=$1,069M. Marked `extraction_method=reported_earnings_release`, `requires_manual_review=Yes`. After user confirms, set `requires_manual_review` to empty/No. Then rerun `calculate_metrics.py NVDA` and `export_excel.py NVDA` to recalculate FCF and TTM FCF.
2. **Diluted EPS Q4** (×3) — cannot derive by subtraction
3. **$1M rounding gaps** (×5) — documented in validation checklist with `validation_status=rounding_tolerance`. Tolerance rule: |quarterly_sum − FY_total| ≤ $1,000,000. Not extraction failures.
4. **CapEx tag scope** — `PaymentsToAcquireProductiveAssets` is broader than PP&E; `PaymentsToAcquirePropertyPlantAndEquipment` has no data after FY2012

### Nvidia-specific notes

- Fiscal year ends last Sunday of **January** (~Jan 26); FY numbering is offset +1 from calendar year (FY2026 = Feb 2025 – Jan 2026)
- Uses same Revenue, CostOfRevenue, and CapEx tags as Qualcomm
- Total Debt uses `LongTermDebt` as a single instant tag (includes both noncurrent and current portion)
- Revenue scale is dramatically larger ($216B FY2026) — this does not affect extraction logic but matters for peer comparison

## Intel pipeline

### Data summary

- **Raw:** `data/raw/intel_CIK0000050863_2026-06-05.json` (4.5 MB)
- **Processed:** `data/processed/intel_financials_2026-06-05.csv` (132 rows, 11 metrics, FY2023–FY2025)
- **Metrics:** `data/processed/intel_metrics.csv` (120 rows; 105 calculated, 15 missing)
- **Workbook:** `output/intel_financial_history.xlsx` (6 tabs)
- **Validation:** `data/manual_checks/intel_validation_checklist.csv` (36 checks)
- **Flagged:** 5 items (Diluted EPS Q4 × 3, Cash FY2025 Q2/Q3 × 2)

### Intel validation results

- All 24 FY total reconciliations pass with zero rounding gaps (8 duration metrics × 3 FYs)
- Derived Gross Profit matches reported `GrossProfit` XBRL tag exactly for all 3 FYs
- Total Debt cross-check: `LongTermDebtNoncurrent` + `DebtCurrent` = `LongTermDebt` for all 3 FY year-ends

### Intel manual-review items

1. **Cash tag includes restricted cash** — Intel uses `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` instead of `CashAndCashEquivalentsAtCarryingValue`. FY2025 year-end: broader tag $14,712M vs narrow tag $14,265M (difference $447M / 3% restricted cash). The narrow tag has no data for FY2023/FY2024 (Intel stopped reporting it ~FY2019, resumed Q2 FY2025). Broader tag chosen for coverage (10 of 12 quarters vs 3 of 12). Inconsistent with the other 3 companies for peer comparison.
2. **Cash FY2025 Q2/Q3 missing** — broader cash tag has no Q2/Q3 entries for FY2025 (Intel switched back to narrow tag mid-year). Could be sourced from earnings press releases.
3. **Diluted EPS Q4** (×3) — cannot derive by subtraction
4. **Total Debt includes commercial paper** during interim quarters when Intel has CP outstanding (e.g., Q2 FY2025: $2,000M CP included in DebtCurrent)
5. **Operating Income and Net Income include large non-recurring charges** — FY2024 Q3 Net Income = −$16,639M (goodwill/intangible impairments). FY2024 full-year Operating Income = −$11,678M (restructuring). Direct comparison to prior periods or peers is misleading without non-GAAP adjustments.

### Intel-specific notes

- Fiscal year ends last Saturday of **December** (~Dec 28); 52/53-week calendar (FY2022 was 370 days). Same calendar structure as AMD.
- Intel is an IDM (integrated device manufacturer) — operates its own fabs, unlike fabless QCOM/AMD/NVDA. This creates dramatically higher CapEx ($14–26B/year vs $1–6B for peers) and structurally negative FCF.
- Uses ASC 606 revenue tag (same as AMD); `SalesRevenueNet` discontinued after ~FY2017
- Uses narrower PP&E CapEx tag (same as AMD); `PaymentsToAcquireProductiveAssets` not available
- Gross margin (28–46%) and FCF margin (deeply negative) are structurally different from fabless peers due to manufacturing overhead

## Broadcom pipeline

### Data summary

- **Raw:** `data/raw/broadcom_CIK0001730168_2026-06-05.json`
- **Processed:** `data/processed/broadcom_financials_2026-06-05.csv` (132 rows, 11 metrics, FY2023–FY2025)
- **Metrics:** `data/processed/broadcom_metrics.csv` (120 rows; 107 calculated, 13 missing)
- **Workbook:** `output/broadcom_financial_history.xlsx` (6 tabs)
- **Validation:** `data/manual_checks/broadcom_validation_checklist.csv` (40 checks)
- **Flagged:** 3 items (Diluted EPS Q4 × 3)

### Broadcom validation results

- All 21 FY total reconciliations pass with zero rounding gaps (7 duration metrics × 3 FYs)
- Derived Gross Profit matches reported `GrossProfit` XBRL tag exactly for all 3 FYs
- Total Debt cross-check: `DebtInstrumentCarryingAmount` $67,120M = `DebtLongtermAndShorttermCombinedAmount` $67,120M for FY2024/FY2025; FY2023 combined tag not available (pre-VMware)
- Total Debt components at FY2025 year-end: `LongTermDebtNoncurrent` $61,984M + `LongTermDebtCurrent` $3,152M = $65,136M (net carrying value); pipeline uses gross principal $67,120M (difference = ~$1,984M unamortized discounts)
- Q4 derivation verified for Revenue, Operating Income, Operating Cash Flow, Capital Expenditure
- FY-end cash balance ($16,178M) matches 10-K snapshot exactly
- Revenue confirmed consolidated (no segment-dimension tags; ASC 606)
- CapEx all positive (outflow convention); FCF = OCF − CapEx
- Qualcomm regression passes; AMD/NVDA/INTC output unchanged after classify_entries() fix

### Broadcom manual-review items

1. **Diluted EPS Q4** (×3) — cannot derive by subtraction
2. **Net Income uses `ProfitLoss` tag** — `NetIncomeLoss` has FY-only data in XBRL. Noncontrolling interest is $0 for all recent periods, so ProfitLoss = NetIncomeLoss. FY totals verified identical. First company to require this tag.
3. **Total Debt is gross principal** — `DebtInstrumentCarryingAmount` ($67.1B) is ~$2B higher than carrying value ($65.1B) due to unamortized discounts/issuance costs. Inconsistent with other 4 companies for peer comparison.
4. **FY2024 is 53-week VMware transition year** — 370 days (Q1 = 97 days). Revenue jumped $35.8B → $51.6B (+44%), roughly half from VMware. Cost of Revenue nearly doubled. Operating margin compressed from 45% to 26% due to acquired intangible amortization (~$8–10B/year). Direct YoY or peer comparison is misleading.
5. **Net Income Q3 FY2024 = −$1,875M** — VMware integration charges, acquired intangible amortization, and restructuring. Full-year FY2024 Net Income $5.9B vs FY2023 $14.1B and FY2025 $23.1B.
6. **Pre-VMware FY ended late October; post-VMware shifted to early November** — FY2023 ends 2023-10-29, FY2024 ends 2024-11-03, FY2025 ends 2025-11-02.

### Broadcom-specific notes

- Fiscal year ends first Sunday of November (~Nov 3); 52/53-week calendar
- FY2024 was 53 weeks (370 days) due to VMware acquisition transition; all other recent FYs are 363 days
- Broadcom is fabless (like QCOM/AMD/NVDA) — CapEx $452–623M/year, comparable to fabless peers, unlike Intel IDM
- Uses ASC 606 revenue tag and `CostOfRevenue` (not `CostOfGoodsAndServicesSold`)
- Total Debt ~$67B driven by VMware acquisition financing; being gradually deleveraged
- Revenue mix shifted from primarily semiconductors to ~50/50 semiconductors + infrastructure software post-VMware

### Bug fix: classify_entries() standalone Q2/Q3 selection

Discovered during Broadcom validation. The `ProfitLoss` XBRL tag has prior-period comparison entries that SEC re-tags with the current filing's `fp` label (e.g., Q1 data re-reported in the Q3 10-Q as `fp=Q3`). The old code selected the most recently **filed** entry, which picked the re-reported Q1 data. Fix: select by latest **end date** first (actual quarter data always has a later end date than re-reported prior-period data), with filing date as tiebreaker. Qualcomm regression passes. AMD/NVDA/INTC output identical.

## Important accounting rules

1. **Do not assume calendar quarters.** Each company has a different fiscal year-end (Sep for Qualcomm, Dec for AMD/Intel, Jan for Nvidia, Nov for Broadcom). The pipeline uses SEC `fy`/`fp` fields and date-range filters (340–400 days for FY, 60–115 for standalone quarter, etc.) rather than calendar-date matching.

2. **Q4 duration metrics are derived:** Q4 = full-year 10-K value minus 9-month YTD from the Q3 10-Q. None of the companies processed so far file a standalone Q4 10-Q.

3. **Q4 balance-sheet values use the fiscal-year-end snapshot** from the 10-K directly. Not derived by subtraction.

4. **EPS must not be derived by subtraction.** Diluted share counts change across quarters. Q4 EPS is always flagged `missing_requires_review`.

5. **Prior-year comparison data must be filtered out.** The cleaning script anchors on the FY entry with the latest end date and rejects entries inconsistent with that anchor.

6. **Cash-flow metrics only have cumulative YTD entries** for Q2/Q3. Standalone Q2/Q3 must be derived by YTD subtraction.

7. **Reported and derived values are visibly distinguished** via `extraction_method` labels and yellow/pink shading in Excel.

8. **Each company may use different XBRL tags** for the same financial concept. Tag selections are documented in `config/xbrl_tags/<short_id>.json` with explanations in the validation checklists.

## Existing data files

### data/raw/
- `qualcomm_CIK0000804328_2026-06-04.json` (8.4 MB)
- `amd_CIK0000002488_2026-06-04.json` (4.0 MB)
- `nvidia_CIK0001045810_2026-06-05.json`
- `intel_CIK0000050863_2026-06-05.json` (4.5 MB)
- `broadcom_CIK0001730168_2026-06-05.json`

### data/processed/
- `qualcomm_financials_2026-06-04.csv` — 132 rows, FY2023–FY2025
- `qualcomm_metrics.csv` — 120 rows
- `amd_financials_2026-06-04.csv` — 132 rows, FY2023–FY2025
- `amd_metrics.csv` — 120 rows
- `nvidia_financials_2026-06-05.csv` — 132 rows, FY2024–FY2026
- `nvidia_metrics.csv` — 120 rows
- `intel_financials_2026-06-05.csv` — 132 rows, FY2023–FY2025
- `intel_metrics.csv` — 120 rows
- `broadcom_financials_2026-06-05.csv` — 132 rows, FY2023–FY2025
- `broadcom_metrics.csv` — 120 rows
- `semiconductor_peer_metrics.csv` — 1,260 rows, consolidated five-company peer data

### data/manual_checks/
- `qualcomm_missing_metrics_2026-06-04.csv` — 3 flagged items
- `qualcomm_q4_validation.csv` — FY2025 Q4 reconciliation
- `amd_missing_metrics_2026-06-04.csv` — 4 flagged items
- `amd_validation_checklist.csv` — 20 checks
- `nvidia_missing_metrics_2026-06-05.csv` — 3 flagged items (Diluted EPS Q4 × 3)
- `nvidia_validation_checklist.csv` — 23 checks (includes rounding tolerance rule and CapEx FY reconciliation)
- `intel_missing_metrics_2026-06-05.csv` — 5 flagged items (EPS Q4 × 3, Cash Q2/Q3 × 2)
- `intel_validation_checklist.csv` — 36 checks
- `broadcom_missing_metrics_2026-06-05.csv` — 3 flagged items (Diluted EPS Q4 × 3)
- `broadcom_validation_checklist.csv` — 40 checks

### data/benchmarks/qualcomm/
- Immutable copies of validated Qualcomm output (financials CSV, missing-metrics CSV, metrics CSV). Used by `src/regression_check.py`. Do not modify.

### output/
- `qualcomm_financial_history.xlsx` — 6-tab workbook
- `amd_financial_history.xlsx` — 6-tab workbook
- `nvidia_financial_history.xlsx` — 6-tab workbook
- `intel_financial_history.xlsx` — 6-tab workbook
- `broadcom_financial_history.xlsx` — 6-tab workbook
- `semiconductor_peer_comparison.xlsx` — 9-tab peer comparison workbook
- `q4_logic_audit.csv` — historical reference from Stage 5

### output/benchmarks/qualcomm/
- Immutable copy of validated Qualcomm workbook. Do not modify.

### config/
- `companies.csv` — company metadata (name, ticker, CIK, short_id, FY-end month/day)
- `xbrl_tags/qualcomm.json` — Qualcomm XBRL tag map
- `xbrl_tags/amd.json` — AMD XBRL tag map
- `xbrl_tags/nvidia.json` — Nvidia XBRL tag map
- `xbrl_tags/intel.json` — Intel XBRL tag map
- `xbrl_tags/broadcom.json` — Broadcom XBRL tag map

### archive/pre_q4_fix/
- Backup of pre-Stage-7 scripts and outputs. Safe to delete once Stage 9 is stable.

## Stage 10: Five-company peer comparison model

### What was built

`src/build_peer_comparison.py` reads the 10 validated company-level CSVs (5 financials + 5 metrics) and produces:

- **`data/processed/semiconductor_peer_metrics.csv`** — 1,260 rows, consolidated long-format file with all five companies' financials and calculated metrics. Columns: company, ticker, fiscal_year, fiscal_quarter, metric_name, value, unit, extraction_method, source_reference, derived_from, requires_manual_review, formula.
- **`output/semiconductor_peer_comparison.xlsx`** — 9-tab workbook:
  1. **Peer Summary** — latest-quarter snapshot + TTM for each company, with business-model annotations and comparability notes
  2. **Quarterly Trends** — all 21 metrics × all quarters × all companies in long format
  3. **Revenue Growth** — quarterly revenue, YoY growth, TTM revenue (companies as columns)
  4. **Margins** — gross margin, operating margin, FCF margin
  5. **R&D Intensity** — R&D expense and R&D as % of revenue
  6. **Balance Sheet** — cash, total debt, net cash/debt
  7. **Validation** — missing values, manual-review flags, derived-value counts, company-specific limitations, cross-company comparability warnings
  8. **Data Dictionary** — metric definitions, formulas, extraction-method label explanations
  9. **Source Audit Trail** — 660 rows, every extracted financial metric with SEC filing URL, extraction method, derived-from, and review status

### Design decisions

- No values were imputed. Missing values display as "N/A" with pink shading.
- Derived values (Q4 YTD subtraction, FY-end balance sheet) are shaded yellow.
- Manual-review items (Nvidia CapEx 8-K sourced) are shaded amber.
- Each company keeps its own fiscal quarters — no calendar-quarter alignment yet.
- Company-level output files were verified unchanged (zero git diff).
- Business-model annotations identify: Qualcomm's licensing exposure, Intel's IDM/fab intensity, Broadcom's software revenue mix, Nvidia's scale and FY offset.

### Summary statistics

| Ticker | Financials rows | Metrics rows | Latest quarter | Missing values | Manual review flags |
|--------|----------------|-------------|----------------|----------------|---------------------|
| QCOM | 132 | 120 | FY2025 Q4 | 16 | 0 |
| AMD | 132 | 120 | FY2025 Q4 | 18 | 0 |
| NVDA | 132 | 120 | FY2026 Q4 | 25 | 3 |
| INTC | 132 | 120 | FY2025 Q4 | 20 | 0 |
| AVGO | 132 | 120 | FY2025 Q4 | 16 | 0 |

### Next potential steps

1. Calendar-quarter alignment for cross-company comparison (different FY-end dates)
2. Non-GAAP adjustments for Intel (impairments) and Broadcom (VMware amortization)
3. Charts and visual dashboards
4. Resolve remaining manual-review items (EPS Q4, Intel Cash Q2/Q3, Nvidia CapEx confirmation)

## Unresolved issues

1. **Nvidia CapEx FY2024 Q1–Q3 (RESOLVED, pending manual confirmation)** — Values sourced from Nvidia quarterly earnings press releases (8-K filings): Q1=$248M, Q2=$289M, Q3=$278M. Cross-validates against XBRL YTD and FY totals. Marked `requires_manual_review=Yes` until user confirms. After confirmation, rerun `calculate_metrics.py NVDA` and `export_excel.py NVDA` to fill in FCF and TTM FCF for FY2024.

2. **Nvidia $1M rounding gaps (RESOLVED)** — Five instances documented with `validation_status=rounding_tolerance`. Tolerance rule applied: |difference| ≤ $1,000,000. Not treated as extraction failures. No further action needed.

3. **AMD Total Debt FY2023 Q1 missing** — `DebtLongtermAndShorttermCombinedAmount` tag coverage begins Q2 FY2023. Could be manually sourced from the FY2023 Q1 10-Q filing.

4. **Diluted EPS Q4** — Missing for all five companies (15 instances total). Cannot be derived from XBRL data. Requires earnings press releases as an independent source.

5. **Qualcomm FY2025 Q4 Net Income = −$3.1B** — Arithmetic is correct but the large Q4 loss likely reflects a one-time charge. Not verified against 10-K notes.

6. **Cross-company peer comparison** — Fiscal year-end dates differ significantly (Sep, Dec, Jan, Nov). Direct FY-label comparison is misleading. Calendar-quarter alignment is not yet implemented.

7. **Broadcom fiscal year-end (RESOLVED)** — Post-VMware, FY shifted from late October (~Oct 29) to early November (~Nov 3). FY2024 was 53 weeks (370 days). Config uses month=11, day=3. Pipeline handles the shift correctly via date-range filtering.

8. **Intel cash tag includes restricted cash** — `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` used instead of `CashAndCashEquivalentsAtCarryingValue` (other 3 companies). Difference ~$447M / 3% for FY2025. Inconsistent for peer comparison.

9. **Intel Cash FY2025 Q2/Q3 missing** — broader cash tag has no Q2/Q3 entries for FY2025. Could be sourced from earnings press releases.

10. **Intel Operating Income / Net Income include large non-recurring charges** — FY2024 includes ~$15.9B goodwill/intangible impairments and restructuring charges. Direct comparison to peers misleading without non-GAAP adjustments.

11. **Intel CapEx is structurally different from fabless peers** — As an IDM, Intel's CapEx ($14–26B/year) is 10–20× larger than QCOM/AMD/NVDA. FCF is structurally negative. Peer CapEx and FCF comparison requires business-model adjustment.

12. **Broadcom Net Income uses `ProfitLoss` tag** — `NetIncomeLoss` has FY-only data. NCI is zero so values are identical, but this is the only company using this tag. If Broadcom ever has noncontrolling interest, `ProfitLoss` would overstate parent-attributable net income.

13. **Broadcom Total Debt is gross principal** — `DebtInstrumentCarryingAmount` ($67.1B) is ~$2B higher than net carrying value ($65.1B) due to unamortized discounts/issuance costs. Other 4 companies use carrying-value tags. Inconsistent for peer Total Debt comparison (~3% overstatement).

14. **Broadcom FY2024 VMware comparability** — 53-week year, ~$16B VMware revenue contribution, ~$8–10B acquired intangible amortization depressing operating/net income. FY2024 metrics are not directly comparable to FY2023 (pre-VMware) or to peers. Non-GAAP adjustments not yet implemented.

15. **classify_entries() fix applied (RESOLVED)** — Standalone Q2/Q3 selection changed from latest filing date to latest end date to prevent prior-period comparison data from being selected. Qualcomm regression passes. All 4 prior companies output unchanged.

## Non-negotiable rules

1. **Preserve raw source data unchanged.** Never modify files in `data/raw/`.
2. **Do not silently fill missing values.** Flag them with `missing_requires_review`.
3. **Maintain source references.** Every extracted value must carry an SEC filing URL.
4. **Distinguish reported, derived, and manually reviewed values** via the `extraction_method` column.
5. **Explain proposed changes before editing files.** The user is learning and needs to understand what will change and why.
6. **Run validation checks after refactoring.** Verify that prior company outputs are unchanged before adding new companies.
7. **Preserve the working Qualcomm output as a regression benchmark.** Immutable copies in `data/benchmarks/qualcomm/`.
8. **Use company-specific fiscal calendars.** Do not assume calendar quarters or December year-ends.
