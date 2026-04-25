## OpenClaw Web Crawl Agent — Demo Results

**Test Date**: 2026-04-25  
**Host**: pluto-prod (AWS US, headless Linux)

### Results Matrix

| Tool | 微信公众号 | GitHub Pages | TechCrunch | GDM Homepage | Speed |
|---|---|---|---|---|---|
| **urllib** | ❌ JS not rendered | ✅ | ✅ | ✅ | ⚡ 0.1s |
| **Crawl4AI** | ❌ 环境异常 (bot detected) | ✅ | ✅ | ✅ | 🔵 1-4s |
| **Playwright+Stealth** | ✅ **唯一成功** | ✅ | ❌ timeout | ✅ | 🟡 3-12s |
| **DDG Search** | N/A | N/A | N/A | N/A | ⚡ 1.0s |

### Key Findings

1. **微信公众号**: Only Playwright+Stealth works. urllib gets raw JS, Crawl4AI gets "环境异常" bot detection.
2. **Static pages** (GitHub Pages, personal homepages): urllib is fastest (0.1s), all tools work.
3. **Crawl4AI** gives the best markdown output for general pages (57K chars for GDM homepage vs 13K from Playwright).
4. **Playwright+Stealth** is the Swiss Army knife — handles anti-bot but slower and can timeout on heavy pages.

### Recommended Tool Chain

```
Input URL
  ├─ Static/simple page → urllib (0.1s, free)
  ├─ Need markdown/structured → Crawl4AI (1-4s, free)
  ├─ WeChat/anti-bot sites → Playwright+Stealth (3-12s, free)
  ├─ XHS (小红书) → Camoufox (not tested here, see README.md)
  ├─ Douyin (抖音) → f2 API (not tested here, see README.md)
  └─ Web search → DuckDuckGo HTML (1s, free)
```

### Raw Results

See `results/openclaw_crawl_demo.json` for full data.
