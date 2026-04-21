#!/usr/bin/env python3
"""
Test f2 library (github.com/Johnserf-Seed/f2) for Douyin video extraction.

Tests:
1. Short link resolution (v.douyin.com -> aweme_id / sec_user_id)
2. Video metadata extraction (title, likes, author, etc.)
3. User profile extraction from sec_uid
"""

import asyncio
import json
import time
import traceback
from pathlib import Path


def build_kwargs():
    """Build kwargs with proper tokens for f2."""
    from f2.apps.douyin.utils import TokenManager, VerifyFpManager

    ttwid = TokenManager.gen_ttwid()
    mstoken = TokenManager.gen_real_msToken()
    verify_fp = VerifyFpManager.gen_verify_fp()

    cookie = f"ttwid={ttwid}; msToken={mstoken}; s_v_web_id={verify_fp}"

    return {
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://www.douyin.com/",
        },
        "proxies": {"http://": None, "https://": None},
        "cookie": cookie,
        "timeout": 15,
        "max_retries": 5,
        "max_connections": 5,
        "max_tasks": 5,
        "max_counts": 0,
        "page_counts": 20,
        "path": "/tmp/f2_test",
        "naming": "{create}_{desc}",
        "lyric": False,
    }


# ============================================================
# Test 1: Short link resolution via AwemeIdFetcher + SecUserIdFetcher
# ============================================================
async def test_short_link_resolution():
    """Resolve Douyin short links to aweme_id or sec_user_id."""
    from f2.apps.douyin.utils import AwemeIdFetcher, SecUserIdFetcher

    # Test with a video short link
    video_url = "https://v.douyin.com/i2wyU53P/"

    result = {
        "test": "short_link_resolution",
        "input_url": video_url,
        "success": False,
        "aweme_id": None,
        "sec_user_id": None,
        "resolved_type": None,
        "error": None,
        "time_seconds": 0,
    }

    start = time.time()

    # First try as video (aweme_id)
    try:
        aweme_id = await AwemeIdFetcher.get_aweme_id(video_url)
        result["aweme_id"] = aweme_id
        result["resolved_type"] = "video"
        result["success"] = True
        print(f"[OK] Short link resolved to aweme_id: {aweme_id}")
    except Exception as e:
        print(f"[INFO] Not a video link: {e}")
        result["error_aweme"] = str(e)

    # Then try as user profile (sec_user_id)
    if not result["success"]:
        try:
            sec_uid = await SecUserIdFetcher.get_sec_user_id(video_url)
            result["sec_user_id"] = sec_uid
            result["resolved_type"] = "user_profile"
            result["success"] = sec_uid is not None and len(str(sec_uid)) > 0
            print(f"[OK] Short link resolved to sec_user_id: {sec_uid}")
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            print(f"[FAIL] SecUserIdFetcher: {e}")
            traceback.print_exc()

    # Also test a known video URL directly
    video_direct = "https://www.douyin.com/video/7628940941864324394"
    try:
        aid = await AwemeIdFetcher.get_aweme_id(video_direct)
        result["direct_url_test"] = {"url": video_direct, "aweme_id": aid, "success": True}
        print(f"[OK] Direct video URL resolved to aweme_id: {aid}")
    except Exception as e:
        result["direct_url_test"] = {"url": video_direct, "error": str(e), "success": False}
        print(f"[FAIL] Direct video URL: {e}")

    result["time_seconds"] = round(time.time() - start, 3)
    return result


