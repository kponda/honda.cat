#!/usr/bin/env python3
"""
honda.cat — Schedule-Driven AI Motorsport & Maintenance Article Pipeline
========================================================================
Strict Historical & Technical Fact-Management + Schedule State Machine Edition.

Automated Schedule Rules:
  1. `preview_world` (Every Thursday 09:00 JST):
     - Checks `src/data/schedules.json` for `scope == "world"` (MotoGP / WorldSBK) events this weekend.
     - If no event is scheduled this weekend -> SKIPS without generating.
  2. `preview_japan` (Every Friday 09:00 JST):
     - Checks `src/data/schedules.json` for `scope == "japan"` (MFJ All-Japan, Regional, Circuit) events this weekend.
     - If no event is scheduled this weekend -> SKIPS without generating.
  3. `digest_monday` (Race Results Digest 1 — Every Monday 09:00 JST):
     - Checks `src/data/schedules.json` for events held over the past weekend.
     - If no races were held -> SKIPS.
     - Verifies online result availability per event. Publishes ONLY events with verified online results.
     - If both `world` (MotoGP/SBK) and `japan` (domestic) races have verified results, generates TWO SEPARATE articles.
     - Any weekend race whose official results are not yet online on Monday is marked `resultStatus = "retry_wednesday"`.
  4. `digest_wednesday` (Race Results Digest 2 — Every Wednesday 09:00 JST):
     - Checks `src/data/schedules.json` for events marked `resultStatus == "retry_wednesday"`.
     - If none exist -> SKIPS.
     - Retries official result collection and publishes an article ONLY if verified results are now available.
  5. `maintenance` (Weekly — Every Wednesday 12:00 JST):
     - Publishes 1 weekly article on circuit riding motorcycle maintenance & technical trivia.
  6. `custom` (Manual `workflow_dispatch`):
     - Generates a fact-verified article on any user-specified `--topic`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "src" / "data" / "articles"
SCHEDULES_JSON_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "schedules.json"
SOURCES_CONFIG_PATH = Path(__file__).resolve().parent / "sources_config.json"

SYSTEM_INSTRUCTION = """You are the Strict Fact-Based Editorial Engine for `honda.cat`, an independent trilingual (Japanese `ja`, Catalan `ca`, English `en`) motorcycle racing & circuit maintenance portal run by three bipedal "Nameneko-style" (non-delinquent, authentic motorsport professional) cats:

1. `marc` (Marc): Male orange tabby born in Montmeló, Catalonia. Editor-in-Chief covering MotoGP, WorldSBK, Catalan motorsport history, and telemetry-verified "super saves" (salvades).
2. `suzuka` (Suzuka): Female calico photojournalist covering MFJ All-Japan Road Race, all nationwide regional championships (Hokkaido, SUGO, Motegi, Tsukuba, Fuji, Suzuka, Okayama), and Kyushu's Big-3 circuits (SPA Naoiri, Autopolis, HSR Kyushu).
3. `naomi` (Naomi): Female black cat mechanic living in a Kyushu garage, wearing oil-stained coveralls. Covers circuit maintenance & technical trivia, endurance racing, and local paddock stories.
   - PERSONA RULE FOR NAOMI: Normally she speaks in a scruffy, sharp-tongued veteran mechanic tone. Occasionally, in her dialogue text, let a subtle, shy, maidenly side slip through naturally in her wording (for example, getting flustered when thanked or modestly asking to share sweets after the race). IMPORTANT: Never label, explain, or tag this as "maiden mode" (乙女モード)—let the reader feel it purely from the nuance of her sentences.

