"""
OpenClaw Web Crawl Agent — Demo
Tests 4 tools × 4 target types, outputs structured results.
Run: python3 demo_openclaw_crawl.py
"""
import asyncio
import json
import time
import ssl
import urllib.request

# ============================================================
# Test targets
# ============================================================
TARGETS = {
    "wechat": {
        "url": "https://mp.weixin.qq.com/s/TakSwaSv6yCLcitHYk6qCg",
        "name": "微信公众号 - 微软买断",
        "expected_keyword": "微软",
    },
    "github_homepage": {
        "url": "https://hansizeng.github.io/",
        "name": "GitHub Pages - PhD Homepage",
        "expected_keyword": "Hansi",
    },
    "techcrunch": {
        "url": "https://techcrunch.com/2026/04/23/microsoft-offers-buyout-for-up-to-7-of-u-s-employees/",
        "name": "TechCrunch - News Article",
        "expected_keyword": "Microsoft",
    },
    "google_scholar_page": {
        "url": "https://pengsongyou.github.io/",
        "name": "Google DeepMind RS Homepage",
        "expected_keyword": "Songyou",
    },
}

results = []

def log(tool, target, status, length, time_s, snippet="", error=""):
    r = {
        "tool": tool,
        "target": target,
        "status": status,
        "content_length": length,
        "time_seconds": round(time_s, 2),
        "snippet": snippet[:200],
        "error": error[:200] if error else "",
    }
    results.append(r)
    icon = "✅" if status == "OK" else "❌"
    print(f"  {icon} {tool:20s} → {target:25s} | {status:10s} | {length:6d} chars | {time_s:.1f}s")
    if snippet:
        print(f"     snippet: {snippet[:100]}")
    if error:
        print(f"     error: {error[:100]}")


# ============================================================
# Tool 1: urllib (simplest, no deps)
# ============================================================
def test_urllib(name, url, keyword):
    t0 = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        text = resp.read().decode("utf-8", errors="ignore")[:20000]
        dt = time.time() - t0
        
        # Extract visible text (rough)
        import re
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        found = keyword.lower() in clean.lower()
        status = "OK" if found else "NO_KEYWORD"
        log("urllib", name, status, len(clean), dt, clean[:200])
    except Exception as e:
        log("urllib", name, "FAIL", 0, time.time() - t0, error=str(e))


# ============================================================
# Tool 2: Crawl4AI
# ============================================================
async def test_crawl4ai(name, url, keyword):
    t0 = time.time()
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            md = result.markdown or ""
            dt = time.time() - t0
            found = keyword.lower() in md.lower()
            status = "OK" if found else "NO_KEYWORD"
            log("crawl4ai", name, status, len(md), dt, md[:200])
    except Exception as e:
        log("crawl4ai", name, "FAIL", 0, time.time() - t0, error=str(e))


# ============================================================
# Tool 3: Playwright + Stealth
# ============================================================
async def test_playwright_stealth(name, url, keyword):
    t0 = time.time()
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN"
            )
            page = await context.new_page()
            
            # Apply stealth
            try:
                from playwright_stealth import Stealth
                s = Stealth()
                await s.apply(page)
            except:
                pass
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Try #js_content for WeChat, else body
            el = await page.query_selector("#js_content")
            if el:
                text = await el.inner_text()
            else:
                text = await page.inner_text("body")
            
            await browser.close()
            dt = time.time() - t0
            found = keyword.lower() in text.lower()
            status = "OK" if found else "NO_KEYWORD"
            log("playwright+stealth", name, status, len(text), dt, text[:200])
    except Exception as e:
        log("playwright+stealth", name, "FAIL", 0, time.time() - t0, error=str(e))


# ============================================================
# Tool 4: DuckDuckGo Search (for search capability)
# ============================================================
def test_ddg_search():
    t0 = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        query = "Microsoft+voluntary+buyout+7+percent+US+employees+April+2026"
        url = f"https://duckduckgo.com/html/?q={query}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        text = resp.read().decode("utf-8", errors="ignore")
        dt = time.time() - t0
        
        import re
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"', text)
        titles = re.findall(r'class="result__a"[^>]*>([^<]+)', text)
        
        n = len(links)
        snippet = f"Found {n} results. "
        if titles:
            snippet += f"Top: {titles[0][:80]}"
        
        status = "OK" if n > 0 else "NO_RESULTS"
        log("ddg_search", "Web Search", status, n, dt, snippet)
    except Exception as e:
        log("ddg_search", "Web Search", "FAIL", 0, time.time() - t0, error=str(e))


# ============================================================
# Main
# ============================================================
async def main():
    print("=" * 80)
    print("OpenClaw Web Crawl Agent — Demo")
    print("=" * 80)
    
    # Test each tool on each target
    print("\n📡 Tool 1: urllib (pure Python, no browser)")
    for key, t in TARGETS.items():
        test_urllib(t["name"], t["url"], t["expected_keyword"])
    
    print("\n🕷️ Tool 2: Crawl4AI (Playwright-based markdown extractor)")
    for key, t in TARGETS.items():
        await test_crawl4ai(t["name"], t["url"], t["expected_keyword"])
    
    print("\n🥷 Tool 3: Playwright + Stealth (anti-detection browser)")
    for key, t in TARGETS.items():
        await test_playwright_stealth(t["name"], t["url"], t["expected_keyword"])
    
    print("\n🔍 Tool 4: DuckDuckGo Search")
    test_ddg_search()
    
    # Summary table
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"{'Tool':<22} {'Target':<28} {'Status':<12} {'Chars':>8} {'Time':>6}")
    print("-" * 80)
    for r in results:
        print(f"{r['tool']:<22} {r['target']:<28} {r['status']:<12} {r['content_length']:>8} {r['time_seconds']:>5.1f}s")
    
    # Save results
    output = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "host": "pluto-prod (AWS, US IP)",
        "results": results,
        "summary": {
            "total_tests": len(results),
            "ok": sum(1 for r in results if r["status"] == "OK"),
            "fail": sum(1 for r in results if r["status"] == "FAIL"),
            "no_keyword": sum(1 for r in results if r["status"] == "NO_KEYWORD"),
        }
    }
    
    with open("results/openclaw_crawl_demo.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to results/openclaw_crawl_demo.json")

if __name__ == "__main__":
    asyncio.run(main())
