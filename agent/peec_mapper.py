#!/usr/bin/env python3
"""
peec_mapper.py — Peec Dashboard CSV → AIVx Agent Format
Avenue Z · AIVx Report Pipeline

Confirmed for actual Peec export format (2026-05-20).

CONFIRMED CSV SCHEMAS:

  Prompts CSV (export from General > Prompts):
    status, topic_id, topic_name, id, prompt, visibility, visibility_delta,
    sentiment, sentiment_delta, position, position_delta, mentions, volume,
    tags, location, share_of_voice, share_of_voice_delta, added_at

  URLs CSV (export from Sources > URLs):
    url, domain, url_classification, domain_classification, title, type,
    mentioned, mentions, retrievals, citation_rate

  Domains CSV (export from Sources > Domains):
    domain, type, retrieved, retrieval_rate, citation_rate, citation_rate_delta

HOW TO EXPORT FROM PEEC DASHBOARD:
  Filters to set BEFORE every export:
    - Brand:  All brands
    - Date:   Last 7 days
    - Model:  ChatGPT ONLY
    - Tags:   All Tags
    - Topics: All Topics

  1. General > Prompts    → export CSV → peec_prompts.csv
  2. Sources > URLs       → export CSV → peec_urls.csv
  3. Sources > Domains    → export CSV → peec_domains.csv

USAGE:
  python peec_mapper.py \\
      --prompts peec_prompts.csv \\
      --urls    peec_urls.csv \\
      --domains peec_domains.csv \\
      --owned-brand "Chime" \\
      --output  peec_mapped.csv

  Then run the agent:
  python agent.py \\
      --industry "Fintech: Digital Banks" \\
      --peec peec_mapped.csv \\
      --report-slug "digital-banks-2026-05" \\
      --output /Users/thomaschangavenuez/Desktop/aivx-reports/reports \\
      --hub /Users/thomaschangavenuez/Desktop/aivx-reports/index.html

METHODOLOGY NOTE:
  The live API path creates one row per brand per ChatGPT conversation (~800 total).
  This CSV path creates one row per brand per prompt (binary presence from mentions column).
  Relative SOV rankings are preserved. Absolute citation counts differ from live API runs.
  This is the correct workaround while Peec's pitch workspace API limit is unresolved.
"""

import argparse
import os
import sys

import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN TYPE MAP
# Peec domain_classification → agent media_type
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_TYPE_MAP = {
    "editorial":   "editorial",
    "reference":   "reference",
    "corporate":   "direct recommendation",
    "you":         "owned_blog",
    "other":       "editorial",
    "ugc":         "ugc",
    "alternative": "editorial",
    "listicle":    "editorial",
}


# ─────────────────────────────────────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def load_prompts(path: str) -> pd.DataFrame:
    """Load Peec prompts export. Filters to active prompts only."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    before = len(df)
    if "status" in df.columns:
        df = df[df["status"].str.lower() == "active"].copy()
    print(f"  Prompts: {len(df)} active rows (filtered from {before})")
    print(f"  Columns: {list(df.columns)}")

    # Validate required columns
    for col in ["id", "prompt", "topic_name", "mentions"]:
        if col not in df.columns:
            raise ValueError(
                f"Required column '{col}' not found in prompts CSV.\n"
                f"Found: {list(df.columns)}"
            )
    return df


def load_brand_url_map(path: str) -> dict:
    """
    Build {brand_lower: top_url} from URLs CSV.
    Picks the highest-retrieval URL per brand.
    """
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    if "retrievals" in df.columns:
        df["retrievals"] = pd.to_numeric(df["retrievals"], errors="coerce").fillna(0)
        df = df.sort_values("retrievals", ascending=False)

    brand_url_map = {}
    for _, row in df.iterrows():
        url = str(row.get("url", "")).strip()
        mentions_raw = row.get("mentions", "")
        if not url or pd.isna(mentions_raw) or not str(mentions_raw).strip():
            continue
        brands = [b.strip() for b in str(mentions_raw).split(",") if b.strip()]
        for brand in brands:
            key = brand.lower()
            if key not in brand_url_map:
                brand_url_map[key] = url

    print(f"  URLs: {len(brand_url_map)} brand→URL mappings")
    return brand_url_map


def load_domain_type_map(path: str) -> dict:
    """Build {domain: media_type} from Domains CSV."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    result = {}
    for _, row in df.iterrows():
        domain = str(row.get("domain", "")).strip().lower()
        dtype  = str(row.get("type", "")).strip().lower()
        result[domain] = DOMAIN_TYPE_MAP.get(dtype, "editorial")

    print(f"  Domains: {len(result)} domain→media_type mappings")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_domain(url: str) -> str:
    """Extract root domain from a URL string."""
    if not url:
        return ""
    url = url.lower().split("//")[-1].split("/")[0]
    parts = url.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else url


# ─────────────────────────────────────────────────────────────────────────────
# CORE MAPPER
# ─────────────────────────────────────────────────────────────────────────────

