# Project Status — Semiconductor Research Terminal

Last updated: 2026-06-05

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
| Intel Corp. | INTC | 0000050863 | intel | 12 | 28 | Not started |
| Broadcom Inc. | AVGO | 0001730168 | broadcom | 11 | 3 | Not started |

### Scripts (6 files in `src/`)

| Script | Purpose |
|--------|---------|
| `src/config_loader.py` | Shared utility — reads company config, XBRL tag maps, parses ticker args, builds SEC filing URLs |
| `src/fetch_sec_data.py` | Downloads a company's company-facts JSON from SEC EDGAR |
| `src/clean_financials.py` | Extracts and structures quarterly financial data with Q4 derivation |
| `src/export_excel.py` | Generates analyst-ready multi-tab Excel workbook |
| `src/calculate_metrics.py` | Calculates financial ratios, margins, FCF, TTM aggregates |
| `src/regression_check.py` | Compares test outputs against immutable Qualcomm benchmarks |

### Tag-map files

| File | Notes |
|------|-------|
| `config/xbrl_tags/qualcomm.json` | Uses `Revenues`, `CostOfRevenue`, `PaymentsToAcquireProductiveAssets`; Total Debt = `LongTermDebt` + `DebtCurrent` (instant_sum) |
| `config/xbrl_tags/amd.json` | Uses `RevenueFromContractWithCustomerExcludingAssessedTax`, `CostOfGoodsAndServicesSold`, `PaymentsToAcquirePropertyPlantAndEquipment`; Total Debt = `DebtLongtermAndShorttermCombinedAmount` (single instant) |
| `config/xbrl_tags/nvidia.json` | Uses `Revenues`, `CostOfRevenue`, `PaymentsToAcquireProductiveAssets`; Total Debt = `LongTermDebt` (single instant, includes noncurrent + current portion) |

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
- **Validation:** `data/manual_checks/nvidia_validation_checklist.csv` (22 checks)
- **Flagged:** 6 items

### Nvidia validation results

- Revenue: all 3 FY totals reconcile exactly
- 5 metrics have $1M rounding gaps between quarterly sums and FY totals (Cost of Revenue FY2025, Operating Income FY2024/FY2025, Net Income FY2024, R&D FY2024). These are XBRL data artifacts — standalone quarterly values and cumulative YTD values differ by $1M in the filed data. Not pipeline errors.
- Derived Gross Profit matches reported `GrossProfit` tag (FY2024 exact, FY2025 ±$1M from same rounding, FY2026 exact)
- Total Debt cross-check: `LongTermDebt` $8,468M = `LongTermDebtNoncurrent` $7,469M + `LongTermDebtCurrent` $999M for FY2026

### Nvidia manual-review items

1. **Capital Expenditure FY2024 Q1–Q3** — `PaymentsToAcquireProductiveAssets` has no Q1/Q2 YTD entries for fy=2024; tag quarterly coverage begins fy=2025. Q4 FY2024 is present (derived from Q3 YTD and FY). This causes FCF and TTM FCF to have additional missing values.
2. **Diluted EPS Q4** (×3) — cannot derive by subtraction
3. **$1M rounding gaps** (×5) — documented in validation checklist; XBRL-level artifacts
4. **CapEx tag scope** — `PaymentsToAcquireProductiveAssets` is broader than PP&E; `PaymentsToAcquirePropertyPlantAndEquipment` has no data after FY2012

### Nvidia-specific notes

- Fiscal year ends last Sunday of **January** (~Jan 26); FY numbering is offset +1 from calendar year (FY2026 = Feb 2025 – Jan 2026)
- Uses same Revenue, CostOfRevenue, and CapEx tags as Qualcomm
- Total Debt uses `LongTermDebt` as a single instant tag (includes both noncurrent and current portion)
- Revenue scale is dramatically larger ($216B FY2026) — this does not affect extraction logic but matters for peer comparison

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

### data/processed/
- `qualcomm_financials_2026-06-04.csv` — 132 rows, FY2023–FY2025
- `qualcomm_metrics.csv` — 120 rows
- `amd_financials_2026-06-04.csv` — 132 rows, FY2023–FY2025
- `amd_metrics.csv` — 120 rows
- `nvidia_financials_2026-06-05.csv` — 132 rows, FY2024–FY2026
- `nvidia_metrics.csv` — 120 rows