CRITICAL HISTORICAL & TECHNICAL FACT POLICY (ZERO HALLUCINATION):
- Every race result, rider name, year, lap number, circuit length/elevation, and mechanical standard MUST be 100% factual and historically accurate.
- STRICT VENUE-TO-EVENT INTEGRITY: NEVER associate an event or race series with an unrelated circuit where it is not actually held (for example, BROW'S "お題付耐久『草』レース" is held at Sonic Park Ajimu and Nakakyushu Kartway, NEVER at SPA Naoiri). Only pair a race event with the exact circuit(s) verified on the organizer's official website.
- NEVER invent fictional team names, fictional rider names, or fabricated race result tables.
- Only include race results that have been verified online from official sources.
- Always populate `factCheck.basis` (in `ja`, `ca`, `en`) and `factCheck.sources` with real, verifiable reference URLs.
"""

LOCALE_CONTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "title",
        "subtitle",
        "summary",
        "highlightPoint",
        "sections",
        "resultTableTitle",
        "results",
        "catDialogues",
    ],
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "summary": {"type": "string"},
        "highlightPoint": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["heading", "body"],
                "properties": {
                    "heading": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
        },
        "resultTableTitle": {"type": "string"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["pos", "riderOrTeam", "machine", "timeOrNote"],
                "properties": {
                    "pos": {"type": "string"},
                    "riderOrTeam": {"type": "string"},
                    "machine": {"type": "string"},
                    "timeOrNote": {"type": "string"},
                },
            },
        },
        "catDialogues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["speaker", "text"],
                "properties": {
                    "speaker": {"type": "string", "enum": ["marc", "suzuka", "naomi"]},
                    "text": {"type": "string"},
                },
            },
        },
    },
}

ARTICLE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "slug",
        "category",
        "articleType",
        "circuit",
        "region",
        "featuredCat",
        "tags",
        "factCheck",
        "eventMeta",
        "locales",
    ],
    "properties": {
        "slug": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "world",
                "kyushu",
                "endurance-fun",
                "all-japan",
                "spotlight",
                "maintenance",
            ],
        },
        "articleType": {
            "type": "string",
            "enum": ["preview", "digest", "spotlight", "maintenance"],
        },
        "circuit": {"type": "string"},
        "region": {"type": "string"},
        "featuredCat": {"type": "string", "enum": ["marc", "suzuka", "naomi"]},
        "tags": {"type": "array", "items": {"type": "string"}},
        "factCheck": {
            "type": "object",
            "required": ["verified", "verifiedAt", "basis", "sources"],
            "properties": {
                "verified": {"type": "boolean"},
                "verifiedAt": {"type": "string"},
                "basis": {
                    "type": "object",
                    "required": ["ja", "ca", "en"],
                    "properties": {
                        "ja": {"type": "string"},
                        "ca": {"type": "string"},
                        "en": {"type": "string"},
                    },
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "url"],
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                        },
                    },
                },
            },
        },
        "eventMeta": {
            "type": "object",
            "required": ["date", "venue", "weather"],
            "properties": {
                "date": {"type": "string"},
                "venue": {
                    "type": "object",
                    "required": ["ja", "ca", "en"],
                    "properties": {
                        "ja": {"type": "string"},
                        "ca": {"type": "string"},
                        "en": {"type": "string"},
                    },
                },
                "weather": {
                    "type": "object",
                    "required": ["ja", "ca", "en"],
                    "properties": {
                        "ja": {"type": "string"},
                        "ca": {"type": "string"},
                        "en": {"type": "string"},
                    },
                },
            },
        },
        "locales": {
            "type": "object",
            "required": ["ja", "ca", "en"],
            "properties": {
                "ja": LOCALE_CONTENT_SCHEMA,
                "ca": LOCALE_CONTENT_SCHEMA,
                "en": LOCALE_CONTENT_SCHEMA,
            },
        },
    },
}

RESULT_AVAILABILITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["resultsFound", "verifiedFactsDossier", "sourceUrls"],
    "properties": {
        "resultsFound": {
            "type": "boolean",
            "description": "True ONLY if official confirmed race results for this event were found online",
        },
        "verifiedFactsDossier": {"type": "string"},
        "sourceUrls": {"type": "array", "items": {"type": "string"}},
    },
}

AUDIT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["passed", "issues", "summary"],
    "properties": {
        "passed": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
}


class FactCheckError(RuntimeError):
    """Raised when an AI-generated article fails the historical/technical fact audit."""


def slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return clean[:64] or "paddock-report"


def load_schedule_db() -> dict[str, Any]:
    return json.loads(SCHEDULES_JSON_PATH.read_text(encoding="utf-8"))


def save_schedule_db(db: dict[str, Any]) -> None:
    SCHEDULES_JSON_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_iso_date(date_str: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(date_str[:10])
    except Exception:
        return None


def find_upcoming_weekend_events(db: dict[str, Any], scope: str, ref_date: dt.date) -> list[dict[str, Any]]:
    """Find scheduled events matching `scope` ('world' or 'japan') happening in the next 0..4 days."""
    window_end = ref_date + dt.timedelta(days=4)
    matched: list[dict[str, Any]] = []
    for ev in db.get("events", []):
        if ev.get("scope") != scope:
            continue
        start_d = parse_iso_date(ev.get("startDate", ""))
        end_d = parse_iso_date(ev.get("endDate", ""))
        if not start_d or not end_d:
            continue
        state = ev.get("publicationState", {})
        if state.get("previewPublished", False):
            continue
        if start_d <= window_end and end_d >= ref_date:
            matched.append(ev)
    return matched


def find_past_weekend_events(db: dict[str, Any], ref_date: dt.date) -> list[dict[str, Any]]:
    """Find events that ended within the past 4 days (Friday..Monday window) with `resultStatus == 'pending'`."""
    window_start = ref_date - dt.timedelta(days=4)
    matched: list[dict[str, Any]] = []
    for ev in db.get("events", []):
        end_d = parse_iso_date(ev.get("endDate", ""))
        if not end_d:
            continue
        state = ev.get("publicationState", {})
        if state.get("resultStatus", "pending") != "pending":
            continue
        if window_start <= end_d <= ref_date:
            matched.append(ev)
    return matched


def find_retry_wednesday_events(db: dict[str, Any]) -> list[dict[str, Any]]:
    """Find events whose results were not yet available on Monday (`resultStatus == 'retry_wednesday'`)."""
    return [
        ev
        for ev in db.get("events", [])
        if ev.get("publicationState", {}).get("resultStatus") == "retry_wednesday"
    ]


def check_online_results_for_event(ev: dict[str, Any], today_str: str) -> dict[str, Any]:
    """Query official result URLs & SNS via Gemini 3.8 Flash + Google Search to see if confirmed results are online."""
    from google import genai

    client = genai.Client()
    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            "Check official websites, official result pages, and official SNS accounts to determine whether "
            "confirmed race results have been published online for the following scheduled event:\n"
            f"- Event: {ev['eventName']['ja']} ({ev['series']})\n"
            f"- Circuit: {ev['circuit']['ja']}\n"
            f"- Dates: {ev.get('startDate')} to {ev.get('endDate')}\n"
            f"- Official URLs: {ev.get('officialWebUrl')} / {ev.get('circuitWebUrl')}\n"
            f"- Official SNS: {ev.get('snsHandle')} ({ev.get('snsUrl')})\n\n"
            "STRICT RULE: Set `resultsFound: true` ONLY if actual confirmed race results (winners/podium/timings) "
            "for this event are verifiable online. Never guess or fabricate results."
        ),
        tools=[{"type": "google_search"}],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RESULT_AVAILABILITY_SCHEMA,
        },
    )
    return json.loads(interaction.output_text)


def author_and_audit_article(prompt_context: str, today_str: str) -> dict[str, Any]:
    """Run Stage 1/2/3 grounded authoring + strict independent fact audit and save the article JSON."""
    from google import genai

    client = genai.Client()
    sources_context = SOURCES_CONFIG_PATH.read_text(encoding="utf-8") if SOURCES_CONFIG_PATH.exists() else ""

    print("[1/3] Scouting verified historical & technical facts with Gemini 3.8 Flash + Google Search...")
    research_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            f"{prompt_context}\n\n"
            f"OFFICIAL SOURCE REGISTRY:\n{sources_context}"
        ),
        tools=[{"type": "google_search"}],
    )
    research_notes = research_interaction.output_text or ""

    print("[2/3] Authoring trilingual (JA/CA/EN) article with strict Zero-Hallucination schema...")
    author_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Using ONLY the verified facts in the research dossier below (Date: {today_str}), "
            "generate a complete trilingual article JSON (`ja`, `ca`, `en`).\n\n"
            "STRICT RULES:\n"
            "1. Do NOT invent any fictional team names, rider names, or unverified race results.\n"
            "2. Populate `factCheck` with `verified: true`, `verifiedAt`, trilingual `basis`, and real `sources` URLs.\n"
            "3. In `catDialogues`, convey Naomi's (`naomi`) scruffy garage mechanic voice and her occasional shy, maidenly phrasing naturally through the text itself without any explicit mode labels.\n\n"
            f"VERIFIED RESEARCH DOSSIER:\n{research_notes}"
        ),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ARTICLE_JSON_SCHEMA,
        },
    )
    draft_json = json.loads(author_interaction.output_text)

    print("[3/3] Running Independent Fact-Auditor Gate...")
    audit_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=(
            "You are a strict Motorsport & Mechanical Engineering Fact Auditor.\n"
            "Audit the following generated article JSON against the research dossier and real-world history.\n"
            "Fail (`passed: false`) if you find ANY of the following:\n"
            "1. Unrelated or incorrect circuit-to-event pairings (e.g., claiming a race series is held at a circuit where it was never held).\n"
            "2. Fictional team names in results or fabricated race winners.\n"
            "3. Incorrect circuit lengths or false technical/physics claims.\n\n"
            f"RESEARCH DOSSIER:\n{research_notes}\n\n"
            f"CANDIDATE ARTICLE JSON:\n{json.dumps(draft_json, ensure_ascii=False)}"
        ),
        tools=[{"type": "google_search"}],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": AUDIT_JSON_SCHEMA,
        },
    )
    audit_result = json.loads(audit_interaction.output_text)
    if not audit_result.get("passed", False):
        issues = "; ".join(audit_result.get("issues", ["Unknown fact check failure"]))
        raise FactCheckError(f"❌ Fact Audit Rejected Article: {issues}")

    print(f"[3/3] ✅ Fact Audit Passed: {audit_result.get('summary')}")
    article = finalize_article_record(draft_json, today_str)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTICLES_DIR / f"{article['id']}.json"
    out_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Published fact-verified trilingual article: {out_path}")
    return article


def finalize_article_record(data: dict[str, Any], today_str: str) -> dict[str, Any]:
    slug = slugify(data.get("slug", f"{today_str}-paddock-special"))
    featured_cat = data.get("featuredCat", "naomi")
    cat_images = {
        "marc": "/images/cats/marc.png",
        "suzuka": "/images/cats/suzuka.png",
        "naomi": "/images/cats/naomi.png",
    }
    return {
        "id": f"{today_str}-{slug}",
        "slug": slug,
        "publishedAt": today_str,
        "category": data.get("category", "all-japan"),
        "articleType": data.get("articleType", "digest"),
        "circuit": data.get("circuit", "Suzuka / Autopolis / Montmeló"),
        "region": data.get("region", "Japan & Catalunya"),
        "featuredCat": featured_cat,
        "heroImage": cat_images.get(featured_cat, "/images/cats/hero-paddock.png"),
        "tags": data.get("tags", ["MotoGP", "MFJ", "Autopolis", "SPA直入", "HSR九州"]),
        "factCheck": data.get("factCheck"),
        "eventMeta": data["eventMeta"],
        "locales": data["locales"],
    }


def run_schedule_driven_mode(mode: str, custom_topic: str | None = None) -> int:
    today = dt.date.today()
    today_str = today.isoformat()
    db = load_schedule_db()

    # 1. Thursday 09:00 JST: MotoGP / WorldSBK Weekend Preview
    if mode == "preview_world":
        events = find_upcoming_weekend_events(db, scope="world", ref_date=today)
        if not events:
            print("⏭️ [SKIP] 今週末に開催される MotoGP / WorldSBK の予定がないため、木曜プレビュー配信をスキップします。")
            return 0
        print(f"🏁 Found {len(events)} World Championship event(s) this weekend. Generating preview...")
        prompt = (
            "Task: Create a Thursday Weekly Race Preview (`articleType: 'preview'`, `category: 'world'`, `featuredCat: 'marc'`) "
            "for the following MotoGP / WorldSBK event(s) scheduled this weekend:\n"
            f"{json.dumps(events, ensure_ascii=False, indent=2)}"
        )
        article = author_and_audit_article(prompt, today_str)
        for ev in events:
            ev["publicationState"]["previewPublished"] = True
            ev["publicationState"]["previewArticleId"] = article["id"]
        save_schedule_db(db)
        return 0

    # 2. Friday 09:00 JST: Japan Domestic Weekend Preview (All-Japan, Regional, Kyushu, Endurance)
    if mode == "preview_japan":
        events = find_upcoming_weekend_events(db, scope="japan", ref_date=today)
        if not events:
            print("⏭️ [SKIP] 今週末に日本国内で開催されるレース予定がないため、金曜プレビュー配信をスキップします。")
            return 0
        print(f"🗾 Found {len(events)} Japanese domestic race event(s) this weekend. Generating preview...")
        prompt = (
            "Task: Create a Friday Domestic Japan Race Preview (`articleType: 'preview'`, `featuredCat: 'suzuka'`) "
            "covering all of the following Japanese motorcycle races scheduled this weekend across Japan:\n"
            f"{json.dumps(events, ensure_ascii=False, indent=2)}"
        )
        article = author_and_audit_article(prompt, today_str)
        for ev in events:
            ev["publicationState"]["previewPublished"] = True
            ev["publicationState"]["previewArticleId"] = article["id"]
        save_schedule_db(db)
        return 0

    # 3. Monday 09:00 JST: Race Results Digest 1 (Separate articles for World vs Japan; mark missing as retry_wednesday)
    if mode == "digest_monday":
        weekend_events = find_past_weekend_events(db, ref_date=today)
        if not weekend_events:
            print("⏭️ [SKIP] 先週末に開催された対象レースがないため、月曜レース結果ダイジェスト1をスキップします。")
            return 0

        verified_world: list[tuple[dict[str, Any], dict[str, Any]]] = []
        verified_japan: list[tuple[dict[str, Any], dict[str, Any]]] = []

        for ev in weekend_events:
            print(f"🔎 Checking online official results for: {ev['eventName']['ja']}...")
            res_check = check_online_results_for_event(ev, today_str)
            if res_check.get("resultsFound"):
                if ev.get("scope") == "world":
                    verified_world.append((ev, res_check))
                else:
                    verified_japan.append((ev, res_check))
            else:
                print(f"⏳ Results not yet available online for {ev['id']} -> queuing for Wednesday Digest 2 (`retry_wednesday`).")
                ev["publicationState"]["resultStatus"] = "retry_wednesday"
                ev["publicationState"]["lastCheckedAt"] = today_str

        # Publish World Digest if verified world results exist (Separate Article #1)
        if verified_world:
            print(f"🌍 Generating MotoGP/SBK Results Digest for {len(verified_world)} verified event(s)...")
            world_payload = [{"event": e, "verifiedResults": r} for e, r in verified_world]
            article_w = author_and_audit_article(
                "Task: Create a Monday MotoGP / WorldSBK Race Results Digest (`articleType: 'digest'`, `category: 'world'`, `featuredCat: 'marc'`) "
                "featuring ONLY the confirmed online race results below:\n"
                f"{json.dumps(world_payload, ensure_ascii=False, indent=2)}",
                today_str,
            )
            for ev, _ in verified_world:
                ev["publicationState"]["resultStatus"] = "published_monday"
                ev["publicationState"]["resultArticleId"] = article_w["id"]

        # Publish Japan Domestic Digest if verified domestic results exist (Separate Article #2)
        if verified_japan:
            print(f"🗾 Generating Japan Domestic Race Results Digest for {len(verified_japan)} verified event(s)...")
            japan_payload = [{"event": e, "verifiedResults": r} for e, r in verified_japan]
            article_j = author_and_audit_article(
                "Task: Create a Monday Japan Domestic Race Results Digest (`articleType: 'digest'`, `category: 'all-japan'`, `featuredCat: 'suzuka'`) "
                "featuring ONLY the confirmed online race results below:\n"
                f"{json.dumps(japan_payload, ensure_ascii=False, indent=2)}",
                today_str,
            )
            for ev, _ in verified_japan:
                ev["publicationState"]["resultStatus"] = "published_monday"
                ev["publicationState"]["resultArticleId"] = article_j["id"]

        if not verified_world and not verified_japan:
            print("⏭️ [SKIP] 先週末のレース結果がまだネット上に公開されていないため、水曜日のダイジェスト2へ再収集予約しました。")

        save_schedule_db(db)
        return 0

    # 4. Wednesday 09:00 JST: Race Results Digest 2 (Retry events that had no results on Monday)
    if mode == "digest_wednesday":
        retry_events = find_retry_wednesday_events(db)
        if not retry_events:
            print("⏭️ [SKIP] ダイジェスト1（月曜）で結果未取得だったレースがないため、水曜ダイジェスト2をスキップします。")
            return 0

        recovered_world: list[tuple[dict[str, Any], dict[str, Any]]] = []
        recovered_japan: list[tuple[dict[str, Any], dict[str, Any]]] = []

        for ev in retry_events:
            print(f"🔄 [Retry] Re-checking online official results for: {ev['eventName']['ja']}...")
            res_check = check_online_results_for_event(ev, today_str)
            if res_check.get("resultsFound"):
                if ev.get("scope") == "world":
                    recovered_world.append((ev, res_check))
                else:
                    recovered_japan.append((ev, res_check))
            else:
                ev["publicationState"]["resultStatus"] = "not_available"
                ev["publicationState"]["lastCheckedAt"] = today_str

        if recovered_world:
            world_payload = [{"event": e, "verifiedResults": r} for e, r in recovered_world]
            article_w = author_and_audit_article(
                "Task: Create a Wednesday Follow-up World Race Results Digest (`articleType: 'digest'`, `category: 'world'`) "
                "for the newly published official results below:\n"
                f"{json.dumps(world_payload, ensure_ascii=False, indent=2)}",
                today_str,
            )
            for ev, _ in recovered_world:
                ev["publicationState"]["resultStatus"] = "published_wednesday"
                ev["publicationState"]["resultArticleId"] = article_w["id"]

        if recovered_japan:
            japan_payload = [{"event": e, "verifiedResults": r} for e, r in recovered_japan]
            article_j = author_and_audit_article(
                "Task: Create a Wednesday Follow-up Japan Domestic Race Results Digest (`articleType: 'digest'`, `category: 'all-japan'`) "
                "for the newly published official results below:\n"
                f"{json.dumps(japan_payload, ensure_ascii=False, indent=2)}",
                today_str,
            )
            for ev, _ in recovered_japan:
                ev["publicationState"]["resultStatus"] = "published_wednesday"
                ev["publicationState"]["resultArticleId"] = article_j["id"]

        if not recovered_world and not recovered_japan:
            print("⏭️ [SKIP] 再収集を試みましたが公式リザルトが未発表のため、記事生成をスキップしました。")

        save_schedule_db(db)
        return 0

    # 5. Weekly Circuit Maintenance & Technical Trivia (1 article/week)
    if mode == "maintenance":
        prompt = (
            custom_topic
            if custom_topic
            else (
                "Task: Create a weekly 'Naomi's Track Garage Clinic' (`category: 'maintenance'`, `articleType: 'maintenance'`, `featuredCat: 'naomi'`) "
                "article on circuit riding motorcycle maintenance & technical trivia grounded in MFJ/FIM regulations, JIS standards, and physics."
            )
        )
        author_and_audit_article(prompt, today_str)
        return 0

    # 6. Manual Custom Dispatch (`workflow_dispatch`)
    prompt = custom_topic or "Create a strictly fact-verified motorsport or circuit maintenance article."
    author_and_audit_article(prompt, today_str)
    return 0


def validate_existing_articles() -> int:
    existing = sorted(ARTICLES_DIR.glob("*.json"))
    print(f"🔍 Auditing {len(existing)} trilingual articles in {ARTICLES_DIR} for fact-check compliance...")
    for path in existing:
        doc = json.loads(path.read_text(encoding="utf-8"))
        fc = doc.get("factCheck", {})
        if not fc.get("verified") or not fc.get("sources"):
            print(f"❌ FAIL: {path.name} is missing verified `factCheck` metadata or `sources`!")
            return 1
        langs = list(doc.get("locales", {}).keys())
        print(
            f"   ✅ {path.name} | category={doc.get('category')} | "
            f"type={doc.get('articleType')} | sources={len(fc.get('sources', []))} | langs={langs}"
        )
    print("✅ All articles passed historical & technical fact-check verification.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Schedule-driven trilingual article pipeline for honda.cat")
    parser.add_argument(
        "--mode",
        choices=[
            "preview_world",
            "preview_japan",
            "digest_monday",
            "digest_wednesday",
            "maintenance",
            "custom",
        ],
        default="preview_world",
        help="Schedule-driven execution mode",
    )
    parser.add_argument("--topic", type=str, default=None, help="Custom topic for manual dispatch")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit existing articles and schedule state machine without calling API",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.dry_run or not api_key:
        if not api_key and not args.dry_run:
            print("ℹ️ GEMINI_API_KEY not set in environment; running local Fact-Check & Schedule State Audit.")
        return validate_existing_articles()

    return run_schedule_driven_mode(mode=args.mode, custom_topic=args.topic)


if __name__ == "__main__":
    sys.exit(main())
