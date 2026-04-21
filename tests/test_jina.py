import requests
import time
import json
import os

urls = [
    ("douyin_short", "https://v.douyin.com/i2wyU53P/"),
    ("douyin_share", "https://www.iesdouyin.com/share/video/7628940941864324394/"),
    ("xhs_profile", "https://www.xiaohongshu.com/user/profile/64e95bd60000000001005b74"),
]

results = []
for name, url in urls:
    print(f"\n{'='*60}")
    print(f"Testing: {name} -> {url}")
    t0 = time.time()
    try:
        r = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/markdown", "X-No-Cache": "true"},
            timeout=30,
        )
        elapsed = time.time() - t0
        entry = {
            "test": name,
            "status": r.status_code,
            "time": round(elapsed, 1),
            "content_len": len(r.text),
            "preview": r.text[:500],
            "success": r.status_code == 200 and len(r.text) > 100,
        }
        results.append(entry)
        print(f"  Status: {r.status_code} | Time: {elapsed:.1f}s | Content length: {len(r.text)}")
        print(f"  Preview:\n{r.text[:500]}")
    except Exception as e:
        elapsed = time.time() - t0
        entry = {"test": name, "error": str(e), "time": round(elapsed, 1), "success": False}
        results.append(entry)
        print(f"  ERROR: {e}")

# Save results
out_dir = "/home/colligo/download_video/crawl_bench/results"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "jina_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n\nResults saved to {out_path}")
print("\n{'='*60}")
print("SUMMARY")
print("="*60)
for r in results:
    status = "OK" if r.get("success") else "FAIL"
    error = r.get("error", "")
    t = r.get("time", "?")
    clen = r.get("content_len", 0)
    print(f"  [{status}] {r['test']}: status={r.get('status','N/A')}, time={t}s, len={clen} {error}")
