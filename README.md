# 中国社交媒体爬虫方案对比测评

**目标**: 找到一个 scalable、成本可控、AI agent 可用的方案，稳定爬取抖音/小红书等中国社交平台内容。

## 测评结果总览

| 方案 | 抖音 | 小红书 | 成本 | 速度 | AI集成 | 许可证 | 推荐度 |
|------|:----:|:------:|:----:|:----:|:------:|:------:|:------:|
| **f2** | ✅ 完美 | ❌ 不支持 | 免费 | 2s/请求 | ⭐⭐⭐ Python API | Apache-2.0 | ⭐⭐⭐⭐⭐ (抖音) |
| **TikHub API** | ✅ 完美 | ✅ 有端点 | $0.001-0.01/req | 0.5-8s | ⭐⭐⭐ REST API | 商业 | ⭐⭐⭐⭐⭐ (全平台) |
| **Camoufox** | ✅ 绕过指纹 | ✅ 绕过指纹 | 免费 | 10s/页 | ⭐⭐ 需封装 | MPL-2.0 | ⭐⭐⭐⭐ (反检测) |
| **xhshow签名** | N/A | ✅ 签名OK | 免费 | 即时 | ⭐⭐⭐ Python | MIT | ⭐⭐⭐⭐ (需cookie) |
| **MediaCrawler** | ✅ 需登录 | ✅ 需登录 | 免费 | 中等 | ⭐⭐ CLI为主 | ⚠️ 非商用 | ⭐⭐⭐ (学习用) |
| **Jina Reader** | ❌ 空内容 | ❌ 登录墙 | 免费 | 17s | ⭐ 简单API | - | ⭐ (不可用) |
| **Firecrawl** | ❓ 需Key | ❓ 需Key | $? | ? | ⭐⭐⭐ API | - | ⭐⭐ (未验证) |

## 推荐方案

### 🏆 最佳组合: f2 (抖音) + TikHub API (小红书/全平台)

```
抖音任务 → f2 Python API (免费, 2s, Apache-2.0)
  ├── 短链接解析 → AwemeIdFetcher / SecUserIdFetcher
  ├── 视频详情 → fetch_one_video (146个字段!)
  ├── 用户主页 → fetch_user_profile + fetch_user_posts
  └── 无需浏览器, 纯HTTP, ABogus算法内置

小红书任务 → TikHub API ($0.001/req) 或 Camoufox + xhshow
  ├── TikHub: 78个XHS端点, 无需管理cookie
  ├── Camoufox: 绕过指纹检测, 但仍需登录cookie
  └── xhshow: 纯Python签名, 但需有效cookie

通用爬取 → Camoufox (反检测最强的stealth浏览器)
  ├── C++级指纹注入 (不是JS patch)
  ├── sannysoft 20/20 全通过
  └── XHS可以加载完整页面 (Playwright被拦截)
```

### 成本估算 (轻度使用 ~1000 req/月)

| 方案 | 月成本 |
|------|--------|
| f2 only (抖音) | $0 |
| f2 + TikHub (抖音+小红书) | $1-10 |
| f2 + Camoufox + 中国代理 | $5-20 (代理费) |
| 全部用 TikHub | $10-50 |

## 详细测试报告

### 1. f2 — 抖音最佳方案 ⭐⭐⭐⭐⭐

