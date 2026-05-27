#!/usr/bin/env python3
"""
AIVx Report Agent v1.0 — Avenue Z
Ingests a Peec workspace export and generates a branded interactive HTML report.

Usage:
    python agent.py --industry "Fintech: Payments" --peec path/to/export.csv
    python agent.py --industry "Fintech: Payments" --peec path/to/export.csv --output ./my-reports
"""

import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# BRAND CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BRAND_COLORS = ["#FF6B35", "#60FF80", "#60FDFF", "#39A0FF", "#6034FF", "#8A8A8A"]

PLOTLY_BASE = dict(
    paper_bgcolor="#000000",
    plot_bgcolor="#1a1a1a",
    font=dict(family="Nunito Sans, sans-serif", color="#FFFFFF", size=13),
    hoverlabel=dict(
        bgcolor="#272727",
        bordercolor="rgba(255,255,255,0.1)",
        font=dict(family="Nunito Sans", color="#FFFFFF", size=13),
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# MARKET RESEARCH LIBRARY (Section 2 data — update as stats evolve)
# ─────────────────────────────────────────────────────────────────────────────

MARKET_RESEARCH = {
    "platform_share": {
        "ChatGPT": 60,
        "Google Gemini": 20,
        "Perplexity": 10,
        "Claude": 5,
        "Other": 5,
    },
    "key_stats": [
        {
            "value": "400M+",
            "label": "ChatGPT Monthly Active Users",
            "source": "OpenAI, Feb 2025",
        },
        {
            "value": "55%",
            "label": "US Adults Who Have Used Generative AI",
            "source": "Pew Research, 2024",
        },
        {
            "value": "65%+",
            "label": "B2B Buyers Using AI in Purchase Decisions",
            "source": "Gartner/Forrester, 2025",
        },
        {
            "value": "~60%",
            "label": "ChatGPT Share of Generative AI Tool Usage",
            "source": "Various industry estimates, 2025",
        },
    ],
    # How users engage with AI — text, voice, browsing, agentic (PRD Section 2 requirement)
    "engagement_modes": [
        {
            "mode": "Text Chat",
            "share": "73%",
            "description": "The dominant interface. Users type queries directly into ChatGPT, Claude, or Gemini. Brand citations appear in direct responses, the primary visibility surface.",
            "trend": "Mature",
        },
        {
            "mode": "AI-Augmented Search",
            "share": "18%",
            "description": "Perplexity, Bing Copilot, and Google AI Overviews layer AI responses on top of web search. Citations appear with source links; visibility requires both brand authority and web presence.",
            "trend": "Fast-growing",
        },
        {
            "mode": "Voice & Mobile",
            "share": "6%",
            "description": "Siri, Alexa, and mobile AI assistants surface single-answer responses. The brand that owns the top citation wins the entire query. Zero-sum visibility.",
            "trend": "Emerging",
        },
        {
            "mode": "Agentic / Autonomous",
            "share": "3%",
            "description": "AI agents that browse, compare, and transact on behalf of users. Early-stage but growing fast. Brands with structured data and API accessibility have a significant head start.",
            "trend": "Early-stage",
        },
    ],
    "narrative": {
        "adoption": (
            "AI adoption has crossed the mainstream threshold. More than half of US adults have now "
            "used a generative AI tool, and weekly active usage is growing rapidly across every demographic. "
            "For business buyers, AI is already embedded in the research and decision-making process. "
            "65% of B2B buyers report using AI tools when evaluating vendors and making purchasing decisions."
        ),
        "behavior_shift": (
            "The behavioral shift is structural, not cyclical. Consumers and buyers are increasingly "
            "turning to AI as a first stop for information, before visiting brand websites, before "
            "reading reviews, and before engaging with sales teams. When an AI model recommends a brand, "
            "that recommendation carries authority. When a brand is absent from AI responses, it is "
            "effectively invisible to a growing segment of its target market."
        ),
        "implication": (
            "For brands in this industry, AI visibility is not a future concern. It is a present "
            "competitive reality. The brands that establish strong AI citation patterns now will "
            "benefit from compounding advantage as AI usage continues to grow. Waiting to invest "
            "means competing against a field that has already built citation authority."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING + NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────


def load_peec_data(filepath: str) -> pd.DataFrame:
    """
    Load and normalize a Peec workspace CSV export.

    Expected columns (flexible naming — we normalize):
        prompt_id, prompt_text, topic_cluster, platform,
        brand, cited_url, media_type, is_owned, citation_rank

    Filters to ChatGPT data only (V1 requirement).
    Raises ValueError with clear message if required data is missing.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Peec export not found: {filepath}")

    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = ["brand", "media_type", "is_owned", "topic_cluster", "platform",
                "prompt_id", "prompt_text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns in Peec export: {missing}\n"
            f"Found columns: {list(df.columns)}\n"
            f"Check peec-data-spec.md for expected schema."
        )

    # Filter to ChatGPT only — capture platforms BEFORE filtering for clear error messages
    all_platforms = df["platform"].unique().tolist()
    original_len = len(df)
    df = df[df["platform"].str.lower().str.contains("chatgpt", na=False)].copy()
    if len(df) == 0:
        raise ValueError(
            f"No ChatGPT rows found. Found platforms: {all_platforms}"
        )

    df["is_owned"] = pd.to_numeric(df["is_owned"], errors="coerce").fillna(0).astype(int)
    df["brand"] = df["brand"].str.strip()

    filtered = original_len - len(df)
    if filtered > 0:
        print(f"  Filtered {filtered} non-ChatGPT rows.")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# EARNED MEDIA TYPE CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

_UGC_DOMAINS = {
    "reddit.com", "quora.com", "g2.com", "trustpilot.com", "capterra.com",
    "clutch.co", "glassdoor.com", "yelp.com", "producthunt.com", "getapp.com",
    "softwareadvice.com", "tripadvisor.com",
}
_REFERENCE_DOMAINS = {
    "wikipedia.org", "semrush.com", "ahrefs.com", "moz.com",
    "searchenginejournal.com", "searchengineland.com", "hubspot.com",
    "gartner.com", "forrester.com", "statista.com", "marketingland.com",
    "techradar.com", "cnet.com", "pcmag.com", "zdnet.com", "investopedia.com",
    "inc.com", "entrepreneur.com", "neilpatel.com", "backlinko.com",
}


def classify_earned_type(domain: str) -> str:
    """Classify a third-party domain as editorial, reference, or ugc."""
    if not domain:
        return "brand_mention"
    d = domain.lower().lstrip("www.")
    for ugc in _UGC_DOMAINS:
        if ugc in d:
            return "ugc"
    for ref in _REFERENCE_DOMAINS:
        if ref in d:
            return "reference"
    return "editorial"


def extract_domain_simple(url: str) -> str:
    """Extract root domain from a URL string."""
    if not url:
        return ""
    url = url.lower().split("//")[-1].split("/")[0]
    parts = url.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else url


# ─────────────────────────────────────────────────────────────────────────────
# LIVE API FETCH
# ─────────────────────────────────────────────────────────────────────────────


def list_peec_projects(api_key: str) -> list:
    """
    Fetch all Peec workspaces available for this API key.
    Returns a list of project dicts: [{id, name, domain, status}, ...]
    """
    r = requests.get(
        "https://api.peec.ai/customer/v1/projects",
        headers={"X-API-Key": api_key},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    # Handle both {data: [...]} and [...] response shapes
    return data.get("data", data) if isinstance(data, dict) else data


def resolve_project_id(api_key: str, cli_project_id: str = None) -> str:
    """
    Resolve which Peec project to run against.

    Priority:
      1. --project-id flag passed on CLI
      2. PEEC_PROJECT_ID in .env
      3. Auto-discover: fetch /projects and prompt user to pick

    Returns the resolved project_id string.
    """
    if cli_project_id:
        return cli_project_id

    env_id = os.getenv("PEEC_PROJECT_ID")
    if env_id:
        return env_id

    # Auto-discover
    print("\n  No project ID provided — fetching available Peec workspaces...")
    try:
        projects = list_peec_projects(api_key)
    except Exception as e:
        raise SystemExit(f"  Could not fetch Peec projects: {e}")

    if not projects:
        raise SystemExit("  No Peec workspaces found for this API key.")

    if len(projects) == 1:
        p = projects[0]
        name = p.get("name") or p.get("domain") or p.get("id")
        print(f"  One workspace found — using: {name} ({p['id']})\n")
        return p["id"]

    # Multiple projects — print list and prompt
    print("\n  Available Peec workspaces:\n")
    for i, p in enumerate(projects, 1):
        name   = p.get("name")   or p.get("domain") or "Unnamed"
        domain = p.get("domain") or ""
        status = p.get("status") or ""
        print(f"    [{i}] {name}  |  {domain}  |  {status}  |  id: {p['id']}")

    print()
    while True:
        raw = input("  Select workspace number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(projects):
            chosen = projects[int(raw) - 1]
            print(f"  Using: {chosen.get('name') or chosen['id']}\n")
            return chosen["id"]
        print(f"  Enter a number between 1 and {len(projects)}.")


def fetch_peec_data(api_key: str, project_id: str) -> pd.DataFrame:
    """
    Pull citation data live from the Peec API. Read-only (GET requests only).
    Returns the same normalized DataFrame that load_peec_data() produces.
    """
    BASE = "https://api.peec.ai/customer/v1"
    HDR = {"X-API-Key": api_key}

    def get(path, params=None, _retries=4):
        import time
        p = dict(params or {})
        p["project_id"] = project_id
        for attempt in range(_retries):
            r = requests.get(f"{BASE}{path}", headers=HDR, params=p, timeout=30)
            if r.status_code == 429 and attempt < _retries - 1:
                wait = 15 * (attempt + 1)
                print(f"    Rate limited — waiting {wait}s before retry {attempt + 1}/{_retries - 1}...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()
        return r.json()

    # --- Lookup tables ---
    print("    Fetching prompts...")
    raw_prompts = get("/prompts", {"limit": 500})["data"]
    prompt_text_map = {p["id"]: p["messages"][0]["content"] for p in raw_prompts}

    print("    Fetching tags...")
    raw_tags = get("/tags")["data"]
    tag_name_map = {t["id"]: t["name"] for t in raw_tags}

    print("    Fetching topics...")
    try:
        raw_topics = get("/topics")["data"]
        topic_name_map = {t["id"]: t["name"] for t in raw_topics}
    except Exception:
        topic_name_map = {}

    prompt_cluster_map = {}
    for p in raw_prompts:
        # Prefer the topic field (PRD-correct source) — fall back to first tag
        topic_obj = p.get("topic") or {}
        topic_id = topic_obj.get("id") if isinstance(topic_obj, dict) else None
        if topic_id and topic_id in topic_name_map:
            prompt_cluster_map[p["id"]] = topic_name_map[topic_id]
        else:
            first_tag_id = (p.get("tags") or [{}])[0].get("id")
            prompt_cluster_map[p["id"]] = (
                tag_name_map.get(first_tag_id, "General") if first_tag_id else "General"
            )

    print("    Fetching brands...")
    raw_brands = get("/brands", {"limit": 500})["data"]
    brand_map = {b["id"]: b for b in raw_brands}

    # --- Resolve ChatGPT model channel ID dynamically (Issue 2) ---
    print("    Resolving ChatGPT channel ID...")
    chatgpt_channel_id = "openai-0"  # default fallback
    try:
        ch_resp = get("/model-channels")
        ch_list = ch_resp.get("data", ch_resp) if isinstance(ch_resp, dict) else ch_resp
        for ch in (ch_list or []):
            model_info = ch.get("current_model") or {}
            ch_id = ch.get("id", "")
            model_id = model_info.get("id", "")
            if "chatgpt" in model_id.lower() or "openai" in ch_id.lower():
                chatgpt_channel_id = ch_id
                break
    except Exception as e:
        print(f"    Could not resolve channel ID ({e}) -- defaulting to openai-0")
    print(f"    ChatGPT channel: {chatgpt_channel_id}")

    # --- Compute 7-day date window (PRD requirement) ---
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=7)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")
    print(f"    Date window: {start_date} to {end_date}")

    # --- Fetch full chat list (paginated) ---
    print("    Fetching chat list...")
    all_chats, offset, limit = [], 0, 100
    while True:
        result = get("/chats", {
            "model_channel_id": chatgpt_channel_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        })
        all_chats.extend(result["data"])
        if len(all_chats) >= result["totalCount"]:
            break
        offset += limit
    print(f"    {len(all_chats)} chats found")

    # --- Fetch chat content concurrently (read-only GET) ---
    print("    Fetching citation data...")

    def fetch_content(chat):
        try:
            content = get(f"/chats/{chat['id']}/content")
            pid = chat["prompt"]["id"]
            out = []
            for bm in content.get("brands_mentioned", []):
                bid = bm.get("id", "")
                binfo = brand_map.get(bid, {})
                is_owned = 1 if binfo.get("is_own", False) else 0
                cited_url = ""
                for src in content.get("sources", []):
                    u = src.get("url") or src.get("domain") or ""
                    if u:
                        cited_url = u
                        break
                if is_owned:
                    media_type = "owned_blog"
                else:
                    domain = extract_domain_simple(cited_url)
                    raw_type = classify_earned_type(domain)
                    media_type = "direct recommendation" if raw_type == "brand_mention" else raw_type
                out.append({
                    "prompt_id":     pid,
                    "prompt_text":   prompt_text_map.get(pid, ""),
                    "topic_cluster": prompt_cluster_map.get(pid, "General"),
                    "platform":      "chatgpt",
                    "brand":         bm.get("name", ""),
                    "cited_url":     cited_url,
                    "media_type":    media_type,
                    "is_owned":      is_owned,
                    "citation_rank": bm.get("position", 0),
                })
            return out
        except Exception:
            return []

    rows = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_content, chat): chat for chat in all_chats}
        done = 0
        for future in as_completed(futures):
            rows.extend(future.result())
            done += 1
            if done % 50 == 0:
                print(f"    {done}/{len(all_chats)} chats processed")

    if not rows:
        raise ValueError("No citation data returned from Peec workspace.")

    df = pd.DataFrame(rows)
    df["brand"] = df["brand"].str.strip()
    df["is_owned"] = df["is_owned"].astype(int)
    print(f"    {len(df)} citations | {df['prompt_id'].nunique()} prompts | {df['brand'].nunique()} brands")

    workspace_meta = {
        "total_workspace_prompts": len(raw_prompts),
        "prompt_text_map": prompt_text_map,
        "prompt_cluster_map": prompt_cluster_map,
        "start_date": start_date,
        "end_date": end_date,
    }
    return df, workspace_meta


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────────────────────


def analyze_share_of_voice(df: pd.DataFrame) -> dict:
    """
    Leaderboard rankings, SOV percentages, tier classification,
    concentration analysis, and prompt coverage per brand.
    """
    # Core citation counts
    brand_counts = (
        df.groupby("brand").size().reset_index(name="citation_count")
    )
    total_citations = brand_counts["citation_count"].sum()
    brand_counts["sov_pct"] = (
        brand_counts["citation_count"] / total_citations * 100
    ).round(1)
    brand_counts = brand_counts.sort_values(
        "citation_count", ascending=False
    ).reset_index(drop=True)
    brand_counts["rank"] = range(1, len(brand_counts) + 1)

    # Prompt reach (how many unique prompts each brand appears in)
    total_prompts = df["prompt_id"].nunique()
    prompt_reach = (
        df.groupby("brand")["prompt_id"]
        .nunique()
        .reset_index(name="prompt_count")
    )
    prompt_reach["prompt_pct"] = (
        prompt_reach["prompt_count"] / total_prompts * 100
    ).round(1)
    brand_counts = brand_counts.merge(prompt_reach, on="brand", how="left")

    # Tier classification (Leader / Challenger / Emerging / Developing)
    n = len(brand_counts)

    def tier(rank):
        p = rank / n
        if p <= 0.15:
            return "Leader"
        if p <= 0.35:
            return "Challenger"
        if p <= 0.65:
            return "Emerging"
        return "Developing"

    brand_counts["tier"] = brand_counts["rank"].apply(tier)

    # Concentration metrics
    top5_sov = brand_counts.head(5)["sov_pct"].sum()
    top10_sov = brand_counts.head(10)["sov_pct"].sum()

    return {
        "leaderboard": brand_counts.to_dict("records"),
        "total_brands": n,
        "total_citations": int(total_citations),
        "total_prompts": total_prompts,
        "top5_sov": round(top5_sov, 1),
        "top10_sov": round(top10_sov, 1),
        "is_concentrated": top5_sov > 60,
        "top_brand": brand_counts.iloc[0]["brand"],
        "top_brand_sov": brand_counts.iloc[0]["sov_pct"],
        "top_brand_prompts": brand_counts.iloc[0]["prompt_pct"],
    }


def analyze_earned_media(df: pd.DataFrame) -> dict:
    """
    Earned vs. owned split, editorial/reference/UGC breakdown,
    top media sources, per-brand earned ratios.
    """
    earned = df[df["is_owned"] == 0].copy()
    owned = df[df["is_owned"] == 1].copy()
    total = len(df)

    earned_pct = round(len(earned) / total * 100, 1) if total else 0
    owned_pct = round(len(owned) / total * 100, 1) if total else 0

    # Earned media type breakdown (only when source URL data is available)
    # Rename 'owned_blog' to 'Brand Website' in earned citations — these are competitor
    # brand pages (is_owned=0) classified by URL pattern, not the owned brand's content.
    # Keeps the label from colliding with the 'Owned Media' section terminology.
    _EARNED_LABEL_MAP = {"owned_blog": "Brand Website"}
    if len(earned):
        earned_types = earned[earned["media_type"] != ""].groupby("media_type").size()
        earned_breakdown = {
            _EARNED_LABEL_MAP.get(t, t).title(): {
                "count": int(c),
                "pct": round(c / len(earned) * 100, 1),
            }
            for t, c in earned_types.items()
        }
    else:
        earned_breakdown = {}

    # Top media source domains
    top_sources = []
    if "cited_url" in df.columns and len(earned):

        def extract_domain(url):
            m = re.search(r"(?:https?://)?(?:www\.)?([^/\n?]+)", str(url))
            return m.group(1) if m else str(url)

        earned = earned.copy()
        earned["source_domain"] = earned["cited_url"].apply(extract_domain)
        src_counts = (
            earned[earned["source_domain"] != ""]
            .groupby("source_domain")
            .size()
            .sort_values(ascending=False)
            .head(10)
        )
        top_sources = [
            {"domain": d, "count": int(c)} for d, c in src_counts.items()
        ]

    # Per-brand earned/owned breakdown (top 15 brands by total)
    brand_split = (
        df.groupby(["brand", "is_owned"]).size().unstack(fill_value=0)
    )
    col_map = {0: "earned", 1: "owned"}
    brand_split = brand_split.rename(
        columns={k: v for k, v in col_map.items() if k in brand_split.columns}
    )
    for col in ["earned", "owned"]:
        if col not in brand_split.columns:
            brand_split[col] = 0
    brand_split["total"] = brand_split["earned"] + brand_split["owned"]
    brand_split["earned_pct"] = (
        brand_split["earned"] / brand_split["total"] * 100
    ).round(1)
    brand_split = (
        brand_split.sort_values("total", ascending=False)
        .head(15)
        .reset_index()
    )

    return {
        "earned_pct": earned_pct,
        "owned_pct": owned_pct,
        "earned_count": int(len(earned)),
        "owned_count": int(len(owned)),
        "earned_breakdown": earned_breakdown,
        "top_sources": top_sources,
        "brand_ratios": brand_split.to_dict("records"),
    }


def analyze_owned_media(df: pd.DataFrame) -> dict:
    """Content type breakdown for owned citations."""
    owned = df[df["is_owned"] == 1].copy()
    total_owned = len(owned)

    if not total_owned:
        return {"content_breakdown": [], "total_owned": 0, "top_owned_brand": "N/A"}

    content_types = owned.groupby("media_type").size().sort_values(ascending=False)
    content_breakdown = [
        {
            "type": t,
            "count": int(c),
            "pct": round(c / total_owned * 100, 1),
        }
        for t, c in content_types.items()
    ]

    # Brand with highest owned citation rate
    brand_split = (
        df.groupby(["brand", "is_owned"]).size().unstack(fill_value=0)
    )
    if 1 in brand_split.columns:
        brand_split = brand_split.rename(columns={0: "earned", 1: "owned"})
    if "owned" not in brand_split.columns:
        brand_split["owned"] = 0
    if "earned" not in brand_split.columns:
        brand_split["earned"] = 0
    brand_split["total"] = brand_split["earned"] + brand_split["owned"]
    brand_split["owned_pct"] = (
        brand_split["owned"] / brand_split["total"] * 100
    ).round(1)
    qualified = brand_split[brand_split["total"] >= 5].sort_values(
        "owned_pct", ascending=False
    )
    top_owned_brand = qualified.index[0] if len(qualified) else "N/A"

    return {
        "content_breakdown": content_breakdown,
        "total_owned": total_owned,
        "top_owned_brand": str(top_owned_brand),
    }


def analyze_technical_factors(df: pd.DataFrame) -> dict:
    """
    Uses citation_rank as a proxy for technical visibility quality.
    Lower average citation rank = cited earlier in AI responses = stronger presence.
    """
    if "citation_rank" not in df.columns:
        return {"has_rank_data": False, "technical_leaders": [], "top_technical_brand": "N/A"}

    brand_avg_rank = df.groupby("brand")["citation_rank"].mean().round(2)
    brand_counts = df.groupby("brand").size().rename("citation_count")
    tech_df = pd.DataFrame(
        {"avg_rank": brand_avg_rank, "citation_count": brand_counts}
    )
    tech_df = (
        tech_df[tech_df["citation_count"] >= 3]
        .sort_values("avg_rank")
        .head(15)
        .reset_index()
    )
    top_brand = tech_df.iloc[0]["brand"] if len(tech_df) else "N/A"

    # Detect whether position data is actually differentiated.
    # On the CSV path, all competitor citation_ranks are hardcoded to 1 by the mapper,
    # producing a flat table where every brand ties at avg=1.0. When this happens,
    # naming a "leader" is misleading — suppress that narrative.
    min_rank = tech_df["avg_rank"].min() if len(tech_df) else 1.0
    brands_at_min = (tech_df["avg_rank"] == min_rank).sum()
    position_is_differentiated = bool(brands_at_min <= 2 and min_rank < tech_df["avg_rank"].max())

    return {
        "has_rank_data": True,
        "technical_leaders": tech_df.to_dict("records"),
        "top_technical_brand": str(top_brand),
        "position_is_differentiated": position_is_differentiated,
    }


def analyze_yoy(sov: dict, prior_pdf_path: str = None) -> dict:
    """
    Year-over-year comparison. Returns baseline dict when no prior PDF is supplied.
    When prior_pdf_path is provided, parses brand rankings and computes rank movement.

    Prior PDF format (from historical manual AIVx reports):
        Numbered list: "1. Stripe 98.5"  "2. PayPal 94.0"  etc.
    """
    base = {
        "has_prior_data": False,
        "current_leaderboard": sov["leaderboard"][:10],
        "top_brand": sov["top_brand"],
        "top_brand_sov": sov["top_brand_sov"],
        "is_concentrated": sov["is_concentrated"],
    }

    if not prior_pdf_path:
        return base

    try:
        import pdfplumber
    except ImportError:
        print("  pdfplumber not installed -- YoY comparison skipped. Install with: pip install pdfplumber")
        return base

    try:
        prior_rankings = {}
        with pdfplumber.open(prior_pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Match patterns like: "1. Stripe 98.5" or "1. PayPal 94.0"
        # Brand names may contain spaces, ampersands, commas, dots
        pattern = re.compile(
            r"(?:^|\n)\s*(\d{1,2})\.\s+([A-Za-z][A-Za-z0-9\s&,\.\-]{1,40}?)\s+([\d]{1,3}\.[\d]{1,2})\s*(?:\n|$)",
            re.MULTILINE,
        )
        for match in pattern.finditer(full_text):
            rank = int(match.group(1))
            brand = match.group(2).strip().rstrip(".,")
            score = float(match.group(3))
            if 1 <= rank <= 60 and brand:
                # Deduplicate: keep highest-ranked occurrence per brand name
                key = brand.lower()
                if key not in prior_rankings or prior_rankings[key]["rank"] > rank:
                    prior_rankings[key] = {"rank": rank, "score": score, "name": brand}

        if not prior_rankings:
            print("  Could not extract prior rankings from PDF -- YoY comparison skipped.")
            return base

        print(f"  Parsed {len(prior_rankings)} prior brands from PDF.")

        # Build movement data for current top-20 brands
        current_map = {b["brand"].lower(): b for b in sov["leaderboard"]}
        movers = []
        for brand_lower, curr in current_map.items():
            prior = prior_rankings.get(brand_lower)
            if prior:
                rank_change = prior["rank"] - curr["rank"]  # positive = improved
                movers.append({
                    "brand": curr["brand"],
                    "current_rank": curr["rank"],
                    "prior_rank": prior["rank"],
                    "rank_change": rank_change,
                    "sov_pct": curr["sov_pct"],
                    "citation_count": curr["citation_count"],
                    "tier": curr["tier"],
                    "prior_score": prior["score"],
                    "is_new_entrant": False,
                })
            else:
                movers.append({
                    "brand": curr["brand"],
                    "current_rank": curr["rank"],
                    "prior_rank": None,
                    "rank_change": None,
                    "sov_pct": curr["sov_pct"],
                    "citation_count": curr["citation_count"],
                    "tier": curr["tier"],
                    "prior_score": None,
                    "is_new_entrant": True,
                })

        # Brands from prior top-20 that are absent from current leaderboard
        current_names = set(current_map.keys())
        dropoffs = [
            {"brand": v["name"], "prior_rank": v["rank"], "prior_score": v["score"]}
            for k, v in prior_rankings.items()
            if k not in current_names and v["rank"] <= 20
        ]

        movers.sort(key=lambda x: x["current_rank"])

        return {
            "has_prior_data": True,
            "current_leaderboard": sov["leaderboard"][:10],
            "movers": movers[:20],
            "dropoffs": dropoffs,
            "top_brand": sov["top_brand"],
            "top_brand_sov": sov["top_brand_sov"],
            "is_concentrated": sov["is_concentrated"],
        }

    except Exception as e:
        print(f"  YoY PDF parsing failed: {e} -- using baseline report.")
        return base


def synthesize_trends(df: pd.DataFrame, sov: dict, earned: dict, owned: dict) -> list:
    """Generate 3-5 data-grounded trend statements with strategic implications."""
    trends = []

    # Trend 1: Market concentration
    if sov["is_concentrated"]:
        trends.append(
            {
                "title": "Winner-take-most dynamics are already in play",
                "insight": (
                    f"The top 5 brands command {sov['top5_sov']}% of all AI citations in this category. "
                    f"AI models have formed strong associations with a small group of leaders, and those "
                    f"associations compound with every query answered."
                ),
                "implication": (
                    "For brands outside the top 5, the window to close the gap is narrowing. "
                    "Earned media, structured content, and technical optimization need to move "
                    "in parallel, not in sequence. Treating AEO as a future initiative means "
                    "entering an increasingly expensive fight."
                ),
            }
        )
    else:
        trends.append(
            {
                "title": "AI visibility is still contestable in this category",
                "insight": (
                    f"The top 5 brands hold {sov['top5_sov']}% of AI citations, more distributed than "
                    f"typical mature categories. No single brand has locked in dominant position."
                ),
                "implication": (
                    "This is a genuine opening. Brands that invest in AEO now can reach the top tier "
                    "before the category concentrates. First-mover advantage in AI visibility is real, "
                    "and it is closing fast."
                ),
            }
        )

    # Trend 2: Earned vs owned dynamics
    if earned["earned_pct"] >= 65:
        trends.append(
            {
                "title": "PR and earned media are the primary drivers of AI visibility",
                "insight": (
                    f"{earned['earned_pct']}% of all AI citations reference earned media: "
                    f"editorial coverage, third-party references, and authoritative external sources. "
                    f"AI models calibrate trust based on what credible third parties say about a brand, "
                    f"not what the brand says about itself."
                ),
                "implication": (
                    "Every PR placement in a credible outlet is a citation asset. "
                    "Brands that treat PR and AEO as separate disciplines are leaving significant "
                    "visibility on the table. The most direct path to AI citation is authoritative "
                    "third-party coverage."
                ),
            }
        )
    else:
        trends.append(
            {
                "title": "Owned content plays an unusually strong role in AI citation here",
                "insight": (
                    f"{owned['owned_pct']}% of citations in this category reference brand-owned content, "
                    f"higher than typical. Brands with well-structured, answer-first content are getting "
                    f"cited directly by AI models."
                ),
                "implication": (
                    "Content infrastructure is a direct AI visibility lever in this category. "
                    "Structured, answer-oriented content is what AI models cite. "
                    "Marketing copy does not convert to citations, regardless of volume."
                ),
            }
        )

    # Trend 3: Prompt coverage breadth
    top_brand_prompts = sov.get("top_brand_prompts", 0)
    trends.append(
        {
            "title": "Broad topical authority drives consistent AI citation",
            "insight": (
                f"The category leader appears in {top_brand_prompts}% of all prompts analyzed, "
                f"demonstrating authority across the full range of buyer questions, not just a "
                f"few high-volume queries. Breadth of topic coverage is a key differentiator "
                f"between leaders and challengers."
            ),
            "implication": (
                "Brands optimizing for a narrow set of keywords or topics are capping their "
                "AI visibility ceiling. A content and PR strategy that covers the full topic "
                "cluster map, including long-tail and comparison queries, "
                "is required to compete at the top tier."
            ),
        }
    )

    # Trend 4: Long tail invisibility
    if sov["total_brands"] > 10:
        bottom_brands = sov["leaderboard"][sov["total_brands"] // 2:]
        bottom_sov = round(sum(b["sov_pct"] for b in bottom_brands), 1)
        trends.append(
            {
                "title": "The bottom half of the market is effectively invisible to AI",
                "insight": (
                    f"The bottom {len(bottom_brands)} brands in this analysis share only "
                    f"{bottom_sov}% of AI citations between them. For most brands in this "
                    f"category, AI visibility is not low. It is absent."
                ),
                "implication": (
                    "AI visibility follows a power law. Breaking into the top tier requires "
                    "systematic, sustained investment across earned media, owned content, "
                    "and technical optimization running simultaneously. Incremental changes "
                    "produce incremental results in a field where incremental is indistinguishable from zero."
                ),
            }
        )

    # Trend 5: Topic cluster concentration
    cluster_dist = df.groupby("topic_cluster").size()
    top_cluster = cluster_dist.idxmax()
    top_cluster_pct = round(cluster_dist.max() / cluster_dist.sum() * 100, 1)
    trends.append(
        {
            "title": f"'{top_cluster.replace('_', ' ').title()}' queries drive the most AI citations",
            "insight": (
                f"The '{top_cluster.replace('_', ' ')}' topic cluster accounts for "
                f"{top_cluster_pct}% of citation activity, the highest of any cluster analyzed. "
                f"Brands with strong positioning in this topic cluster benefit "
                f"disproportionately across the query landscape."
            ),
            "implication": (
                "Topic cluster weighting is not uniform. Identifying which question categories "
                "drive the most AI activity in your industry, and ensuring authoritative "
                "coverage of those clusters, is a higher-leverage investment than generic content volume."
            ),
        }
    )

    return trends[:5]


def generate_recommendations(
    sov: dict,
    earned: dict,
    owned: dict,
    trends: list,
    technical: dict = None,
    n_clusters: int = 5,
    top_cluster: dict = None,
) -> list:
    """1-5 prioritized, data-grounded action recommendations.

    All injected values come directly from computed Peec variables — no LLM,
    no generation. Every field falls back to generic text if the underlying
    data is absent or insufficient, so no wrong information is ever shown.
    """

    # ── Rec 1: earned media source injection ─────────────────────────────────
    top_srcs = earned.get("top_sources", [])
    if len(top_srcs) >= 3:
        src_str = (
            f"{top_srcs[0]['domain']}, {top_srcs[1]['domain']}, "
            f"and {top_srcs[2]['domain']}"
        )
        rec1_what = (
            f"{src_str} are the top citation sources in this dataset. These are the "
            f"outlets to prioritize for PR and editorial outreach. Build a dedicated "
            f"strategy targeting these publications specifically. Secure placements that "
            f"position your brand as an authoritative industry voice, not just product "
            f"coverage."
        )
    elif len(top_srcs) >= 1:
        src_str = " and ".join(s["domain"] for s in top_srcs[:2])
        rec1_what = (
            f"{src_str} lead citation activity in this dataset. Build a dedicated PR "
            f"strategy targeting the top-cited outlets. Prioritize placements that "
            f"position your brand as an authoritative industry source, not just product "
            f"coverage."
        )
    else:
        rec1_what = (
            "Identify the top media sources appearing in this report's citation data. "
            "Build a dedicated PR strategy targeting those specific outlets. "
            "Prioritize placements that position your brand as an authoritative industry "
            "source, not just product coverage."
        )

    # ── Rec 2: owned media stats injection ───────────────────────────────────
    # owned_pct lives in the earned analysis dict (earned/owned split), not in analyze_owned_media()
    owned_pct = earned.get("owned_pct", 0)
    top_owned_brand = owned.get("top_owned_brand", "")
    if owned_pct > 0 and top_owned_brand and top_owned_brand != "N/A":
        rec2_why = (
            f"{owned_pct}% of AI citations in this dataset reference brand-owned content. "
            f"{top_owned_brand} leads all brands with the highest owned citation rate, "
            f"demonstrating that well-structured, answer-first content is cited directly by "
            f"AI models. Most brand content is built to persuade, not to inform, which actively "
            f"reduces citation probability regardless of volume."
        )
    elif owned_pct > 0:
        rec2_why = (
            f"{owned_pct}% of AI citations in this dataset reference brand-owned content. "
            f"AI models favor content that directly answers questions in the first paragraph. "
            f"Most brand content is structured to persuade, not to inform, which actively "
            f"reduces citation probability regardless of volume."
        )
    else:
        rec2_why = (
            f"In this dataset, {earned['earned_pct']}% of citations come from earned sources, "
            f"demonstrating that AI models overwhelmingly favor third-party coverage over "
            f"brand-owned content. The gap exists because most brand content is structured "
            f"to persuade, not to inform, which actively reduces citation probability "
            f"regardless of volume."
        )

    # ── Rec 3: top cluster injection ─────────────────────────────────────────
    if top_cluster:
        rec3_why = (
            f"AI citations are distributed unevenly across the {n_clusters} topic "
            f"clusters in this analysis. '{top_cluster['name']}' alone drives "
            f"{top_cluster['pct']}% of citation activity. Brands with no coverage in "
            f"high-volume clusters are completely invisible to that share of buyer queries."
        )
        rec3_what = (
            f"Use the topic clusters in this report as your content and PR brief. "
            f"'{top_cluster['name']}' is the highest-activity cluster in this dataset. "
            f"Authoritative coverage there is the single highest-leverage content "
            f"investment. For every cluster where your brand appears fewer than 3 times: "
            f"create one owned piece and pursue one editorial placement. Treat each "
            f"cluster as a distinct visibility campaign."
        )
    else:
        rec3_why = (
            f"AI citations are distributed unevenly across the {n_clusters} topic "
            f"clusters in this analysis. Brands with coverage gaps in high-activity "
            f"clusters are invisible to a meaningful portion of buyer queries."
        )
        rec3_what = (
            "Use the topic clusters in this report as a content and PR brief. "
            "For each cluster where your brand appears fewer than 3 times: "
            "create one authoritative owned piece and pursue one editorial placement. "
            "Treat each cluster as a distinct visibility campaign."
        )

    # ── Rec 4: technical leader injection ────────────────────────────────────
    top_tech_brand = (technical or {}).get("top_technical_brand", "")
    has_rank_data = (technical or {}).get("has_rank_data", False)
    position_differentiated = (technical or {}).get("position_is_differentiated", False)
    if has_rank_data and top_tech_brand and top_tech_brand != "N/A" and position_differentiated:
        rec4_why = (
            f"Technical signals including schema markup, entity recognition, and structured data "
            f"help AI models identify and trust your brand as a category authority. "
            f"{top_tech_brand} leads this dataset on citation positioning, appearing earlier "
            f"in AI responses than any other brand analyzed. Brands with strong technical "
            f"optimization show better citation consistency across all prompt types."
        )
        rec4_what = (
            f"Study {top_tech_brand}'s technical footprint. They are the current benchmark "
            f"for citation positioning in this category. Add Organization, Product, and FAQ "
            f"schema to all key pages. Verify your brand's Wikipedia entry exists and is accurate. "
            f"Confirm your Google Knowledge Panel is claimed and complete. "
            f"Run a schema validation audit and fix all errors."
        )
    else:
        _proxy_brand = sov.get("top_brand", "")
        if _proxy_brand:
            rec4_why = (
                f"Technical signals including schema markup, entity recognition, and structured data "
                f"help AI models identify and trust your brand as a category authority. "
                f"{_proxy_brand}, the current visibility leader in this dataset, demonstrates "
                f"the compounding advantage of being established as a recognized category entity."
            )
            rec4_what = (
                f"Study {_proxy_brand}'s technical footprint. They are the current benchmark "
                f"for AI visibility in this category. Add Organization, Product, and FAQ "
                f"schema to all key pages. Verify your brand's Wikipedia entry exists and is accurate. "
                f"Confirm your Google Knowledge Panel is claimed and complete. "
                f"Run a schema validation audit and fix all errors."
            )
        else:
            rec4_why = (
                "Technical signals including schema markup, entity recognition, and structured data "
                "help AI models identify and trust your brand as a category authority. "
                "Brands with strong technical optimization show better citation consistency "
                "across all prompt types."
            )
            rec4_what = (
                "Add Organization, Product, and FAQ schema to all key pages. "
                "Verify your brand's Wikipedia entry exists and is accurate. "
                "Confirm your Google Knowledge Panel is claimed and complete. "
                "Run a schema validation audit and fix all errors."
            )

    # ── Rec 5: competitor benchmark injection ────────────────────────────────
    leaderboard = sov.get("leaderboard", [])
    if len(leaderboard) >= 3:
        top5 = [b["brand"] for b in leaderboard[: min(5, len(leaderboard))]]
        brand_str = ", ".join(top5[:-1]) + f", and {top5[-1]}"
        rec5_what = (
            f"Set up a Peec workspace for your brand and benchmark it against "
            f"{brand_str}, the current AI visibility leaders in this analysis. "
            f"Run the AIVx report on a monthly cadence. "
            f"Track: overall rank, SOV%, prompt coverage %, and tier classification. "
            f"Treat AI visibility as a core marketing KPI alongside organic search rank."
        )
    else:
        rec5_what = (
            "Set up a Peec workspace for your brand and top 10 competitors. "
            "Run the AIVx analysis on a monthly cadence. "
            "Track: overall rank, SOV%, prompt coverage %, and tier classification. "
            "Treat AI visibility as a core marketing KPI alongside organic search rank."
        )

    return [
        {
            "priority": 1,
            "title": "Build Earned Media as Your Primary AI Visibility Engine",
            "why": (
                f"{earned['earned_pct']}% of AI citations in this dataset come from "
                f"earned sources. Editorial coverage in authoritative outlets is the "
                f"single highest-leverage action a brand can take to improve AI visibility."
            ),
            "what": rec1_what,
            "owner": "PR / Communications",
            "horizon": "This quarter",
        },
        {
            "priority": 2,
            "title": "Restructure Key Content Pages for Answer-Engine Format",
            "why": rec2_why,
            "what": (
                "Audit your top 20 organic landing pages and resource articles. "
                "Rewrite for answer-first format: question-based H2 headings, "
                "direct answers in the opening paragraph, factual claims with attributable "
                "sources. Add FAQ schema markup to every restructured page."
            ),
            "owner": "Content / SEO",
            "horizon": "This quarter",
        },
        {
            "priority": 3,
            "title": "Map Your Content and PR to the Topic Cluster Map in This Report",
            "why": rec3_why,
            "what": rec3_what,
            "owner": "Content / Marketing",
            "horizon": "Next 6 months",
        },
        {
            "priority": 4,
            "title": "Implement Entity Markup and Structured Data Across Core Pages",
            "why": rec4_why,
            "what": rec4_what,
            "owner": "Development / SEO",
            "horizon": "This quarter",
        },
        {
            "priority": 5,
            "title": "Establish Monthly AI Visibility Tracking Before Your Competitors Do",
            "why": (
                f"You cannot optimize what you do not measure. "
                f"The {sov['total_brands']} brands in this analysis are your competitive "
                f"set in AI. Brands that begin tracking now will have 6-12 months of "
                f"directional data before the category standardizes on AI visibility as a KPI."
            ),
            "what": rec5_what,
            "owner": "Marketing / Analytics",
            "horizon": "Immediate",
        },
    ]

def compute_z_scores(sov: dict, technical: dict, earned: dict) -> list:
    """
    Avenue Z Z-Score: proprietary composite AI visibility index (0-100).

    Four signals, four weights:
      Breadth     40%  -- prompt coverage (% of total prompts brand appeared in)
      Depth       30%  -- citation share relative to the category leader
      Authority   20%  -- citation positioning quality (cited earlier = higher score)
      Positioning 10%  -- earned media ratio (third-party validation drives AI trust)

    All signals are normalized 0-100 before weighting so no single input dominates.
    Returns list of dicts sorted by z_score descending.
    """
    leaderboard = sov.get("leaderboard", [])
    if not leaderboard:
        return []

    # Normalization bounds
    max_citations = leaderboard[0]["citation_count"] if leaderboard else 1
    prompt_pcts = [b.get("prompt_pct", 0) for b in leaderboard]
    max_prompt_pct = max(prompt_pcts) if prompt_pcts else 1

    # Technical authority: brand -> avg_rank (lower rank = cited first = better)
    tech_leaders = (technical or {}).get("technical_leaders", [])
    tech_lookup = {t["brand"]: t["avg_rank"] for t in tech_leaders}
    if len(tech_lookup) > 1:
        min_rank = min(tech_lookup.values())
        max_rank = max(tech_lookup.values())
        rank_range = max_rank - min_rank
    else:
        min_rank = max_rank = rank_range = 1

    # Earned ratio: brand -> earned_pct
    earned_lookup = {
        r["brand"]: r.get("earned_pct", 50)
        for r in earned.get("brand_ratios", [])
    }
    category_earned_pct = earned.get("earned_pct", 50)

    scores = []
    for b in leaderboard:
        brand = b["brand"]

        # Breadth: prompt coverage relative to top performer
        breadth_raw = b.get("prompt_pct", 0)
        breadth = min(100.0, (breadth_raw / max_prompt_pct) * 100) if max_prompt_pct > 0 else 0.0

        # Depth: citation count relative to category leader
        depth = min(100.0, (b["citation_count"] / max_citations) * 100) if max_citations > 0 else 0.0

        # Authority: invert avg_rank so lower rank = higher score
        if brand in tech_lookup and rank_range > 0:
            avg_rank = tech_lookup[brand]
            authority = max(0.0, (1 - (avg_rank - min_rank) / rank_range) * 100)
        elif brand in tech_lookup:
            authority = 100.0  # only brand with rank data
        else:
            authority = 50.0  # neutral default when no position data

        # Positioning: earned citation ratio (higher = more third-party authority)
        earned_pct = earned_lookup.get(brand, category_earned_pct)
        positioning = min(100.0, float(earned_pct))

        # Weighted composite
        z = round(
            breadth * 0.40 +
            depth * 0.30 +
            authority * 0.20 +
            positioning * 0.10,
            1,
        )

        scores.append({
            "brand": brand,
            "z_score": z,
            "breadth": round(breadth, 1),
            "depth": round(depth, 1),
            "authority": round(authority, 1),
            "positioning": round(positioning, 1),
            "tier": b.get("tier", "Developing"),
            "rank": b.get("rank", 0),
            "sov_pct": b.get("sov_pct", 0),
        })

    scores.sort(key=lambda x: x["z_score"], reverse=True)
    return scores


def generate_executive_summary(
    sov: dict,
    earned: dict,
    trends: list,
    recs: list,
    industry: str,
) -> dict:
    """
    3-5 takeaways for a CMO or Head of Growth audience.
    Synthesized directly from existing findings -- no new analysis or LLM.
    Returns dict with: headline, subheadline, takeaways list.
    """
    top_brand = sov["top_brand"]
    top_sov = sov["top_brand_sov"]
    total_brands = sov["total_brands"]
    total_citations = sov["total_citations"]
    earned_pct = earned["earned_pct"]
    top5_sov = sov["top5_sov"]

    takeaways = []

    # Takeaway 1: who leads and concentration
    other_count = max(0, total_brands - 5)
    remaining_pct = round(100 - top5_sov, 1)
    takeaways.append({
        "number": 1,
        "headline": f"{top_brand} leads {industry} AI visibility with {top_sov}% share of voice",
        "detail": (
            f"Across {total_citations:,} AI citations analyzed, {top_brand} captured {top_sov}% "
            f"of all brand mentions. The top 5 brands together hold {top5_sov}% of citations"
            + (
                f", leaving {other_count} other brands competing for the remaining {remaining_pct}%."
                if other_count > 0
                else "."
            )
        ),
        "action": (
            f"Benchmark your brand's share of voice against {top_brand} to quantify the gap "
            f"and identify which topic clusters to prioritize first."
        ),
    })

    # Takeaway 2: earned media is the primary lever
    takeaways.append({
        "number": 2,
        "headline": f"{earned_pct}% of AI citations come from earned media, not brand-owned content",
        "detail": (
            f"AI models predominantly cite third-party sources: editorial coverage, reference sites, "
            f"and user reviews. Brands that dominate AI visibility have strong PR and earned media "
            f"footprints. Owned content alone does not move the needle."
        ),
        "action": (
            "PR and editorial outreach should be treated as a core AI visibility investment, "
            "not a brand-awareness function separate from AEO."
        ),
    })

    # Takeaway 3: market concentration signal
    if sov["is_concentrated"]:
        takeaways.append({
            "number": 3,
            "headline": f"AI visibility in {industry} is concentrated, and the gap is widening",
            "detail": (
                f"The top 5 brands account for {top5_sov}% of all AI citations. "
                f"AI models form associations based on citation history, and those patterns compound. "
                f"Brands outside the top tier will need sustained, coordinated investment to break through."
            ),
            "action": (
                "The cost of entry to the top tier increases every quarter. "
                "An AEO program started now reaches maturity faster than one started in 12 months."
            ),
        })
    else:
        takeaways.append({
            "number": 3,
            "headline": f"AI visibility in {industry} is still contestable, but that window is closing",
            "detail": (
                f"The top 5 brands hold {top5_sov}% of citations, more distributed than mature categories. "
                f"No single brand has established dominant position. This is a genuine opening for "
                f"a well-resourced challenger to reach the top tier."
            ),
            "action": (
                "Act before this category concentrates. The distribution that exists today "
                "will not exist in 12 months."
            ),
        })

    # Takeaway 4: pick a trend that doesn't duplicate takeaways 2 or 3
    # Skip concentration/contestability trends (covered in #3) and earned/owned trends (covered in #2)
    # "winner" covers "Winner-take-most" (concentrated path) which mirrors takeaway 3
    # "owned content" covers the high-owned variant of trend 2 which mirrors takeaway 2
    _skip_keywords = (
        "contestable", "concentrated", "concentration",
        "winner",
        "earned", "pr and", "press",
        "owned content",
    )
    t4 = None
    for t in trends:
        title_lower = t["title"].lower()
        if not any(kw in title_lower for kw in _skip_keywords):
            t4 = t
            break
    if t4 is None and trends:
        # Fallback: use last trend (least likely to overlap with 2/3)
        t4 = trends[-1]
    if t4:
        takeaways.append({
            "number": 4,
            "headline": t4["title"],
            "detail": t4["insight"],
            "action": t4["implication"],
        })

    # Takeaway 5: highest-priority recommendation (no truncation — full action text)
    if recs:
        r = recs[0]
        takeaways.append({
            "number": 5,
            "headline": f"Highest-priority action: {r['title']}",
            "detail": r["why"],
            "action": r["what"],
        })

    return {
        "headline": f"Who owns AI visibility in {industry}, and what it takes to compete",
        "subheadline": (
            f"{total_brands} brands analyzed across {total_citations:,} AI citations. "
            f"ChatGPT data, 7-day collection window."
        ),
        "takeaways": takeaways[:5],
    }


# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────


def _donut_legend() -> dict:
    """Shared legend style for all donut charts."""
    return dict(
        orientation="h",
        font=dict(family="Nunito Sans", color="#FFFFFF", size=12),
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
        x=0.5,
        y=-0.06,
        xanchor="center",
        yanchor="top",
    )


def build_platform_chart() -> str:
    """AI platform market share donut chart."""
    data = MARKET_RESEARCH["platform_share"]
    labels = list(data.keys())
    values = list(data.values())
    colors = BRAND_COLORS[: len(labels)]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color="#000000", width=3)),
            textinfo="percent",
            textposition="inside",
            insidetextfont=dict(family="Nunito Sans", size=13, color="#FFFFFF"),
            outsidetextfont=dict(size=1, color="rgba(0,0,0,0)"),
            hovertemplate="<b>%{label}</b><br>Share: %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_BASE,
        showlegend=True,
        legend=_donut_legend(),
        height=400,
        margin=dict(l=24, r=24, t=24, b=64),
        annotations=[
            dict(
                text="AI Platform<br>Market Share",
                x=0.5, y=0.5,
                xanchor="center", yanchor="middle",
                showarrow=False,
                font=dict(size=12, color="#8A8A8A", family="Nunito Sans"),
            )
        ],
    )
    return pio.to_html(
        fig, include_plotlyjs="cdn", full_html=False, config={"displayModeBar": False}
    )


def build_sov_donut(sov: dict) -> str:
    """Share of voice donut — top 5 brands + Other."""
    top5 = sov["leaderboard"][:5]
    other = max(0, 100 - sum(b["sov_pct"] for b in top5))
    labels = [b["brand"] for b in top5]
    values = [b["sov_pct"] for b in top5]
    colors = BRAND_COLORS[:5]
    if other > 0.5:
        other_count = max(0, sov.get("total_brands", 0) - 5)
        other_label = f"All Other Brands ({other_count})" if other_count > 0 else "All Other Brands"
        labels.append(other_label)
        values.append(round(other, 1))
        colors.append("#3a3a3a")

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color="#000000", width=3)),
            textinfo="percent",
            textposition="inside",
            insidetextfont=dict(family="Nunito Sans", size=13, color="#FFFFFF"),
            outsidetextfont=dict(size=1, color="rgba(0,0,0,0)"),
            hovertemplate="<b>%{label}</b><br>SOV: %{value}%<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_BASE,
        showlegend=True,
        legend=_donut_legend(),
        height=400,
        margin=dict(l=24, r=24, t=24, b=64),
        annotations=[
            dict(
                text=f"<b>{sov['top_brand']}</b><br>{sov['top_brand_sov']}% SOV",
                x=0.5, y=0.5,
                xanchor="center", yanchor="middle",
                showarrow=False,
                font=dict(size=13, color="#FFFFFF", family="Nunito Sans"),
            )
        ],
    )
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False, config={"displayModeBar": False}
    )


def build_leaderboard_chart(sov: dict) -> str:
    """Horizontal bar chart — top 15 brands by citation count."""
    top15 = sov["leaderboard"][:15]
    top15_rev = list(reversed(top15))
    brands = [b["brand"] for b in top15_rev]
    counts = [b["citation_count"] for b in top15_rev]
    bar_colors = [
        BRAND_COLORS[min(b["rank"] - 1, len(BRAND_COLORS) - 1)] for b in top15_rev
    ]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=brands,
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color="rgba(0,0,0,0)", width=0),
            ),
            hovertemplate="<b>%{y}</b><br>Citations: %{x}<extra></extra>",
            text=counts,
            textposition="outside",
            textfont=dict(color="#8A8A8A", size=11),
        )
    )
    fig.update_layout(
        **PLOTLY_BASE,
        height=max(420, len(top15) * 38),
        xaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.06)",
            showgrid=True,
            zeroline=False,
            tickfont=dict(color="#8A8A8A", size=11),
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            tickfont=dict(color="#FFFFFF", size=12, family="Nunito Sans"),
        ),
        bargap=0.38,
    )
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False, config={"displayModeBar": False}
    )


def build_earned_breakdown_chart(earned: dict) -> str:
    """Donut chart — earned media type breakdown."""
    breakdown = earned.get("earned_breakdown", {})
    if not breakdown:
        return "<p style='color:#8A8A8A;padding:24px 0'>No earned media breakdown data available.</p>"

    labels = [k.title() for k in breakdown.keys()]
    values = [breakdown[k]["count"] for k in breakdown.keys()]
    colors = BRAND_COLORS[: len(labels)]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker=dict(colors=colors, line=dict(color="#000000", width=3)),
            textinfo="percent",
            textposition="inside",
            insidetextfont=dict(family="Nunito Sans", size=13, color="#FFFFFF"),
            outsidetextfont=dict(size=1, color="rgba(0,0,0,0)"),
            hovertemplate="<b>%{label}</b><br>Citations: %{value}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_BASE,
        showlegend=True,
        legend=_donut_legend(),
        height=360,
        margin=dict(l=24, r=24, t=24, b=64),
    )
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False, config={"displayModeBar": False}
    )


def build_owned_content_chart(owned: dict) -> str:
    """Horizontal bar — owned content type breakdown."""
    breakdown = owned.get("content_breakdown", [])
    if not breakdown:
        return "<p style='color:#8A8A8A;padding:24px 0'>No owned content data available.</p>"

    labels = [b["type"].replace("_", " ").title() for b in breakdown]
    values = [b["count"] for b in breakdown]
    colors = BRAND_COLORS[: len(labels)]

    fig = go.Figure(
        go.Bar(
            y=labels,
            x=values,
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="<b>%{y}</b><br>Citations: %{x}<extra></extra>",
            text=values,
            textposition="outside",
            textfont=dict(color="#8A8A8A", size=11),
        )
    )
    fig.update_layout(
        **PLOTLY_BASE,
        height=280,
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
            tickfont=dict(color="#8A8A8A"),
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color="#FFFFFF", size=12),
        ),
        bargap=0.4,
    )
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False, config={"displayModeBar": False}
    )


# ─────────────────────────────────────────────────────────────────────────────
# HUB CARD INJECTION
# ─────────────────────────────────────────────────────────────────────────────


def inject_hub_card(hub_path: str, findings: dict, report_filename: str) -> None:
    """
    Auto-inject a report card into the hub index.html.
    Inserts at the top of the grid so newest reports appear first.
    Skips silently if the card already exists (idempotent).
    """
    if not os.path.exists(hub_path):
        print(f"  Hub not found at {hub_path} — skipping card injection.")
        return

    with open(hub_path, "r", encoding="utf-8") as f:
        content = f.read()

    report_href = f"reports/{report_filename}"

    if report_href in content:
        print(f"  Hub card already exists — skipping.")
        return

    sov      = findings["sov"]
    meta     = findings["metadata"]
    date     = findings["report_date"]
    industry = findings["industry"]
    # Card title is always just the industry name — no client name per naming convention
    card_title = industry

    card = (
        f'    <a class="card" href="{report_href}">\n'
        f'      <div class="card-label">{date} · V1</div>\n'
        f'      <div class="card-title">{card_title}</div>\n'
        f'      <div class="card-meta">ChatGPT · AI Citation Analysis</div>\n'
        f'      <div class="badge">Published</div>\n'
        f'      <div class="card-stats">\n'
        f'        <div class="stat"><div class="stat-val">{meta["brands_analyzed"]}</div>'
        f'<div class="stat-lbl">Brands</div></div>\n'
        f'        <div class="stat"><div class="stat-val">{meta["prompts_analyzed"]}</div>'
        f'<div class="stat-lbl">Prompts</div></div>\n'
        f'        <div class="stat"><div class="stat-val">{sov["total_citations"]}</div>'
        f'<div class="stat-lbl">Citations</div></div>\n'
        f'        <div class="stat"><div class="stat-val">{sov["top_brand_sov"]}%</div>'
        f'<div class="stat-lbl">Top SOV</div></div>\n'
        f'      </div>\n'
        f'    </a>'
    )

    updated = content.replace('<div class="grid">', f'<div class="grid">\n{card}', 1)

    if updated == content:
        print("  Could not locate grid in hub — skipping card injection.")
        return

    with open(hub_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"  Hub card injected → {hub_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="AIVx Report Agent v1.0 — Avenue Z",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--industry",
        required=True,
        help='Industry label for the report (e.g. "Fintech: Payments")',
    )
    parser.add_argument(
        "--peec",
        default=None,
        help="Path to Peec workspace CSV export (optional — omit to pull live from API via .env)",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="Peec project ID (overrides PEEC_PROJECT_ID in .env — use this to switch clients)",
    )
    parser.add_argument(
        "--prior-pdf",
        default=None,
        help="Path to prior-year PDF report for year-over-year comparison",
    )
    parser.add_argument(
        "--output",
        default="../outputs/reports",
        help="Output directory for the generated HTML report",
    )
    parser.add_argument(
        "--hub",
        default=None,
        help="Path to hub index.html — auto-injects a card for this report when provided",
    )
    parser.add_argument(
        "--report-slug",
        default=None,
        help=(
            "Override the filename slug (e.g. 'renaissance-dma'). "
            "Use this so each client gets a unique file without changing the industry display label. "
            "If omitted, slug is derived from --industry."
        ),
    )
    parser.add_argument(
        "--client",
        default=None,
        help=(
            "Client/workspace label shown in the hub card title (e.g. 'Renaissance'). "
            "Appended after the industry: 'Digital Marketing Agencies · Renaissance'. "
            "If omitted, only the industry label is shown."
        ),
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

    print(f"\n  AIVx Report Agent v1.0 — Avenue Z")
    print(f"  Industry : {args.industry}")
    print(f"  Input    : {args.peec or 'Live Peec API'}")
    print(f"  Output   : {args.output}")
    print("  " + "─" * 42)

    # 1. Load
    workspace_meta = None
    if args.peec:
        print("  Loading Peec data from CSV...")
        df = load_peec_data(args.peec)
    else:
        api_key = os.getenv("PEEC_API_KEY")
        if not api_key:
            raise SystemExit(
                "PEEC_API_KEY not found. Add it to .env or set it as an environment variable."
            )
        project_id = resolve_project_id(api_key, args.project_id)
        print("  Fetching live data from Peec API...")
        df, workspace_meta = fetch_peec_data(api_key, project_id)
    n_prompts = df["prompt_id"].nunique()
    n_brands = df["brand"].nunique()
    print(f"    {len(df)} citations | {n_prompts} prompts | {n_brands} brands")

    # 2. Analyze
    print("  Running analysis...")
    topic_clusters = sorted(df["topic_cluster"].unique().tolist())
    sov = analyze_share_of_voice(df)
    earned = analyze_earned_media(df)
    owned = analyze_owned_media(df)
    technical = analyze_technical_factors(df)
    trends = synthesize_trends(df, sov, earned, owned)

    # Compute cluster percentages for all clusters (used in rec injection + renderer)
    _cluster_counts = df.groupby("topic_cluster").size().sort_values(ascending=False)
    top_cluster = (
        {
            "name": _cluster_counts.index[0],
            "count": int(_cluster_counts.iloc[0]),
            "pct": round(_cluster_counts.iloc[0] / len(df) * 100, 1),
        }
        if len(_cluster_counts) > 0
        else None
    )
    # All cluster percentages dict: {cluster_name: pct} — passed to renderer
    _total_citations = len(df)
    cluster_pcts = {
        str(cluster): round(int(count) / _total_citations * 100, 1)
        for cluster, count in _cluster_counts.items()
    } if _total_citations > 0 else {}

    recs = generate_recommendations(
        sov, earned, owned, trends,
        technical=technical,
        n_clusters=len(topic_clusters),
        top_cluster=top_cluster,
    )
    z_scores = compute_z_scores(sov, technical, earned)
    exec_summary = generate_executive_summary(sov, earned, trends, recs, args.industry)
    yoy = analyze_yoy(sov, prior_pdf_path=args.prior_pdf)
    print(f"    Leader: {sov['top_brand']} ({sov['top_brand_sov']}% SOV)")
    print(f"    Top 5 concentration: {sov['top5_sov']}%")
    if z_scores:
        print(f"    Z-Score leader: {z_scores[0]['brand']} ({z_scores[0]['z_score']})")

    # 3. Build charts
    print("  Building charts...")
    charts = {
        "platform": build_platform_chart(),
        "sov_donut": build_sov_donut(sov),
        "leaderboard_bar": build_leaderboard_chart(sov),
        "earned_breakdown": build_earned_breakdown_chart(earned),
        "owned_content": build_owned_content_chart(owned),
    }

    # 4. Assemble findings package
    # Workspace prompt count: use total workspace prompts (includes prompts with 0 citations)
    ws_prompt_count = (
        workspace_meta["total_workspace_prompts"] if workspace_meta else n_prompts
    )
    # Data period: actual date range when live API, generic label when CSV
    if workspace_meta:
        data_period = f"{workspace_meta['start_date']} to {workspace_meta['end_date']}"
    else:
        data_period = "7-day collection window"
    # Example prompts: built from workspace prompt list (not citation data)
    if workspace_meta:
        ptm = workspace_meta["prompt_text_map"]
        pcm = workspace_meta["prompt_cluster_map"]
        example_prompts: dict = {}
        for pid, cluster in pcm.items():
            if cluster in topic_clusters:
                bucket = example_prompts.setdefault(cluster, [])
                if len(bucket) < 2:
                    text = ptm.get(pid, "")
                    if text:
                        bucket.append(text)
        # Fill any cluster still missing prompts from citation data as fallback
        for cluster in topic_clusters:
            if not example_prompts.get(cluster):
                example_prompts[cluster] = (
                    df[df["topic_cluster"] == cluster]["prompt_text"].unique()[:2].tolist()
                )
    else:
        example_prompts = {
            cluster: df[df["topic_cluster"] == cluster]["prompt_text"].unique()[:2].tolist()
            for cluster in topic_clusters
        }

    findings = {
        "industry": args.industry,
        "client": args.client,  # e.g. "Renaissance" — None if not specified
        "report_date": datetime.now().strftime("%B %Y"),
        "metadata": {
            "brands_analyzed": sov["total_brands"],
            "prompts_analyzed": ws_prompt_count,
            "platform": "ChatGPT",
            "data_period": data_period,
            "topic_clusters": topic_clusters,
            "cluster_pcts": cluster_pcts,
            "example_prompts": example_prompts,
        },
        "sov": sov,
        "earned": earned,
        "owned": owned,
        "technical": technical,
        "trends": trends,
        "yoy": yoy,
        "recommendations": recs,
        "z_scores": z_scores,
        "executive_summary": exec_summary,
        "market_research": MARKET_RESEARCH,
        "charts": charts,
    }

    # 5. Render HTML
    print("  Rendering report...")
    from renderer import render_report
    html = render_report(findings)

    # 6. Save
    os.makedirs(args.output, exist_ok=True)
    if args.report_slug:
        slug = re.sub(r"[^a-z0-9]+", "-", args.report_slug.lower()).strip("-")
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", args.industry.lower()).strip("-")
    filename = f"aivx-{slug}-{datetime.now().strftime('%Y-%m')}.html"
    output_path = os.path.join(args.output, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  Report saved: {output_path}")

    # 7. Inject hub card (if --hub path provided)
    if args.hub:
        inject_hub_card(args.hub, findings, filename)

    print(f"  Open in your browser to review.\n")


if __name__ == "__main__":
    main()
