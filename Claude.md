# Semiconductor Research Terminal

Read PROJECT_STATUS.md before making changes.

## Objective
Build an auditable equity-research workflow for five public semiconductor companies.

## Initial scope
The Qualcomm pipeline is complete and serves as the regression benchmark.
When generalizing to additional companies, verify that Qualcomm output is
unchanged before and after any refactoring.

## Core rules
1. Use SEC EDGAR data as the primary source for historical financial statements.
2. Preserve raw downloaded data without modifying it.
3. Save cleaned data separately in data/processed.
4. Attach a source, filing date and reporting period to every extracted financial metric.
5. Do not silently fill missing values.
6. Flag accounting inconsistencies and unusual changes for human review.
7. Separate sourced facts from AI-generated interpretation.
8. Keep scripts modular and easy for a beginner to understand.
9. Explain important code changes before making them.
10. Never publish personal credentials or configuration details to GitHub.

## Initial company
Qualcomm Incorporated

## Initial metrics
- Revenue
- Gross profit
- Operating income
- Net income
- Diluted EPS
- Cash and cash equivalents
- Total debt
- Operating cash flow
- Capital expenditure
- Free cash flow
- R&D expense
- Gross margin
- Operating margin
- Free-cash-flow margin
- R&D as a percentage of revenue

## Quarterly reporting logic

Some companies do not file a separate Q4 10-Q.

For duration metrics:
- Derive Q4 as full fiscal-year value from the 10-K minus the first-nine-month YTD value from the Q3 10-Q.
- Record the derivation method and source periods.
- Do not silently treat Q4 as missing.

For point-in-time balance-sheet metrics:
- Use the reported fiscal-year-end value from the 10-K as the Q4 ending balance.

For EPS:
- Do not derive quarterly EPS by subtracting year-to-date EPS.
- Use a reported standalone quarterly source where available.
- Otherwise flag the metric for manual review.

For every metric:
- distinguish reported values from derived values;
- label each value with an extraction_method: reported_standalone,
  derived_ytd_difference, fiscal_year_end_balance, or missing_requires_review;
- preserve source references;
- flag ambiguous accounting tags;
- create validation checks where an official standalone Q4 earnings release is available.