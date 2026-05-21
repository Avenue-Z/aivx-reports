# AIVx Report Agent — Avenue Z

Automated AI visibility benchmarking. Turns a completed Peec workspace into a published, Avenue Z-branded interactive industry report — in minutes.

**Live hub:** [aivx-reports.vercel.app](https://aivx-reports.vercel.app)

---

## What It Does

The AIVx Report Agent reads real ChatGPT citation data from a Peec workspace, runs competitive analysis across share of voice, earned/owned media, technical authority, and topic coverage, then renders a self-contained interactive HTML report ready to publish.

**Time saved:** 20-30 hours of manual work per report, down to a single command.

**Output:** A hosted, Avenue Z-branded interactive report with 5 sections:
1. **Research Overview** — methodology, competitors, prompts, topic clusters
2. **State of AI Usage** — market context, platform adoption, buyer behavior
3. **Analysis Findings** — SOV rankings, earned vs. owned split, trends
4. **Competitive Standings** — every brand ranked and tiered
5. **What Brands Need to Do Next** — 5 data-grounded recommendations

---

## Repo Structure

```
aivx-reports/
├── agent/                    # Pipeline code — edit here to change analysis or report design
│   ├── agent.py              # Core analysis engine and CLI entry point
│   ├── peec_mapper.py        # Transforms Peec CSV exports into agent format (CSV path only)
│   ├── renderer.py           # HTML/CSS report builder
│   ├── test_harness.py       # Test suite — run before every live report
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Copy to .env and fill in your Peec credentials
│   └── mock_data/
│       └── mock_peec_export.csv   # Sample data for testing without real Peec access
├── reports/                  # Published HTML reports (auto-generated — do not edit manually)
├── index.html                # Hub page — new report cards are auto-injected here
└── vercel.json               # Vercel deployment config
```

---

## Setup

**Requirements:** Python 3.10+

```bash
cd agent
pip install -r requirements.txt
```

**Credentials (for live API path only):**
```bash
cp agent/.env.example agent/.env
# Fill in PEEC_API_KEY and PEEC_PROJECT_ID in agent/.env
```

---

## How to Run a New Report

There are two paths depending on your Peec workspace type.

### Path 1: CSV Export (Current V1 — use this for pitch workspaces)

Peec pitch workspaces have an API limitation. Export CSVs manually instead.

**Step 1: Export from Peec**

Set these filters in the Peec dashboard before every export:
- Brand: All brands
- Date: Last 7 days
- Model: ChatGPT ONLY
- Tags: All Tags
- Topics: All Topics

Then export three files:
| Export | Location in Peec |
|--------|-----------------|
| Prompts CSV | General > Prompts > Export |
| URLs CSV | Sources > URLs > Export |
| Domains CSV | Sources > Domains > Export |

**Step 2: Run the mapper**

```bash
cd agent

python peec_mapper.py \
    --prompts /path/to/peec_prompts.csv \
    --urls /path/to/peec_urls.csv \
    --domains /path/to/peec_domains.csv \
    --owned-brand "Your Client Brand" \
    --output peec_mapped.csv
```

`--owned-brand` is the brand marked as "You" in the Peec workspace. Everything else is treated as a competitor.

**Step 3: Run the agent**

```bash
python agent.py \
    --industry "Category: Subcategory" \
    --peec peec_mapped.csv \
    --report-slug "category-subcategory" \
    --output ../reports \
    --hub ../index.html
```

**Step 4: Publish**

```bash
cd ..
git add reports/ index.html
git commit -m "Add Category: Subcategory report May 2026"
git push
```

Vercel deploys automatically. Report is live within 60 seconds.

---

### Path 2: Live API (Non-pitch workspaces)

For customer-space workspaces, the agent can pull data directly — no CSV exports needed.

```bash
cd agent

python agent.py \
    --industry "Category: Subcategory" \
    --project-id YOUR_PEEC_PROJECT_ID \
    --report-slug "category-subcategory" \
    --output ../reports \
    --hub ../index.html

cd ..
git add reports/ index.html && git commit -m "Add report" && git push
```

The agent auto-discovers workspaces if `--project-id` is omitted and multiple are available.

---

## Naming Convention

Report titles follow this format — enforced across all published reports:

```
[Category]: [Subcategory] — 2026 AI Visibility Report
```

**Examples:**
- `Fintech: Digital Banks`
- `Healthcare: Insurance`
- `B2B SaaS: Marketing Tools`

No client names in report titles. Ever. The `--client` flag is available for internal tracking only — it does not appear on the published hub card.

---

## CLI Reference

### agent.py

| Flag | Required | Description |
|------|----------|-------------|
| `--industry` | Yes | Report title (e.g. `"Fintech: Digital Banks"`) |
| `--peec` | No* | Path to mapped CSV (CSV path) |
| `--project-id` | No* | Peec project ID (live API path) |
| `--report-slug` | No | Filename override — do NOT include date, agent appends YYYY-MM automatically |
| `--output` | No | Output directory for HTML report (default: `../reports`) |
| `--hub` | No | Path to hub index.html — auto-injects card when provided |
| `--prior-pdf` | No | Path to prior-year PDF for year-over-year comparison |
| `--client` | No | Internal client label — not shown on hub card |

*One of `--peec` or a valid Peec API key in `.env` is required.

### peec_mapper.py

| Flag | Required | Description |
|------|----------|-------------|
| `--prompts` | Yes | Peec prompts export CSV |
| `--urls` | No | Peec URLs export CSV (enriches media type classification) |
| `--domains` | No | Peec domains export CSV (enriches media type classification) |
| `--owned-brand` | No | Brand marked as "You" in the workspace (default: Chime) |
| `--output` | No | Output path for mapped CSV (default: `peec_mapped.csv`) |

---

## Running Tests

Run the test harness before every live report. It catches schema issues, broken imports, and analysis logic failures in under 10 seconds without making any API calls.

```bash
cd agent
python test_harness.py
```

All tests should pass (green). If any fail, fix the issue before running the agent.

---

## How the Analysis Works

Every number in the report is computed from the citation data — no AI, no generation.

| Analysis | Method |
|----------|--------|
| Share of Voice | Citation count per brand / total citations |
| Prompt Coverage | Unique prompts each brand appeared in / total prompts |
| Tier Classification | Percentile rank: Leader (top 15%), Challenger, Emerging, Developing |
| Earned vs. Owned | `is_owned` flag per row — 0 = earned, 1 = owned |
| Media Type | Domain matched against hardcoded lists (UGC, Reference, Editorial) |
| Technical Authority | Average citation position per brand (lower = cited earlier) |
| Trends | 5 conditional pattern checks with real data injected into pre-written templates |
| Recommendations | 5 pre-written action items with real numbers, domains, and brand names injected from the analysis |

---

## Publishing Checklist

Before every publish:

- [ ] `python test_harness.py` — all tests passing
- [ ] Open the HTML in a browser locally and check all 5 sections
- [ ] Verify hub card was injected correctly in `index.html`
- [ ] Check report slug does not duplicate an existing file in `reports/`
- [ ] `git push` and confirm Vercel deployment at [aivx-reports.vercel.app](https://aivx-reports.vercel.app)

---

## Live Reports

| Report | URL |
|--------|-----|
| Fintech: Digital Banks | [aivx-reports.vercel.app/reports/aivx-digital-banks-2026-05](https://aivx-reports.vercel.app/reports/aivx-digital-banks-2026-05) |
| Ancillary & Supplemental Benefits | [aivx-reports.vercel.app/reports/aivx-renaissance-benefits-2026-05](https://aivx-reports.vercel.app/reports/aivx-renaissance-benefits-2026-05) |
| Digital Marketing Agencies | [aivx-reports.vercel.app/reports/aivx-digital-marketing-agencies-2026-05](https://aivx-reports.vercel.app/reports/aivx-digital-marketing-agencies-2026-05) |

---

## Known Limitations

**Peec pitch workspace API limit:** Pitch workspaces cannot be accessed via the live API (rate limited). Use the CSV export path (Path 1 above). Flagged to Peec support — no ETA on fix. Once resolved, the live API path works for all workspace types.

**Year-over-year comparison:** Requires a prior-year PDF report passed via `--prior-pdf`. For first-edition reports, Section 4 shows current competitive standings as a baseline for future comparisons.

**ChatGPT only:** V1 analyzes ChatGPT data exclusively. Perplexity, Gemini, and Claude are V2 scope.

---

## Contact

Built and maintained by Thomas Chang, AI Automation Engineer — Avenue Z.
Questions: thomas.chang@avenuez.com
