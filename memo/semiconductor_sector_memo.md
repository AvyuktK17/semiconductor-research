# Semiconductor Peer Comparison

**Date:** June 6, 2026 | **Coverage:** QCOM, AMD, NVDA, INTC, AVGO | **Source:** SEC EDGAR XBRL filings (10-K/10-Q)

---

## Executive view

The dominant theme across this five-company peer group is structural divergence -- in business model, AI exposure, and capital intensity. **Nvidia has the strongest operating profile**: 75% gross margins, 65% operating margins, and $97B in trailing FCF on $216B of revenue. **Intel's valuation is the hardest to justify on current fundamentals** -- 11.2x EV/TTM Revenue despite negative operating income, negative FCF, and three years of restructuring; the market is pricing in the foundry turnaround and 18A node. **Broadcom is the most structurally distinct**, operating a hybrid semiconductor-plus-software model (58/42 split) with no peer parallel. Cross-peer comparison without adjusting for these differences is misleading.

## Operating comparison

**Revenue growth.** Nvidia led at +65% ($130.5B to $215.9B), followed by AMD +34% ($25.8B to $34.6B), Broadcom +24% ($51.6B to $63.9B, partly VMware transition), Qualcomm +14% ($39.0B to $44.3B), and Intel roughly flat at $52.9B.

**Margins.** Latest-quarter gross margins: Nvidia 75%, Broadcom 68% (boosted by software subscriptions), Qualcomm 55% (inflated by 72%-margin QTL licensing), AMD 54%, Intel 36%. Intel's Foundry segment posted a $10.3B operating loss; the Products division alone earned 26% operating margin.

**FCF generation.** Nvidia $97B TTM, Broadcom $26.9B, Qualcomm $12.8B, AMD $6.7B (growing but modest relative to market cap), Intel -$4.9B (structurally negative from $11.2B net CapEx).

**R&D intensity.** Intel 24%, AMD 23%, Qualcomm 21%, Broadcom 17% (low ratio reflects software base), Nvidia 8% (lowest ratio but highest absolute spend at $18.5B).

**Balance sheet.** Nvidia and AMD are net-cash positive (~$2B each). Qualcomm carries $9.3B net debt. Broadcom ($50.9B) and Intel ($31.9B) are heavily leveraged -- Broadcom from VMware, Intel from its fab buildout with $34.5B in construction in progress.

## Valuation comparison

| Metric | QCOM | AMD | NVDA | INTC | AVGO |
|---|---|---|---|---|---|
| EV/TTM Revenue | 6.0x | 24.6x | 24.5x | 11.2x | 31.8x |
| P/TTM FCF | 19.9x | 126.7x | 54.7x | N/A | 73.7x |
| FCF Yield | 5.0% | 0.8% | 1.8% | -0.9% | 1.4% |

Broadcom's 31.8x prices in AI networking growth and recurring software revenue. AMD and Nvidia trade at nearly identical revenue multiples (~24.5x) despite Nvidia's far superior margins -- AMD's multiple assumes substantial margin expansion. Qualcomm at 6.0x is cheapest on every metric, reflecting Apple insourcing risk and limited data-center AI exposure. Intel's multiple on negative FCF is a foundry bet.

**P/E and EV/EBITDA are excluded.** Q4 diluted EPS is missing for all five companies (cannot be derived from YTD XBRL data) and EBITDA requires depreciation/amortization tags not yet in the pipeline.

## Key company-specific observations

**Qualcomm.** QTL licensing (~13% of revenue, 72% margin) has no peer equivalent. Three named customers (Apple, Samsung, Xiaomi) each exceed 10% of revenue; Apple modem insourcing risk is explicitly disclosed. AI exposure is on-device only.

**AMD.** Data Center is 48% of revenue, growing 32% YoY. Margin improving to 50% despite $440M MI308 export-control charges. R&D growth (+25% to $8.1B) prioritized over buybacks ($1.3B).

