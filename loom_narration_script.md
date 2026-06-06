# Loom Narration Script
## Semiconductor Equity Research Terminal
### Total estimated runtime: ~4:30

---

## SECTION 1 — Hook (0:00–0:30)
*[Screen: Dashboard header, overview section visible]*

This is a semiconductor equity research terminal built entirely on public SEC filings.

It covers five companies: Qualcomm, AMD, Nvidia, Intel, and Broadcom.

Every financial metric in this dashboard traces back to a specific SEC EDGAR filing URL. Nothing is manually entered. Nothing is estimated. If the data isn't in a filing, it's flagged as missing.

---

## SECTION 2 — The Problem (0:30–1:05)
*[Screen: Stay on overview, scroll slowly]*

Building this required solving problems that don't have obvious solutions.

None of these companies file a standalone Q4 report with the SEC. So every Q4 figure is derived — by subtracting the nine-month year-to-date value from the full fiscal year total.

These five companies also don't share a fiscal calendar. Qualcomm's year ends in September. Nvidia's ends in January. Broadcom's ends in November. Comparing them directly requires careful labeling, not assumptions.

The pipeline handles all of this automatically — and marks every derived value so you always know what you're looking at.

---

## SECTION 3 — Peer Comparison Table (1:05–2:00)
*[Screen: Navigate to Peer Comparison section]*

The peer table is the core of the dashboard.

Each row is a key metric. Each column is a company. The numbers come directly from SEC XBRL data — the structured financial tags embedded in every public filing.

Look at revenue. Nvidia is in a different league — over two hundred billion dollars in its most recent fiscal year, driven by AI infrastructure demand.

Free cash flow margin: Qualcomm, AMD, and Nvidia are all above twenty percent. Broadcom is also strong, though temporarily compressed by the VMware acquisition.

Intel is the outlier — deeply negative free cash flow. That's structural. Intel operates its own chip factories, which means capital expenditure of ten to twenty billion dollars per year. The other four companies are fabless. The business models aren't directly comparable.

R&D intensity rounds out the picture. AMD and Qualcomm invest heavily relative to revenue. Nvidia's ratio has compressed as revenue scaled dramatically.

---

## SECTION 4 — Company Deep Dive (2:00–2:55)
*[Screen: Navigate to Company Deep Dive, select Qualcomm]*

The company deep dive goes quarter by quarter for each company.

Notice the shading. Yellow values are derived — calculated by the Q4 subtraction method. Unshaded values were reported directly in an SEC filing. That distinction is visible on every row so you always know the provenance of the number.

Qualcomm's Q4 fiscal year 2025 net income shows negative 3.1 billion dollars. That's not an operational loss — it's a non-cash tax charge from a U.S. tax law change. The dashboard flags it for review rather than treating it as a normal data point. That kind of transparency is built into every company view.

---

## SECTION 5 — Trend Charts (2:55–3:20)
*[Screen: Navigate to Trend Charts, let charts render]*

The trend charts plot all five companies over time on the same axes.

Revenue growth, margins, R&D intensity — the divergence between Nvidia and the rest of the group is hard to miss. These charts pull from the same underlying data as the peer table. No separate entry.

---

## SECTION 6 — Evidence Explorer and Limitations (3:20–4:05)
*[Screen: Navigate to Evidence Explorer, then Limitations]*

This is where the dashboard differs from a typical financial model.

Every qualitative claim — about AI demand, product strategy, capital allocation — is sourced from an official SEC filing. Each has a direct quote and a link to the source document. All forty claims were manually reviewed.

The limitations section documents where comparison breaks down: Intel's non-recurring charges, Broadcom's VMware transition year, the differing fiscal calendars, missing Q4 EPS across all five companies.

Most dashboards don't show you their blind spots. This one does.

---

## SECTION 7 — Close (4:05–4:30)
*[Screen: Back to Overview / peer table visible]*

The pipeline behind this runs in six Python scripts. Data comes from SEC EDGAR. Raw files are never modified. Metrics are calculated, validated, and exported. The dashboard reads from those outputs.

Claude accelerated the repetitive extraction work. But the accounting logic, validation checks, and analytical conclusions required human judgment at every step.

Every number here has a source. Every derived value is labeled. Every limitation is documented.

That's the standard this terminal was built to.

---

*Script end — estimated 4:20–4:35 depending on AI voice speed*
*Tip: If using Loom's AI voice, set speed to 1.0x — the trimmed script is tight enough without slowing down.*