### data/manual_checks/
- `qualcomm_missing_metrics_2026-06-04.csv` — 3 flagged items
- `qualcomm_q4_validation.csv` — FY2025 Q4 reconciliation
- `amd_missing_metrics_2026-06-04.csv` — 4 flagged items
- `amd_validation_checklist.csv` — 20 checks
- `nvidia_missing_metrics_2026-06-05.csv` — 6 flagged items
- `nvidia_validation_checklist.csv` — 22 checks

### data/benchmarks/qualcomm/
- Immutable copies of validated Qualcomm output (financials CSV, missing-metrics CSV, metrics CSV). Used by `src/regression_check.py`. Do not modify.

### output/
- `qualcomm_financial_history.xlsx` — 6-tab workbook
- `amd_financial_history.xlsx` — 6-tab workbook
- `nvidia_financial_history.xlsx` — 6-tab workbook
- `q4_logic_audit.csv` — historical reference from Stage 5

### output/benchmarks/qualcomm/
- Immutable copy of validated Qualcomm workbook. Do not modify.

### config/
- `companies.csv` — company metadata (name, ticker, CIK, short_id, FY-end month/day)
- `xbrl_tags/qualcomm.json` — Qualcomm XBRL tag map
- `xbrl_tags/amd.json` — AMD XBRL tag map
- `xbrl_tags/nvidia.json` — Nvidia XBRL tag map

### archive/pre_q4_fix/
- Backup of pre-Stage-7 scripts and outputs. Safe to delete once Stage 9 is stable.

## Next objective — Stage 9D: Intel

Add Intel as the fourth company:

1. Download raw SEC JSON: `.venv/bin/python src/fetch_sec_data.py INTC`
2. Run XBRL tag discovery against the Intel raw JSON
3. Create `config/xbrl_tags/intel.json`
4. Validate Intel tag selections and fiscal calendar (FY ends last Saturday of December, ~Dec 28)
5. Run the pipeline: clean → export → calculate
6. Create `data/manual_checks/intel_validation_checklist.csv`
7. Verify Qualcomm/AMD/Nvidia outputs are unchanged

After Intel is validated, proceed to Broadcom (the final company, FY ends first Sunday of November).

## Unresolved issues

1. **Nvidia CapEx FY2024 Q1–Q3 missing** — `PaymentsToAcquireProductiveAssets` has no Q1/Q2 YTD entries for fy=2024. This cascades into missing FCF and TTM FCF values. The `PaymentsToAcquirePropertyPlantAndEquipment` tag has no data after FY2012, so there is no alternative in XBRL. Could potentially be sourced from Nvidia's earnings press releases.

2. **Nvidia $1M rounding gaps** — Five instances where quarterly sums differ from FY totals by exactly $1M. Documented in the validation checklist. These are XBRL data artifacts, not pipeline errors. No action required unless exact reconciliation is needed for audit purposes.

3. **AMD Total Debt FY2023 Q1 missing** — `DebtLongtermAndShorttermCombinedAmount` tag coverage begins Q2 FY2023. Could be manually sourced from the FY2023 Q1 10-Q filing.

4. **Diluted EPS Q4** — Missing for all companies (9 instances total). Cannot be derived from XBRL data. Requires earnings press releases as an independent source.

5. **Qualcomm FY2025 Q4 Net Income = −$3.1B** — Arithmetic is correct but the large Q4 loss likely reflects a one-time charge. Not verified against 10-K notes.

6. **Cross-company peer comparison** — Fiscal year-end dates differ significantly (Sep, Dec, Jan, Nov). Direct FY-label comparison is misleading. Calendar-quarter alignment is not yet implemented.

7. **Broadcom fiscal year-end may have changed** — Broadcom's FY traditionally ended in the first week of November, but may have shifted after the VMware acquisition. Verify during Broadcom tag discovery.

## Non-negotiable rules

1. **Preserve raw source data unchanged.** Never modify files in `data/raw/`.
2. **Do not silently fill missing values.** Flag them with `missing_requires_review`.
3. **Maintain source references.** Every extracted value must carry an SEC filing URL.
4. **Distinguish reported, derived, and manually reviewed values** via the `extraction_method` column.
5. **Explain proposed changes before editing files.** The user is learning and needs to understand what will change and why.
6. **Run validation checks after refactoring.** Verify that prior company outputs are unchanged before adding new companies.
7. **Preserve the working Qualcomm output as a regression benchmark.** Immutable copies in `data/benchmarks/qualcomm/`.
8. **Use company-specific fiscal calendars.** Do not assume calendar quarters or December year-ends.
