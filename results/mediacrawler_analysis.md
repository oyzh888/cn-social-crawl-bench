# MediaCrawler Architecture Analysis

**Repo**: https://github.com/NanmiCoder/MediaCrawler
**Cloned to**: `/home/colligo/download_video/crawl_bench/mediacrawler/`
**Analysis date**: 2026-04-20

---

## 1. Architecture Summary

MediaCrawler is a Playwright-based multi-platform social media crawler. The core design:

```
main.py (CLI entry)
  -> CrawlerFactory (selects platform)
    -> AbstractCrawler subclass (e.g., XiaoHongShuCrawler)
      -> Playwright browser launch (CDP or standard mode)
      -> Login (QR code / phone / cookie)
      -> Platform-specific API client (e.g., XiaoHongShuClient)
        -> Signing (x-s/x-t for XHS, a_bogus for Douyin)
        -> httpx requests with signed headers
      -> Store layer (CSV / JSON / JSONL / Excel / SQLite / MySQL / MongoDB / Postgres)
```

**Key design pattern**: Each platform has a `core.py` (crawler orchestrator), `client.py` (API client with signing), `login.py`, `help.py` (utilities), and `field.py` (enums/constants).

**Browser modes**:
- **CDP mode (default)**: Connects to user's existing Chrome via DevTools Protocol on port 9222. Best anti-detection since it uses real browser fingerprint.
- **Standard Playwright mode**: Launches managed Chromium with `stealth.min.js` injection.

---

## 2. Supported Platforms & Data

| Platform | Key | Data Extracted |
|----------|-----|----------------|
| Xiaohongshu (XHS) | `xhs` | Notes (posts), comments, sub-comments, creator profiles, images, videos |
| Douyin | `dy` | Videos/posts, comments, sub-comments, creator profiles, video downloads, images |
| Kuaishou | `ks` | Videos, comments, creator profiles |
| Bilibili | `bili` | Videos, comments, creator profiles |
| Weibo | `wb` | Posts, comments, images, videos |
| Baidu Tieba | `tieba` | Posts, comments |
| Zhihu | `zhihu` | Answers/articles, comments |

**Crawl modes** (all platforms):
- `search` - Keyword search, paginated
- `detail` - Specific post IDs
- `creator` - All posts from specific creator profiles

---

## 3. Signing Algorithm Implementations

### XHS (Xiaohongshu) - x-s / x-t / x-s-common

**Current approach: Pure Python algorithm via `xhshow` library** (no browser JS execution needed).

