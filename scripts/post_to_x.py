#!/usr/bin/env python3
"""
scripts/post_to_x.py
--------------------------------------------------------------------------------
honda.cat - Schedule-Driven Auto-Publisher to X (Twitter)
Posts new article announcements to X using the persona/tone of the assigned cat reporter:
  - marc: Marc (Chief Editor, European / World championships, enthusiastic, Catalan flair, '〜ニャ！')
  - suzuka: Suzuka (Calico photojournalist, All-Japan & regional racing, polite, energetic, '〜ですよ！')
  - naomi: Naomi (Veteran black cat mechanic, circuit maintenance clinic, tsundere craftsman, '〜なんだよ！')

Supports:
  - Gemini API (gemini-2.5-flash) for dynamic, vibrant reporter copywriting
  - Robust template fallback when Gemini API is unavailable or rate-limited
  - OAuth 1.0a authentication (via requests_oauthlib or pure standard library fallback)
  - Duplicate prevention registry via src/data/x_posted.json
  - Dry-run mode for testing (--dry-run)
  - Selective manual posting (--slug <slug>)
--------------------------------------------------------------------------------
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTICLES_DIR = ROOT_DIR / "src" / "data" / "articles"
POSTED_FILE = ROOT_DIR / "src" / "data" / "x_posted.json"
BASE_URL = "https://honda.cat"

# Latest X Developer Platform endpoint (api.x.com)
X_API_URL = "https://api.x.com/2/tweets"


# -----------------------------------------------------------------------------
# OAuth 1.0a Helper (Standard Library + requests_oauthlib compatibility)
# -----------------------------------------------------------------------------
def get_oauth1_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str,
    token_secret: str,
) -> str:
    """Generate RFC 5849 OAuth 1.0a Authorization header using pure standard library."""
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time()))

    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_token": token,
        "oauth_version": "1.0",
    }

    # Normalize parameters
    sorted_params = sorted(params.items())
    param_str = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted_params
    )

    # Signature base string
    base_string = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(param_str, safe=""),
    ])

    # Signing key
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}".encode("utf-8")

    # HMAC-SHA1 signature
    hashed = hmac.new(signing_key, base_string.encode("utf-8"), hashlib.sha1)
    signature = base64.b64encode(hashed.digest()).decode("utf-8")

    params["oauth_signature"] = signature

    # Build header string
    header_parts = [
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(params.items())
    ]
    return f"OAuth {', '.join(header_parts)}"


def send_tweet(text: str, dry_run: bool = False) -> dict[str, Any]:
    """Send tweet via X API v2 (POST https://api.x.com/2/tweets).

    Supports:
      1. OAuth 1.0a User Context (API Key, API Secret, Access Token, Access Token Secret)
         Recommended by X for personal automated publishing / bot accounts ("Acting as yourself")
      2. OAuth 2.0 Bearer Token / User Access Token (Single token authorization: Bearer <token>)
    """
    api_key = os.getenv("X_API_KEY") or os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("X_API_SECRET") or os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")

    # Check authentication mode
    has_oauth1 = bool(api_key and api_secret and access_token and access_token_secret)
    has_bearer = bool(bearer_token or (access_token and not (api_key and api_secret)))

    if not has_oauth1 and not has_bearer:
        if dry_run:
            print("ℹ️ X API credentials not fully set, but running in dry-run mode.")
            return {"data": {"id": "dry_run_sample_id", "text": text}}
        raise ValueError(
            "Missing X API credentials. Please provide either:\n"
            "  Option A (OAuth 1.0a - recommended for personal bots): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET\n"
            "  Option B (OAuth 2.0 User Access Token): X_BEARER_TOKEN (or X_ACCESS_TOKEN with tweet.write scope)"
        )

    if dry_run:
        auth_mode = "OAuth 1.0a (User Context)" if has_oauth1 else "OAuth 2.0 (Bearer Token)"
        print(f"🔍 [DRY-RUN] Tweet would be posted via {auth_mode} to {X_API_URL}:")
        print("--------------------------------------------------")
        print(text)
        print("--------------------------------------------------")
        print(f"Character count approx: {len(text)} chars")
        return {"data": {"id": "dry_run_id", "text": text}}

    payload = json.dumps({"text": text}).encode("utf-8")

    # Mode 1: OAuth 2.0 Bearer Token (if OAuth 1.0a is not configured)
    if not has_oauth1 and has_bearer:
        token = bearer_token or access_token
        print("🔐 Authenticating with OAuth 2.0 Bearer Token...")
        req = urllib.request.Request(
            X_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "HondaCatPublisher/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"X API HTTP {e.code} error: {err_body}") from e

    # Mode 2: OAuth 1.0a User Context
    print("🔐 Authenticating with OAuth 1.0a User Context (RFC 5849)...")
    try:
        from requests_oauthlib import OAuth1Session  # type: ignore
        session = OAuth1Session(
            client_key=api_key,
            client_secret=api_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        response = session.post(
            X_API_URL,
            json={"text": text},
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        if response.status_code != 201:
            raise RuntimeError(f"X API error ({response.status_code}): {response.text}")
        return response.json()
    except ImportError:
        # Fallback to standard library urllib
        auth_header = get_oauth1_header(
            "POST", X_API_URL, api_key, api_secret, access_token, access_token_secret
        )
        req = urllib.request.Request(
            X_API_URL,
            data=payload,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
                "User-Agent": "HondaCatPublisher/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"X API HTTP {e.code} error: {err_body}") from e


# -----------------------------------------------------------------------------
# Reporter Copywriting & Tone Generator (Marc / Suzuka / Naomi)
# -----------------------------------------------------------------------------
PERSONA_PROMPTS = {
    "marc": {
        "name": "マルク編集長 (Marc)",
        "role": "二足歩行の茶トラ猫編集長。MotoGP・WorldSBK・世界選手権・カタルーニャ担当。",
        "tone_guidelines": (
            "・一人称は『マルク編集長』または『オレ』。語尾は『〜ニャ！』『〜だニャ！』『〜見てほしいニャ！』『〜チェックするニャ！』\n"
            "・冒頭の掛け声は『アミーゴ！マルク編集長ニャ！🐾』など熱血かつ親しみやすく。\n"
            "・世界最高峰の極限バトル、60度超えのバンク角、肘＆肉球スーパーセーブ、テレメトリやマシンの挙動に大興奮する熱血スタイル。"
        ),
        "default_hashtag": "#MotoGP",
    },
    "suzuka": {
        "name": "スズカ特派員 (Suzuka)",
        "role": "カメラマンベストを着た二足歩行の三毛猫フォトジャーナリスト。全日本ロードレース・地方選手権・九州サーキット取材担当。",
        "tone_guidelines": (
            "・一人称は『スズカ』。語尾は丁寧かつ元気な『〜ですよ！』『〜ですね！』『〜バッチリ撮りました！』『〜お届けします！』\n"
            "・冒頭の挨拶は『パドック特派員スズカです！📸✨』など明るく爽やかに。\n"
            "・全国各地のサーキット現場の臨場感、路面コンディション、朝のブリーフィング、ライダーたちの熱い走りを丁寧に伝えるしっかり者スタイル。"
        ),
        "default_hashtag": "#全日本ロードレース",
    },
    "naomi": {
        "name": "ナオミチーフ (Naomi)",
        "role": "九州のガレージに棲みつく二足歩行の黒猫メカニック。サーキット整備・耐久＆ガレージ担当。",
        "tone_guidelines": (
            "・一人称は『アタシ』または『ナオミ』。語尾は『〜なんだよ！』『〜しなさいよね』『〜言ってるでしょ！』『…べ、別にあんたのために〜じゃないわよ』\n"
            "・冒頭の呼びかけは『ったく…メカニックのナオミよ🔧』『現場のナオミよ』などぶっきらぼうに。\n"
            "・ツンデレ職人気質。タイムを削る前に足回り整備、適正空気圧、ボルトのトルク、ワイヤリングなどの基本安全点検をビシッと指導する現場主義。"
        ),
        "default_hashtag": "#バイクメンテナンス",
    },
}


def build_fallback_tweet(article_data: dict[str, Any]) -> str:
    """Generate robust template-based tweet text in the reporter's tone."""
    featured_cat = article_data.get("featuredCat", "naomi")
    slug = article_data.get("slug", "")
    url = f"{BASE_URL}/articles/{slug}/"

    ja_meta = article_data.get("locales", {}).get("ja", {})
    raw_title = ja_meta.get("title") or article_data.get("title", "")
    # Remove bracketed prefixes like 【木曜世界戦プレビュー】 from short title if long
    clean_title = re.sub(r"^【[^】]+】\s*", "", raw_title).strip()
    if len(clean_title) > 42:
        clean_title = clean_title[:40] + "…"

    tags = article_data.get("tags", [])
    primary_tag = tags[0] if tags else "バイク"
    if not primary_tag.startswith("#"):
        primary_tag = f"#{primary_tag}"
    # Avoid duplicate tags
    custom_tag = primary_tag if primary_tag not in ["#honda_cat", "#honda"] else "#モータースポーツ"

    if featured_cat == "marc":
        body = (
            f"アミーゴ！マルク編集長ニャ！🐾\n"
            f"【{clean_title}】を公開したニャ！極限バトルとスーパーセーブの神髄を今すぐチェックするニャ🏁\n"
            f"{url}\n"
            f"#honda_cat {custom_tag}"
        )
    elif featured_cat == "suzuka":
        body = (
            f"パドック特派員スズカです！📸✨\n"
            f"【{clean_title}】をアップしました！現場の熱気と激しい走りをバッチリ激写＆レポートですよ🏁\n"
            f"{url}\n"
            f"#honda_cat {custom_tag}"
        )
    else:  # naomi
        body = (
            f"ったく…メカニックのナオミよ🔧\n"
            f"【{clean_title}】を書いたわ。タイム削る前にまずきっちり整備しなさいよね！…べ、別にあんたの心配じゃないわよ。\n"
            f"{url}\n"
            f"#honda_cat {custom_tag}"
        )

    return body


def build_gemini_tweet(article_data: dict[str, Any]) -> str | None:
    """Generate vibrant, dynamic copywriting via Gemini API using the cat reporter's persona."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None

    featured_cat = article_data.get("featuredCat", "naomi")
    persona = PERSONA_PROMPTS.get(featured_cat, PERSONA_PROMPTS["naomi"])
    slug = article_data.get("slug", "")
    url = f"{BASE_URL}/articles/{slug}/"

    ja_meta = article_data.get("locales", {}).get("ja", {})
    title = ja_meta.get("title") or article_data.get("title", "")
    summary = ja_meta.get("summary") or ja_meta.get("highlightPoint") or ""
    category = article_data.get("category", "")
    tags = article_data.get("tags", [])
    tag_str = " ".join(f"#{t}" for t in tags[:2] if t)

    system_instruction = (
        "あなたはモータースポーツ＆サーキット情報ポータル「HONDA.CAT」の記者キャラクターです。\n"
        "新しく公開された記事を読者に届けるため、X（旧Twitter）向けの日本語ポスト文を1件作成してください。\n\n"
        f"【担当記者ペルソナ】\n"
        f"名前: {persona['name']}\n"
        f"役割: {persona['role']}\n"
        f"口調ルール:\n{persona['tone_guidelines']}\n\n"
        "【厳格な文字数・形式ルール】\n"
        "1. 出力はツイート本文（プレーンテキスト）のみを出力してください。引用符やマークダウン装飾、挨拶の前置きは不要です。\n"
        "2. URLはシステム側で末尾に付加するため、**出力内にURLは含めないでください**。\n"
        "3. 本文＋ハッシュタグ全体で【全角80文字〜105文字以内】に必ず収めてください（厳格）。140文字制限を絶対に超過しないこと。\n"
        "4. 末尾には #honda_cat と、もう1つ関連ハッシュタグを含めてください。\n"
        "5. 言語は日本語のみです。"
    )

    prompt = (
        f"以下の新着記事を紹介するポスト文を作成してください：\n\n"
        f"■ 記事タイトル: {title}\n"
        f"■ カテゴリ: {category}\n"
        f"■ 概要: {summary[:150]}\n"
        f"■ 推奨タグ候補: #honda_cat {tag_str}\n"
    )

    try:
        # Use google-genai SDK Interactions API
        from google import genai  # type: ignore
        client = genai.Client()
        interaction = client.interactions.create(
            model="gemini-3.8-flash",
            system_instruction=system_instruction,
            input=prompt,
        )
        text = (interaction.output_text or "").strip()
        # Clean quotes
        text = re.sub(r'^["\'「]+|["\'」]+$', '', text).strip()
        # Remove any stray URL Gemini might have generated
        text = re.sub(r"https?://\S+", "", text).strip()

        if text and 30 <= len(text) <= 115:
            # Append URL
            full_tweet = f"{text}\n{url}"
            return full_tweet
    except Exception as e:
        print(f"⚠️ Gemini dynamic tweet generation failed ({e}). Falling back to template.")

    return None


def generate_tweet_text(article_data: dict[str, Any]) -> str:
    """Generate final tweet text with tone matching the reporter cat."""
    # Try dynamic Gemini first
    dynamic_tweet = build_gemini_tweet(article_data)
    if dynamic_tweet:
        return dynamic_tweet

    # Fallback to robust template
    return build_fallback_tweet(article_data)


# -----------------------------------------------------------------------------
# Posted Registry Management
# -----------------------------------------------------------------------------
def load_posted_slugs() -> set[str]:
    """Load the set of already posted article slugs."""
    if not POSTED_FILE.exists():
        return set()
    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("posted_slugs", []))
    except Exception as e:
        print(f"⚠️ Could not read {POSTED_FILE}: {e}")
        return set()


def save_posted_slugs(slugs: set[str]) -> None:
    """Save the updated set of posted slugs to src/data/x_posted.json."""
    data = {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": "Registry of articles posted to X (Twitter) by honda.cat cat reporters.",
        "posted_slugs": sorted(list(slugs)),
    }
    POSTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Updated posted registry: {POSTED_FILE} ({len(slugs)} articles recorded)")


def find_unposted_articles(limit: int = 1) -> list[tuple[Path, dict[str, Any]]]:
    """Find article JSON files that have not been posted to X yet."""
    posted_slugs = load_posted_slugs()
    articles: list[tuple[str, Path, dict[str, Any]]] = []

    for path in ARTICLES_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                slug = data.get("slug")
                if not slug or slug in posted_slugs:
                    continue
                pub_date = data.get("publishedAt", path.stem[:10])
                articles.append((pub_date, path, data))
        except Exception as e:
            print(f"⚠️ Skipping invalid JSON {path.name}: {e}")

    # Sort by published date descending (or ascending to post in order)
    # Posting ascending (oldest unposted first) ensures chronological sequence
    articles.sort(key=lambda x: x[0])
    selected = [(path, data) for _, path, data in articles]
    return selected[:limit] if limit > 0 else selected


# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish honda.cat new article announcements to X in the cat reporter's tone."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview tweet without posting to X")
    parser.add_argument("--slug", type=str, help="Post a specific article by its slug")
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Max number of unposted articles to publish in this run (default: 1)",
    )
    parser.add_argument(
        "--all-unposted",
        action="store_true",
        help="Publish all unposted articles found (use with caution)",
    )
    args = parser.parse_args()

    posted_slugs = load_posted_slugs()

    targets: list[dict[str, Any]] = []

    if args.slug:
        # Target specific article
        found = False
        for path in ARTICLES_DIR.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("slug") == args.slug:
                        targets.append(data)
                        found = True
                        break
            except Exception:
                pass
        if not found:
            print(f"❌ Article with slug '{args.slug}' not found in {ARTICLES_DIR}.")
            return 1
    else:
        limit = 0 if args.all_unposted else args.limit
        unposted = find_unposted_articles(limit=limit)
        if not unposted:
            print("🐾 No new unposted articles found. Everything is up to date!")
            return 0
        targets = [data for _, data in unposted]

    print(f"🚀 Found {len(targets)} article(s) to process for X posting.")

    success_count = 0
    for article in targets:
        slug = article.get("slug", "unknown")
        featured_cat = article.get("featuredCat", "naomi")
        cat_name = PERSONA_PROMPTS.get(featured_cat, {}).get("name", featured_cat)

        print(f"\n📝 Generating post for: {slug} (Reporter: {cat_name})")
        tweet_text = generate_tweet_text(article)

        print(f"💬 Tweet Preview ({len(tweet_text)} chars):\n{tweet_text}\n")

        try:
            resp = send_tweet(tweet_text, dry_run=args.dry_run)
            tweet_id = resp.get("data", {}).get("id", "dry_run")
            print(f"✅ Successfully posted to X! (Tweet ID: {tweet_id})")

            if not args.dry_run:
                posted_slugs.add(slug)
                save_posted_slugs(posted_slugs)
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to post tweet for '{slug}': {e}")
            # Don't abort completely if processing multiple; but return non-zero if all fail

    print(f"\n✨ Done. Successfully processed {success_count}/{len(targets)} post(s).")
    return 0 if success_count == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
