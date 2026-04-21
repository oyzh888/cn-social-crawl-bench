#!/usr/bin/env python3
"""Test Firecrawl's scrape endpoint with Chinese social media URLs.

Tests:
1. Direct API call without API key
2. Direct API call with empty key
3. firecrawl-py SDK (if installed)
"""

import requests
import time
import json
import os
import sys

URLS = [
    ("douyin_short", "https://v.douyin.com/i2wyU53P/"),
    ("xhs_profile", "https://www.xiaohongshu.com/user/profile/64e95bd60000000001005b74"),
]

RESULTS_DIR = "/home/colligo/download_video/crawl_bench/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

all_results = []

# ── Test 1: Direct API call, no auth header ──
print("=" * 60)
print("Test 1: Direct API call WITHOUT any auth header")
print("=" * 60)

for name, url in URLS:
    print(f"\n  [{name}] {url}")
    t0 = time.time()
    try:
        r = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            json={"url": url, "formats": ["markdown"]},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed = time.time() - t0
        body = r.text[:1000]
        print(f"    Status: {r.status_code} | Time: {elapsed:.1f}s")
        print(f"    Response: {body[:200]}")
        all_results.append({
            "approach": "api_no_auth",
            "test": name,
            "url": url,
            "status_code": r.status_code,
            "time_sec": round(elapsed, 1),
            "response_preview": body,
            "success": r.status_code == 200,
        })
    except Exception as e:
        elapsed = time.time() - t0
        print(f"    ERROR: {e}")
        all_results.append({
            "approach": "api_no_auth",
            "test": name,
            "url": url,
            "error": str(e),
            "time_sec": round(elapsed, 1),
            "success": False,
        })

# ── Test 2: Direct API call with dummy bearer token ──
print("\n" + "=" * 60)
print("Test 2: Direct API call WITH dummy bearer token")
print("=" * 60)

for name, url in URLS:
    print(f"\n  [{name}] {url}")
    t0 = time.time()
    try:
        r = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            json={"url": url, "formats": ["markdown"]},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer fc-test",
            },
            timeout=30,
        )
        elapsed = time.time() - t0
        body = r.text[:1000]
        print(f"    Status: {r.status_code} | Time: {elapsed:.1f}s")
        print(f"    Response: {body[:200]}")
        all_results.append({
            "approach": "api_dummy_key",
            "test": name,
            "url": url,
            "status_code": r.status_code,
            "time_sec": round(elapsed, 1),
            "response_preview": body,
            "success": r.status_code == 200,
        })
    except Exception as e:
        elapsed = time.time() - t0
        print(f"    ERROR: {e}")
        all_results.append({
            "approach": "api_dummy_key",
            "test": name,
            "url": url,
            "error": str(e),
            "time_sec": round(elapsed, 1),
            "success": False,
        })

# ── Test 3: firecrawl-py SDK ──
print("\n" + "=" * 60)
print("Test 3: firecrawl-py SDK (no API key)")
print("=" * 60)

try:
    from firecrawl import FirecrawlApp

    # Try with no key
    try:
        app = FirecrawlApp(api_key="fc-test")
        for name, url in URLS:
            print(f"\n  [{name}] {url}")
            t0 = time.time()
            try:
                result = app.scrape(url, formats=["markdown"])
                elapsed = time.time() - t0
                content_preview = str(result)[:500]
                print(f"    Time: {elapsed:.1f}s")
                print(f"    Result: {content_preview[:200]}")
                all_results.append({
                    "approach": "sdk_no_key",
                    "test": name,
                    "url": url,
                    "time_sec": round(elapsed, 1),
                    "response_preview": content_preview,
                    "success": True,
                })
            except Exception as e:
                elapsed = time.time() - t0
                print(f"    ERROR: {e}")
                all_results.append({
                    "approach": "sdk_no_key",
                    "test": name,
                    "url": url,
                    "error": str(e)[:500],
                    "time_sec": round(elapsed, 1),
                    "success": False,
                })
    except Exception as e:
        print(f"  SDK init failed: {e}")
        all_results.append({
            "approach": "sdk_no_key",
            "test": "init",
            "error": str(e)[:500],
            "success": False,
        })
except ImportError:
    print("  firecrawl-py not installed")
    all_results.append({
        "approach": "sdk_no_key",
        "test": "import",
        "error": "firecrawl-py not installed",
        "success": False,
    })

# ── Test 4: Check if there's a free/playground endpoint ──
print("\n" + "=" * 60)
print("Test 4: Check playground / free endpoints")
print("=" * 60)

free_endpoints = [
    ("v0_scrape", "https://api.firecrawl.dev/v0/scrape"),
    ("health", "https://api.firecrawl.dev/v1/"),
]

for ename, endpoint in free_endpoints:
    print(f"\n  [{ename}] {endpoint}")
    t0 = time.time()
    try:
        if "scrape" in endpoint:
            r = requests.post(
                endpoint,
                json={"url": URLS[0][1]},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
        else:
            r = requests.get(endpoint, timeout=15)
        elapsed = time.time() - t0
        print(f"    Status: {r.status_code} | Time: {elapsed:.1f}s")
        print(f"    Response: {r.text[:200]}")
        all_results.append({
            "approach": "free_endpoint",
            "test": ename,
            "status_code": r.status_code,
            "time_sec": round(elapsed, 1),
            "response_preview": r.text[:500],
            "success": r.status_code == 200,
        })
    except Exception as e:
        elapsed = time.time() - t0
        print(f"    ERROR: {e}")
        all_results.append({
            "approach": "free_endpoint",
            "test": ename,
            "error": str(e),
            "time_sec": round(elapsed, 1),
            "success": False,
        })

# ── Save results ──
out_path = os.path.join(RESULTS_DIR, "firecrawl_results.json")
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n{'=' * 60}")
print(f"Results saved to {out_path}")
print(f"Total tests: {len(all_results)}")
print(f"Successes: {sum(1 for r in all_results if r.get('success'))}")
print(f"Failures: {sum(1 for r in all_results if not r.get('success'))}")

# Summary
print(f"\n{'=' * 60}")
print("SUMMARY")
print("=" * 60)
for r in all_results:
    status = "OK" if r.get("success") else "FAIL"
    code = r.get("status_code", "N/A")
    err = r.get("error", "")[:80]
    preview = r.get("response_preview", "")[:80] if not err else ""
    print(f"  [{status}] {r['approach']}/{r['test']} — HTTP {code} {err}{preview}")