- Dependency: `xhshow>=0.1.9` (PyPI package, MIT license, by Cloxl: https://github.com/Cloxl/xhshow)
- File: `media_platform/xhs/playwright_sign.py` -> `sign_with_xhshow()`
- How it works:
  1. Builds a content string from URI + params/payload
  2. Computes MD5 hash of the content string
  3. Uses `xhshow.Xhshow()` to build a cryptographic payload array with custom hash functions
  4. XOR transforms the payload, encodes with custom Base64
  5. Outputs `x-s`, `x-t` (timestamp), `x-s-common`, `x-b3-traceid`
- **Notable**: There's a monkey-patch (`_patch_xhshow_a3_hash`) fixing a bug in xhshow's GET request signing (the library incorrectly strips query params for GET a3_hash calculation)
- The old `xhs_sign.py` has helper functions (custom Base64, CRC32 variant) used for x-s-common generation
- **Does NOT need Playwright page for signing** -- purely algorithmic

### Douyin - a_bogus

**Approach: Local JS execution via PyExecJS** (NOT Playwright browser).

- File: `media_platform/douyin/help.py` -> `get_a_bogus()` / `get_a_bogus_from_js()`
- JS file: `libs/douyin.js` (434 lines, contains RC4 encryption + signature logic)
- How it works:
  1. Compiles `libs/douyin.js` using `execjs` at module load time
  2. Calls JS function `sign_datail(params, user_agent)` or `sign_reply(params, user_agent)` for reply endpoints
  3. The JS implements RC4 encryption + custom encoding to produce the `a_bogus` parameter
- Also adds common params: `device_platform`, `aid`, `msToken` (from browser localStorage), `webid` (random)
- **There's a deprecated Playwright-based approach** (`get_a_bogus_from_playwright`) that calls `window.bdms.init._v[2].p[42]` but it's no longer used
- **Requires Node.js >= 16** for PyExecJS runtime

### Zhihu

- Uses `libs/zhihu.js` for signing (similar PyExecJS approach)

---

## 4. Login Requirements

**ALL platforms require login/cookies to make API calls.**

Login methods supported:
1. **QR Code** (`--lt qrcode`) - Opens browser, shows QR code, user scans with mobile app
2. **Phone SMS** (`--lt phone`) - Sends SMS verification code
3. **Cookie** (`--lt cookie`) - Pre-set cookies in `config.COOKIES`

Login state is cached in `browser_data/{platform}_user_data_dir/` when `SAVE_LOGIN_STATE = True` (default).

**Can anything work without login?**
- `get_note_by_id_from_html()` in XHS client has an `enable_cookie=False` option that fetches note detail page HTML without cookies. This parses `window.__INITIAL_STATE__` from the HTML. However, this is a fallback method and may be CAPTCHA-blocked.
- The `pong()` methods explicitly check login state before proceeding
- **In practice: No meaningful crawling works without login.** The API endpoints return errors without valid session cookies.

---

## 5. Proxy Configuration

**Config flags** (`config/base_config.py`):
```python
ENABLE_IP_PROXY = False          # Master switch
IP_PROXY_POOL_COUNT = 2          # Pool size
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # Provider
DISABLE_SSL_VERIFY = False       # For MITM proxies
```

**Built-in proxy providers** (`proxy/providers/`):
- `kuaidl_proxy.py` - KuaiDaili (快代理) - Chinese proxy service
- `wandou_http_proxy.py` - WanDou HTTP proxy
- `jishu_http_proxy.py` - JiShu HTTP proxy

**Architecture**: `ProxyIpPool` manages a pool of `IpInfoModel` objects. Each API client has `ProxyRefreshMixin` that auto-refreshes expired proxies before requests. Proxy validation uses `https://echo.apifox.cn/`.

**IP caching**: Uses Redis (`IpCache` class) to store proxy IPs with TTL.

**Custom proxy**: You can implement `ProxyProvider` abstract class for your own proxy source.

---

## 6. API / Programmatic Usage

### WebUI API (FastAPI)
- Entry: `api/main.py` -> FastAPI app on port 8080
- Routers: `api/routers/` - crawler control, data access, WebSocket for real-time logs
- Start: `uvicorn api.main:app --port 8080 --reload`
- Endpoints: `/api/health`, `/api/config/platforms`, `/api/config/options`, etc.

### Programmatic (import as library)
The code CAN be imported and used programmatically, but with caveats:

```python
# Theoretically possible:
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.playwright_sign import sign_with_xhshow

# XHS signing works standalone (no browser needed):
signs = sign_with_xhshow(uri="/api/sns/web/v1/feed", data=payload, cookie_str="a1=xxx;...")

# But the full client requires:
# 1. A Playwright Page object (for cookie management)
# 2. Valid cookies from a logged-in session
# 3. The httpx request pipeline
```

**The signing functions are the most reusable parts:**
- `sign_with_xhshow()` - Pure Python, no browser dependency, can be called standalone
- `get_a_bogus_from_js()` - Needs PyExecJS + Node.js but no browser

**Challenges for library use:**
- Heavy coupling to Playwright browser context
- Config module uses module-level globals (not instance-based)
- Login flow requires interactive browser
- No clean "headless API client" abstraction

---

## 7. License Restrictions

**NON-COMMERCIAL LEARNING LICENSE 1.1**

Key restrictions:
- Non-commercial use only (learning and research purposes)
- No large-scale crawling or platform disruption
- No commercial use without written consent from copyright owner
- Must include copyright notice in all copies

**This is NOT MIT/Apache/GPL.** Cannot be used for any commercial purpose.

The `xhshow` dependency is MIT licensed (more permissive).

---

## 8. Requirements & Potential Conflicts

Key dependencies:
```
playwright==1.45.0      # Browser automation (heavy)
httpx==0.28.1           # HTTP client
pyexecjs==1.5.1         # JS execution (needs Node.js)
xhshow>=0.1.9           # XHS signature algorithm
fastapi==0.110.2        # WebUI API
pydantic==2.5.2         # Data models
redis~=4.6.0            # Caching (proxy IPs)
sqlalchemy>=2.0.43      # DB ORM
opencv-python           # Image processing
pandas==2.2.3           # Data handling
```

**Potential conflicts:**
- `pydantic==2.5.2` is pinned (many projects use different versions)
- `playwright==1.45.0` is pinned (may conflict with other playwright users)
- `httpx==0.28.1` is pinned
- `redis~=4.6.0` is pinned to 4.x
- Node.js >= 16 required for Douyin/Zhihu signing

---

## 9. Key Takeaways

### What's most useful to extract:

1. **XHS signing (`xhshow` library)** - Can generate x-s/x-t/x-s-common headers with just cookies (no browser). This is the most reusable component. Just `pip install xhshow` and call it.

2. **Douyin a_bogus (`libs/douyin.js`)** - 434-line JS file that can be called via execjs. Self-contained, no browser needed.

3. **Data parsing logic** - `store/xhs/`, `store/douyin/` have field extraction and normalization code.

### What's NOT useful standalone:

1. **The crawler orchestration** - Tightly coupled to Playwright browser lifecycle
2. **Login flows** - All interactive, require browser
3. **Proxy system** - Specific to Chinese proxy providers

### Could it work without login?

**Practically no.** All API endpoints require valid cookies. The only exception is the XHS HTML parsing fallback (`get_note_by_id_from_html` with `enable_cookie=False`), but it's unreliable and CAPTCHA-prone.

### Architecture quality:

- Clean abstract base classes (`AbstractCrawler`, `AbstractApiClient`, `AbstractStore`)
- Good separation: signing, client, crawler, store layers
- Async throughout (asyncio + httpx)
- But config is global module state (not injectable), making it hard to use as a library
- CDP mode is well-designed for anti-detection