# ============================================================
# Test 2: Video metadata extraction via DouyinHandler
# ============================================================
async def test_video_metadata(aweme_id: str = "7628940941864324394"):
    """Fetch video metadata by aweme_id."""
    from f2.apps.douyin.handler import DouyinHandler

    result = {
        "test": "video_metadata",
        "aweme_id": aweme_id,
        "success": False,
        "metadata": {},
        "error": None,
        "time_seconds": 0,
        "abogus_used": False,
    }

    kwargs = build_kwargs()

    start = time.time()
    try:
        handler = DouyinHandler(kwargs)
        video = await handler.fetch_one_video(aweme_id)

        # Check which encryption/bogus algorithm is used
        from f2.apps.douyin.utils import ClientConfManager
        encryption = ClientConfManager.encryption()
        result["abogus_used"] = encryption == "ab"
        result["encryption_type"] = encryption

        # Extract all available metadata
        metadata = {}
        fields = [
            "aweme_id", "aweme_type", "desc", "desc_raw", "create_time",
            "duration", "media_type",
            # Author info
            "nickname", "nickname_raw", "sec_user_id", "uid", "unique_id", "short_id",
            # Stats
            "digg_count", "comment_count", "collect_count", "share_count",
            "play_count", "admire_count",
            # Video URLs
            "video_play_addr", "cover", "animated_cover",
            # Music
            "music_author", "music_id", "music_play_url", "music_duration",
            # Status
            "is_ads", "is_top", "is_delete", "is_prohibited",
            "can_comment", "can_forward", "can_share",
            # Mix
            "mix_id", "mix_name",
            # Other
            "hashtag_names", "region", "position",
        ]

        for field in fields:
            try:
                val = getattr(video, field)
                # Truncate long strings for readability
                if isinstance(val, str) and len(val) > 500:
                    val = val[:500] + "...[truncated]"
                elif isinstance(val, list) and len(str(val)) > 500:
                    val = str(val)[:500] + "...[truncated]"
                metadata[field] = val
            except Exception as e:
                metadata[field] = f"ERROR: {e}"

        result["metadata"] = metadata
        result["success"] = metadata.get("desc_raw") is not None
        print(f"[OK] Video metadata fetched for {aweme_id}")
        print(f"     Title: {metadata.get('desc_raw', 'N/A')}")
        print(f"     Author: {metadata.get('nickname_raw', 'N/A')}")
        print(f"     Likes: {metadata.get('digg_count', 'N/A')}")
        print(f"     Comments: {metadata.get('comment_count', 'N/A')}")
        print(f"     Shares: {metadata.get('share_count', 'N/A')}")
        print(f"     Plays: {metadata.get('play_count', 'N/A')}")
        print(f"     Encryption: {encryption}")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"[FAIL] Video metadata: {e}")
        traceback.print_exc()

    result["time_seconds"] = round(time.time() - start, 3)
    return result


# ============================================================
# Test 3: User profile extraction
# ============================================================
async def test_user_profile(sec_user_id: str = None):
    """Fetch user profile by sec_user_id."""
    from f2.apps.douyin.handler import DouyinHandler

    result = {
        "test": "user_profile",
        "sec_user_id": sec_user_id,
        "success": False,
        "profile": {},
        "error": None,
        "time_seconds": 0,
    }

    if not sec_user_id:
        result["error"] = "No sec_user_id provided (will try to get from video metadata)"
        print(f"[SKIP] User profile: no sec_user_id available")
        return result

    kwargs = build_kwargs()

    start = time.time()
    try:
        handler = DouyinHandler(kwargs)
        user = await handler.fetch_user_profile(sec_user_id)

        profile = {}
        fields = [
            "nickname", "nickname_raw", "uid", "sec_user_id", "unique_id", "short_id",
            "signature", "signature_raw", "avatar_url",
            "gender", "city", "country", "ip_location",
            "aweme_count", "follower_count", "following_count",
            "total_favorited", "favoriting_count",
            "is_ban", "is_star", "live_status", "school_name", "user_age",
        ]

        for field in fields:
            try:
                val = getattr(user, field)
                if isinstance(val, str) and len(val) > 500:
                    val = val[:500] + "...[truncated]"
                profile[field] = val
            except Exception as e:
                profile[field] = f"ERROR: {e}"

        result["profile"] = profile
        result["success"] = profile.get("nickname_raw") is not None
        print(f"[OK] User profile fetched")
        print(f"     Nickname: {profile.get('nickname_raw', 'N/A')}")
        print(f"     Followers: {profile.get('follower_count', 'N/A')}")
        print(f"     Videos: {profile.get('aweme_count', 'N/A')}")
        print(f"     Total likes: {profile.get('total_favorited', 'N/A')}")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"[FAIL] User profile: {e}")
        traceback.print_exc()

    result["time_seconds"] = round(time.time() - start, 3)
    return result


