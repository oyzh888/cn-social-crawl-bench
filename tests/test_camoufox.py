#!/usr/bin/env python3
"""
Test Camoufox (github.com/daijro/camoufox) - stealthy Firefox fork with C++ fingerprint injection.

Tests:
1. Bot detection site (bot.sannysoft.com) - compare Camoufox vs regular Playwright
2. Douyin share page - check if real content or captcha
3. XHS profile page - check if real content or login wall
4. Performance comparison with regular Playwright Chromium
"""

import json
import time
import traceback
from pathlib import Path


# ── Test targets ──────────────────────────────────────────────────────────────

TARGETS = {
    "bot_detection": {
        "url": "https://bot.sannysoft.com/",
        "desc": "Bot detection fingerprint test",
        "wait_until": "networkidle",
        "timeout": 30000,
        "sleep": 3,
    },
    "douyin_share": {
        "url": "https://www.iesdouyin.com/share/video/7628940941864324394/",
        "desc": "Douyin share video page",
        "wait_until": "domcontentloaded",
        "timeout": 20000,
        "sleep": 5,
    },
    "xhs_profile": {
        "url": "https://www.xiaohongshu.com/user/profile/64e95bd60000000001005b74",
        "desc": "Xiaohongshu user profile",
        "wait_until": "domcontentloaded",
        "timeout": 20000,
        "sleep": 5,
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def analyze_bot_detection(page) -> dict:
    """Extract key results from bot.sannysoft.com."""
    results = {}
    try:
        # Get all table rows
        rows = page.query_selector_all("table#fp2 tr")
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) >= 2:
                key = cells[0].inner_text().strip()
                val = cells[1].inner_text().strip()
                has_fp = "fp2" in (row.get_attribute("class") or "")
                results[key] = val

        # Also check the main detection table
        rows2 = page.query_selector_all("table#fp tr")
        for row in rows2:
            cells = row.query_selector_all("td")
            if len(cells) >= 2:
                key = cells[0].inner_text().strip()
                val = cells[1].inner_text().strip()
                results[key] = val
    except Exception as e:
        results["_parse_error"] = str(e)

    return results


def analyze_douyin(html: str) -> dict:
    """Analyze Douyin page content."""
    signals = {
        "has_video_tag": "<video" in html.lower(),
        "has_player": "xgplayer" in html.lower() or "video-player" in html.lower(),
        "has_captcha": "captcha" in html.lower() or "verify" in html.lower(),
        "has_login_wall": "login" in html.lower() and "modal" in html.lower(),
        "has_video_title": "desc-info" in html or "video-info" in html,
        "has_author": "author" in html.lower() or "nickname" in html.lower(),
        "has_like_count": "like-count" in html or "digg" in html.lower(),
        "content_length": len(html),
    }
    return signals


def analyze_xhs(html: str) -> dict:
    """Analyze XHS page content."""
    signals = {
        "has_notes": "note-item" in html or "note-card" in html,
        "has_captcha": "captcha" in html.lower() or "verify" in html.lower(),
        "has_login_wall": ("请登录" in html or "login" in html.lower()),
        "has_user_info": "user-name" in html or "user-info" in html,
        "has_avatar": "avatar" in html.lower(),
        "has_note_count": "笔记" in html or "notes" in html.lower(),
        "content_length": len(html),
    }
    return signals


def screenshot_path(browser_name: str, target: str) -> str:
    out_dir = Path("/home/colligo/download_video/crawl_bench/results/screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / f"camoufox_{browser_name}_{target}.png")


# ── Camoufox test ─────────────────────────────────────────────────────────────

def test_camoufox() -> dict:
    """Run all targets through Camoufox."""
    from camoufox.sync_api import Camoufox

    results = {}
    t_total_start = time.time()

    try:
        with Camoufox(headless=True) as browser:
            page = browser.new_page()

            for name, target in TARGETS.items():
                print(f"\n[Camoufox] Testing {name}: {target['url']}")
                t0 = time.time()
                result = {"url": target["url"], "desc": target["desc"]}

                try:
                    page.goto(
                        target["url"],
                        wait_until=target["wait_until"],
                        timeout=target["timeout"],
                    )
                    time.sleep(target["sleep"])

                    html = page.content()
                    result["load_time_s"] = round(time.time() - t0, 2)
                    result["content_length"] = len(html)
                    result["title"] = page.title()
                    result["final_url"] = page.url

                    # Screenshot
                    ss_path = screenshot_path("camoufox", name)
                    page.screenshot(path=ss_path, full_page=True)
                    result["screenshot"] = ss_path

                    # Analyze
                    if name == "bot_detection":
                        result["detection_results"] = analyze_bot_detection(page)
                    elif name == "douyin_share":
                        result["analysis"] = analyze_douyin(html)
                    elif name == "xhs_profile":
                        result["analysis"] = analyze_xhs(html)

                    result["status"] = "ok"
                    print(f"  OK - {len(html)} bytes, {result['load_time_s']}s")

                except Exception as e:
                    result["status"] = "error"
                    result["error"] = str(e)
                    result["load_time_s"] = round(time.time() - t0, 2)
                    print(f"  ERROR: {e}")

                results[name] = result

    except Exception as e:
        results["_launch_error"] = str(e)
        traceback.print_exc()

    results["_total_time_s"] = round(time.time() - t_total_start, 2)
    return results


# ── Regular Playwright test ───────────────────────────────────────────────────

def test_playwright() -> dict:
    """Run all targets through regular Playwright Chromium (no stealth)."""
    from playwright.sync_api import sync_playwright

    results = {}
    t_total_start = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for name, target in TARGETS.items():
                print(f"\n[Playwright] Testing {name}: {target['url']}")
                t0 = time.time()
                result = {"url": target["url"], "desc": target["desc"]}

                try:
                    page.goto(
                        target["url"],
                        wait_until=target["wait_until"],
                        timeout=target["timeout"],
                    )
                    time.sleep(target["sleep"])

                    html = page.content()
                    result["load_time_s"] = round(time.time() - t0, 2)
                    result["content_length"] = len(html)
                    result["title"] = page.title()
                    result["final_url"] = page.url

                    # Screenshot
                    ss_path = screenshot_path("playwright", name)
                    page.screenshot(path=ss_path, full_page=True)
                    result["screenshot"] = ss_path

                    # Analyze
                    if name == "bot_detection":
                        result["detection_results"] = analyze_bot_detection(page)
                    elif name == "douyin_share":
                        result["analysis"] = analyze_douyin(html)
                    elif name == "xhs_profile":
                        result["analysis"] = analyze_xhs(html)

                    result["status"] = "ok"
                    print(f"  OK - {len(html)} bytes, {result['load_time_s']}s")

                except Exception as e:
                    result["status"] = "error"
                    result["error"] = str(e)
                    result["load_time_s"] = round(time.time() - t0, 2)
                    print(f"  ERROR: {e}")

                results[name] = result

            browser.close()

    except Exception as e:
        results["_launch_error"] = str(e)
        traceback.print_exc()

    results["_total_time_s"] = round(time.time() - t_total_start, 2)
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("CAMOUFOX vs PLAYWRIGHT STEALTH BENCHMARK")
    print("=" * 70)

    # Run Camoufox
    print("\n" + "─" * 50)
    print("Phase 1: Camoufox (stealthy Firefox)")
    print("─" * 50)
    camoufox_results = test_camoufox()

    # Run Playwright
    print("\n" + "─" * 50)
    print("Phase 2: Regular Playwright Chromium (baseline)")
    print("─" * 50)
    playwright_results = test_playwright()

    # Build comparison
    comparison = {}
    for name in TARGETS:
        c = camoufox_results.get(name, {})
        p = playwright_results.get(name, {})
        comparison[name] = {
            "camoufox_status": c.get("status"),
            "playwright_status": p.get("status"),
            "camoufox_content_len": c.get("content_length"),
            "playwright_content_len": p.get("content_length"),
            "camoufox_time_s": c.get("load_time_s"),
            "playwright_time_s": p.get("load_time_s"),
        }

    # Summary
    final = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tool": "camoufox",
        "version": "0.4.11",
        "comparison_summary": comparison,
        "camoufox": camoufox_results,
        "playwright_baseline": playwright_results,
    }

    out_path = Path("/home/colligo/download_video/crawl_bench/results/camoufox_results.json")
    out_path.write_text(json.dumps(final, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out_path}")

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Target':<20} {'Camoufox':<25} {'Playwright':<25}")
    print("-" * 70)
    for name, comp in comparison.items():
        cf = f"{comp['camoufox_status']} ({comp['camoufox_content_len']} bytes, {comp['camoufox_time_s']}s)"
        pw = f"{comp['playwright_status']} ({comp['playwright_content_len']} bytes, {comp['playwright_time_s']}s)"
        print(f"{name:<20} {cf:<25} {pw:<25}")

    cf_total = camoufox_results.get("_total_time_s", "?")
    pw_total = playwright_results.get("_total_time_s", "?")
    print(f"\nTotal time: Camoufox={cf_total}s, Playwright={pw_total}s")


if __name__ == "__main__":
    main()
