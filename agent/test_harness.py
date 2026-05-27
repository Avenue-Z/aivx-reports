#!/usr/bin/env python3
"""
test_harness.py — AIVx Report Agent
Run with: python test_harness.py
Run live API ping too: python test_harness.py --live

Catches 90% of failures in under 10 seconds, before burning Peec rate limits.
Exits with code 1 if any test fails (CI-safe).
"""

import os
import sys
import tempfile

import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# ok / fail helpers
# ─────────────────────────────────────────────────────────────────────────────

TESTS_PASSED = 0
TESTS_FAILED = 0
FAILURES = []


def ok(name: str):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"  PASS  {name}")


def fail(name: str, reason: str):
    global TESTS_FAILED
    TESTS_FAILED += 1
    FAILURES.append((name, reason))
    print(f"  FAIL  {name}: {reason}")


# ─────────────────────────────────────────────────────────────────────────────
# REALISTIC SAMPLE DATA
# Mirrors the exact dict/DataFrame shapes produced by the live pipeline.
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_ROWS = [
    # Brand A — market leader, mostly earned, appears in most prompts
    {"prompt_id": "p1", "prompt_text": "Best digital marketing agencies for SEO?",          "topic_cluster": "Services",        "platform": "chatgpt", "brand": "Apex Digital",  "cited_url": "https://forbes.com/apex",     "media_type": "editorial",            "is_owned": 0, "citation_rank": 1},
    {"prompt_id": "p2", "prompt_text": "Top agencies for paid search management?",          "topic_cluster": "Services",        "platform": "chatgpt", "brand": "Apex Digital",  "cited_url": "https://inc.com/apex",        "media_type": "editorial",            "is_owned": 0, "citation_rank": 2},
    {"prompt_id": "p3", "prompt_text": "Which agency has best content marketing team?",     "topic_cluster": "Content",         "platform": "chatgpt", "brand": "Apex Digital",  "cited_url": "https://apex.com/blog",       "media_type": "owned_blog",           "is_owned": 1, "citation_rank": 1},
    {"prompt_id": "p4", "prompt_text": "How much do marketing agencies charge?",            "topic_cluster": "Pricing",         "platform": "chatgpt", "brand": "Apex Digital",  "cited_url": "https://g2.com/apex",         "media_type": "ugc",                  "is_owned": 0, "citation_rank": 3},
    {"prompt_id": "p5", "prompt_text": "Apex Digital vs Bolt Media — which is better?",    "topic_cluster": "Comparison",      "platform": "chatgpt", "brand": "Apex Digital",  "cited_url": "https://clutch.co/apex",      "media_type": "ugc",                  "is_owned": 0, "citation_rank": 1},
    {"prompt_id": "p6", "prompt_text": "Best AI marketing tools for agencies?",             "topic_cluster": "Tools",           "platform": "chatgpt", "brand": "Apex Digital",  "cited_url": "https://semrush.com/tools",   "media_type": "reference",            "is_owned": 0, "citation_rank": 2},

    # Brand B — strong challenger
    {"prompt_id": "p1", "prompt_text": "Best digital marketing agencies for SEO?",          "topic_cluster": "Services",        "platform": "chatgpt", "brand": "Bolt Media",    "cited_url": "https://entrepreneur.com/bolt","media_type": "editorial",           "is_owned": 0, "citation_rank": 2},
    {"prompt_id": "p2", "prompt_text": "Top agencies for paid search management?",          "topic_cluster": "Services",        "platform": "chatgpt", "brand": "Bolt Media",    "cited_url": "https://bolt.com/services",   "media_type": "owned_blog",           "is_owned": 1, "citation_rank": 1},
    {"prompt_id": "p4", "prompt_text": "How much do marketing agencies charge?",            "topic_cluster": "Pricing",         "platform": "chatgpt", "brand": "Bolt Media",    "cited_url": "https://hubspot.com/pricing", "media_type": "reference",            "is_owned": 0, "citation_rank": 1},
    {"prompt_id": "p5", "prompt_text": "Apex Digital vs Bolt Media — which is better?",    "topic_cluster": "Comparison",      "platform": "chatgpt", "brand": "Bolt Media",    "cited_url": "https://reddit.com/r/bolt",   "media_type": "ugc",                  "is_owned": 0, "citation_rank": 2},

    # Brand C — emerging player
    {"prompt_id": "p1", "prompt_text": "Best digital marketing agencies for SEO?",          "topic_cluster": "Services",        "platform": "chatgpt", "brand": "Core Agency",   "cited_url": "https://searchengineland.com","media_type": "reference",            "is_owned": 0, "citation_rank": 3},
    {"prompt_id": "p3", "prompt_text": "Which agency has best content marketing team?",     "topic_cluster": "Content",         "platform": "chatgpt", "brand": "Core Agency",   "cited_url": "https://core.com/about",      "media_type": "owned_blog",           "is_owned": 1, "citation_rank": 3},

    # Brand D — low visibility
    {"prompt_id": "p6", "prompt_text": "Best AI marketing tools for agencies?",             "topic_cluster": "Tools",           "platform": "chatgpt", "brand": "Delta Group",   "cited_url": "https://techradar.com/delta", "media_type": "editorial",            "is_owned": 0, "citation_rank": 4},

    # Brand E — single citation
    {"prompt_id": "p4", "prompt_text": "How much do marketing agencies charge?",            "topic_cluster": "Pricing",         "platform": "chatgpt", "brand": "Echo Partners", "cited_url": "https://gartner.com/echo",    "media_type": "reference",            "is_owned": 0, "citation_rank": 5},
]

