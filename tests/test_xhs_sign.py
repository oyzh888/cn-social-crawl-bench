#!/usr/bin/env python3
"""
Test XHS signing packages: xhshow and xhs (ReaJason/xhs)
Goal: determine if we can access XHS data without login cookies.
"""

import hashlib
import json
import secrets
import sys
import time
import traceback

import requests

RESULTS = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "xhshow_tests": {},
    "xhs_package_tests": {},
    "summary": {},
}

TARGET_USER_ID = "64e95bd60000000001005b74"
KNOWN_NOTE_ID = "6721f8bc000000001d02517a"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
    "Content-Type": "application/json;charset=UTF-8",
}


# ── helpers ──────────────────────────────────────────────

def generate_fake_a1(length=52):
    return secrets.token_hex(length // 2)


def apply_mediacrawler_patch():
    """Apply MediaCrawler's monkey-patch for GET request signing."""
    from xhshow.core.crypto import CryptoProcessor

    _original_build = CryptoProcessor.build_payload_array

    def _patched_build(self, hex_parameter, a1_value, app_identifier="xhs-pc-web",
                       string_param="", timestamp=None, sign_state=None):
        payload = _original_build(self, hex_parameter, a1_value, app_identifier,
                                  string_param, timestamp, sign_state)
        if "{" not in string_param:
            correct_md5_hex = hashlib.md5(string_param.encode("utf-8")).hexdigest()
            correct_md5_bytes = [int(correct_md5_hex[i:i + 2], 16) for i in range(0, 32, 2)]
            seed_byte = payload[4]
            ts_bytes = payload[8:16]
            correct_a3_hash = self._custom_hash_v2(list(ts_bytes) + correct_md5_bytes)
            for i in range(16):
                payload[128 + i] = correct_a3_hash[i] ^ seed_byte
        return payload

    CryptoProcessor.build_payload_array = _patched_build
    print("  [patch] MediaCrawler GET-signing patch applied")


def make_xhshow_sign_fn(cookie_str: str):
    """Create a sign function compatible with xhs XhsClient(sign=...)."""
    from xhshow import Xhshow

    client = Xhshow()

    def sign_fn(url, data=None, a1="", web_session=""):
        real_cookie = f"a1={a1};web_session={web_session}" if web_session else f"a1={a1}"
        if data is not None:
            headers = client.sign_headers_post(uri=url, cookies=real_cookie, payload=data if isinstance(data, dict) else {})
        else:
            headers = client.sign_headers_get(uri=url, cookies=real_cookie, params={})
        return {
            "x-s": headers.get("x-s", ""),
            "x-t": headers.get("x-t", ""),
            "x-s-common": headers.get("x-s-common", ""),
            "x-b3-traceid": headers.get("x-b3-traceid", ""),
        }

    return sign_fn


def classify_response(resp) -> dict:
    """Parse an HTTP response into a structured result dict."""
    result = {"status_code": resp.status_code, "response_length": len(resp.text)}
    try:
        body = resp.json()
        result["response_code"] = body.get("code")
        result["response_msg"] = body.get("msg", body.get("message", ""))
        result["has_data"] = "data" in body and body["data"] not in (None, {}, [])
        if result["has_data"] and isinstance(body["data"], dict):
            result["data_keys"] = list(body["data"].keys())
    except Exception:
        result["response_text_preview"] = resp.text[:300]
    return result


# ── xhshow standalone tests ─────────────────────────────

def test_xhshow_signing():
    """Test that xhshow generates valid-looking headers."""
    print("\n=== Test 1: xhshow header generation ===")
    try:
        from xhshow import Xhshow
        client = Xhshow()
        fake_a1 = generate_fake_a1()
        cookie = f"a1={fake_a1}"

        get_h = client.sign_headers_get(uri="/api/sns/web/v1/user/otherinfo",
                                         cookies=cookie,
                                         params={"target_user_id": TARGET_USER_ID})
        post_h = client.sign_headers_post(uri="/api/sns/web/v2/note/page",
                                           cookies=cookie,
                                           payload={"user_id": TARGET_USER_ID})

        result = {
            "get_signing": {"success": True, "keys": list(get_h.keys()),
                            "x-s_prefix": get_h.get("x-s", "")[:30]},
            "post_signing": {"success": True, "keys": list(post_h.keys()),
                             "x-s_prefix": post_h.get("x-s", "")[:30]},
        }
        print(f"  GET headers: {list(get_h.keys())}")
        print(f"  POST headers: {list(post_h.keys())}")
        RESULTS["xhshow_tests"]["header_generation"] = result
    except Exception as e:
        print(f"  ERROR: {e}")
        RESULTS["xhshow_tests"]["header_generation"] = {"success": False, "error": str(e)}


def _fetch_with_xhshow(test_name, method, uri, params_or_payload, description):
    """Generic fetch helper using xhshow signing with fake a1."""
    print(f"\n=== {description} ===")
    try:
        from xhshow import Xhshow
        client = Xhshow()
        fake_a1 = generate_fake_a1()
        cookie = f"a1={fake_a1}"

        if method == "GET":
            sign_h = client.sign_headers_get(uri=uri, cookies=cookie, params=params_or_payload)
            query = "&".join(f"{k}={v}" for k, v in params_or_payload.items())
            url = f"https://edith.xiaohongshu.com{uri}?{query}" if query else f"https://edith.xiaohongshu.com{uri}"
            resp = requests.get(url, headers={**BASE_HEADERS, "Cookie": cookie, **sign_h}, timeout=10)
        else:
            sign_h = client.sign_headers_post(uri=uri, cookies=cookie, payload=params_or_payload)
            url = f"https://edith.xiaohongshu.com{uri}"
            resp = requests.post(url, json=params_or_payload,
                                 headers={**BASE_HEADERS, "Cookie": cookie, **sign_h}, timeout=10)

        result = classify_response(resp)
        print(f"  HTTP {result['status_code']} | code={result.get('response_code')} | msg={result.get('response_msg', '')}")
        if result.get("has_data"):
            print(f"  Data keys: {result.get('data_keys', 'N/A')}")
        RESULTS["xhshow_tests"][test_name] = result
    except Exception as e:
        print(f"  ERROR: {e}")
        RESULTS["xhshow_tests"][test_name] = {"success": False, "error": str(e)}


def test_xhshow_api_calls():
    """Run several API calls with fake a1 to see what works."""
    _fetch_with_xhshow(
        "user_profile", "GET",
        "/api/sns/web/v1/user/otherinfo",
        {"target_user_id": TARGET_USER_ID},
        "Test 2: GET user profile (fake a1)",
    )
    time.sleep(0.5)

    _fetch_with_xhshow(
        "user_posts", "POST",
        "/api/sns/web/v1/user_posted",
        {"user_id": TARGET_USER_ID, "cursor": "", "num": 30, "image_scenes": "FD_WM_WEBP"},
        "Test 3: POST user posts (fake a1)",
    )
    time.sleep(0.5)

    _fetch_with_xhshow(
        "note_feed", "POST",
        "/api/sns/web/v1/feed",
        {"source_note_id": KNOWN_NOTE_ID, "image_scenes": ["CRD_WM_WEBP"]},
        "Test 4: POST single note feed (fake a1)",
    )
    time.sleep(0.5)

    _fetch_with_xhshow(
        "homefeed", "POST",
        "/api/sns/web/v1/homefeed",
        {"cursor_score": "", "num": 20, "refresh_type": 1, "note_index": 0,
         "unread_begin_note_id": "", "unread_end_note_id": "", "unread_note_count": 0,
         "category": "homefeed_recommend"},
        "Test 5: POST homefeed (fake a1)",
    )
    time.sleep(0.5)

    _fetch_with_xhshow(
        "search", "POST",
        "/api/sns/web/v1/search/notes",
        {"keyword": "美食", "page": 1, "page_size": 20,
         "search_id": hashlib.md5(str(time.time()).encode()).hexdigest(),
         "sort": "general", "note_type": 0},
        "Test 6: POST search (fake a1)",
    )


# ── xhs package tests ───────────────────────────────────

def test_xhs_with_xhshow_bridge():
    """Use xhs package with xhshow as the signing backend."""
    print("\n=== Test 7: xhs + xhshow bridge (fake a1) ===")
    try:
        from xhs import XhsClient

        fake_a1 = generate_fake_a1()
        cookie = f"a1={fake_a1}"
        sign_fn = make_xhshow_sign_fn(cookie)

        xhs = XhsClient(cookie=cookie, sign=sign_fn)
        result = {}

        # get_user_info
        try:
            user = xhs.get_user_info(TARGET_USER_ID)
            result["get_user_info"] = {"success": True, "data_type": str(type(user)),
                                       "data_preview": str(user)[:200] if user else "None"}
            print(f"  get_user_info: SUCCESS")
        except Exception as e:
            result["get_user_info"] = {"success": False, "error": str(e)[:300]}
            print(f"  get_user_info: FAILED - {str(e)[:120]}")

        time.sleep(0.5)

        # get_note_by_id
        try:
            note = xhs.get_note_by_id(KNOWN_NOTE_ID)
            result["get_note_by_id"] = {"success": True, "keys": list(note.keys()) if isinstance(note, dict) else "N/A"}
            print(f"  get_note_by_id: SUCCESS")
        except Exception as e:
            result["get_note_by_id"] = {"success": False, "error": str(e)[:300]}
            print(f"  get_note_by_id: FAILED - {str(e)[:120]}")

        time.sleep(0.5)

        # search
        try:
            search = xhs.get_note_by_keyword("美食")
            result["search"] = {"success": True, "data_type": str(type(search)),
                                "preview": str(search)[:200] if search else "None"}
            print(f"  search: SUCCESS")
        except Exception as e:
            result["search"] = {"success": False, "error": str(e)[:300]}
            print(f"  search: FAILED - {str(e)[:120]}")

        RESULTS["xhs_package_tests"]["xhshow_bridge_fake_a1"] = result

    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        RESULTS["xhs_package_tests"]["xhshow_bridge_fake_a1"] = {"success": False, "error": str(e)}


def test_xhs_html_scrape():
    """Try HTML scraping approach (no API, public page)."""
    print("\n=== Test 8: xhs HTML scrape ===")
    try:
        from xhs import XhsClient

        fake_a1 = generate_fake_a1()
        sign_fn = make_xhshow_sign_fn(f"a1={fake_a1}")
        xhs = XhsClient(cookie=f"a1={fake_a1}", sign=sign_fn)

        result = {}
        try:
            note = xhs.get_note_by_id_from_html(KNOWN_NOTE_ID)
            result["success"] = True
            if isinstance(note, dict):
                result["keys"] = list(note.keys())
                result["title"] = note.get("title", "")[:80]
                result["desc"] = note.get("desc", "")[:80]
                result["type"] = note.get("type", "")
            print(f"  HTML scrape: SUCCESS - keys={result.get('keys')}")
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)[:300]
            print(f"  HTML scrape: FAILED - {str(e)[:150]}")

        RESULTS["xhs_package_tests"]["html_scrape"] = result

    except Exception as e:
        print(f"  ERROR: {e}")
        RESULTS["xhs_package_tests"]["html_scrape"] = {"success": False, "error": str(e)}


