"""
renderer.py — AIVx Report HTML Generator
Avenue Z brand system. Static, self-contained output.
"""

from __future__ import annotations
import html as html_lib

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def esc(text: str) -> str:
    return html_lib.escape(str(text))


def tier_badge(tier: str) -> str:
    classes = {
        "Leader":     "badge-leader",
        "Challenger": "badge-challenger",
        "Emerging":   "badge-emerging",
        "Developing": "badge-developing",
    }
    cls = classes.get(tier, "badge-developing")
    return f'<span class="badge {cls}">{esc(tier)}</span>'


def horizon_badge(horizon: str) -> str:
    if "Immediate" in horizon:
        cls = "badge-leader"
    elif "quarter" in horizon.lower():
        cls = "badge-challenger"
    else:
        cls = "badge-emerging"
    return f'<span class="badge {cls}">{esc(horizon)}</span>'


def gradient_number(n: int) -> str:
    return f'<span class="gradient-text">{n}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #000000;
  --surface:   #272727;
  --subtle:    #1a1a1a;
  --white:     #FFFFFF;
  --muted:     #9A9A9A;
  --border:    rgba(255,255,255,0.08);
  --yellow:    #F5EF8A;
  --green:     #7AFFAA;
  --cyan:      #7AF5F7;
  --blue:      #55AEFF;
  --purple:    #8060FF;
  --grad:      linear-gradient(135deg, #F5EF8A, #7AFFAA, #7AF5F7, #55AEFF, #8060FF);
  --sidebar-w: 240px;
}

html { scroll-behavior: smooth; font-size: 16px; }

body {
  font-family: 'Nunito Sans', sans-serif;
  background: var(--bg);
  color: var(--white);
  display: flex;
  min-height: 100vh;
  line-height: 1.7;
}

/* ── Sidebar ─────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-w);
  min-height: 100vh;
  background: #0a0a0a;
  border-right: 1px solid var(--border);
  position: fixed;
  top: 0; left: 0;
  overflow-y: auto;
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  padding: 28px 24px 24px;
  border-bottom: 1px solid var(--border);
}
.sidebar-logo .aivx-brand {
  font-size: 18px;
  font-weight: 900;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}
.sidebar-logo .powered {
  font-size: 10px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: 4px;
}

.sidebar-industry {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.sidebar-industry span {
  display: block;
  color: var(--white);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: none;
  margin-top: 4px;
}

.sidebar-nav {
  padding: 16px 0;
  flex: 1;
}
.sidebar-nav a {
  display: block;
  padding: 9px 24px;
  color: var(--muted);
  text-decoration: none;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.03em;
  border-left: 3px solid transparent;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  line-height: 1.4;
}
.sidebar-nav a:hover,
.sidebar-nav a.active {
  color: var(--white);
  border-left-color: var(--cyan);
  background: rgba(96,253,255,0.05);
}
.sidebar-nav .nav-num {
  font-size: 10px;
  color: var(--muted);
  font-weight: 700;
  margin-right: 6px;
  letter-spacing: 0.06em;
}

.sidebar-footer {
  padding: 20px 24px;
  border-top: 1px solid var(--border);
}
.sidebar-footer a {
  font-size: 11px;
  color: var(--muted);
  text-decoration: none;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.sidebar-footer a:hover { color: var(--cyan); }

/* ── Main Content ────────────────────────────────────────── */
.main {
  margin-left: var(--sidebar-w);
  flex: 1;
  max-width: calc(100vw - var(--sidebar-w));
}

/* ── Hero ────────────────────────────────────────────────── */
.hero {
  padding: 72px 64px 64px;
  background: linear-gradient(180deg, #0c0c0c 0%, var(--bg) 100%);
  border-bottom: 1px solid var(--border);
}
.hero-series {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 16px;
}
.hero-industry {
  font-size: clamp(36px, 5vw, 60px);
  font-weight: 900;
  line-height: 1.1;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}
.hero-subtitle {
  font-size: 22px;
  font-weight: 300;
  color: rgba(255,255,255,0.7);
  margin-bottom: 32px;
}
.hero-meta {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9999px;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.04em;
}
.hero-badge .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--green);
}

/* ── Gradient Divider ────────────────────────────────────── */
.grad-divider {
  height: 1px;
  background: var(--grad);
  margin: 56px 0;
  opacity: 0.6;
}

/* ── Section ─────────────────────────────────────────────── */
.section {
  padding: 64px;
  border-bottom: 1px solid var(--border);
}
.section-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}
.section-title {
  font-size: 28px;
  font-weight: 800;
  color: var(--white);
  padding-left: 16px;
  border-left: 4px solid var(--cyan);
  margin-bottom: 8px;
  line-height: 1.2;
}
.section-intro {
  font-size: 17px;
  color: rgba(255,255,255,0.72);
  font-weight: 300;
  max-width: 720px;
  margin-bottom: 40px;
  line-height: 1.75;
}

/* ── KPI Strip ───────────────────────────────────────────── */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 48px;
}
.kpi-card {
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 24px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--grad);
}
.kpi-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}
.kpi-value {
  font-size: 32px;
  font-weight: 900;
  color: var(--white);
  line-height: 1;
}
.kpi-sub {
  font-size: 12px;
  color: var(--muted);
  margin-top: 6px;
  font-weight: 600;
}

/* ── Topic Clusters ──────────────────────────────────────── */
.clusters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 32px;
}
.cluster-card {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 20px;
}
.cluster-name {
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--cyan);
  margin-bottom: 4px;
}
.cluster-pct {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.45);
  margin-bottom: 10px;
  letter-spacing: 0.04em;
}
.cluster-prompts {
  list-style: none;
  padding: 0;
}
.cluster-prompts li {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  padding: 4px 0;
  padding-left: 14px;
  position: relative;
  line-height: 1.4;
  font-style: italic;
}
.cluster-prompts li::before {
  content: '›';
  position: absolute;
  left: 0;
  color: var(--muted);
}