def map_to_citations(
    prompts_df: pd.DataFrame,
    brand_url_map: dict,
    domain_type_map: dict,
    owned_brand: str,
) -> pd.DataFrame:
    """
    Expand Peec prompts CSV into citation-level rows for agent.py.

    For each prompt row, parses the comma-separated 'mentions' column
    and creates one output row per brand — one row = one citation.

    owned_brand (e.g. "Chime") gets is_owned=1; all others get is_owned=0.
    citation_rank uses the owned brand's 'position' value; others default to 1.
    """
    owned_lower = owned_brand.lower().strip()
    rows = []

    for _, row in prompts_df.iterrows():
        prompt_id     = str(row["id"]).strip()
        prompt_text   = str(row["prompt"]).strip()
        topic_cluster = str(row.get("topic_name", "General")).strip() or "General"

        # Owned brand's citation rank for this prompt
        try:
            owned_rank = int(round(float(row.get("position") or 1)))
        except (ValueError, TypeError):
            owned_rank = 1

        mentions_raw = row.get("mentions", "")
        if pd.isna(mentions_raw) or not str(mentions_raw).strip():
            continue

        brands = [b.strip() for b in str(mentions_raw).split(",") if b.strip()]

        for brand in brands:
            is_owned = 1 if brand.lower() == owned_lower else 0

            # Cited URL — top URL where this brand appears
            cited_url = brand_url_map.get(brand.lower(), "")

            # Media type
            if is_owned:
                media_type    = "owned_blog"
                citation_rank = owned_rank
            else:
                domain        = extract_domain(cited_url)
                media_type    = domain_type_map.get(domain, "editorial")
                citation_rank = 1

            rows.append({
                "prompt_id":     prompt_id,
                "prompt_text":   prompt_text,
                "topic_cluster": topic_cluster,
                "platform":      "chatgpt",
                "brand":         brand,
                "cited_url":     cited_url,
                "media_type":    media_type,
                "is_owned":      is_owned,
                "citation_rank": citation_rank,
            })

    df_out = pd.DataFrame(rows)

    if len(df_out) == 0:
        return df_out

    # Print summary
    print(f"\n  Expansion: {len(prompts_df)} prompts → {len(df_out)} citation rows")
    print(f"  Brands:  {df_out['brand'].nunique()}")
    print(f"  Clusters: {sorted(df_out['topic_cluster'].unique())}")
    print(f"  Owned ({owned_brand}): {int(df_out['is_owned'].sum())} rows")
    print(f"  Earned:  {int((df_out['is_owned'] == 0).sum())} rows")
    print(f"\n  Top 10 brands by prompt appearances:")
    top = df_out.groupby("brand").size().sort_values(ascending=False).head(10)
    for brand, count in top.items():
        print(f"    {brand}: {count}")

    return df_out


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="peec_mapper.py — Transform Peec dashboard exports into AIVx agent CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--prompts",     required=True,              help="Peec prompts export CSV")
    parser.add_argument("--urls",        default=None,               help="Peec URLs export CSV (optional — enriches media type)")
    parser.add_argument("--domains",     default=None,               help="Peec domains export CSV (optional — enriches media type)")
    parser.add_argument("--owned-brand", default="Chime",            help="Brand marked as You in this workspace (default: Chime)")
    parser.add_argument("--output",      default="peec_mapped.csv",  help="Output CSV path (default: peec_mapped.csv)")
    args = parser.parse_args()

    print(f"\n  peec_mapper.py — Avenue Z AIVx Pipeline")
    print(f"  Owned brand : {args.owned_brand}")
    print(f"  Output      : {args.output}")
    print(f"  {'─' * 42}")

    if not os.path.exists(args.prompts):
        print(f"  ERROR: --prompts file not found: {args.prompts}")
        sys.exit(1)

    # Load
    prompts_df = load_prompts(args.prompts)

    brand_url_map = {}
    if args.urls:
        if os.path.exists(args.urls):
            brand_url_map = load_brand_url_map(args.urls)
        else:
            print(f"  WARNING: --urls file not found ({args.urls}) — skipping URL enrichment")

    domain_type_map = {}
    if args.domains:
        if os.path.exists(args.domains):
            domain_type_map = load_domain_type_map(args.domains)
        else:
            print(f"  WARNING: --domains file not found ({args.domains}) — skipping domain enrichment")

    # Map
    df_out = map_to_citations(prompts_df, brand_url_map, domain_type_map, args.owned_brand)

    if len(df_out) == 0:
        print(
            "\n  ERROR: No citation rows produced.\n"
            "  Check that your prompts CSV has a 'mentions' column with brand names.\n"
            "  Sample of your prompts CSV columns: " + str(list(prompts_df.columns))
        )
        sys.exit(1)

    # Save
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    df_out.to_csv(args.output, index=False)

    print(f"\n  Saved: {args.output}")
    print(f"\n  Next — run the agent:")
    print(f"    cd /Users/thomaschangavenuez/Desktop/asana-assistant/tasks/aivx-report-creation/agent")
    print(f"    python agent.py \\")
    print(f'        --industry "Fintech: Digital Banks" \\')
    print(f"        --peec {os.path.abspath(args.output)} \\")
    print(f'        --report-slug "digital-banks-2026-05" \\')
    print(f"        --output /Users/thomaschangavenuez/Desktop/aivx-reports/reports \\")
    print(f"        --hub /Users/thomaschangavenuez/Desktop/aivx-reports/index.html\n")


if __name__ == "__main__":
    main()