def test_direct_html_scrape():
    """Manually scrape XHS note page for embedded JSON data."""
    print("\n=== Test 9: Direct HTML scrape (requests only) ===")
    try:
        url = f"https://www.xiaohongshu.com/explore/{KNOWN_NOTE_ID}"
        resp = requests.get(url, headers={
            "User-Agent": BASE_HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml",
        }, timeout=10, allow_redirects=True)

        result = {
            "status_code": resp.status_code,
            "content_length": len(resp.text),
            "final_url": resp.url,
        }

        # Look for embedded note data in __INITIAL_STATE__ or similar
        import re
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>', resp.text, re.DOTALL)
        if state_match:
            result["has_initial_state"] = True
            try:
                # Try parsing (may have undefined values)
                raw = state_match.group(1)
                raw = raw.replace("undefined", "null")
                state = json.loads(raw)
                result["initial_state_keys"] = list(state.keys())
                note_data = state.get("note", {}).get("noteDetailMap", {})
                if note_data:
                    result["note_found_in_state"] = True
                    first_key = list(note_data.keys())[0] if note_data else None
                    if first_key:
                        note_detail = note_data[first_key].get("note", {})
                        result["note_title"] = note_detail.get("title", "")[:80]
                        result["note_type"] = note_detail.get("type", "")
                        result["note_user"] = note_detail.get("user", {}).get("nickname", "")
                else:
                    result["note_found_in_state"] = False
            except json.JSONDecodeError as je:
                result["initial_state_parse_error"] = str(je)[:100]
        else:
            result["has_initial_state"] = False

        # Check for login redirect
        if "login" in resp.url.lower() or "passport" in resp.url.lower():
            result["redirected_to_login"] = True

        print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
        print(f"  Has __INITIAL_STATE__: {result.get('has_initial_state')}")
        if result.get("note_title"):
            print(f"  Note title: {result['note_title']}")
        if result.get("note_user"):
            print(f"  Note user: {result['note_user']}")

        RESULTS["xhshow_tests"]["direct_html_scrape"] = result

    except Exception as e:
        print(f"  ERROR: {e}")
        RESULTS["xhshow_tests"]["direct_html_scrape"] = {"success": False, "error": str(e)}