[f2](https://github.com/Johnserf-Seed/f2) 是纯 Python 的多平台下载器，内置 ABogus 算法。

**测试结果**:

| 测试 | 结果 | 耗时 |
|------|------|------|
| 短链接解析 | ✅ 正确提取 sec_user_id | 5.9s |
| 视频详情 (aweme_id) | ✅ 146字段完整数据 | 2.3s |
| 用户资料 | ✅ 粉丝数/作品数/获赞数 | 2.2s |

**提取的数据示例** (视频7628940941864324394):
```json
{
  "desc": "你的ViT一直用背景在分类！LaSt-ViT【CVPR26】",
  "author": "Lau博士的云组会",
  "digg_count": 7260,
  "comment_count": 106,
  "collect_count": 3928,
  "share_count": 1696,
  "duration": 459222,
  "hashtags": ["AI新星计划", "Transformer", "大模型", "CVPR", "计算机视觉"],
  "video_play_addr": "https://...",  // 直接下载链接
  "cover": "https://..."
}
```

**关键优势**:
- ✅ 纯 HTTP，无需浏览器，2秒/请求
- ✅ ABogus 算法内置且有效
- ✅ Apache-2.0 许可证（可商用）
- ✅ TokenManager 自动生成 ttwid/msToken（不需手动管理 cookie）
- ✅ 支持: 抖音、TikTok、Twitter、微博

**局限**:
- ❌ 不支持小红书
- ⚠️ 需要 token 初始化（首次约 5s）

### 2. TikHub API — 最省心的全平台方案 ⭐⭐⭐⭐⭐

[TikHub.io](https://tikhub.io) 是商业 API 服务，覆盖 20+ 平台。

**测试结果**:

| 测试 | 结果 |
|------|------|
| 免费 Demo 端点 (抖音) | ✅ 完整视频数据，146字段 |
| 正式端点 (无key) | ❌ 401 需要token |
| SDK (tikhub PyPI) | ✅ 安装成功，API清晰 |

**亮点**:
- 1,058 个端点，覆盖抖音(290)/TikTok(206)/小红书(78)/微博(64)/B站(41)/YouTube(44)
- 按量付费 $0.001-$0.01/请求
- 新用户约 50 次免费请求
- 10 QPS 默认限速

**适合场景**: AI agent 直接调 REST API，零基础设施，无需管理 cookie/签名。

### 3. Camoufox — 最强反检测浏览器 ⭐⭐⭐⭐

[Camoufox](https://github.com/daijro/camoufox) 是 Firefox 的 C++ 级修改版，注入指纹在浏览器引擎层。

**对比测试**:

| 测试 | Camoufox | Playwright Chrome |
|------|----------|-------------------|
| bot.sannysoft.com | ✅ 20/20 全通过 | ❌ 5 FAIL + 1 WARN |
| 小红书用户页 | ✅ 完整加载 (775K) | ❌ IP风险拦截 (300012) |
| 抖音分享页 | ✅ 页面加载 | ✅ 页面加载 |
| 速度 | 29.9s | 27.2s |

**XHS 是关键区别**: Playwright 直接被 XHS 检测并拦截 ("IP存在风险")，Camoufox 完全绕过。

**适合场景**: 需要浏览器渲染的场景，特别是 XHS 和其他指纹检测严格的站点。

### 4. xhshow — XHS 纯 Python 签名 ⭐⭐⭐⭐

[xhshow](https://pypi.org/project/xhshow/) 实现了 XHS 的 x-s/x-t/x-s-common 签名算法。

**测试结果**:
- ✅ 签名生成完美工作（纯 Python，无需浏览器）
- ❌ API 调用需要有效的登录 cookie（a1 + web_session）
- ❌ 假 cookie 返回 code -101 "无登录信息"

**结论**: 签名不是问题，**登录 cookie 是唯一瓶颈**。配合有效 cookie，xhshow 可以完全替代浏览器进行 XHS API 调用。

### 5. MediaCrawler — 最全面但非商用 ⭐⭐⭐

[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 支持 7 个平台，48K stars。

**架构**:
- Playwright + CDP 模式（连接真实 Chrome）
- 模块化: 每个平台有 core/client/login/store 层
- 抖音签名: `libs/douyin.js` (RC4-based) via PyExecJS
- XHS 签名: 调用 xhshow 包
- 内置代理池（快代理/豌豆）
- FastAPI WebUI (port 8080)

**关键限制**:
- ⚠️ **非商用许可证** (Non-Commercial Learning License 1.1)
- 所有平台都需要登录
- 作为库使用困难（全局配置状态 + Playwright 强耦合）
- Pro 版有 AI Agent Skill 支持但需付费

### 6. Jina Reader — 不可用 ⭐

| 测试 | 结果 |
|------|------|
| 抖音短链 | ❌ 空内容 (159B), "page not fully loaded" |
| 抖音分享页 | ❌ 空内容 (187B) |
| XHS 用户页 | ❌ 只拿到登录墙 (577B) |

**结论**: Jina Reader 的无头浏览器无法处理中国平台的 JS 渲染和反爬机制。

### 7. Firecrawl — 未充分验证 ⭐⭐

- 需要 API key（无免费 tier）
- `pip install firecrawl-py` 安装成功
- 所有端点返回 401
- 即使有 key，也很可能无法处理抖音/XHS 的特定反爬

## AI Agent 集成建议

### 最简路径: f2 + TikHub

```python
# 抖音 — 用 f2 (免费)
from f2.apps.douyin.handler import DouyinHandler
video = await handler.fetch_one_video(aweme_id="7628940941864324394")

# 小红书 — 用 TikHub ($0.001/req)
import requests
r = requests.get("https://api.tikhub.io/api/v1/xiaohongshu/web/get_note_info",
                  params={"note_id": "xxx"},
                  headers={"Authorization": f"Bearer {TIKHUB_TOKEN}"})
```

### 进阶路径: f2 + Camoufox + xhshow

```python
# 抖音 — 用 f2
# 小红书 — Camoufox 浏览器获取 cookie，xhshow 签名，直接调 API
from camoufox.sync_api import Camoufox
from xhshow import sign

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto("https://www.xiaohongshu.com")
    # ... login flow, extract cookies ...
    
# Then use cookies + xhshow for API calls (no browser needed)
```

## 测试环境

- Python 3.12, venv at `/home/colligo/download_video/crawl_bench/.venv/`
- 海外 IP (美国 AWS)
- 测试日期: 2026-04-21

## 文件结构

```
├── README.md                          # 本文件
├── tests/
│   ├── test_f2.py                     # f2 库测试
│   ├── test_jina.py                   # Jina Reader 测试
│   ├── test_firecrawl.py              # Firecrawl 测试
│   ├── test_xhs_sign.py              # xhshow + xhs 签名测试
│   └── test_camoufox.py              # Camoufox 隐身浏览器测试
├── results/
│   ├── f2_results.json               # f2 测试数据
│   ├── jina_results.json             # Jina 测试数据
│   ├── firecrawl_results.json        # Firecrawl 测试数据
│   ├── tikhub_results.json           # TikHub 测试数据
│   ├── xhs_sign_results.json         # XHS 签名测试数据
│   ├── camoufox_results.json         # Camoufox 测试数据
│   ├── mediacrawler_analysis.md      # MediaCrawler 架构分析
│   └── screenshots/                   # Camoufox vs Playwright 截图
└── mediacrawler/                      # MediaCrawler 源码 (参考)
```

## License

MIT