# ============================================================
# Test 4: Test with resolved aweme_id from short link
# ============================================================
async def test_video_from_short_link(aweme_id_from_test1: str):
    """If test 1 resolved a different ID, also test that."""
    if not aweme_id_from_test1 or aweme_id_from_test1 == "7628940941864324394":
        return None
    print(f"\n--- Test 4: Video metadata for resolved ID {aweme_id_from_test1} ---")
    return await test_video_metadata(aweme_id_from_test1)


# ============================================================
# Main
# ============================================================
async def main():
    print("=" * 60)
    print("F2 Library Test Suite - Douyin Video Extraction")
    print("=" * 60)

    all_results = {
        "library": "f2",
        "version": None,
        "license": "Apache-2.0",
        "method": "pure HTTP (no browser)",
        "tests": [],
    }

    try:
        import f2
        all_results["version"] = f2.__version__
        print(f"f2 version: {f2.__version__}")
    except:
        pass

    # Test 1: Short link resolution
    print("\n--- Test 1: Short Link Resolution ---")
    t1 = await test_short_link_resolution()
    all_results["tests"].append(t1)

    # Test 2: Video metadata with known ID
    print("\n--- Test 2: Video Metadata (known ID: 7628940941864324394) ---")
    t2 = await test_video_metadata("7628940941864324394")
    all_results["tests"].append(t2)

    # Test 3: User profile (using sec_user_id from test 1 or test 2)
    sec_uid = None
    if t1.get("sec_user_id"):
        sec_uid = t1["sec_user_id"]
    elif t2["success"] and t2["metadata"].get("sec_user_id"):
        sec_uid = t2["metadata"]["sec_user_id"]
    print(f"\n--- Test 3: User Profile (sec_user_id: {sec_uid or 'N/A'}) ---")
    t3 = await test_user_profile(sec_uid)
    all_results["tests"].append(t3)

    # Test 4: Video from resolved short link (if different ID)
    resolved_id = t1.get("aweme_id")
    t4 = await test_video_from_short_link(resolved_id)
    if t4:
        all_results["tests"].append(t4)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success_count = sum(1 for t in all_results["tests"] if t["success"])
    total_count = len(all_results["tests"])
    total_time = sum(t["time_seconds"] for t in all_results["tests"])
    print(f"Tests passed: {success_count}/{total_count}")
    print(f"Total time: {total_time:.2f}s")

    all_results["summary"] = {
        "tests_passed": success_count,
        "tests_total": total_count,
        "total_time_seconds": round(total_time, 3),
        "abogus_works": t2.get("abogus_used", False) and t2["success"],
        "short_link_resolution_works": t1["success"],
        "video_metadata_works": t2["success"],
        "user_profile_works": t3["success"],
    }

    # Capabilities summary
    if t2["success"]:
        meta = t2["metadata"]
        all_results["capabilities"] = {
            "video_info": ["aweme_id", "title/desc", "create_time", "duration", "media_type"],
            "author_info": ["nickname", "uid", "sec_user_id", "unique_id"],
            "stats": ["likes(digg_count)", "comments", "shares", "plays", "collects", "admires"],
            "media_urls": ["video_play_addr", "cover", "animated_cover", "music_play_url"],
            "music_info": ["music_id", "music_author", "music_duration"],
            "other": ["hashtags", "region", "mix_info", "permissions(can_comment/share/forward)"],
            "has_video_url": meta.get("video_play_addr") is not None,
            "has_cover_url": meta.get("cover") is not None,
        }

    # Save results
    output_path = Path("/home/colligo/download_video/crawl_bench/results/f2_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Make sure everything is JSON serializable
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(make_serializable(all_results), f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_path}")
    return all_results


if __name__ == "__main__":
    asyncio.run(main())