/* ── Stat Callouts ───────────────────────────────────────── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 48px;
}
.stat-callout {
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 32px;
  position: relative;
  overflow: hidden;
}
.stat-callout::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--grad);
}
.stat-value {
  font-size: 48px;
  font-weight: 900;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  margin-bottom: 8px;
}
.stat-label {
  font-size: 15px;
  font-weight: 700;
  color: var(--white);
  margin-bottom: 4px;
}
.stat-source {
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
}

/* ── Engagement Modes ────────────────────────────────────── */
.engagement-modes-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 24px;
}
.engagement-mode-card {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 20px 24px;
}
.engagement-mode-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.engagement-mode-name {
  font-size: 14px;
  font-weight: 800;
  color: var(--white);
  flex: 1;
}
.engagement-share {
  font-size: 18px;
  font-weight: 900;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.engagement-mode-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  line-height: 1.6;
  font-weight: 400;
}

/* ── Chart Wrapper ───────────────────────────────────────── */
.chart-wrap {
  background: #000;
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 8px;
  margin: 24px 0;
  overflow: hidden;
}
.chart-title {
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  padding: 16px 16px 8px;
}

/* ── Two-column layout ───────────────────────────────────── */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  margin: 32px 0;
}

/* ── Narrative Paragraphs ────────────────────────────────── */
.narrative {
  font-size: 16px;
  color: rgba(255,255,255,0.82);
  font-weight: 400;
  line-height: 1.82;
  max-width: 780px;
  margin-bottom: 24px;
}

/* ── Sub-Section ─────────────────────────────────────────── */
.sub-section {
  margin-top: 56px;
  padding-top: 40px;
  border-top: 1px solid var(--border);
}
.sub-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 6px;
}
.sub-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--white);
  margin-bottom: 6px;
}
.sub-intro {
  font-size: 14px;
  color: rgba(255,255,255,0.55);
  font-weight: 300;
  max-width: 640px;
  margin-bottom: 24px;
  line-height: 1.65;
}

/* ── Leaderboard Table ───────────────────────────────────── */
.leaderboard-wrap {
  overflow-x: auto;
  margin: 24px 0;
  border-radius: 16px;
  border: 1px solid var(--border);
}
.leaderboard {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.leaderboard thead tr {
  border-bottom: 1px solid var(--border);
}
.leaderboard th {
  padding: 14px 20px;
  text-align: left;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  background: #0a0a0a;
  white-space: nowrap;
}
.leaderboard tbody tr {
  border-bottom: 1px solid rgba(255,255,255,0.04);
  transition: background 0.1s;
}
.leaderboard tbody tr:hover {
  background: rgba(255,255,255,0.02);
}
.leaderboard tbody tr:last-child {
  border-bottom: none;
}
.leaderboard td {
  padding: 14px 20px;
  vertical-align: middle;
}
.rank-num {
  font-size: 14px;
  font-weight: 900;
  color: var(--muted);
  width: 40px;
}
.rank-num.top3 {
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 16px;
}
.brand-name {
  font-weight: 700;
  color: var(--white);
  font-size: 14px;
}
.sov-bar-cell { min-width: 160px; }
.sov-bar-outer {
  background: rgba(255,255,255,0.06);
  border-radius: 9999px;
  height: 6px;
  overflow: hidden;
  margin-bottom: 4px;
}
.sov-bar-inner {
  height: 100%;
  border-radius: 9999px;
  background: var(--grad);
}
.sov-pct {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}
.cite-count {
  font-size: 14px;
  font-weight: 700;
  color: var(--white);
}
.prompt-reach {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

/* ── Insight Callout ─────────────────────────────────────── */
.insight-box {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  border-left: 4px solid var(--yellow);
  padding: 20px 24px;
  margin: 24px 0;
  font-size: 14px;
  color: rgba(255,255,255,0.8);
  line-height: 1.65;
  font-weight: 400;
}
.insight-box strong {
  color: var(--yellow);
  font-weight: 800;
}

/* ── Source Table ────────────────────────────────────────── */
.source-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 16px;
}
.source-table td {
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 13px;
}
.source-table td:first-child {
  color: var(--cyan);
  font-weight: 700;
  width: 60%;
}
.source-table td:last-child {
  color: var(--muted);
  text-align: right;
  font-weight: 600;
}

/* ── Trends ──────────────────────────────────────────────── */
.trends-list { margin-top: 8px; }
.trend-item {
  padding: 28px 32px;
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--border);
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}
.trend-item::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  bottom: 0;
  width: 3px;
  background: var(--grad);
}
.trend-num {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 6px;
}
.trend-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--white);
  margin-bottom: 10px;
  line-height: 1.3;
}
.trend-insight {
  font-size: 15px;
  color: rgba(255,255,255,0.78);
  line-height: 1.72;
  margin-bottom: 14px;
}
.trend-implication {
  font-size: 14px;
  color: rgba(255,255,255,0.82);
  font-weight: 400;
  line-height: 1.65;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.trend-implication-label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--cyan);
  margin-bottom: 6px;
}