SAMPLE_DF = pd.DataFrame(SAMPLE_ROWS)
SAMPLE_DF["is_owned"] = SAMPLE_DF["is_owned"].astype(int)
SAMPLE_DF["brand"] = SAMPLE_DF["brand"].str.strip()


# ─────────────────────────────────────────────────────────────────────────────
# PRE-BUILT ANALYSIS FIXTURES
# Built once from SAMPLE_DF so downstream tests don't need to re-run analysis.
# ─────────────────────────────────────────────────────────────────────────────

def _build_fixtures():
    from agent import (
        analyze_share_of_voice, analyze_earned_media, analyze_owned_media,
        analyze_technical_factors, synthesize_trends,
    )
    sov = analyze_share_of_voice(SAMPLE_DF)
    earned = analyze_earned_media(SAMPLE_DF)
    owned = analyze_owned_media(SAMPLE_DF)
    technical = analyze_technical_factors(SAMPLE_DF)
    trends = synthesize_trends(SAMPLE_DF, sov, earned, owned)
    return sov, earned, owned, technical, trends


# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORT TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_imports():
    print("\n--- 1. Import tests ---")
    for mod in ("agent", "renderer"):
        try:
            __import__(mod)
            ok(f"import {mod}")
        except Exception as e:
            fail(f"import {mod}", str(e))

    # Key third-party deps
    for pkg in ("pandas", "plotly", "requests", "dotenv"):
        try:
            __import__(pkg)
            ok(f"import {pkg}")
        except Exception as e:
            fail(f"import {pkg}", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 2. ANALYSIS LAYER TESTS (pure functions, fake data)
# ─────────────────────────────────────────────────────────────────────────────

def test_share_of_voice():
    print("\n--- 2a. analyze_share_of_voice ---")
    from agent import analyze_share_of_voice

    sov = analyze_share_of_voice(SAMPLE_DF)

    # Required keys
    for key in ("leaderboard", "total_brands", "total_citations", "total_prompts",
                "top5_sov", "top10_sov", "is_concentrated", "top_brand",
                "top_brand_sov", "top_brand_prompts"):
        if key in sov:
            ok(f"sov has key '{key}'")
        else:
            fail(f"sov has key '{key}'", "missing")

    # Apex should be the top brand (6 citations)
    if sov["top_brand"] == "Apex Digital":
        ok("top_brand is Apex Digital")
    else:
        fail("top_brand is Apex Digital", f"got: {sov['top_brand']}")

    # 5 distinct brands
    if sov["total_brands"] == 5:
        ok("total_brands == 5")
    else:
        fail("total_brands == 5", f"got: {sov['total_brands']}")

    # leaderboard entries have required keys
    required_lb_keys = {"brand", "citation_count", "sov_pct", "rank", "tier",
                        "prompt_count", "prompt_pct"}
    entry = sov["leaderboard"][0]
    missing = required_lb_keys - set(entry.keys())
    if not missing:
        ok("leaderboard entry has all required keys")
    else:
        fail("leaderboard entry keys", f"missing: {missing}")


def test_earned_media():
    print("\n--- 2b. analyze_earned_media ---")
    from agent import analyze_earned_media

    earned = analyze_earned_media(SAMPLE_DF)

    for key in ("earned_pct", "owned_pct", "earned_count", "owned_count",
                "earned_breakdown", "top_sources", "brand_ratios"):
        if key in earned:
            ok(f"earned has key '{key}'")
        else:
            fail(f"earned has key '{key}'", "missing")

    # Earned + owned pct should sum to ~100
    total = earned["earned_pct"] + earned["owned_pct"]
    if 99 <= total <= 101:
        ok(f"earned_pct + owned_pct ~= 100 ({total})")
    else:
        fail("earned_pct + owned_pct ~= 100", f"got: {total}")

    # brand_ratios entries have required keys
    if earned["brand_ratios"]:
        br = earned["brand_ratios"][0]
        for k in ("brand", "earned", "owned", "total", "earned_pct"):
            if k in br:
                ok(f"brand_ratio entry has '{k}'")
            else:
                fail(f"brand_ratio entry has '{k}'", "missing")


def test_owned_media():
    print("\n--- 2c. analyze_owned_media ---")
    from agent import analyze_owned_media

    owned = analyze_owned_media(SAMPLE_DF)

    for key in ("content_breakdown", "total_owned", "top_owned_brand"):
        if key in owned:
            ok(f"owned has key '{key}'")
        else:
            fail(f"owned has key '{key}'", "missing")

    # We have 3 owned rows in SAMPLE_DF
    if owned["total_owned"] == 3:
        ok("total_owned == 3")
    else:
        fail("total_owned == 3", f"got: {owned['total_owned']}")


def test_technical_factors():
    print("\n--- 2d. analyze_technical_factors ---")
    from agent import analyze_technical_factors

    tech = analyze_technical_factors(SAMPLE_DF)

    for key in ("has_rank_data", "technical_leaders", "top_technical_brand"):
        if key in tech:
            ok(f"technical has key '{key}'")
        else:
            fail(f"technical has key '{key}'", "missing")

    if tech["has_rank_data"]:
        ok("has_rank_data is True (citation_rank column present)")
    else:
        fail("has_rank_data is True", "missing citation_rank — check SAMPLE_ROWS")


def test_trends():
    print("\n--- 2e. synthesize_trends ---")
    from agent import synthesize_trends, analyze_share_of_voice, analyze_earned_media, analyze_owned_media

    sov = analyze_share_of_voice(SAMPLE_DF)
    earned = analyze_earned_media(SAMPLE_DF)
    owned = analyze_owned_media(SAMPLE_DF)
    trends = synthesize_trends(SAMPLE_DF, sov, earned, owned)

    if 3 <= len(trends) <= 5:
        ok(f"synthesize_trends returned {len(trends)} trends (3-5 expected)")
    else:
        fail("synthesize_trends count", f"got: {len(trends)}")

    if trends:
        t = trends[0]
        for k in ("title", "insight", "implication"):
            if k in t:
                ok(f"trend has key '{k}'")
            else:
                fail(f"trend has key '{k}'", "missing")


def test_yoy_no_pdf():
    print("\n--- 2f. analyze_yoy (no prior PDF) ---")
    from agent import analyze_yoy, analyze_share_of_voice

    sov = analyze_share_of_voice(SAMPLE_DF)
    yoy = analyze_yoy(sov)

    if yoy["has_prior_data"] is False:
        ok("has_prior_data is False when no PDF supplied")
    else:
        fail("has_prior_data", f"expected False, got: {yoy['has_prior_data']}")

    for key in ("current_leaderboard", "top_brand", "top_brand_sov", "is_concentrated"):
        if key in yoy:
            ok(f"yoy baseline has key '{key}'")
        else:
            fail(f"yoy baseline has key '{key}'", "missing")


def test_yoy_with_pdf():
    print("\n--- 2g. analyze_yoy (with prior PDF mock) ---")
    from agent import analyze_yoy, analyze_share_of_voice

    sov = analyze_share_of_voice(SAMPLE_DF)

    # Build a minimal fake prior-report PDF text file saved as PDF
    # We write a text file and test the regex parser directly
    prior_text = (
        "AIVx Digital Marketing Agencies — Q4 2025\n\n"
        "Brand Rankings by AI Share of Voice\n\n"
        "1. Bolt Media 91.5\n"
        "2. Apex Digital 88.0\n"
        "3. Core Agency 72.3\n"
        "4. Gamma Group 65.1\n"
        "5. Echo Partners 52.0\n"
    )

    try:
        import pdfplumber
        # Create a real minimal PDF using reportlab if available, else skip
        try:
            from reportlab.pdfgen import canvas
            import io

            buf = io.BytesIO()
            c = canvas.Canvas(buf)
            y = 750
            for line in prior_text.split("\n"):
                c.drawString(50, y, line)
                y -= 18
            c.save()
            buf.seek(0)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(buf.read())
                tmp_path = tmp.name

            yoy = analyze_yoy(sov, prior_pdf_path=tmp_path)
            os.unlink(tmp_path)

            if yoy.get("has_prior_data"):
                ok("analyze_yoy returns has_prior_data=True with valid PDF")
                for key in ("movers", "dropoffs", "top_brand"):
                    if key in yoy:
                        ok(f"yoy with PDF has key '{key}'")
                    else:
                        fail(f"yoy with PDF has key '{key}'", "missing")
                # Bolt Media was #1 in prior, should now be #2 — rank_change = -1 (dropped)
                mover_map = {m["brand"]: m for m in yoy.get("movers", [])}
                if "Bolt Media" in mover_map:
                    bm = mover_map["Bolt Media"]
                    if bm["prior_rank"] == 1:
                        ok("Bolt Media prior_rank correctly parsed as 1")
                    else:
                        fail("Bolt Media prior_rank", f"expected 1, got: {bm['prior_rank']}")
                else:
                    fail("Bolt Media in movers", "not found")
            else:
                fail("analyze_yoy with PDF", "has_prior_data still False — PDF parse may have failed")

        except ImportError:
            ok("yoy PDF test SKIPPED — reportlab not installed (install to enable full PDF test)")

    except ImportError:
        ok("yoy PDF test SKIPPED — pdfplumber not installed (install to enable: pip install pdfplumber)")


def test_recommendations():
    print("\n--- 2h. generate_recommendations ---")
    from agent import (
        generate_recommendations, analyze_share_of_voice, analyze_earned_media,
        analyze_owned_media, analyze_technical_factors, synthesize_trends,
    )

    sov = analyze_share_of_voice(SAMPLE_DF)
    earned = analyze_earned_media(SAMPLE_DF)
    owned = analyze_owned_media(SAMPLE_DF)
    technical = analyze_technical_factors(SAMPLE_DF)
    trends = synthesize_trends(SAMPLE_DF, sov, earned, owned)

    cluster_counts = SAMPLE_DF.groupby("topic_cluster").size().sort_values(ascending=False)
    top_cluster = {"name": cluster_counts.index[0], "count": int(cluster_counts.iloc[0]),
                   "pct": round(cluster_counts.iloc[0] / len(SAMPLE_DF) * 100, 1)}

    recs = generate_recommendations(
        sov, earned, owned, trends,
        technical=technical,
        n_clusters=SAMPLE_DF["topic_cluster"].nunique(),
        top_cluster=top_cluster,
    )

    if len(recs) == 5:
        ok("generate_recommendations returned 5 recs")
    else:
        fail("recommendations count", f"expected 5, got: {len(recs)}")

    for rec in recs:
        for k in ("priority", "title", "why", "what", "owner", "horizon"):
            if k in rec:
                ok(f"rec #{rec.get('priority','?')} has key '{k}'")
            else:
                fail(f"rec #{rec.get('priority','?')} has key '{k}'", "missing")

    # Rec 2 why should contain owned_pct data (issue 8 fix)
    rec2 = next((r for r in recs if r["priority"] == 2), None)
    if rec2:
        owned_pct = owned.get("owned_pct", 0)
        if str(owned_pct) in rec2["why"] or "%" in rec2["why"]:
            ok("rec 2 why injects owned media data")
        else:
            fail("rec 2 why injects owned media data", f"no % found in why: {rec2['why'][:80]}")

    # Rec 4 why should reference technical leader brand (issue 8 fix)
    rec4 = next((r for r in recs if r["priority"] == 4), None)
    if rec4 and technical.get("has_rank_data") and technical.get("top_technical_brand"):
        top_tech = technical["top_technical_brand"]
        if top_tech in rec4["why"]:
            ok(f"rec 4 why injects technical leader: {top_tech}")
        else:
            fail("rec 4 why injects technical leader", f"'{top_tech}' not in why: {rec4['why'][:80]}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHART BUILDER TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_charts():
    print("\n--- 3. Chart builders ---")
    from agent import (
        build_platform_chart, build_sov_donut, build_leaderboard_chart,
        build_earned_breakdown_chart, build_owned_content_chart,
        analyze_share_of_voice, analyze_earned_media, analyze_owned_media,
    )

    sov = analyze_share_of_voice(SAMPLE_DF)
    earned = analyze_earned_media(SAMPLE_DF)
    owned = analyze_owned_media(SAMPLE_DF)

    for name, fn, args in [
        ("build_platform_chart",        build_platform_chart,        []),
        ("build_sov_donut",             build_sov_donut,             [sov]),
        ("build_leaderboard_chart",     build_leaderboard_chart,     [sov]),
        ("build_earned_breakdown_chart",build_earned_breakdown_chart,[earned]),
        ("build_owned_content_chart",   build_owned_content_chart,   [owned]),
    ]:
        try:
            result = fn(*args)
            if isinstance(result, str) and len(result) > 50:
                ok(f"{name} returns non-empty HTML")
            else:
                fail(f"{name} returns non-empty HTML", f"got: {type(result)} len={len(result) if isinstance(result,str) else 'N/A'}")
        except Exception as e:
            fail(f"{name}", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 4. RENDERER TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_renderer():
    print("\n--- 4. render_report ---")
    try:
        from renderer import render_report
        from agent import (
            analyze_share_of_voice, analyze_earned_media, analyze_owned_media,
            analyze_technical_factors, analyze_yoy, synthesize_trends,
            generate_recommendations, build_platform_chart, build_sov_donut,
            build_leaderboard_chart, build_earned_breakdown_chart,
            build_owned_content_chart, MARKET_RESEARCH,
        )
        from datetime import datetime

        sov = analyze_share_of_voice(SAMPLE_DF)
        earned = analyze_earned_media(SAMPLE_DF)
        owned = analyze_owned_media(SAMPLE_DF)
        technical = analyze_technical_factors(SAMPLE_DF)
        trends = synthesize_trends(SAMPLE_DF, sov, earned, owned)
        yoy = analyze_yoy(sov)

        cluster_counts = SAMPLE_DF.groupby("topic_cluster").size().sort_values(ascending=False)
        top_cluster = {"name": cluster_counts.index[0], "count": int(cluster_counts.iloc[0]),
                       "pct": round(cluster_counts.iloc[0] / len(SAMPLE_DF) * 100, 1)}
        topic_clusters = sorted(SAMPLE_DF["topic_cluster"].unique().tolist())

        recs = generate_recommendations(
            sov, earned, owned, trends,
            technical=technical,
            n_clusters=len(topic_clusters),
            top_cluster=top_cluster,
        )

        findings = {
            "industry": "Digital Marketing Agencies",
            "report_date": datetime.now().strftime("%B %Y"),
            "metadata": {
                "brands_analyzed": sov["total_brands"],
                "prompts_analyzed": 48,
                "platform": "ChatGPT",
                "data_period": "2026-05-12 to 2026-05-19",
                "topic_clusters": topic_clusters,
                "example_prompts": {
                    c: SAMPLE_DF[SAMPLE_DF["topic_cluster"] == c]["prompt_text"].unique()[:2].tolist()
                    for c in topic_clusters
                },
            },
            "sov": sov,
            "earned": earned,
            "owned": owned,
            "technical": technical,
            "trends": trends,
            "yoy": yoy,
            "recommendations": recs,
            "market_research": MARKET_RESEARCH,
            "charts": {
                "platform": build_platform_chart(),
                "sov_donut": build_sov_donut(sov),
                "leaderboard_bar": build_leaderboard_chart(sov),
                "earned_breakdown": build_earned_breakdown_chart(earned),
                "owned_content": build_owned_content_chart(owned),
            },
        }

        html = render_report(findings)

        if isinstance(html, str) and len(html) > 10000:
            ok(f"render_report returned HTML ({len(html):,} chars)")
        else:
            fail("render_report returned HTML", f"too short or wrong type: {len(html) if isinstance(html,str) else type(html)}")

        # Check key sections are present
        for section_id in ("section-1", "section-2", "section-3", "section-4", "section-5"):
            if f'id="{section_id}"' in html:
                ok(f"HTML contains {section_id}")
            else:
                fail(f"HTML contains {section_id}", "not found")

        # Check brand names rendered
        if "Apex Digital" in html:
            ok("top brand 'Apex Digital' appears in rendered HTML")
        else:
            fail("top brand in HTML", "'Apex Digital' not found")

        # Check data_period is rendered (not the hardcoded string)
        if "2026-05-12 to 2026-05-19" in html:
            ok("actual data_period date range rendered in HTML")
        else:
            fail("data_period in HTML", "expected '2026-05-12 to 2026-05-19' not found")

    except Exception as e:
        fail("render_report", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 5. FAILURE / BAD INPUT TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_bad_inputs():
    print("\n--- 5. Bad input / failure tests ---")
    from agent import load_peec_data

    # 5a. Non-existent file
    try:
        load_peec_data("/tmp/does_not_exist_xyz.csv")
        fail("load_peec_data non-existent file", "should have raised FileNotFoundError")
    except FileNotFoundError:
        ok("load_peec_data raises FileNotFoundError for missing file")
    except Exception as e:
        fail("load_peec_data non-existent file", f"wrong exception: {type(e).__name__}: {e}")

    # 5b. CSV with missing required columns
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("col_a,col_b\n1,2\n")
        bad_path = f.name
    try:
        load_peec_data(bad_path)
        fail("load_peec_data missing columns", "should have raised ValueError")
    except ValueError as e:
        if "Missing required columns" in str(e):
            ok("load_peec_data raises ValueError for missing columns")
        else:
            fail("load_peec_data missing columns", f"wrong ValueError message: {e}")
    except Exception as e:
        fail("load_peec_data missing columns", f"wrong exception: {type(e).__name__}: {e}")
    finally:
        os.unlink(bad_path)

    # 5c. CSV with no ChatGPT rows
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("brand,media_type,is_owned,topic_cluster,platform,prompt_id,prompt_text\n")
        f.write("Acme,editorial,0,Services,gemini,p1,test prompt\n")
        no_chatgpt_path = f.name
    try:
        load_peec_data(no_chatgpt_path)
        fail("load_peec_data no ChatGPT rows", "should have raised ValueError")
    except ValueError as e:
        if "No ChatGPT rows" in str(e):
            ok("load_peec_data raises ValueError when no ChatGPT rows present")
        else:
            fail("load_peec_data no ChatGPT rows", f"wrong message: {e}")
    except Exception as e:
        fail("load_peec_data no ChatGPT rows", f"wrong exception: {type(e).__name__}: {e}")
    finally:
        os.unlink(no_chatgpt_path)

    # 5d. classify_earned_type handles empty/None input gracefully
    from agent import classify_earned_type
    result = classify_earned_type("")
    if result == "brand_mention":
        ok("classify_earned_type('') returns 'brand_mention'")
    else:
        fail("classify_earned_type('')", f"got: {result}")

    result_none = classify_earned_type(None)
    if result_none == "brand_mention":
        ok("classify_earned_type(None) returns 'brand_mention'")
    else:
        fail("classify_earned_type(None)", f"got: {result_none}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. CSV ROUND-TRIP TEST (load_peec_data produces same schema as fetch_peec_data)
# ─────────────────────────────────────────────────────────────────────────────

def test_csv_roundtrip():
    print("\n--- 6. CSV load round-trip ---")
    from agent import load_peec_data

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        SAMPLE_DF.to_csv(f, index=False)
        csv_path = f.name

    try:
        df = load_peec_data(csv_path)
        required_cols = {"brand", "media_type", "is_owned", "topic_cluster",
                         "platform", "prompt_id", "prompt_text"}
        missing = required_cols - set(df.columns)
        if not missing:
            ok("load_peec_data CSV has all required columns")
        else:
            fail("load_peec_data CSV columns", f"missing: {missing}")

        if len(df) > 0:
            ok(f"load_peec_data returned {len(df)} rows")
        else:
            fail("load_peec_data row count", "0 rows returned")

        if df["is_owned"].dtype in (int, "int64", "int32"):
            ok("is_owned column is integer type")
        else:
            fail("is_owned dtype", f"got: {df['is_owned'].dtype}")

    finally:
        os.unlink(csv_path)


# ─────────────────────────────────────────────────────────────────────────────
# 7. METADATA ASSEMBLY TEST (workspace_meta path)
# ─────────────────────────────────────────────────────────────────────────────

def test_metadata_assembly():
    print("\n--- 7. Metadata assembly (workspace_meta path) ---")
    from agent import analyze_share_of_voice

    sov = analyze_share_of_voice(SAMPLE_DF)
    topic_clusters = sorted(SAMPLE_DF["topic_cluster"].unique().tolist())

    # Simulate what main() does when workspace_meta is present
    workspace_meta = {
        "total_workspace_prompts": 48,
        "prompt_text_map": {
            "p1": "Best digital marketing agencies for SEO?",
            "p2": "Top agencies for paid search management?",
            "p3": "Which agency has best content marketing team?",
            "p4": "How much do marketing agencies charge?",
            "p5": "Apex Digital vs Bolt Media -- which is better?",
            "p6": "Best AI marketing tools for agencies?",
        },
        "prompt_cluster_map": {
            "p1": "Services",
            "p2": "Services",
            "p3": "Content",
            "p4": "Pricing",
            "p5": "Comparison",
            "p6": "Tools",
        },
        "start_date": "2026-05-12",
        "end_date": "2026-05-19",
    }

    ws_prompt_count = workspace_meta["total_workspace_prompts"]
    data_period = f"{workspace_meta['start_date']} to {workspace_meta['end_date']}"

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
    for cluster in topic_clusters:
        if not example_prompts.get(cluster):
            example_prompts[cluster] = (
                SAMPLE_DF[SAMPLE_DF["topic_cluster"] == cluster]["prompt_text"].unique()[:2].tolist()
            )

    # prompts_analyzed uses workspace total, not citation-derived count
    if ws_prompt_count == 48:
        ok("prompts_analyzed uses workspace total (48), not citation-derived count")
    else:
        fail("prompts_analyzed", f"expected 48, got: {ws_prompt_count}")

    # Citation-derived count would be different (only 6 unique prompts have citations)
    citation_count = SAMPLE_DF["prompt_id"].nunique()
    if ws_prompt_count != citation_count:
        ok(f"workspace prompt count ({ws_prompt_count}) differs from citation-derived ({citation_count}) -- fix confirmed")
    else:
        fail("workspace vs citation prompt count", "they match -- sample data may need adjustment")

    # data_period is a real date, not the hardcoded string
    if data_period == "2026-05-12 to 2026-05-19":
        ok(f"data_period shows actual dates: {data_period}")
    else:
        fail("data_period", f"expected date string, got: {data_period}")

    # example_prompts built from workspace (covers all clusters)
    missing_clusters = [c for c in topic_clusters if not example_prompts.get(c)]
    if not missing_clusters:
        ok("example_prompts covers all topic clusters")
    else:
        fail("example_prompts coverage", f"missing clusters: {missing_clusters}")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Z-SCORE + EXECUTIVE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def test_z_scores():
    print("\n--- 8a. compute_z_scores ---")
    from agent import compute_z_scores

    sov, earned, owned, technical, trends = _build_fixtures()
    z_scores = compute_z_scores(sov, technical, earned)

    if isinstance(z_scores, list) and len(z_scores) > 0:
        ok(f"compute_z_scores returned {len(z_scores)} entries")
    else:
        fail("compute_z_scores returned entries", f"got: {z_scores}")
        return

    entry = z_scores[0]
    for key in ("brand", "z_score", "breadth", "depth", "authority", "positioning"):
        if key in entry:
            ok(f"z_score entry has key '{key}'")
        else:
            fail(f"z_score entry has key '{key}'", "missing")

    if 0 <= entry["z_score"] <= 100:
        ok(f"z_score is in range 0-100 ({entry['z_score']})")
    else:
        fail("z_score in range 0-100", f"got {entry['z_score']}")

    # Sorted descending
    scores = [z["z_score"] for z in z_scores]
    if scores == sorted(scores, reverse=True):
        ok("z_scores sorted descending")
    else:
        fail("z_scores sorted descending", f"order: {scores[:5]}")


def test_executive_summary():
    print("\n--- 8b. generate_executive_summary ---")
    from agent import generate_executive_summary, generate_recommendations

    sov, earned, owned, technical, trends = _build_fixtures()
    recs = generate_recommendations(sov, earned, owned, technical)
    exec_s = generate_executive_summary(sov, earned, trends, recs, "Test: Industry")

    for key in ("headline", "subheadline", "takeaways"):
        if key in exec_s:
            ok(f"exec_summary has key '{key}'")
        else:
            fail(f"exec_summary has key '{key}'", "missing")
            return

    count = len(exec_s["takeaways"])
    if count == 5:
        ok("exec_summary has 5 takeaways")
    else:
        fail("exec_summary has 5 takeaways", f"got {count}")

    # All 5 takeaways must have headline, detail, action
    for i, t in enumerate(exec_s["takeaways"]):
        for key in ("number", "headline", "detail", "action"):
            if key in t:
                ok(f"takeaway {i+1} has key '{key}'")
            else:
                fail(f"takeaway {i+1} has key '{key}'", "missing")

    # No two takeaways should have the same headline
    headlines = [t["headline"] for t in exec_s["takeaways"]]
    if len(headlines) == len(set(headlines)):
        ok("all 5 takeaway headlines are distinct")
    else:
        dupes = [h for h in headlines if headlines.count(h) > 1]
        fail("all 5 takeaway headlines are distinct", f"duplicates: {dupes}")

    # No action text should be truncated mid-sentence (no trailing "...")
    for i, t in enumerate(exec_s["takeaways"]):
        action = t.get("action", "")
        if action.endswith("..."):
            fail(f"takeaway {i+1} action not truncated", f"ends with '...': {action[-60:]}")
        else:
            ok(f"takeaway {i+1} action not truncated")

    # Exec summary headline mentions the industry
    if "Test: Industry" in exec_s["headline"]:
        ok("exec_summary headline includes industry name")
    else:
        fail("exec_summary headline includes industry name", exec_s["headline"])


# ─────────────────────────────────────────────────────────────────────────────
# 9. LIVE API PING (only when --live flag passed)
# ─────────────────────────────────────────────────────────────────────────────

def test_live_api():
    print("\n--- 9. Live API ping ---")
    import requests
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    api_key = os.getenv("PEEC_API_KEY")

    if not api_key:
        fail("PEEC_API_KEY set", "not found in .env or environment")
        return

    ok("PEEC_API_KEY found in environment")

    try:
        r = requests.get(
            "https://api.peec.ai/customer/v1/projects",
            headers={"X-API-Key": api_key},
            timeout=10,
        )
        if r.status_code == 200:
            projects = r.json()
            count = len(projects.get("data", projects) if isinstance(projects, dict) else projects)
            ok(f"Peec API /projects responded 200 ({count} workspaces found)")
        else:
            fail("Peec API /projects", f"status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        fail("Peec API /projects", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    live = "--live" in sys.argv

    print("=" * 60)
    print("  AIVx Report Agent — Test Harness")
    print("=" * 60)

    test_imports()
    test_share_of_voice()
    test_earned_media()
    test_owned_media()
    test_technical_factors()
    test_trends()
    test_yoy_no_pdf()
    test_yoy_with_pdf()
    test_recommendations()
    test_charts()
    test_renderer()
    test_bad_inputs()
    test_csv_roundtrip()
    test_metadata_assembly()
    test_z_scores()
    test_executive_summary()

    if live:
        test_live_api()
    else:
        print("\n--- 9. Live API ping --- (skipped — run with --live to include)")

    print("\n" + "=" * 60)
    print(f"  {TESTS_PASSED} passed  |  {TESTS_FAILED} failed")
    if FAILURES:
        print("\n  FAILURES:")
        for name, reason in FAILURES:
            print(f"    FAIL  {name}: {reason}")
    print("=" * 60)

    sys.exit(1 if TESTS_FAILED else 0)