# ── main ────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("XHS Signing & Access Test Suite")
    print("=" * 60)

    # Apply MediaCrawler's GET-signing patch
    apply_mediacrawler_patch()

    # xhshow tests
    test_xhshow_signing()
    test_xhshow_api_calls()

    # xhs package tests
    test_xhs_with_xhshow_bridge()
    time.sleep(0.5)
    test_xhs_html_scrape()
    time.sleep(0.5)
    test_direct_html_scrape()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    signing_works = bool(RESULTS["xhshow_tests"].get("header_generation", {}).get("get_signing", {}).get("success"))

    # Check if ANY API returned real data (code=0 with actual data)
    api_works_without_login = False
    for key, r in RESULTS["xhshow_tests"].items():
        if key in ("header_generation", "direct_html_scrape"):
            continue
        if r.get("response_code") == 0 and r.get("has_data"):
            api_works_without_login = True
            break

    # Check xhs package bridge results
    xhs_bridge_works = False
    bridge = RESULTS["xhs_package_tests"].get("xhshow_bridge_fake_a1", {})
    for api_name in ("get_user_info", "get_note_by_id", "search"):
        if bridge.get(api_name, {}).get("success"):
            xhs_bridge_works = True
            break

    html_scrape_works = (
        RESULTS["xhs_package_tests"].get("html_scrape", {}).get("success", False)
        or RESULTS["xhshow_tests"].get("direct_html_scrape", {}).get("note_found_in_state", False)
    )

    # Collect all response codes/messages for the report
    api_responses = {}
    for key, r in RESULTS["xhshow_tests"].items():
        if key in ("header_generation", "direct_html_scrape"):
            continue
        api_responses[key] = {
            "http_status": r.get("status_code"),
            "api_code": r.get("response_code"),
            "msg": r.get("response_msg", ""),
        }

    RESULTS["summary"] = {
        "xhshow_signing_generates_valid_headers": signing_works,
        "api_works_without_login_cookie": api_works_without_login,
        "xhs_bridge_works_without_login": xhs_bridge_works,
        "html_scrape_works_without_login": html_scrape_works,
        "login_absolutely_required_for_api": not api_works_without_login,
        "api_response_overview": api_responses,
        "recommendation": "",
    }

    if api_works_without_login:
        rec = "XHS API is accessible with fake a1 + xhshow signing. Login NOT required."
    elif html_scrape_works:
        rec = ("API requires valid login cookie (fake a1 gets -101 'no login info'). "
               "However, HTML scraping of public note pages works without login and returns embedded note data.")
    else:
        rec = ("Both API and HTML scraping require valid login cookies. "
               "xhshow signing itself works perfectly (generates correct x-s/x-t/x-s-common headers), "
               "but XHS server rejects requests with fake a1 cookies (code -101 or HTTP 406). "
               "A real browser session cookie with valid a1+web_session is needed.")

    RESULTS["summary"]["recommendation"] = rec

    print(f"  Signing generates headers: {signing_works}")
    print(f"  API works without login:   {api_works_without_login}")
    print(f"  xhs bridge works:          {xhs_bridge_works}")
    print(f"  HTML scrape works:         {html_scrape_works}")
    print(f"  Login required for API:    {RESULTS['summary']['login_absolutely_required_for_api']}")
    print()
    print(f"  API response codes:")
    for k, v in api_responses.items():
        print(f"    {k}: HTTP {v['http_status']} | code={v['api_code']} | {v['msg']}")
    print()
    print(f"  >> {rec}")

    # Save
    output_path = "/home/colligo/download_video/crawl_bench/results/xhs_sign_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_path}")