/* ── Priority Cards ──────────────────────────────────────── */
.priority-cards { margin-top: 8px; }
.priority-card {
  display: flex;
  gap: 28px;
  align-items: flex-start;
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 32px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}
.priority-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--grad);
}
.priority-num {
  font-size: 52px;
  font-weight: 900;
  line-height: 1;
  min-width: 48px;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  flex-shrink: 0;
}
.priority-body { flex: 1; }
.priority-title {
  font-size: 18px;
  font-weight: 800;
  color: var(--white);
  margin-bottom: 8px;
  line-height: 1.3;
}
.priority-why {
  font-size: 15px;
  color: rgba(255,255,255,0.72);
  line-height: 1.7;
  margin-bottom: 14px;
}
.priority-what {
  font-size: 15px;
  color: rgba(255,255,255,0.86);
  line-height: 1.72;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  border-left: 3px solid var(--cyan);
}
.priority-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.priority-owner {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* ── Badges ──────────────────────────────────────────────── */
.badge {
  display: inline-block;
  border-radius: 9999px;
  padding: 4px 12px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.badge-leader     { background: rgba(255,252,96,0.12);  color: #FFFC60; }
.badge-challenger { background: rgba(96,253,255,0.12);  color: #60FDFF; }
.badge-emerging   { background: rgba(57,160,255,0.12);  color: #39A0FF; }
.badge-developing { background: rgba(138,138,138,0.12); color: #8A8A8A; }

/* ── Footer ──────────────────────────────────────────────── */
.footer {
  padding: 48px 64px;
  border-top: 1px solid var(--border);
  background: #050505;
}
.footer-grad-line {
  height: 1px;
  background: var(--grad);
  margin-bottom: 40px;
  opacity: 0.4;
}
.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 40px;
  flex-wrap: wrap;
}
.footer-brand .avz-name {
  font-size: 18px;
  font-weight: 900;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}
.footer-desc {
  font-size: 13px;
  color: var(--muted);
  max-width: 400px;
  line-height: 1.65;
}
.footer-link {
  font-size: 13px;
  color: var(--cyan);
  text-decoration: none;
  font-weight: 700;
  margin-top: 10px;
  display: inline-block;
}
.footer-link:hover { text-decoration: underline; }
.footer-disclaimer {
  font-size: 11px;
  color: rgba(138,138,138,0.5);
  margin-top: 32px;
  line-height: 1.5;
}

/* ── Methodology note ────────────────────────────────────── */
.method-note {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  font-style: italic;
  line-height: 1.65;
  padding: 16px 20px;
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  border: 1px solid var(--border);
  margin-top: 24px;
  max-width: 680px;
}

/* ── Executive Summary ───────────────────────────────────── */
.exec-summary {
  padding: 56px 64px;
  background: linear-gradient(180deg, #0d0d0d 0%, #060606 100%);
  border-bottom: 1px solid var(--border);
}
.exec-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cyan);
  margin-bottom: 12px;
}
.exec-headline {
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 900;
  color: var(--white);
  line-height: 1.2;
  margin-bottom: 8px;
  max-width: 760px;
}
.exec-subheadline {
  font-size: 14px;
  color: rgba(255,255,255,0.40);
  font-weight: 400;
  margin-bottom: 44px;
  letter-spacing: 0.01em;
}
.exec-takeaways {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.exec-takeaway {
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: 20px;
  align-items: flex-start;
  background: var(--surface);
  border-radius: 14px;
  border: 1px solid var(--border);
  padding: 24px 28px;
  position: relative;
  overflow: hidden;
}
.exec-takeaway::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--grad);
}
.exec-num {
  font-size: 26px;
  font-weight: 900;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  padding-top: 4px;
}
.exec-takeaway-headline {
  font-size: 16px;
  font-weight: 800;
  color: var(--white);
  margin-bottom: 7px;
  line-height: 1.3;
}
.exec-detail {
  font-size: 14px;
  color: rgba(255,255,255,0.65);
  line-height: 1.68;
  margin-bottom: 10px;
}
.exec-action {
  font-size: 13px;
  color: rgba(255,255,255,0.86);
  font-weight: 600;
  line-height: 1.6;
  padding: 10px 14px;
  background: rgba(122,245,247,0.06);
  border-radius: 8px;
  border-left: 3px solid var(--cyan);
}

/* ── Z-Score ─────────────────────────────────────────────── */
.z-score {
  font-size: 14px;
  font-weight: 900;
  white-space: nowrap;
}
.z-score-high { color: var(--green); }
.z-score-mid  { color: var(--cyan); }
.z-score-low  { color: var(--muted); }

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 900px) {
  :root { --sidebar-w: 0px; }
  .sidebar { display: none; }
  .main { margin-left: 0; max-width: 100%; }
  .section { padding: 40px 24px; }
  .hero { padding: 48px 24px; }
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .stat-grid { grid-template-columns: 1fr; }
  .two-col { grid-template-columns: 1fr; }
  .engagement-modes-grid { grid-template-columns: 1fr; }
  .priority-card { flex-direction: column; gap: 16px; }
  .priority-num { font-size: 36px; }
  .footer { padding: 40px 24px; }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# JS
# ─────────────────────────────────────────────────────────────────────────────

JS = """
(function() {
  // Active nav state on scroll
  const sections = document.querySelectorAll('.section[id]');
  const navLinks = document.querySelectorAll('.sidebar-nav a[href^="#"]');

  function updateNav() {
    let current = '';
    sections.forEach(function(section) {
      const top = section.getBoundingClientRect().top;
      if (top <= 120) current = section.getAttribute('id');
    });
    navLinks.forEach(function(link) {
      link.classList.remove('active');
      if (link.getAttribute('href') === '#' + current) {
        link.classList.add('active');
      }
    });
  }

  window.addEventListener('scroll', updateNav, { passive: true });
  updateNav();
})();
"""

# ─────────────────────────────────────────────────────────────────────────────
# SECTION BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_sidebar(findings: dict) -> str:
    industry = esc(findings["industry"])
    report_date = esc(findings["report_date"])
    return f"""
<nav class="sidebar">
  <div class="sidebar-logo">
    <div class="aivx-brand">AIVx</div>
    <div class="powered">Powered by Avenue Z</div>
  </div>
  <div class="sidebar-industry">
    Industry Report
    <span>{industry}</span>
  </div>
  <nav class="sidebar-nav">
    <a href="#exec-summary"><span class="nav-num">00</span> Executive Summary</a>
    <a href="#section-1"><span class="nav-num">01</span> Research Overview</a>
    <a href="#section-2"><span class="nav-num">02</span> State of AI Usage</a>
    <a href="#section-3"><span class="nav-num">03</span> Analysis Findings</a>
    <a href="#section-4"><span class="nav-num">04</span> Winners &amp; Losers</a>
    <a href="#section-5"><span class="nav-num">05</span> What To Do Next</a>
  </nav>
  <div class="sidebar-footer">
    <a href="https://avenuez.com" target="_blank" rel="noopener">avenuez.com ↗</a>
  </div>
</nav>"""


def build_hero(findings: dict) -> str:
    industry = esc(findings["industry"])
    date = esc(findings["report_date"])
    meta = findings["metadata"]
    n_brands = meta["brands_analyzed"]
    n_prompts = meta["prompts_analyzed"]
    platform = esc(meta["platform"])
    return f"""
<header class="hero">
  <div class="hero-series">AIVx Industry Intelligence Report</div>
  <h1 class="hero-industry">{industry}</h1>
  <div class="hero-subtitle">AI Visibility Analysis &nbsp;·&nbsp; {date}</div>
  <div class="hero-meta">
    <span class="hero-badge"><span class="dot"></span>{n_brands} Brands Analyzed</span>
    <span class="hero-badge"><span class="dot"></span>{n_prompts} Prompts</span>
    <span class="hero-badge"><span class="dot"></span>{platform}</span>
    <span class="hero-badge"><span class="dot"></span>Powered by Avenue Z</span>
  </div>
</header>"""


def build_executive_summary(findings: dict) -> str:
    """Executive summary block: 3-5 takeaways for CMO/Head of Growth audience."""
    exec_s = findings.get("executive_summary")
    if not exec_s:
        return ""

    headline = esc(exec_s.get("headline", ""))
    subheadline = esc(exec_s.get("subheadline", ""))
    takeaways = exec_s.get("takeaways", [])

    takeaways_html = ""
    for t in takeaways:
        num = t.get("number", "")
        th = esc(t.get("headline", ""))
        detail = esc(t.get("detail", ""))
        action = esc(t.get("action", ""))
        takeaways_html += f"""
      <div class="exec-takeaway">
        <div class="exec-num">{num}</div>
        <div>
          <div class="exec-takeaway-headline">{th}</div>
          <div class="exec-detail">{detail}</div>
          <div class="exec-action">{action}</div>
        </div>
      </div>"""

    return f"""
<section id="exec-summary" class="exec-summary">
  <div class="exec-label">Executive Summary</div>
  <div class="exec-headline">{headline}</div>
  <div class="exec-subheadline">{subheadline}</div>
  <div class="exec-takeaways">{takeaways_html}</div>
</section>"""


def build_section1(findings: dict) -> str:
    meta = findings["metadata"]
    clusters = meta["topic_clusters"]
    examples = meta["example_prompts"]
    n_brands = meta["brands_analyzed"]
    n_prompts = meta["prompts_analyzed"]
    platform = esc(meta["platform"])
    period = esc(meta["data_period"])

    cluster_pcts = meta.get("cluster_pcts", {})
    clusters_html = ""
    for cluster in clusters:
        prompts_for_cluster = examples.get(cluster, [])
        prompts_html = "".join(
            f"<li>&ldquo;{esc(p)}&rdquo;</li>" for p in prompts_for_cluster
        )
        pct = cluster_pcts.get(cluster, 0)
        pct_html = f'<div class="cluster-pct">{pct}% of citations</div>' if pct else ""
        clusters_html += f"""
        <div class="cluster-card">
          <div class="cluster-name">{esc(cluster.replace('_', ' '))}</div>
          {pct_html}
          <ul class="cluster-prompts">{prompts_html}</ul>
        </div>"""

    return f"""
<section id="section-1" class="section">
  <div class="section-label">01 / Research Overview</div>
  <h2 class="section-title">How This Analysis Was Conducted</h2>
  <p class="section-intro">
    This report is grounded in a structured analysis of how AI models respond
    to real buyer and consumer queries in the {esc(findings["industry"])} category.
    Every data point in this report traces back to observed AI behavior, not surveys,
    not keyword rankings, not traffic estimates.
  </p>

  <div class="kpi-strip">
    <div class="kpi-card">
      <div class="kpi-label">Competitors Analyzed</div>
      <div class="kpi-value">{n_brands}</div>
      <div class="kpi-sub">Brands tracked across all prompts</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Prompts Analyzed</div>
      <div class="kpi-value">{n_prompts}</div>
      <div class="kpi-sub">Unique buyer and research queries</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">AI Platform</div>
      <div class="kpi-value">{platform}</div>
      <div class="kpi-sub">V1, single platform analysis</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Topic Clusters</div>
      <div class="kpi-value">{len(clusters)}</div>
      <div class="kpi-sub">Query categories · {period}</div>
    </div>
  </div>

  <div class="sub-section">
    <div class="sub-label">Methodology</div>
    <div class="sub-title">What We Measured</div>
    <p class="narrative">
      A Peec workspace was configured for the {esc(findings["industry"])} category,
      populated with {n_prompts} prompts spanning {len(clusters)} distinct topic clusters.
      Each prompt reflects a real question that buyers, researchers, or decision-makers
      are asking AI models when evaluating brands in this space.
    </p>
    <p class="narrative">
      For every prompt, we recorded which brands were cited, whether the source was
      earned media (editorial, reference, user-generated) or owned media (brand-controlled
      content), and the citation rank within the AI response. The result is a dataset
      that directly measures how AI models perceive and recommend brands in this category.
    </p>
    <div class="method-note">
      Analysis covers ChatGPT responses only (V1). Multi-platform expansion (Perplexity,
      Gemini, Claude) planned for V2. All data reflects a {period}.
    </div>
  </div>

  <div class="sub-section">
    <div class="sub-label">Topic Coverage</div>
    <div class="sub-title">Query Clusters Analyzed</div>
    <p class="sub-intro">
      Prompts were organized into {len(clusters)} topic clusters representing the major
      question categories buyers use when researching this space.
    </p>
    <div class="clusters-grid">{clusters_html}</div>
  </div>

  <div class="grad-divider"></div>
</section>"""


def build_section2(findings: dict) -> str:
    mr = findings["market_research"]
    stats_html = ""
    for s in mr["key_stats"]:
        stats_html += f"""
        <div class="stat-callout">
          <div class="stat-value">{esc(s['value'])}</div>
          <div class="stat-label">{esc(s['label'])}</div>
          <div class="stat-source">{esc(s['source'])}</div>
        </div>"""

    chart_platform = findings["charts"]["platform"]

    # Engagement modes — PRD Section 2 requirement
    engagement_html = ""
    for mode in mr.get("engagement_modes", []):
        trend_class = {
            "Mature": "badge-developing",
            "Fast-growing": "badge-challenger",
            "Emerging": "badge-emerging",
            "Early-stage": "badge-leader",
        }.get(mode["trend"], "badge-developing")
        engagement_html += f"""
        <div class="engagement-mode-card">
          <div class="engagement-mode-header">
            <span class="engagement-mode-name">{esc(mode['mode'])}</span>
            <span class="engagement-share">{esc(mode['share'])}</span>
            <span class="badge {trend_class}" style="font-size:9px">{esc(mode['trend'])}</span>
          </div>
          <p class="engagement-mode-desc">{esc(mode['description'])}</p>
        </div>"""

    engagement_section = ""
    if engagement_html:
        engagement_section = f"""
  <div class="sub-section">
    <div class="sub-label">How Users Engage with AI</div>
    <div class="sub-title">Four Interfaces, Four Visibility Surfaces</div>
    <p class="sub-intro">
      AI is not a single channel. Users interact with AI models across four distinct
      surfaces, each with different implications for brand discoverability.
    </p>
    <div class="engagement-modes-grid">{engagement_html}</div>
  </div>"""

    return f"""
<section id="section-2" class="section">
  <div class="section-label">02 / State of AI Usage</div>
  <h2 class="section-title">Why AI Visibility Matters Right Now</h2>
  <p class="section-intro">
    Before examining how specific brands perform in AI, it is important to understand
    the scale and trajectory of AI adoption, and what the shift means for brand
    discoverability in the {esc(findings["industry"])} category.
  </p>

  <div class="stat-grid">{stats_html}</div>

  <div class="two-col">
    <div>
      <p class="narrative">{mr['narrative']['adoption']}</p>
      <p class="narrative">{mr['narrative']['behavior_shift']}</p>
      <p class="narrative">{mr['narrative']['implication']}</p>
    </div>
    <div>
      <div class="chart-wrap">
        <div class="chart-title">AI Platform Market Share</div>
        {chart_platform}
      </div>
    </div>
  </div>

  {engagement_section}

  <div class="grad-divider"></div>
</section>"""


def build_section3(findings: dict) -> str:
    sov = findings["sov"]
    earned = findings["earned"]
    owned = findings["owned"]
    technical = findings["technical"]
    trends = findings["trends"]
    charts = findings["charts"]
    industry = esc(findings["industry"])

    # Z-Score lookup: brand -> score data
    z_lookup = {z["brand"]: z for z in findings.get("z_scores", [])}

    # ── 3A: Earned Media ────────────────────────────────────────────────────
    top_sources_rows = ""
    for s in earned.get("top_sources", [])[:8]:
        top_sources_rows += (
            f"<tr><td>{esc(s['domain'])}</td><td>{s['count']} citations</td></tr>"
        )

    # Build earned narrative dynamically from actual breakdown data
    breakdown = earned.get("earned_breakdown", {})
    if breakdown:
        dominant_type = max(breakdown.keys(), key=lambda k: breakdown[k]["count"])
        dominant_pct = breakdown[dominant_type]["pct"]
        other_types = [t for t in breakdown.keys() if t != dominant_type]

        _type_descriptions = {
            "editorial": (
                "trade press, industry blogs, and third-party media coverage. "
                "This is the primary signal AI models use to evaluate brand authority."
            ),
            "direct recommendation": (
                "unprompted brand mentions where ChatGPT names a brand without linking "
                "to a specific source, reflecting strong entity recognition"
            ),
            "reference": (
                "authoritative reference sites, directories, and knowledge bases "
                "that AI models treat as trusted category sources"
            ),
            "ugc": (
                "user-generated content including forums, reviews, and community platforms "
                "that AI models draw from for social proof signals"
            ),
        }

        dominant_desc = _type_descriptions.get(
            dominant_type.lower(),
            "the primary citation type in this dataset"
        )

        if other_types:
            other_names = " and ".join(
                f"<strong>{esc(t)}</strong> ({breakdown[t]['pct']}%)" for t in other_types
            )
            other_sentence = (
                f" {other_names} account for the remainder. "
                f"Brands with citations across multiple types have the most durable AI visibility profiles."
            )
        else:
            other_sentence = ""

        earned_narrative = (
            f"Among earned citations, <strong>{esc(dominant_type)}</strong> dominates at "
            f"{dominant_pct}%: {dominant_desc}{other_sentence}"
        )
    else:
        earned_narrative = (
            "Earned citations in this workspace reflect brand-name recommendations from "
            "ChatGPT responses. Source URL classification requires domain-type data from Peec. "
            "The earned/owned split above is based on brand ownership flags and is accurate."
        )

    section_3a = f"""
  <div class="sub-section">
    <div class="sub-label">3B / Earned Media</div>
    <div class="sub-title">How Third-Party Sources Drive AI Citations</div>
    <p class="sub-intro">
      Earned media (editorial coverage, reference sources, and user-generated content)
      accounts for {earned['earned_pct']}% of all AI citations in this category.
    </p>
    <div class="insight-box">
      <strong>{earned['earned_pct']}% earned</strong> vs. {earned['owned_pct']}% owned.
      Third-party credibility is the primary signal AI models use to evaluate and cite brands
      in the {industry} space.
    </div>
    <div class="two-col">
      <div>
        <div class="chart-wrap">
          <div class="chart-title">Earned Media Type Breakdown</div>
          {charts['earned_breakdown']}
        </div>
      </div>
      <div>
        <p class="narrative">{earned_narrative}</p>
        {'<table class="source-table">' + top_sources_rows + '</table>' if top_sources_rows else ''}
      </div>
    </div>
  </div>"""

    # ── 3B: Owned Media ─────────────────────────────────────────────────────
    owned_breakdown_html = ""
    for item in owned.get("content_breakdown", []):
        owned_breakdown_html += f"<tr><td>{esc(item['type'].replace('_',' ').title())}</td><td>{item['count']} citations ({item['pct']}%)</td></tr>"

    section_3b = f"""
  <div class="sub-section">
    <div class="sub-label">3C / Owned Media</div>
    <div class="sub-title">How Brand-Controlled Content Influences AI Responses</div>
    <p class="sub-intro">
      {owned['total_owned']} citations ({earned['owned_pct']}% of total) reference content
      owned and controlled directly by brands. Understanding which content types drive
      these citations reveals where owned content investment creates AI visibility.
    </p>
    <div class="two-col">
      <div>
        <div class="chart-wrap">
          <div class="chart-title">Owned Content by Type</div>
          {charts['owned_content']}
        </div>
      </div>
      <div>
        <p class="narrative">
          The brand with the strongest owned media citation rate in this analysis is
          <strong>{esc(owned['top_owned_brand'])}</strong>, suggesting a content infrastructure
          well-aligned with the questions AI models are answering.
        </p>
        <p class="narrative">
          Brands seeking to strengthen owned media citation should prioritize answer-first
          content formats: FAQ pages, structured how-to articles, and resource guides that
          directly address the query patterns in this report's prompt cluster map.
        </p>
        {'<table class="source-table">' + owned_breakdown_html + '</table>' if owned_breakdown_html else ''}
      </div>
    </div>
  </div>"""

    # ── 3C: Share of Voice ───────────────────────────────────────────────────
    leaderboard_rows = ""
    for brand in sov["leaderboard"]:
        rank = brand["rank"]
        top3_class = "top3" if rank <= 3 else ""
        sov_pct = brand["sov_pct"]
        bar_width = min(100, sov_pct * 2.2)
        # Z-Score cell
        z_data = z_lookup.get(brand["brand"])
        if z_data:
            z_val = z_data["z_score"]
            if z_val >= 70:
                z_cls = "z-score z-score-high"
            elif z_val >= 40:
                z_cls = "z-score z-score-mid"
            else:
                z_cls = "z-score z-score-low"
            z_cell = f'<span class="{z_cls}">{z_val}</span>'
        else:
            z_cell = '<span class="z-score z-score-low">N/A</span>'
        leaderboard_rows += f"""
        <tr>
          <td><span class="rank-num {top3_class}">{rank}</span></td>
          <td class="brand-name">{esc(brand['brand'])}</td>
          <td class="sov-bar-cell">
            <div class="sov-bar-outer">
              <div class="sov-bar-inner" style="width:{bar_width}%"></div>
            </div>
            <span class="sov-pct">{sov_pct}%</span>
          </td>
          <td><span class="cite-count">{brand['citation_count']}</span></td>
          <td><span class="prompt-reach">{brand.get('prompt_pct', 0)}%</span></td>
          <td>{z_cell}</td>
          <td>{tier_badge(brand['tier'])}</td>
        </tr>"""

    concentration_note = (
        f"The top 5 brands hold {sov['top5_sov']}% of AI visibility: a highly concentrated market."
        if sov["is_concentrated"]
        else f"Visibility is relatively distributed. The top 5 brands hold {sov['top5_sov']}% of AI citations."
    )

    section_3c = f"""
  <div class="sub-section">
    <div class="sub-label">3A / Share of Voice</div>
    <div class="sub-title">AI Visibility Leaderboard</div>
    <p class="sub-intro">{concentration_note}</p>
    <div class="insight-box">
      <strong>{esc(sov['top_brand'])}</strong> leads the category with {sov['top_brand_sov']}% AI share
      of voice, appearing in {sov.get('top_brand_prompts', 0)}% of all prompts analyzed.
      The top 10 brands account for {sov['top10_sov']}% of total citations.
    </div>
    <div class="leaderboard-wrap">
      <table class="leaderboard">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Brand</th>
            <th>AI Visibility</th>
            <th>Citations</th>
            <th>Prompt Reach</th>
            <th title="Avenue Z composite AI visibility score: Breadth 40%, Depth 30%, Authority 20%, Positioning 10%">Z-Score &#9432;</th>
            <th>Tier</th>
          </tr>
        </thead>
        <tbody>{leaderboard_rows}</tbody>
      </table>
    </div>
    <div class="two-col" style="margin-top:32px">
      <div>
        <div class="chart-wrap">
          <div class="chart-title">Share of Voice: Top 5 Brands</div>
          {charts['sov_donut']}
        </div>
      </div>
      <div>
        <div class="chart-wrap">
          <div class="chart-title">Citation Volume: Top 15 Brands</div>
          {charts['leaderboard_bar']}
        </div>
      </div>
    </div>
  </div>"""

    # ── 3D: Technical Factors ────────────────────────────────────────────────
    tech_rows = ""
    if technical.get("has_rank_data") and technical.get("technical_leaders"):
        for brand in technical["technical_leaders"][:10]:
            tech_rows += f"""
            <tr>
              <td class="brand-name">{esc(brand['brand'])}</td>
              <td><span class="cite-count">{brand['citation_count']}</span></td>
              <td><span class="sov-pct">{brand['avg_rank']}</span></td>
            </tr>"""

    tech_table = ""
    if tech_rows:
        tech_table = f"""
        <table class="source-table" style="margin-top:24px">
          <tr style="border-bottom:1px solid var(--border)">
            <td style="color:var(--muted);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">BRAND</td>
            <td style="color:var(--muted);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">CITATIONS</td>
            <td style="color:var(--muted);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;text-align:right">AVG POSITION</td>
          </tr>
          {tech_rows}
        </table>"""

    section_3d = f"""
  <div class="sub-section">
    <div class="sub-label">3D / Technical Optimization</div>
    <div class="sub-title">How Technical Quality Correlates with AI Visibility</div>
    <p class="sub-intro">
      Beyond content and earned media, technical factors influence how consistently
      brands are cited and where in an AI response they appear.
    </p>
    <p class="narrative">
      Citation position (where in a response a brand is mentioned) serves as a proxy
      for technical visibility quality. Brands cited earlier, in position 1 or 2,
      tend to have stronger technical signals: cleaner site structure, faster performance,
      better schema markup, and more comprehensive entity recognition.
    </p>
    <p class="narrative">
      <strong>{esc(technical.get('top_technical_brand', 'N/A'))}</strong> leads on average
      citation position in this analysis, suggesting strong technical optimization
      supporting its AI visibility profile.
    </p>
    {tech_table}
    <div class="insight-box" style="margin-top:24px">
      <strong>Key technical factors</strong> correlated with strong AI visibility:
      schema markup (Organization, Product, FAQ), Wikipedia entity presence,
      Google Knowledge Panel accuracy, page load performance, and structured data
      on key landing pages.
    </div>
  </div>"""

    # ── 3E: Trends ───────────────────────────────────────────────────────────
    _impl_labels = [
        "What this means for challengers",
        "How to act on this",
        "The priority this unlocks",
        "Why this matters now",
        "The lever to pull",
    ]
    trends_html = ""
    for i, trend in enumerate(trends, 1):
        impl_label = _impl_labels[(i - 1) % len(_impl_labels)]
        trends_html += f"""
      <div class="trend-item">
        <div class="trend-num">Trend {i}</div>
        <div class="trend-title">{esc(trend['title'])}</div>
        <div class="trend-insight">{esc(trend['insight'])}</div>
        <div class="trend-implication">
          <span class="trend-implication-label">{esc(impl_label)}</span>
          {esc(trend['implication'])}
        </div>
      </div>"""

    section_3e = f"""
  <div class="sub-section">
    <div class="sub-label">3E / General Trends</div>
    <div class="sub-title">Patterns and Strategic Insights from the Data</div>
    <p class="sub-intro">
      Cross-sectional patterns observed across brands, topic clusters, and citation types
      in the {industry} AI visibility dataset.
    </p>
    <div class="trends-list">{trends_html}</div>
  </div>"""

    return f"""
<section id="section-3" class="section">
  <div class="section-label">03 / Findings</div>
  <h2 class="section-title">Analysis of AI Visibility in {industry}</h2>
  <p class="section-intro">
    Five lenses on the data: earned media, owned media, share of voice, technical factors,
    and general trends. Together they tell the complete story of how AI models perceive
    and recommend brands in this category.
  </p>
  {section_3c}
  {section_3a}
  {section_3b}
  {section_3d}
  {section_3e}
  <div class="grad-divider"></div>
</section>"""


def build_section4(findings: dict) -> str:
    yoy = findings.get("yoy", {})
    industry = esc(findings["industry"])
    sov = findings["sov"]

    if not yoy.get("has_prior_data"):
        leaderboard = yoy.get("current_leaderboard", sov["leaderboard"][:10])
        rows_html = ""
        for brand in leaderboard:
            rank = brand["rank"]
            top3_class = "top3" if rank <= 3 else ""
            rows_html += f"""
            <tr>
              <td><span class="rank-num {top3_class}">{rank}</span></td>
              <td class="brand-name">{esc(brand['brand'])}</td>
              <td><span class="sov-pct">{brand['sov_pct']}%</span></td>
              <td><span class="cite-count">{brand['citation_count']}</span></td>
              <td>{tier_badge(brand['tier'])}</td>
            </tr>"""

        top_brand = yoy.get("top_brand", sov["top_brand"])
        top_sov = yoy.get("top_brand_sov", sov["top_brand_sov"])
        is_concentrated = yoy.get("is_concentrated", sov["is_concentrated"])
        concentration_note = (
            "AI visibility is highly concentrated at the top of this category. The brands ranked here have a compounding advantage that grows with every report cycle."
            if is_concentrated
            else "Visibility is relatively distributed, creating real opportunity for brands currently outside the top 5 to break in with focused effort."
        )

        return f"""
<section id="section-4" class="section">
  <div class="section-label">04 / Competitive Standings</div>
  <h2 class="section-title">Winners &amp; Losers: The Baseline Report</h2>
  <p class="section-intro">
    This is the inaugural AIVx {industry} report. No prior-year data exists yet,
    which means this edition defines the baseline. Every future ranking movement
    will be measured against what you see here.
  </p>
  <div class="insight-box">
    <strong>Why this matters:</strong> The brands ranked here today are establishing
    citation authority before the competitive window narrows. AI visibility compounds.
    Brands cited consistently today will be harder to displace six months from now.
    The brands not on this list have a shrinking window to change that.
  </div>
  <p class="narrative" style="margin-bottom:8px">{concentration_note}</p>
  <div class="leaderboard-wrap" style="margin-top:24px">
    <table class="leaderboard">
      <thead>
        <tr>
          <th>Rank</th>
          <th>Brand</th>
          <th>AI Visibility</th>
          <th>Citations</th>
          <th>Tier</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  <div class="sub-section">
    <div class="sub-label">What to watch</div>
    <div class="sub-title">Brands to Monitor in the Next Report Cycle</div>
    <p class="narrative">
      <strong>{esc(top_brand)}</strong> enters the first AIVx {industry} report as the
      category leader with {top_sov}% AI share of voice. The central question for the
      next report cycle: does this lead hold, or do challengers close the gap?
    </p>
    <p class="narrative">
      Watch for brands currently in positions 4 through 8. They are close enough to
      challenge the top 3 but far enough back that any slip in content or earned media
      activity could push them further down. The Developing-tier brands represent the
      most volatile segment: small changes in citation volume will produce large shifts
      in rank from here.
    </p>
    <div class="method-note">
      Year-over-year comparison will be available when a prior AIVx {industry} report
      is supplied as input. The agent will automatically identify rank risers, rank
      decliners, new entrants, and brands that fell off the leaderboard entirely.
    </div>
  </div>
  <div class="grad-divider"></div>
</section>"""

    # Has prior data — build full YoY movement table
    movers = yoy.get("movers", [])
    dropoffs = yoy.get("dropoffs", [])
    top_brand = yoy.get("top_brand", sov["top_brand"])
    top_sov = yoy.get("top_brand_sov", sov["top_brand_sov"])

    mover_rows = ""
    for brand in movers:
        rank = brand["current_rank"]
        top3_class = "top3" if rank <= 3 else ""
        prior_rank = brand.get("prior_rank")
        rank_change = brand.get("rank_change")
        is_new = brand.get("is_new_entrant", False)

        if is_new or prior_rank is None:
            move_html = '<span style="color:#60FF80;font-weight:700;font-size:11px">NEW</span>'
        elif rank_change > 0:
            move_html = f'<span style="color:#60FF80;font-weight:700">&uarr; {rank_change}</span>'
        elif rank_change < 0:
            move_html = f'<span style="color:#FF6B6B;font-weight:700">&darr; {abs(rank_change)}</span>'
        else:
            move_html = '<span style="color:#8A8A8A">&#8211;</span>'

        prior_cell = str(prior_rank) if prior_rank else "N/A"
        mover_rows += f"""
            <tr>
              <td><span class="rank-num {top3_class}">{rank}</span></td>
              <td class="brand-name">{esc(brand['brand'])}</td>
              <td style="text-align:center">{move_html}</td>
              <td style="text-align:center;color:#8A8A8A;font-size:12px">{prior_cell}</td>
              <td><span class="sov-pct">{brand['sov_pct']}%</span></td>
              <td><span class="cite-count">{brand['citation_count']}</span></td>
              <td>{tier_badge(brand['tier'])}</td>
            </tr>"""

    dropoff_html = ""
    if dropoffs:
        dropoff_items = "".join(
            f'<li><strong>{esc(d["brand"])}</strong>, ranked #{d["prior_rank"]} in the prior report</li>'
            for d in sorted(dropoffs, key=lambda x: x["prior_rank"])
        )
        dropoff_html = f"""
  <div class="sub-section" style="margin-top:32px">
    <div class="sub-label">Brands That Fell Off the Leaderboard</div>
    <div class="sub-title">No Longer Appearing in Current Data</div>
    <ul style="color:rgba(255,255,255,0.65);line-height:2;padding-left:20px">
      {dropoff_items}
    </ul>
    <div class="method-note">These brands appeared in the prior AIVx report but generated no citations in the current 7-day collection window. This may indicate a drop in AI visibility, a gap in content activity, or a change in how AI models are classifying the category.</div>
  </div>"""

    return f"""
<section id="section-4" class="section">
  <div class="section-label">04 / Year-Over-Year</div>
  <h2 class="section-title">Winners &amp; Losers Over the Past Year</h2>
  <p class="section-intro">
    Rank movement from the prior AIVx {industry} report. Green arrows indicate improved AI visibility.
    Red arrows indicate decline. NEW marks brands entering the leaderboard for the first time.
  </p>
  <div class="leaderboard-wrap" style="margin-top:24px">
    <table class="leaderboard">
      <thead>
        <tr>
          <th>Rank</th>
          <th>Brand</th>
          <th style="text-align:center">Move</th>
          <th style="text-align:center">Prior Rank</th>
          <th>AI Visibility</th>
          <th>Citations</th>
          <th>Tier</th>
        </tr>
      </thead>
      <tbody>{mover_rows}</tbody>
    </table>
  </div>
  <div class="sub-section" style="margin-top:32px">
    <div class="sub-label">Leader Analysis</div>
    <div class="sub-title">What to Watch Next Report Cycle</div>
    <p class="narrative">
      <strong>{esc(top_brand)}</strong> holds the top position with {top_sov}% AI share of voice.
      The rank movement data above reveals which brands are building citation authority and which
      are losing ground to more aggressive content and PR strategies.
    </p>
    <p class="narrative">
      New entrants in the current report represent brands that have recently invested in AEO —
      their presence signals that the competitive window is not closed. Brands that dropped in rank
      should audit their earned media velocity and content publication cadence against the leaders.
    </p>
  </div>
  {dropoff_html}
  <div class="grad-divider"></div>
</section>"""


def build_section5(findings: dict) -> str:
    recs = findings["recommendations"]
    industry = esc(findings["industry"])

    cards_html = ""
    for rec in recs:
        cards_html += f"""
      <div class="priority-card">
        <div class="priority-num">{rec['priority']}</div>
        <div class="priority-body">
          <div class="priority-title">{esc(rec['title'])}</div>
          <div class="priority-why">{esc(rec['why'])}</div>
          <div class="priority-what">{esc(rec['what'])}</div>
          <div class="priority-meta">
            <span class="priority-owner">{esc(rec['owner'])}</span>
            &nbsp;·&nbsp;
            {horizon_badge(rec['horizon'])}
          </div>
        </div>
      </div>"""

    return f"""
<section id="section-5" class="section">
  <div class="section-label">05 / Recommendations</div>
  <h2 class="section-title">What Brands in {industry} Need To Do Next</h2>
  <p class="section-intro">
    Five prioritized, data-grounded actions. Sequenced for maximum first-move impact.
    Start with #1. Each action compounds the one before it.
  </p>
  <div class="priority-cards">{cards_html}</div>
  <div class="grad-divider"></div>
</section>"""


def build_cta_section(findings: dict) -> str:
    industry = esc(findings["industry"])
    return f"""
<section class="section" style="text-align:center;background:linear-gradient(180deg,#080808 0%,#000000 100%);border-bottom:none">
  <div style="max-width:660px;margin:0 auto;padding:32px 0">
    <div class="section-label" style="text-align:center;margin-bottom:20px">Request a Custom Report</div>
    <h2 style="font-size:clamp(32px,4.5vw,52px);font-weight:900;line-height:1.1;color:var(--white);margin-bottom:24px">
      How does your brand stack up<br>in AI Search?
    </h2>
    <p style="font-size:16px;color:rgba(255,255,255,0.55);line-height:1.75;margin-bottom:40px;max-width:560px;margin-left:auto;margin-right:auto">
      Request a custom AI Search Visibility Report to see where you stand,
      what&rsquo;s driving your visibility, what&rsquo;s holding it back, and how to close the gap.
      Tailored insights and actionable strategies built around your brand, your sector,
      and your competitive landscape.
    </p>
    <a href="https://avenuez.com/ai-report" target="_blank" rel="noopener"
       style="display:inline-block;padding:16px 44px;border:2px solid rgba(255,255,255,0.8);border-radius:9999px;color:var(--white);text-decoration:none;font-size:15px;font-weight:800;letter-spacing:0.04em;transition:border-color 0.2s,color 0.2s">
      Visit&nbsp; <strong style="color:var(--cyan)">AvenueZ.com/ai-report</strong>
    </a>
  </div>
</section>"""


def build_footer(findings: dict) -> str:
    date = esc(findings["report_date"])
    industry = esc(findings["industry"])
    return f"""
<footer class="footer">
  <div class="footer-grad-line"></div>
  <div class="footer-content">
    <div class="footer-brand">
      <div class="avz-name">Avenue Z</div>
      <p class="footer-desc">
        Avenue Z is a digital marketing and PR agency specializing in AI visibility
        and Answer Engine Optimization (AEO). We help brands earn citation authority
        with AI models through earned media, content strategy, and technical optimization.
      </p>
      <a class="footer-link" href="https://avenuez.com" target="_blank" rel="noopener">
        avenuez.com ↗
      </a>
    </div>
    <div>
      <p style="font-size:12px;color:var(--muted);font-weight:700;margin-bottom:6px">
        AIVx REPORT SERIES
      </p>
      <p style="font-size:13px;color:rgba(255,255,255,0.5)">
        {industry}<br>{date}
      </p>
    </div>
  </div>
  <p class="footer-disclaimer">
    This report was generated by the Avenue Z AIVx Report Agent.
    Citation data reflects AI model behavior during a 7-day collection window.
    All market research statistics are sourced from publicly available industry reports
    and are subject to change. Avenue Z makes no representations about future AI visibility
    outcomes. Data is provided for strategic planning purposes only.
  </p>
</footer>"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_report(findings: dict) -> str:
    industry = esc(findings["industry"])
    date = esc(findings["report_date"])

    sidebar = build_sidebar(findings)
    hero = build_hero(findings)
    exec_summary = build_executive_summary(findings)
    s1 = build_section1(findings)
    s2 = build_section2(findings)
    s3 = build_section3(findings)
    s4 = build_section4(findings)
    s5 = build_section5(findings)
    cta = build_cta_section(findings)
    footer = build_footer(findings)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AIVx Report — {industry} — {date} | Avenue Z</title>
  <meta name="description" content="AI Visibility Analysis for the {industry} industry. Powered by Avenue Z AEO Intelligence.">
  <style>{CSS}</style>
</head>
<body>
  {sidebar}
  <div class="main">
    {hero}
    {exec_summary}
    {s1}
    {s2}
    {s3}
    {s4}
    {s5}
    {cta}
    {footer}
  </div>
  <script>{JS}</script>
</body>
</html>"""
