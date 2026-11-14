#!/usr/bin/env python3
"""
scripts/x_photo_finder.py
--------------------------------------------------------------------------------
Photo-attached X (Twitter) post discovery and deterministic verification engine
for `honda.cat`.

Discovery sources (zero auth / zero scraping of unauthorized images):
  1. Yahoo! Realtime Search (`mtype=image`) for recent photo-attached posts
  2. Yahoo! Web Search (`site:x.com ...`) for full-year 2026 official & event status URLs
  3. X Syndication Profile Timeline (`syndication.twitter.com/srv/timeline-profile`)
     as supplement/fallback for official series & circuit handles

Verification gate:
  - `https://cdn.syndication.twimg.com/tweet-result?id={status_id}&lang=ja&token=x`
  - Confirms HTTP 200, valid user/text, and >= 1 verified `https://pbs.twimg.com/...`
    photo URL (`mediaUrls`).
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CACHE_PATH = Path(__file__).resolve().parent / ".cache_verified_tweets.json"
TIMELINE_CACHE_PATH = Path(__file__).resolve().parent / ".cache_timelines.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

NOISE_KEYWORDS = [
    "懸賞",
    "モッピー",
    "ポイ活",
    "プレゼント企画",
    "抽選で",
    "フォロー＆リポスト",
    "フォロー&リポスト",
    "コスプレ",
    "譲渡",
    "買取",
    "無料配布",
    "副業",
    "稼げる",
    "line追加",
    "出会い",
    "裏垢",
    "パチンコ",
    "パチスロ",
    "競輪",
    "競艇",
    "競馬",
    "vtuber",
    "原神",
    "ブルアカ",
    "ウマ娘",
    "ポケモン",
    "アイドル",
    "推し活",
    "ライブ配信アプリ",
    "オンラインカジノ",
    "お小遣い",
]

MOTORSPORT_BOOST_HANDLES = {
    "motogp",
    "worldsbk",
    "fim_ewc",
    "circuitcat_cat",
    "mfj_jrr",
    "suzuka_event",
    "motegi_official",
    "tsukuba_circuit",
    "autopolis2005",
    "spa_naoiri",
    "oic_pr",
    "fswpress",
    "takumagp",
    "takuma_aoki",
    "tetsuma_with_b",
    "ihdcsupporters",
    "hsr_kyushu",
    "sonicparkajimu",
    "brows0305",
    "motobattlelive",
    "tvgweb",
    "ridingsport",
    "autoby_jp",
    "youngmachine",
    "webike_net",
    "dazn_jpn",
    "dazn_es",
    "crash_motogp",
    "ducaticorse",
    "arubaracing",
    "hrc_motogp",
    "yamahamotogp",
    "aprilia",
    "ktm_racing",
    "hondaracing_jp",
    "yamaha_race",
    "suzukiracingjp",
    "teamkagayama",
    "bridgestone_ms",
    "dunlop_moto",
}

MOTORCYCLE_DOMAIN_WORDS = [
    "バイク",
    "ロードレース",
    "オートバイ",
    "サーキット",
    "レーシング",
    "jsb1000",
    "st1000",
    "st600",
    "j-gp3",
    "jgp3",
    "motogp",
    "moto2",
    "moto3",
    "worldsbk",
    "wsbk",
    "ewc",
    "8耐",
    "耐久",
    "レン耐",
    "鉄馬",
    "テイスト",
    "tot",
    "cbr",
    "panigale",
    "yzf",
    "gsx",
    "zx-",
    "ninja",
    "rs-gp",
    "desmosedici",
    "ducati",
    "honda",
    "yamaha",
    "suzuki",
    "kawasaki",
    "aprilia",
    "ktm",
    "ピット",
    "パドック",
    "表彰台",
    "予選",
    "決勝",
    "ライダー",
    "整備",
    "ワイヤリング",
    "フルード",
    "タイヤ",
    "ウォーマー",
    "チェーン",
    "トルクレンチ",
    "クーラント",
    "ブレーキ",
    "podium",
    "sprint",
    "race",
    "victory",
    "pole",
    "qualifying",
    "superpole",
    "champion",
]


def _load_json_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json_cache(path: Path, data: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def _clean_tweet_text(raw_text: str) -> str:
    text = raw_text or ""
    text = re.sub(r"\tSTART\t|\tEND\t", "", text)
    text = re.sub(r"(?:\s*https?://t\.co/[A-Za-z0-9]+)+\s*$", "", text).strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_noise_post(text: str, screen_name: str, name: str) -> bool:
    combined = f"{text} {screen_name} {name}".lower()
    if any(kw in combined for kw in NOISE_KEYWORDS):
        return True
    if combined.count("#") >= 12:
        return True
    return False


def _score_candidate(
    cand: dict[str, Any],
    relevance_keywords: list[str] | None = None,
    target_date: str | None = None,
) -> float:
    text = (cand.get("text") or "").lower()
    sn = (cand.get("screenName") or "").lower()
    name = (cand.get("name") or "").lower()
    combined = f"{text} {sn} {name}"

    score = 0.0

    # Official / motorsport media handle bonus
    if sn in MOTORSPORT_BOOST_HANDLES:
        score += 45.0

    # Photo media count bonus
    media_list = cand.get("media") or []
    image_count = sum(
        1 for m in media_list
        if isinstance(m, dict) and m.get("type") in ("image", "photo", None)
    )
    if image_count > 0:
        score += 12.0 + min(image_count, 4) * 3.0

    # Domain relevance words (motorcycle / racing)
    domain_hits = sum(1 for w in MOTORCYCLE_DOMAIN_WORDS if w in combined)
    score += min(domain_hits, 6) * 5.0

    # Article-specific relevance keywords
    if relevance_keywords:
        for idx, kw in enumerate(relevance_keywords):
            kw_low = kw.strip().lower()
            if not kw_low or len(kw_low) < 2:
                continue
            if kw_low in combined:
                weight = 24.0 if idx < 4 else 12.0
                score += weight

    # Date proximity bonus (if known)
    if target_date and cand.get("publishedDate"):
        try:
            td = dt.date.fromisoformat(target_date[:10])
            pd = dt.date.fromisoformat(str(cand["publishedDate"])[:10])
            diff = abs((td - pd).days)
            if diff <= 7:
                score += 35.0
            elif diff <= 21:
                score += 15.0
            elif pd.year == td.year:
                score += 5.0
            else:
                score -= 25.0
        except Exception:
            pass

    # Engagement signal (bounded)
    likes = int(cand.get("likesCount") or 0)
    rts = int(cand.get("rtCount") or 0)
    score += min((likes + rts * 2) ** 0.5, 20.0)

    # Penalize generic 4-wheel-only mentions when no bike term is present
    if any(car in combined for car in ["super gt", "super formula", "f1", "gt300", "gt500", "d1gp"]) and domain_hits == 0:
        score -= 35.0

    return score


def _search_yahoo_realtime(query: str, max_entries: int = 20) -> list[dict[str, Any]]:
    q = urllib.parse.quote(query)
    url = f"https://search.yahoo.co.jp/realtime/search?p={q}&mtype=image"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
    )
    if not m:
        return []

    try:
        nd = json.loads(m.group(1))
    except Exception:
        return []

    entries = (
        nd.get("props", {})
        .get("pageProps", {})
        .get("pageData", {})
        .get("timeline", {})
        .get("entry", [])
    )
    if not isinstance(entries, list):
        return []

    results: list[dict[str, Any]] = []
    for e in entries[:max_entries]:
        tid = str(e.get("id") or "").strip()
        sn = str(e.get("screenName") or "").strip()
        name = str(e.get("name") or sn).strip()
        if not tid or not sn or not tid.isdigit():
            continue
        if e.get("possiblySensitive"):
            continue
        raw_text = _clean_tweet_text(e.get("displayText") or e.get("displayTextBody") or "")
        if _is_noise_post(raw_text, sn, name):
            continue
        media = e.get("media") or []
        has_image_item = any(
            isinstance(item, dict) and item.get("type") == "image"
            for item in media
        )
        if media and not has_image_item:
            continue

        pub_date = None
        if isinstance(e.get("createdAt"), (int, float)):
            try:
                pub_date = dt.datetime.fromtimestamp(e["createdAt"], tz=dt.timezone.utc).date().isoformat()
            except Exception:
                pass

        results.append(
            {
                "id": tid,
                "screenName": sn,
                "name": name,
                "text": raw_text,
                "publishedDate": pub_date,
                "likesCount": e.get("likesCount") or 0,
                "rtCount": e.get("rtCount") or 0,
                "media": media,
                "source": "yahoo_realtime",
            }
        )
    return results


def _search_yahoo_web(query: str, max_entries: int = 12) -> list[dict[str, Any]]:
    """Search Yahoo! Japan Web Search with `site:x.com` to discover 2026 status URLs across the full year."""
    clean_q = query.strip()
    if "site:x.com" not in clean_q and "site:twitter.com" not in clean_q:
        clean_q = f"site:x.com {clean_q}"
    url = f"https://search.yahoo.co.jp/search?p={urllib.parse.quote(clean_q)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw_html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    decoded_html = urllib.parse.unquote(raw_html)
    matches = re.findall(r"https?://(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)", decoded_html)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for sn, tid in matches:
        if tid in seen_ids or len(tid) < 15:
            continue
        seen_ids.add(tid)
        results.append(
            {
                "id": tid,
                "screenName": sn,
                "name": sn,
                "text": clean_q,
                "publishedDate": None,
                "likesCount": 0,
                "rtCount": 0,
                "media": [],
                "source": "yahoo_web",
            }
        )
        if len(results) >= max_entries:
            break
    return results


def fetch_syndication_timeline(handle: str) -> list[dict[str, Any]]:
    """Fetch recent tweets with photos from X Syndication profile timeline (cached per session/day)."""
    clean_handle = handle.lstrip("@").strip()
    if not clean_handle:
        return []

    cache = _load_json_cache(TIMELINE_CACHE_PATH)
    today_key = dt.date.today().isoformat()
    cache_key = f"{clean_handle.lower()}:{today_key}"
    if cache_key in cache:
        return cache[cache_key]

    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{urllib.parse.quote(clean_handle)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        time.sleep(0.6)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
    )
    if not m:
        return []

    try:
        nd = json.loads(m.group(1))
    except Exception:
        return []

    entries = (
        nd.get("props", {})
        .get("pageProps", {})
        .get("timeline", {})
        .get("entries", [])
    )
    if not isinstance(entries, list):
        return []

    results: list[dict[str, Any]] = []
    for entry in entries:
        tweet = entry.get("content", {}).get("tweet", {})
        if not tweet:
            continue
        tid = str(tweet.get("id_str") or "").strip()
        user = tweet.get("user") or {}
        sn = str(user.get("screen_name") or clean_handle).strip()
        name = str(user.get("name") or sn).strip()
        if not tid or not tid.isdigit():
            continue

        ext_media = (tweet.get("extended_entities") or {}).get("media") or []
        ent_media = (tweet.get("entities") or {}).get("media") or []
        media_items = ext_media or ent_media
        photo_items = [
            m for m in media_items if m.get("type") == "photo" and m.get("media_url_https")
        ]
        if not photo_items:
            continue

        raw_text = _clean_tweet_text(tweet.get("full_text") or tweet.get("text") or "")
        if _is_noise_post(raw_text, sn, name):
            continue

        favs = tweet.get("favorite_count") or 0
        rts = tweet.get("retweet_count") or 0
        pub_date = None
        if tweet.get("created_at"):
            try:
                pub_date = dt.datetime.strptime(
                    tweet["created_at"], "%a %b %d %H:%M:%S %z %Y"
                ).date().isoformat()
            except Exception:
                pass

        results.append(
            {
                "id": tid,
                "screenName": sn,
                "name": name,
                "text": raw_text,
                "publishedDate": pub_date,
                "likesCount": favs,
                "rtCount": rts,
                "media": [
                    {"type": "image", "mediaUrl": p["media_url_https"]}
                    for p in photo_items
                ],
                "source": "x_timeline",
            }
        )

    cache[cache_key] = results
    _save_json_cache(TIMELINE_CACHE_PATH, cache)
    return results


def search_photo_tweets(
    queries: list[str],
    max_candidates: int = 15,
    relevance_keywords: list[str] | None = None,
    handles: list[str] | None = None,
    web_queries: list[str] | None = None,
    target_date: str | None = None,
) -> list[dict[str, Any]]:
    """Search for candidate photo-attached X posts via Yahoo Realtime, Yahoo Web, and X Timelines."""
    by_id: dict[str, dict[str, Any]] = {}

    for idx, q in enumerate(queries):
        q_str = (q or "").strip()
        if not q_str:
            continue
        if idx > 0:
            time.sleep(0.3)
        for cand in _search_yahoo_realtime(q_str, max_entries=20):
            tid = cand["id"]
            if tid not in by_id:
                by_id[tid] = cand

    if web_queries:
        for idx, wq in enumerate(web_queries):
            wq_str = (wq or "").strip()
            if not wq_str:
                continue
            if idx > 0:
                time.sleep(0.35)
            for cand in _search_yahoo_web(wq_str, max_entries=10):
                tid = cand["id"]
                if tid not in by_id:
                    by_id[tid] = cand

    if handles:
        for h in handles:
            for cand in fetch_syndication_timeline(h):
                tid = cand["id"]
                if tid not in by_id:
                    by_id[tid] = cand

    candidates = list(by_id.values())
    for c in candidates:
        c["score"] = _score_candidate(
            c,
            relevance_keywords=relevance_keywords,
            target_date=target_date,
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:max_candidates]


def verify_tweet_with_syndication(status_id: str) -> dict[str, Any] | None:
    """Deterministically verify a tweet exists and contains >= 1 pbs.twimg.com photo URL."""
    sid = str(status_id or "").strip()
    if not sid.isdigit():
        return None

    cache = _load_json_cache(CACHE_PATH)
    if sid in cache:
        cached = cache[sid]
        return cached if cached else None

    url = f"https://cdn.syndication.twimg.com/tweet-result?id={sid}&lang=ja&token=x"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    sdata: dict[str, Any] | None = None
    for attempt in range(3):
        try:
            time.sleep(0.35 * (attempt + 1))
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status != 200:
                    continue
                sdata = json.loads(resp.read().decode("utf-8"))
                break
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                cache[sid] = False
                _save_json_cache(CACHE_PATH, cache)
                return None
            if e.code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt == 2:
                return None

    if not sdata or not isinstance(sdata, dict):
        return None

    user = sdata.get("user")
    raw_text = sdata.get("text")
    if not isinstance(user, dict) or not raw_text:
        cache[sid] = False
        _save_json_cache(CACHE_PATH, cache)
        return None

    screen_name = str(user.get("screen_name") or "").strip()
    account_name = str(user.get("name") or screen_name).strip()
    cleaned_text = _clean_tweet_text(raw_text)
    if not screen_name or _is_noise_post(cleaned_text, screen_name, account_name):
        cache[sid] = False
        _save_json_cache(CACHE_PATH, cache)
        return None

    media_urls: list[str] = []
    for p in sdata.get("photos", []) or []:
        u = p.get("url") if isinstance(p, dict) else None
        if u and u.startswith("https://pbs.twimg.com/") and u not in media_urls:
            media_urls.append(u)

    if not media_urls:
        for m in sdata.get("mediaDetails", []) or []:
            if not isinstance(m, dict):
                continue
            if m.get("type") == "photo":
                u = m.get("media_url_https") or m.get("media_url")
                if u and u.startswith("https://pbs.twimg.com/") and u not in media_urls:
                    media_urls.append(u)

    # Strictly require >= 1 real photo attachment
    if not media_urls:
        cache[sid] = False
        _save_json_cache(CACHE_PATH, cache)
        return None

    created_raw = str(sdata.get("created_at") or "")
    pub_date = created_raw[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", created_raw) else dt.date.today().isoformat()

    verified_obj = {
        "statusId": str(sdata.get("id_str") or sid),
        "screenName": screen_name,
        "accountName": account_name,
        "url": f"https://x.com/{screen_name}",
        "postUrl": f"https://x.com/{screen_name}/status/{sdata.get('id_str') or sid}",
        "publishedDate": pub_date,
        "rawText": cleaned_text,
        "mediaUrls": media_urls[:4],
        "likesCount": int(sdata.get("favorite_count") or 0),
        "rtCount": int(sdata.get("conversation_count") or 0),
    }

    cache[sid] = verified_obj
    _save_json_cache(CACHE_PATH, cache)
    return verified_obj


def find_verified_photo_tweets(
    queries: list[str],
    relevance_keywords: list[str] | None = None,
    handles: list[str] | None = None,
    web_queries: list[str] | None = None,
    target_date: str | None = None,
    count: int = 2,
    exclude_ids: set[str] | None = None,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Search candidates and return up to `count` verified photo-attached tweets, re-scored on real text."""
    excluded = exclude_ids or set()
    candidates = search_photo_tweets(
        queries=queries,
        max_candidates=max(24, count * 12),
        relevance_keywords=relevance_keywords,
        handles=handles,
        web_queries=web_queries,
        target_date=target_date,
    )

    verified_pool: list[dict[str, Any]] = []
    for cand in candidates:
        if cand["id"] in excluded:
            continue
        info = verify_tweet_with_syndication(cand["id"])
        if not info:
            continue
        real_score = _score_candidate(
            {
                "text": info["rawText"],
                "screenName": info["screenName"],
                "name": info["accountName"],
                "publishedDate": info["publishedDate"],
                "likesCount": info.get("likesCount", cand.get("likesCount", 0)),
                "rtCount": info.get("rtCount", cand.get("rtCount", 0)),
                "media": [{"type": "image"} for _ in info["mediaUrls"]],
            },
            relevance_keywords=relevance_keywords,
            target_date=target_date,
        )
        if real_score < min_score:
            continue
        info["score"] = real_score
        verified_pool.append(info)
        # Verify a reasonable pool before re-ranking by actual tweet text
        if len(verified_pool) >= max(count * 3, 6):
            break

    verified_pool.sort(key=lambda x: x["score"], reverse=True)
    selected = verified_pool[:count]
    for s in selected:
        excluded.add(s["statusId"])
    return selected


if __name__ == "__main__":
    import sys

    test_q = sys.argv[1:] or ["全日本ロードレース JSB1000"]
    found = find_verified_photo_tweets(test_q, web_queries=test_q, count=3)
    print(json.dumps(found, ensure_ascii=False, indent=2))