**Nvidia.** Scale leader ($216B revenue, $97B FCF), but gross margin declined on the Blackwell transition and a $4.5B H20 export-control charge. China revenue fell 21% to $19.7B. One customer at 13%.

**Intel.** Fundamental restructuring: FY2025 operating loss $2.2B, FY2024 -$11.7B. Foundry lost $10.3B with only $307M external revenue. Dividends eliminated; $7B raised through dilutive equity issuances (SoftBank, Nvidia); $8B in CHIPS Act funding with 275M shares plus warrants issued to the government.

**Broadcom.** Software segment ($27B, 42% of revenue) has no peer parallel. AI semi revenue $10.8B in Q2 FY2026 (+143% YoY) from custom XPUs and networking. Debt of $67.1B is highest in the group.

## Risks and catalysts

- **AI demand durability.** Nvidia (90% of revenue) and Broadcom (~49% of Q2 revenue) most exposed to hyperscaler CapEx cycles. Intel's Gaudi accelerator has inventory write-downs suggesting weak traction.
- **Export restrictions.** Already triggered $4.5B (Nvidia), $800M (AMD) in charges; further restrictions would compress the AI accelerator TAM.
- **Product transitions.** Blackwell ramp (Nvidia margin pressure), 18A/14A node risk (Intel), Apple modem insourcing (Qualcomm).
- **Customer concentration.** Intel top 3 = 43%, Broadcom top 5 = 40%, Qualcomm three customers each >10%.
- **Capital intensity.** Intel's $11--23B/year CapEx produces structurally negative FCF. Broadcom's $67B debt requires sustained cash generation.
- **Acquisition integration.** Broadcom FY2024 was a 53-week VMware transition year; FY2023-to-FY2024 comparisons are unreliable.

## Data limitations

- **Fiscal year-ends differ:** Qualcomm (Sep), Intel/AMD (Dec), Nvidia (Jan), Broadcom (Nov). Calendar-quarter alignment is not yet implemented.
- **Q4 diluted EPS missing** for all five companies (15 instances); requires earnings press releases.
- **Nvidia FY2024 CapEx Q1--Q3** sourced from 8-K press releases, not XBRL; pending manual confirmation.
- **Intel cash tag** includes ~$447M restricted cash (~3% overstatement vs peers).
- **Intel non-recurring charges:** FY2024 included $7.0B restructuring, $3.1B goodwill impairments, $9.9B deferred tax allowance. GAAP margins are not comparable to peers without non-GAAP adjustment.
- **Intel CapEx** ($11--23B/year IDM) is structurally incomparable to fabless peers ($0.5--6B).
- **Broadcom debt** uses gross principal ($67.1B), ~$2B / ~3% above carrying value used by other peers.
- **Broadcom FY2024:** 53 weeks, VMware full-year consolidation vs ~5 weeks in FY2023. Revenue +44% was primarily acquisition-driven.

## AI-assisted workflow

**Automated by Claude:** SEC EDGAR data download, XBRL quarterly extraction, Q4 derivation (FY minus 9-month YTD), ratio calculation, TTM aggregation, peer consolidation, and qualitative-claim sourcing with direct quotes and SEC filing URLs.

**Required human judgment:** XBRL tag selection (companies use different tags for equivalent concepts), Nvidia CapEx 8-K sourcing confirmation, review of all 40 qualitative claims, valuation input validation, and interpretation of comparability limitations.

**Value labeling:** every metric carries an `extraction_method`: `reported_standalone`, `derived_ytd_difference`, `fiscal_year_end_balance`, `reported_earnings_release`, or `missing_requires_review`. Derived values are shaded yellow in the workbook; missing values pink; manual-review items amber.

**Validation:** Qualcomm serves as an immutable regression benchmark (132 financials, 120 metrics rows). After each company addition or refactor, automated checks confirmed identical Qualcomm output. Cross-validation includes FY total reconciliation, gross-profit tag comparison, and debt-component verification.

---

*This memo does not constitute investment advice. All data sourced from public SEC filings. Qualitative claims are labeled factual or interpretive and have been human-reviewed. No buy or sell recommendation is made.*
