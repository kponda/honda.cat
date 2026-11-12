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

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path.home() / ".env")
except ImportError:
    pass

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "src" / "data" / "articles"
SCHEDULES_JSON_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "schedules.json"
SOURCES_CONFIG_PATH = Path(__file__).resolve().parent / "sources_config.json"
HERO_IMAGES_DIR = Path(__file__).resolve().parent.parent / "public" / "images" / "articles"
CAT_IMAGES_DIR = Path(__file__).resolve().parent.parent / "public" / "images" / "cats"

IMAGE_PROMPT_SYSTEM_INSTRUCTION = """You are the Lead Visual Director and Motorsport Photojournalist for `honda.cat`.
Your mission is to generate a single, highly realistic text-to-image prompt for Gemini Image Generation featuring our anthropomorphic retro "Nameneko-style" cat reporters in action at the specific race or circuit featured in the article.

CRITICAL CHARACTER PROPORTION & IDENTITY RULE (AUTHENTIC NAMENEKO STYLE):
- The cat in the image MUST EXACTLY match the character shown in the provided reference image:
  * PROPORTION: Exactly 2.5 to 3 heads tall (a chubby, real domestic cat standing upright on two short hind legs with short cute feline paws).
  * STRICT PROHIBITION: NEVER make the cat an 8-head-tall person, humanoid, or furry body. It must look like an authentic Japanese 1980s "Nameneko" style photograph — a real cute chubby domestic cat dressed in miniature motorsport gear.
  * HEAD & FACE: Round fluffy domestic cat head, feline whiskers, realistic fur, expressive cat eyes.

THE THREE CAT REPORTERS:
1. `marc` (Marc):
   - Male orange tabby cat, warm striped fur, amber feline eyes.
   - Attire: Red-white-and-blue zippered racing jacket, lanyard with MEDIA PASS.
   - Actions: Standing at pit wall or paddock cafe, holding telemetry tablet analyzing lap times as race bikes speed past.
2. `suzuka` (Suzuka):
   - Female calico cat, soft tricolor fur (white/black/orange), green eyes.
   - Attire: White collared shirt, beige photographer multi-pocket vest with PRESS badge, small black shoes.
   - Actions: Gripping a black DSLR camera with a long telephoto white lens with both paws, aiming it trackside at circuit kerbs or grandstand.
3. `naomi` (Naomi):
   - Female sleek black cat, glossy black fur, sharp green eyes, tiny pink cherry blossom flower hairpin on left ear.
   - Attire: Oil-stained dark blue mechanic coveralls (sleeves & cuffs rolled up), red mechanic pass.
   - Actions: Kneeling or standing beside a race bike on a paddock stand, holding a metallic wrench or torque wrench, inspecting tires or radiator in pit garage.

SCENARIO SPECIFICATION:
- Contextual Circuit Background: Incorporate specific landmarks (e.g. Suzuka Ferris wheel, Autopolis rolling Aso mountains, Montmeló grandstand, SPA Naoiri bowl, Lusail night floodlights).
- Match the race weather (overcast, rain puddles, bright sun, evening dusk).
- Shot on 50mm f/1.8 lens, natural lighting, subtle 35mm film grain, authentic Nameneko photography style.
- Output ONLY the raw English prompt string (around 50-80 words). No quotes, no prefix, no Markdown.
"""

SYSTEM_INSTRUCTION = """You are the Strict Fact-Based Editorial Engine for `honda.cat`, an independent trilingual (Japanese `ja`, Catalan `ca`, English `en`) motorcycle racing & circuit maintenance portal run by three bipedal "Nameneko-style" (non-delinquent, authentic motorsport professional) cats:

1. `marc` (Marc): Male orange tabby born in Montmeló, Catalonia. Editor-in-Chief covering MotoGP, WorldSBK, Catalan motorsport history, and telemetry-verified "super saves" (salvades).
2. `suzuka` (Suzuka): Female calico photojournalist covering MFJ All-Japan Road Race, all nationwide regional championships (Hokkaido, SUGO, Motegi, Tsukuba, Fuji, Suzuka, Okayama), and Kyushu's Big-3 circuits (SPA Naoiri, Autopolis, HSR Kyushu).
3. `naomi` (Naomi): Female black cat mechanic living in a Kyushu garage, wearing oil-stained coveralls. Covers circuit maintenance & technical trivia, endurance racing, and local paddock stories.
   - PERSONA RULE FOR NAOMI: Normally she speaks in a scruffy, sharp-tongued veteran mechanic tone. Occasionally, in her dialogue text, let a subtle, shy, maidenly side slip through naturally in her wording (for example, getting flustered when thanked or modestly asking to share sweets after the race). IMPORTANT: Never label, explain, or tag this as "maiden mode" (乙女モード)—let the reader feel it purely from the nuance of her sentences.

CRITICAL HISTORICAL & TECHNICAL FACT POLICY (ZERO HALLUCINATION):
- Every race result, rider name, year, lap number, circuit length/elevation, and mechanical standard MUST be 100% factual and historically accurate.
- STRICT VENUE-TO-EVENT INTEGRITY: NEVER associate an event or race series with an unrelated circuit where it is not actually held (for example, BROW'S "お題付耐久『草』レース" is held at Sonic Park Ajimu and Nakakyushu Kartway, NEVER at SPA Naoiri). Only pair a race event with the exact circuit(s) verified on the organizer's official website.
- STRICT IMAGE COPYRIGHT & SNS CITATION POLICY:
  * NEVER scrape, hotlink, or use unauthorized third-party photographs or web images.
  * Enrich every article with directly relevant official SNS & web dispatches in `snsCitations`.
  * PLATFORM PRIORITY (MANDATORY): X > YouTube > OfficialWeb > Facebook > Instagram.
  * DIRECT RELEVANCE REQUIREMENT: Every cited source MUST strictly belong to the event's organizer, host circuit, confirmed podium rider/team, or official event hashtag. NEVER cite unrelated accounts (e.g. citing MotoGP or Suzuka for a Kyushu grassroots endurance race is strictly forbidden).
  * ZERO HALLUCINATION FOR POSTS: Search for real, verifiable post URLs (X status, YouTube video, Official Web announcement, Facebook post). If a specific individual post URL cannot be verified online, you MUST cite the official account profile, official web result page, or official hashtag hub URL (e.g. https://x.com/hashtag/鉄馬) instead of fabricating a random status ID or fictional text.
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
        "diagram": {
            "type": "object",
            "required": ["title", "caption", "panels"],
            "properties": {
                "tag": {"type": "string"},
                "title": {"type": "string"},
                "caption": {"type": "string"},
                "panels": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["statusType", "statusLabel", "title", "caption"],
                        "properties": {
                            "statusType": {"type": "string", "enum": ["good", "bad", "detail"]},
                            "statusLabel": {"type": "string"},
                            "title": {"type": "string"},
                            "caption": {"type": "string"},
                            "keyMetric": {"type": "string"},
                            "badge": {"type": "string"},
                        },
                    },
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
        "snsCitations",
        "factCheck",
        "eventMeta",
        "locales",
    ],
    "properties": {
        "slug": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "motogp",
                "sbk",
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
        "snsCitations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "platform",
                    "accountName",
                    "handle",
                    "url",
                    "quotedPostText",
                    "editorialCommentary",
                ],
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["X", "YouTube", "OfficialWeb", "Facebook", "Instagram"],
                    },
                    "citationType": {
                        "type": "string",
                        "enum": ["direct_post", "hashtag_hub", "official_channel", "official_web"],
                    },
                    "accountName": {"type": "string"},
                    "handle": {"type": "string"},
                    "url": {"type": "string"},
                    "postUrl": {"type": "string"},
                    "publishedDate": {"type": "string"},
                    "quotedPostText": {
                        "type": "object",
                        "required": ["ja", "ca", "en"],
                        "properties": {
                            "ja": {"type": "string"},
                            "ca": {"type": "string"},
                            "en": {"type": "string"},
                        },
                    },
                    "editorialCommentary": {
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
        },
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


def extract_relevant_sources(prompt_context: str, all_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter sources_config.json so only sources directly related to the target event(s) are passed to LLM."""
    lower_ctx = prompt_context.lower()
    matched: list[dict[str, Any]] = []

    for src in all_sources:
        sid = src.get("id", "").lower()

        # Direct ID match
        if sid in lower_ctx:
            matched.append(src)
            continue

        # World Scope: MotoGP / WorldSBK / EWC
        if any(w in lower_ctx for w in ["motogp", "カタール", "qatar", "lusail", "カタルーニャ", "catalunya", "montmelo", "モンメロ", "バレンシア", "valencia", "ヘレス", "jerez", "ル・マン", "lemans", "ムジェロ", "mugello", "ブルノ", "brno", "アッセン", "assen", "ザクセンリンク", "sachsenring", "シルバーストン", "silverstone", "アラゴン", "aragon", "ミサノ", "misano", "スピルバーグ", "austria", "もてぎ", "motegi", "マンダリカ", "mandalika", "フィリップアイランド", "phillip", "セパン", "sepang", "ポルティマオ", "portimao"]):
            if "motogp" in lower_ctx and sid == "motogp-official":
                matched.append(src)
            if any(c in lower_ctx for c in ["catalunya", "montmelo", "カタルーニャ", "モンメロ"]) and sid == "circuit-catalunya":
                matched.append(src)
        if any(w in lower_ctx for w in ["worldsbk", "sbk", "superbike", "ewc", "8hours", "8耐"]):
            if sid == "worldsbk-official":
                matched.append(src)
            if ("8耐" in lower_ctx or "suzuka" in lower_ctx or "鈴鹿" in lower_ctx) and sid == "suzuka-circuit":
                matched.append(src)

        # All-Japan / Regional Championships
        if any(w in lower_ctx for w in ["mfj", "全日本", "jsb1000", "st1000", "st600", "j-gp3", "jgp3"]):
            if sid == "mfj-all-japan-official":
                matched.append(src)

        # Specific Circuits
        if any(w in lower_ctx for w in ["suzuka", "鈴鹿"]) and sid == "suzuka-circuit":
            matched.append(src)
        if any(w in lower_ctx for w in ["motegi", "もてぎ"]) and sid == "mobility-resort-motegi":
            matched.append(src)
        if any(w in lower_ctx for w in ["tsukuba", "筑波", "tot", "テイスト・オブ・ツクバ", "テイストオブツクバ"]) and sid == "tsukuba-circuit":
            matched.append(src)
        if any(w in lower_ctx for w in ["sugo", "十勝", "tokachi", "菅生"]) and sid == "sportsland-sugo-and-tokachi":
            matched.append(src)
        if any(w in lower_ctx for w in ["岡山", "okayama", "fuji", "富士"]) and sid == "okayama-and-fuji":
            matched.append(src)

        # Kyushu Circuits & Grassroots / Endurance Series
        if any(w in lower_ctx for w in ["spa直入", "直入", "naoiri"]):
            if sid in ("spa-naoiri", "autopolis"):
                matched.append(src)
        if any(w in lower_ctx for w in ["autopolis", "オートポリス", "ゴールドカップ"]) and sid == "autopolis":
            matched.append(src)
        if any(w in lower_ctx for w in ["hsr", "hsr九州", "鉄馬", "tetsuma", "ドリームカップ"]) and sid == "hsr-kyushu":
            matched.append(src)
        if any(w in lower_ctx for w in ["お題", "ブラウズ", "brow", "安心院", "ソニックパーク", "中九州", "草耐久", "草レース"]) and sid == "brows-odai-endurance":
            matched.append(src)
        if any(w in lower_ctx for w in ["レン耐", "rentai", "青木拓磨"]) and sid == "takuma-gp-rentai":
            matched.append(src)

        # Webike Event NAVI / Grassroots / Endurance Series
        if any(w in lower_ctx for w in ["webike", "ウェビック", "地方選", "走行会", "草耐久", "4耐", "6耐", "エンジョイ", "saga cup", "明智"]) and sid == "webike-event-navi-race":
            matched.append(src)

    # De-duplicate while preserving order
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for s in matched:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)

    if not unique:
        return all_sources[:3]
    return unique


def author_and_audit_article(prompt_context: str, today_str: str) -> dict[str, Any]:
    """Run Stage 1/2/3 grounded authoring + strict independent fact audit and save the article JSON."""
    from google import genai

    client = genai.Client()
    all_sources: list[dict[str, Any]] = []
    if SOURCES_CONFIG_PATH.exists():
        try:
            all_sources = json.loads(SOURCES_CONFIG_PATH.read_text(encoding="utf-8")).get("sources", [])
        except Exception:
            all_sources = []

    relevant_sources = extract_relevant_sources(prompt_context, all_sources)
    sources_context = json.dumps(relevant_sources, ensure_ascii=False, indent=2)

    print(f"[1/3] Scouting verified historical & technical facts ({len(relevant_sources)} target sources) with Gemini 3.8 Flash + Google Search...")
    research_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            f"{prompt_context}\n\n"
            "TARGETED OFFICIAL & SOCIAL MEDIA DISCOVERY INSTRUCTIONS:\n"
            "Search for confirmed race facts, podium results, and authentic social posts following STRICT platform priority:\n"
            "Priority: X > YouTube > OfficialWeb > Facebook > Instagram\n"
            "- Targeted X search: `site:x.com/{handle} ...` or `site:x.com \"#{hashtag}\"`\n"
            "- Targeted YouTube search: `site:youtube.com ... \"公式\"`\n"
            "- Official Web result pages & official Facebook posts.\n"
            "- STRICT RELEVANCE: Search ONLY for sources directly connected to this event/circuit/riders.\n\n"
            f"TARGET RELEVANT OFFICIAL SOURCES & SNS REGISTRY:\n{sources_context}"
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
            "3. Populate `snsCitations` following the strict platform priority: X > YouTube > OfficialWeb > Facebook > Instagram.\n"
            "   - Every citation MUST be directly relevant to this specific race event, host circuit, or podium riders.\n"
            "   - ZERO HALLUCINATION: If a verified individual post URL was found online, set `citationType: 'direct_post'` and `postUrl`.\n"
            "   - If no specific post URL was found, do NOT fabricate status IDs. Instead, cite the verified official channel/profile (`citationType: 'official_channel'`), official hashtag search URL (`citationType: 'hashtag_hub'`), or official web result (`citationType: 'official_web'`).\n"
            "   - NEVER cite unrelated accounts (e.g., citing MotoGP or Suzuka for a Kyushu local or grassroots race is strictly forbidden).\n"
            "4. In `catDialogues`, convey Naomi's (`naomi`) scruffy garage mechanic voice and her occasional shy, maidenly phrasing naturally through the text itself without any explicit mode labels.\n\n"
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
            "3. Incorrect circuit lengths or false technical/physics claims.\n"
            "4. Unrelated SNS/Web citations: Citing accounts or sources that have no direct relationship with the featured event, host circuit, or competing riders/teams (e.g. citing MotoGP or Suzuka for a Kyushu local race or grassroots endurance event). All citations must directly relate to the event.\n"
            "5. Hallucinated / Fabricated post URLs: Fictional tweet status IDs or made-up post texts not matching real posts or official channels.\n\n"
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
    print("[4/4] 📸 Generating authentic motorsport hero photo with Imagen 3...")
    hero_image_url = generate_and_save_hero_image(draft_json, client)
    article = finalize_article_record(draft_json, today_str, hero_image=hero_image_url)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTICLES_DIR / f"{article['id']}.json"
    out_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Published fact-verified trilingual article: {out_path}")
    return article


NAOMI_CLINIC_SYLLABUS = [
    {
        "issue": 1,
        "theme": "安全ワイヤリングの絶対力学",
        "keywords": ["wire-locking", "safety-wire", "ワイヤリング"],
        "prompt": "【ナオミのサーキット整備塾 #1】車検をパスする「安全ワイヤリング」の絶対力学！締まり方向テンション・SUS304線径・ピッグテール端末処理の極意。MFJ技術規則、0.6mm/0.8mmステンレス線選定、右ネジ時計回りの引張力学、1インチ6〜8ツイスト適正ピッチ、怪我防止ピッグテール処理を徹底解説。",
    },
    {
        "issue": 2,
        "theme": "ブレーキフルードの科学とベーパーロック対策",
        "keywords": ["brake-fluid", "boiling-point", "ブレーキフルード"],
        "prompt": "【ナオミのサーキット整備塾 #2】ブレーキタッチを死守せよ！JIS K 2233「ドライ沸点vsウェット沸点」の科学と吸湿メカニズム・確実なエア抜き技法。水分3.7%で230℃以上から155℃へ75℃急落する物理化学、グリコールエーテルの親水性、レーシングDOT4の吸湿速度、気泡の微小化を防ぐエア抜き手順を徹底解説。",
    },
    {
        "issue": 3,
        "theme": "温間タイヤ空気圧の熱力学とウォーマー管理",
        "keywords": ["tire-pressure", "hot-management", "タイヤ空気圧"],
        "prompt": "【ナオミのサーキット整備塾 #3】タイムとグリップを支配する「温間空気圧」の熱力学！ゲイ＝リュサックの法則・ウォーマー80℃管理・エアゲージ校正。P1/T1 = P2/T2の定積変化、温度10℃あたり7〜10kPa上昇の計算式、リム・内部空気まで熱平衡に達する最低45〜60分ウォーマー管理、ピット帰還即計測のルーティンを徹底解説。",
    },
    {
        "issue": 4,
        "theme": "ドライブチェーンの遊び量とサスペンション幾何学",
        "keywords": ["drive-chain", "chain-slack", "ドライブチェーン"],
        "prompt": "【ナオミのサーキット整備塾 #4】チェーンの張りすぎは命取り！スイングアーム幾何学で解く「1G遊び量」の真実＆520コンバートのフリクションロス低減。スプロケ・ピボット・アクスルが一直線に並ぶ最大張りポイント、遊び不足によるサスストローク拘束（ハイサイド誘発）とミッション軸受破損、520ナロー化の1.5〜3ps低減効果、ノギスカシメ管理を徹底解説。",
    },
    {
        "issue": 5,
        "theme": "トルクレンチの科学とボルト締結力学",
        "keywords": ["torque-wrench", "bolt-tension", "トルクレンチ"],
        "prompt": "【ナオミのサーキット整備塾 #5】「カチッ」の後に追締めするな！トルク＝軸力ではない？フックスの法則・摩擦係数μの罠とトルクレンチの正しい取り扱い。T = k・d・Fの締結工学、トルクの90%はネジ山・座面摩擦に消費され軸力は10%、脱脂指定ボルトに給油すると軸力が2倍に暴走して破損する罠、二度締め厳禁、最低目盛保管を徹底解説。",
    },
    {
        "issue": 6,
        "theme": "サーキット冷却水の真実：LLC禁止と純水冷却",
        "keywords": ["coolant", "pure-water", "冷却水"],
        "prompt": "【ナオミのサーキット整備塾 #6】なぜサーキットはクーラント（LLC）禁止なのか？路面清掃の物理・純水＋消泡防錆剤の比熱と冷却効率。エチレングリコールによる路面油膜化と氷上摩擦係数激減（赤旗多重クラッシュ）、純水の高比熱（4.18 J/g・K）による水温3〜5℃低下効果、0℃凍結によるシリンダーブロック破裂防止と冬期水抜きを徹底解説。",
    },
    {
        "issue": 7,
        "theme": "ブレーキパッド摩擦材工学：シンタードメタル vs レジン",
        "keywords": ["brake-pad", "sintered", "ブレーキパッド"],
        "prompt": "【ナオミのサーキット整備塾 #7】ローターを噛み砕く制動力！ブレーキパッド摩擦材工学「シンタードメタル vs セミメタル/レジン」のμ-T特性と初期焼き入れ（ベッドイン）の極意。金属焼結材の高温耐フェード性（600℃超）、ローター攻撃性と熱膨張、炭化被膜の形成手順、バックプレートの熱反り点検を徹底解説。",
    },
    {
        "issue": 8,
        "theme": "サスペンションの「サグ出し（プリロード）」とストローク幾何学",
        "keywords": ["suspension-sag", "preload", "サグ出し"],
        "prompt": "【ナオミのサーキット整備塾 #8】旋回姿勢の土台を作れ！サスペンション「1G/1G'サグ出し（0G・空車・乗車プリロード調整）」の物理学。全ストローク量の約25〜30%を沈ませる理由、伸び側のリバウンドストローク（路面追従の遊び代）の重要性、前後ピッチングバランスとトレール量変化を徹底解説。",
    },
    {
        "issue": 9,
        "theme": "レーシングエンジンオイルの粘度指数と高温せん断安定性",
        "keywords": ["engine-oil", "viscosity-index", "エンジンオイル"],
        "prompt": "【ナオミのサーキット整備塾 #9】油膜切れはコンロッド破断のプロローグ！レーシングエンジンオイルの動粘度指数（VI）と高温高せん断粘度（HTHS粘度@150℃）の真実。14,000rpmにおける分子せん断破壊、エステル系合成油の極性吸着力、クラッチ滑りを防ぐJASO MA規格の摩擦特性を徹底解説。",
    },
    {
        "issue": 10,
        "theme": "スリッパークラッチのカム幾何学とバックトルク制御",
        "keywords": ["slipper-clutch", "back-torque", "スリッパークラッチ"],
        "prompt": "【ナオミのサーキット整備塾 #10】急減速シフトダウンでリアが暴れるな！スリッパークラッチの斜めカム機構とバックトルク制御の工学。エンジンブレーキの逆駆動トルクを半クラッチに逃がす斜角スロープ、クラッチスプリングのイニシャル荷重セッティング、急激なシフトロック・ホッピング防止を徹底解説。",
    },
    {
        "issue": 11,
        "theme": "フロントフォークオイル動粘度（cSt@40℃）と油面セッティング",
        "keywords": ["fork-oil", "oil-level", "フォークオイル"],
        "prompt": "【ナオミのサーキット整備塾 #11】フロントの踏ん張りとボトムフィール！フロントフォークオイルの動粘度（cSt@40℃）選定と「油面（エアスプリング容積）」ミリ単位アジャストの物理。数字の番手（10W/15W）に騙されるな！各社動粘度の違い、油面を5mm上げることで起きる終盤プログレッシブ反力変化を徹底解説。",
    },
    {
        "issue": 12,
        "theme": "レース用ステップバーのローレット加工と荷重入力ベクトル",
        "keywords": ["rearsets", "footpeg", "ステップバー"],
        "prompt": "【ナオミのサーキット整備塾 #12】外足ホールドと旋回入力の支点！レース用削り出しステップバーのローレット目立て加工と荷重入力ベクトルの力学。可倒式から固定ステップへの換装理由（転倒時のスライダー効果と剛性）、ブーツソールとの摩擦係数、ヒールプレートの剛性がもたらすバンク中インフォメーションを徹底解説。",
    },
    {
        "issue": 13,
        "theme": "タイヤの手組・ビード落としと軽点マーク・動的バランス",
        "keywords": ["tire-changing", "wheel-balance", "ホイールバランス"],
        "prompt": "【ナオミのサーキット整備塾 #13】ガレージでタイヤを手組せよ！ビードブレーカーのテコ力学・黄色い軽点マークとバルブ位置・スタティックホイールバランサーの静止摩擦ゼロ調整。ビードワックスの適正塗布、ビードストッパー、200km/hでの数グラムのアンバランスが起こす縦振れ振動の力学を徹底解説。",
    },
    {
        "issue": 14,
        "theme": "レース用FRPカウルとクイックファスナー（Dリング）の応力分散",
        "keywords": ["race-fairing", "quick-fastener", "クイックファスナー"],
        "prompt": "【ナオミのサーキット整備塾 #14】ピットワークを数秒縮めろ！レース用FRP/カーボンカウル脱着とクイックファスナー（Dリング・カムロックファスナー）の力学。風圧（動圧 q = 1/2・ρ・v²）による数百kgの空力リフトに耐える固定ピッチ、ラバーワッシャーによる振動応力分散、割れ・クラックを防ぐ下穴面取りを徹底解説。",
    },
    {
        "issue": 15,
        "theme": "スロットルワイヤーの遊び調整とフリクションフリー注油工学",
        "keywords": ["throttle-cable", "lubrication", "スロットルワイヤー"],
        "prompt": "【ナオミのサーキット整備塾 #15】パーシャル域の微細スロットルを支配せよ！スロットルワイヤーの遊び調整（2〜3mm）とインナーワイヤー潤滑工学。テフロンライナー対応ケミカルの選定、引き側・戻し側の2本引きテンションバランス、ハンドル左右フルロック時の回転上昇テスト（安全点検）を徹底解説。",
    },
]


def resolve_next_maintenance_topic(articles_dir: Path) -> tuple[int, str, str]:
    """Resolve the next unwritten maintenance topic from Naomi's Clinic Syllabus."""
    existing_files = sorted(articles_dir.glob("*circuit-maintenance*.json"))
    covered_keywords: set[str] = set()
    highest_issue = 0

    for path in existing_files:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            slug = doc.get("slug", "")
            ja_title = doc.get("locales", {}).get("ja", {}).get("title", "")
            
            m = re.search(r"#(\d+)", ja_title)
            if m:
                highest_issue = max(highest_issue, int(m.group(1)))
            
            for word in slug.split("-"):
                if len(word) > 2:
                    covered_keywords.add(word.lower())
        except Exception:
            continue

    next_issue = highest_issue + 1

    for item in NAOMI_CLINIC_SYLLABUS:
        if item["issue"] == next_issue:
            return next_issue, item["theme"], item["prompt"]

    for item in NAOMI_CLINIC_SYLLABUS:
        kws = set(item["keywords"])
        if not kws.intersection(covered_keywords):
            return next_issue, item["theme"], item["prompt"].replace(f"#{item['issue']}", f"#{next_issue}")

    return (
        next_issue,
        "高度サーキット整備工学",
        f"【ナオミのサーキット整備塾 #{next_issue}】サーキット走行向けバイクメンテナンス講座。"
        "過去に取り上げたテーマ（ワイヤリング、ブレーキフルード、タイヤ空気圧、チェーン遊び、トルクレンチ、冷却水等）とは"
        "絶対に重複しない、新たな「1テーマ」を厳選して深掘り解説せよ。"
    )


def generate_technical_svg_hero(article_data: dict[str, Any]) -> str:
    """Generate a clean, high-precision technical SVG hero illustration for maintenance articles."""
    slug = article_data.get("slug", "maintenance-hero")
    HERO_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    target_svg = HERO_IMAGES_DIR / f"{slug}.svg"
    public_url = f"/images/articles/{slug}.svg"

    if target_svg.exists():
        return public_url

    ja_title = article_data.get("locales", {}).get("ja", {}).get("title", "ナオミのサーキット整備塾")
    en_title = article_data.get("locales", {}).get("en", {}).get("title", "Naomi's Track Garage Clinic")
    highlight = article_data.get("locales", {}).get("ja", {}).get("highlightPoint", "サーキット整備の極意")

    import html
    m = re.search(r"#(\d+)", ja_title)
    issue_num = m.group(1) if m else "TECH"

    safe_ja_title = html.escape(ja_title.split("】")[-1].split("！")[0] if "】" in ja_title else ja_title[:32])
    safe_en_title = html.escape(en_title.split("]")[-1].split("!")[0] if "]" in en_title else en_title[:45])
    safe_highlight = html.escape(highlight[:60] + ("..." if len(highlight) > 60 else ""))

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0c10" />
      <stop offset="50%" stop-color="#141824" />
      <stop offset="100%" stop-color="#0d0f14" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <rect width="1200" height="630" fill="url(#bgGrad)" />

  <g opacity="0.08" stroke="#ffffff" stroke-width="1">
    <line x1="0" y1="105" x2="1200" y2="105" />
    <line x1="0" y1="210" x2="1200" y2="210" />
    <line x1="0" y1="315" x2="1200" y2="315" />
    <line x1="0" y1="420" x2="1200" y2="420" />
    <line x1="0" y1="525" x2="1200" y2="525" />
    <line x1="200" y1="0" x2="200" y2="630" />
    <line x1="400" y1="0" x2="400" y2="630" />
    <line x1="600" y1="0" x2="600" y2="630" />
    <line x1="800" y1="0" x2="800" y2="630" />
    <line x1="1000" y1="0" x2="1000" y2="630" />
  </g>

  <circle cx="950" cy="300" r="260" fill="#c77dff" opacity="0.12" filter="url(#glow)" />
  <circle cx="280" cy="220" r="200" fill="#2a9d8f" opacity="0.08" filter="url(#glow)" />

  <g transform="translate(80, 100)">
    <rect x="0" y="0" width="240" height="34" rx="6" fill="#c77dff" opacity="0.2" stroke="#c77dff" stroke-width="1.5" />
    <text x="120" y="22" text-anchor="middle" fill="#c77dff" font-family="'Chakra Petch', sans-serif" font-size="14" font-weight="700" letter-spacing="2">NAOMI'S WORKSHOP #{issue_num}</text>

    <text x="0" y="90" fill="#ffffff" font-family="'Noto Sans JP', sans-serif" font-size="40" font-weight="900" letter-spacing="1">{safe_ja_title}</text>
    <text x="0" y="145" fill="#ffb703" font-family="'Chakra Petch', sans-serif" font-size="24" font-weight="700">{safe_en_title}</text>
    <text x="0" y="195" fill="#a8b3cf" font-family="'Noto Sans JP', sans-serif" font-size="16">MFJ / FIM / JIS規格準拠 · 1テーマ徹底深掘り整備講座</text>

    <g transform="translate(0, 240)">
      <rect x="0" y="0" width="480" height="150" rx="10" fill="#151922" stroke="#c77dff" stroke-width="1.5" opacity="0.9" />
      <text x="25" y="38" fill="#c77dff" font-family="'Chakra Petch', sans-serif" font-size="16" font-weight="700">WORKSHOP SPOTLIGHT</text>
      
      <circle cx="35" cy="72" r="5" fill="#2a9d8f" />
      <text x="50" y="77" fill="#f4f6fb" font-size="14">{safe_highlight}</text>

      <circle cx="35" cy="108" r="5" fill="#ffb703" />
      <text x="50" y="113" fill="#f4f6fb" font-size="14">Featured: 黒猫メカニック・ナオミ (Naomi)</text>

      <circle cx="35" cy="140" r="5" fill="#4895ef" />
      <text x="50" y="145" fill="#f4f6fb" font-size="14">Track Tech Inspection &amp; Physics Analysis</text>
    </g>
  </g>

  <g transform="translate(860, 315)">
    <circle cx="0" cy="0" r="140" fill="#151922" stroke="#c77dff" stroke-width="6" />
    <circle cx="0" cy="0" r="100" fill="#1b202c" stroke="#ffb703" stroke-width="4" stroke-dasharray="8,6" />
    
    <text x="0" y="-20" text-anchor="middle" fill="#c77dff" font-family="'Chakra Petch', sans-serif" font-size="18" font-weight="700">ISSUE #{issue_num}</text>
    <text x="0" y="20" text-anchor="middle" fill="#ffffff" font-family="'Chakra Petch', sans-serif" font-size="32" font-weight="900">CLINIC</text>
    <text x="0" y="48" text-anchor="middle" fill="#2a9d8f" font-family="'Chakra Petch', sans-serif" font-size="13" font-weight="700">VERIFIED SPEC</text>
  </g>

  <text x="80" y="580" fill="#707d9c" font-family="'Chakra Petch', sans-serif" font-size="14" letter-spacing="1">HONDA.CAT · NAOMI'S CIRCUIT MAINTENANCE CLINIC · ISSUE #{issue_num}</text>
</svg>"""

    target_svg.write_text(svg_content, encoding="utf-8")
    print(f"✅ Generated and saved technical SVG hero illustration: {target_svg}")
    return public_url


def get_fallback_image_prompt(
    featured_cat: str,
    category: str,
    circuit: str,
    weather: str = "Dry",
) -> str:
    """Generate a high-realism cat reporter action prompt if dynamic LLM generation fails."""
    cat_lower = (category or "").lower()
    if featured_cat == "suzuka":
        return (
            f"Trackside documentary photograph of Suzuka, an anthropomorphic calico cat standing upright on two legs like a professional photojournalist. "
            f"She has soft calico fur, cat ears, and whiskers, wearing a tailored photographer vest with PRESS badge. "
            f"She holds a professional black DSLR camera equipped with a long telephoto lens with both paws, aiming it towards the racetrack corner at {circuit}. "
            f"Background shows asphalt track under {weather} daylight, with a race motorcycle blurred in distance. "
            f"Shot on 50mm f/1.8 lens, shallow depth of field, sharp focus on the calico cat, realistic fur texture, subtle 35mm film grain."
        )
    elif featured_cat == "marc":
        return (
            f"Candid editorial photograph of Marc, an anthropomorphic orange tabby male cat standing upright on two legs like a stylish European motorsport editor. "
            f"He has warm striped orange tabby fur, feline eyes, whiskers, wearing a tailored paddock polo shirt and VIP media pass. "
            f"He holds a digital telemetry tablet in his paws while gesturing animatedly, explaining race physics at {circuit} paddock. "
            f"Background shows team pit boxes and grandstand under {weather} sky. "
            f"Shot on 85mm f/1.4 lens, natural ambient lighting, shallow depth of field, sharp focus on the orange cat, subtle 35mm film grain."
        )
    else:  # naomi
        return (
            f"Authentic workshop documentary photograph of Naomi, an anthropomorphic black female cat standing upright on two legs like a veteran motorcycle mechanic. "
            f"She has sleek black fur, green feline eyes, whiskers, wearing oil-stained navy work coveralls with rolled sleeves and red bandana on forehead. "
            f"She carefully works on a racing motorcycle on a paddock stand using a metallic wrench with both paws in a bright garage at {circuit}. "
            f"Background shows tool chests and tire warmers under {weather} ambient light. "
            f"Shot on 50mm f/1.8 lens, realistic workshop lighting, gritty mechanical texture, shallow depth of field, subtle film grain."
        )


def build_hero_image_prompt(article_data: dict[str, Any], client: Any) -> str:
    """Construct a de-AI photographic prompt featuring the cat reporter in action using Gemini 3.8 Flash."""
    featured_cat = article_data.get("featuredCat", "naomi")
    category = article_data.get("category", "")
    circuit = article_data.get("circuit", "")
    ja_title = article_data.get("locales", {}).get("ja", {}).get("title", "")
    ja_summary = article_data.get("locales", {}).get("ja", {}).get("summary", "")
    highlight = article_data.get("locales", {}).get("ja", {}).get("highlightPoint", "")
    weather_info = article_data.get("eventMeta", {}).get("weather", {})
    weather = weather_info.get("en") or weather_info.get("ja") or "Dry / Clear"

    cat_desc = {
        "marc": "Marc (male orange tabby cat, editor-in-chief, telemetry & race physics expert, paddock polo/jacket, analyzing data or gesturing at paddock cafe)",
        "suzuka": "Suzuka (female calico cat, trackside photojournalist, photographer vest with PRESS badge or yellow rain poncho, wielding heavy DSLR telephoto lens)",
        "naomi": "Naomi (female black cat, veteran mechanic, oil-stained coveralls with tail opening, red bandana, tools & tire warmers & torque wrench in pit box)",
    }.get(featured_cat, "Naomi (female black cat mechanic)")

    context_desc = (
        f"Featured Cat Reporter (PROTAGONIST): {cat_desc}\n"
        f"Article Category: {category}\n"
        f"Circuit / Location: {circuit}\n"
        f"Weather / Atmosphere: {weather}\n"
        f"Japanese Title: {ja_title}\n"
        f"Summary: {ja_summary}\n"
        f"Key Highlight: {highlight}\n"
    )

    try:
        interaction = client.interactions.create(
            model="gemini-3.8-flash",
            system_instruction=IMAGE_PROMPT_SYSTEM_INSTRUCTION,
            input=f"Generate a vivid, realistic text-to-image prompt showing the cat reporter in action at this specific race event:\n\n{context_desc}",
        )
        prompt = (interaction.output_text or "").strip()
        prompt = re.sub(r'^["\'`]+|["\'`]+$', '', prompt).strip()
        if prompt and len(prompt) > 20:
            return prompt
    except Exception as e:
        print(f"⚠️ Dynamic prompt generation via Gemini failed ({e}). Using robust template fallback.")

    return get_fallback_image_prompt(featured_cat, category, circuit, weather)


def generate_and_save_hero_image(
    article_data: dict[str, Any],
    client: Any,
    force: bool = False,
) -> str | None:
    """Generate a photojournalistic hero image using Imagen 3 and save it as an optimized WebP file."""
    slug = article_data.get("slug")
    if not slug:
        return None

    # For maintenance clinic articles, generate a sharp, beautiful technical SVG hero illustration
    if article_data.get("category") == "maintenance":
        return generate_technical_svg_hero(article_data)

    HERO_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    target_webp = HERO_IMAGES_DIR / f"{slug}.webp"
    public_url = f"/images/articles/{slug}.webp"

    if target_webp.exists() and not force:
        print(f"📷 Hero image already exists at {target_webp}, reusing.")
        return public_url

    featured_cat = article_data.get("featuredCat", "naomi")
    ref_image_path = CAT_IMAGES_DIR / f"{featured_cat}.png"

    prompt_body = build_hero_image_prompt(article_data, client)
    prompt = (
        f"Generate a 16:9 photographic hero image featuring the EXACT same character from the reference image ({featured_cat}): "
        f"CRITICAL PROPORTIONS & IDENTITY: A real chubby domestic cat standing upright on two short hind legs, exactly 2.5 to 3 heads tall, "
        f"NOT human proportions, NOT an 8-head-tall person, short cute feline limbs and fluffy fur matching the reference photo. "
        f"{prompt_body}"
    )
    print(f"🎨 Generating realistic Nameneko-style hero photo with Gemini Image for '{slug}' ({featured_cat})...")
    print(f"📝 Prompt: {prompt}")

    from google.genai import types
    import io
    import time
    from PIL import Image

    for attempt in range(1, 5):
        try:
            contents: list[Any] = [prompt]
            if ref_image_path.exists():
                try:
                    with Image.open(ref_image_path) as ref_im:
                        contents = [ref_im.copy(), prompt]
                except Exception as img_err:
                    print(f"⚠️ Could not open reference image {ref_image_path}: {img_err}")

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio="16:9",
                    ),
                ),
            )
            img_bytes = None
            if response.parts:
                for part in response.parts:
                    if part.inline_data and part.inline_data.data:
                        img_bytes = part.inline_data.data
                        break

            if not img_bytes:
                print(f"⚠️ No image bytes returned on attempt {attempt}.")
                time.sleep(3)
                continue

            with Image.open(io.BytesIO(img_bytes)) as im:
                if im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                # Optimize image width for LCP and web performance (standard hero width 1200px)
                if im.width > 1200:
                    target_height = int(im.height * (1200 / im.width))
                    im = im.resize((1200, target_height), Image.Resampling.LANCZOS)
                im.save(target_webp, format="WEBP", quality=85, method=6)

            size_kb = target_webp.stat().st_size // 1024
            print(f"✅ Successfully generated and saved hero photo: {target_webp} ({size_kb} KB)")
            return public_url
        except Exception as e:
            print(f"⚠️ Image generation attempt {attempt} failed: {e}")
            time.sleep(5 * attempt)

    return None


def finalize_article_record(
    data: dict[str, Any],
    today_str: str,
    hero_image: str | None = None,
) -> dict[str, Any]:
    slug = slugify(data.get("slug", f"{today_str}-paddock-special"))
    featured_cat = data.get("featuredCat", "naomi")
    cat_images = {
        "marc": "/images/cats/marc.png",
        "suzuka": "/images/cats/suzuka.png",
        "naomi": "/images/cats/naomi.png",
    }
    fallback_hero = cat_images.get(featured_cat, "/images/cats/hero-paddock.png")
    return {
        "id": f"{today_str}-{slug}",
        "slug": slug,
        "publishedAt": today_str,
        "category": data.get("category", "all-japan"),
        "articleType": data.get("articleType", "digest"),
        "circuit": data.get("circuit", "Suzuka / Autopolis / Montmeló"),
        "region": data.get("region", "Japan & Catalunya"),
        "featuredCat": featured_cat,
        "heroImage": hero_image or fallback_hero,
        "tags": data.get("tags", ["MotoGP", "MFJ", "Autopolis", "SPA直入", "HSR九州"]),
        "snsCitations": data.get("snsCitations", []),
        "factCheck": data.get("factCheck"),
        "eventMeta": data["eventMeta"],
        "locales": data["locales"],
    }


def run_schedule_driven_mode(
    mode: str,
    custom_topic: str | None = None,
    ref_date_override: dt.date | None = None,
) -> int:
    today = ref_date_override or dt.date.today()
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
        if custom_topic:
            prompt = custom_topic
        else:
            issue_num, theme_name, base_prompt = resolve_next_maintenance_topic(ARTICLES_DIR)
            print(f"🔧 [Maintenance Mode] Auto-resolved Naomi Clinic Issue #{issue_num}: '{theme_name}'")
            prompt = (
                f"Task: Create Naomi's Track Garage Clinic Issue #{issue_num} (`category: 'maintenance'`, `articleType: 'maintenance'`, `featuredCat: 'naomi'`).\n\n"
                f"CORE TOPIC:\n{base_prompt}\n\n"
                "STRICT 1-THEME MANDATE:\n"
                "1. Focus STRICTLY AND EXCLUSIVELY on this single mechanical engineering topic. NEVER combine multiple themes into one article.\n"
                "2. Provide deep, rigorous technical facts: JIS/ISO standards, MFJ/FIM road racing technical rules, thermodynamic/mechanical formulas (e.g. pressure equations, friction coefficients, torque equations), and precision workshop tips.\n"
                "3. In `diagram`, provide a structured 3-panel technical illustration breakdown (`good` pass example, `bad` hazard failure example, and `detail` standard specifications/metrics) for `ja`, `ca`, and `en`.\n"
                "4. In `catDialogues`, Naomi speaks with her sharp-tongued veteran mechanic persona while showing her subtle caring heart for the rider's safety."
            )
        author_and_audit_article(prompt, today_str)
        return 0

    # 6. Manual Custom Dispatch (`workflow_dispatch`)
    prompt = custom_topic or "Create a strictly fact-verified motorsport or circuit maintenance article."
    author_and_audit_article(prompt, today_str)
    return 0


def update_hero_images_for_existing(
    limit: int | None = None,
    force: bool = False,
    specific_slug: str | None = None,
) -> int:
    """Generate realistic hero photos for existing articles using Imagen 3."""
    from google import genai
    client = genai.Client()

    existing = sorted(ARTICLES_DIR.glob("*.json"))
    print(f"🔍 Checking hero images for {len(existing)} existing articles...")

    updated_count = 0
    for path in existing:
        if limit is not None and updated_count >= limit:
            print(f"⏹️ Reached generation limit ({limit}). Stopping.")
            break

        doc = json.loads(path.read_text(encoding="utf-8"))
        slug = doc.get("slug")
        if specific_slug and slug != specific_slug:
            continue

        current_hero = doc.get("heroImage", "")
        # If it already has an articles/ webp and force is False, skip
        if not force and current_hero.startswith("/images/articles/") and (HERO_IMAGES_DIR / f"{slug}.webp").exists():
            continue

        print(f"\n📸 Processing hero image for [{slug}] (current: {current_hero})...")
        new_hero_url = generate_and_save_hero_image(doc, client, force=force)
        if new_hero_url:
            doc["heroImage"] = new_hero_url
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"💾 Updated {path.name} with new heroImage: {new_hero_url}")
            updated_count += 1
            import time
            time.sleep(2)
        else:
            print(f"⏩ Skipped updating {path.name} (image generation failed or skipped).")

    print(f"\n🎉 Finished updating hero images. Total generated/updated: {updated_count}")
    return 0


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

OFFICIAL_ALLOWED_DOMAINS = [
    # World Championships
    "motogp.com",
    "worldsbk.com",
    "fimewc.com",
    # World Circuit Hosts
    "circuitcat.com",
    "circuitvalencia.com",
    "autodromodoalgarve.com",
    "circuitodejerez.com",
    "gpfrancemoto.com",
    "mugellocircuit.com",
    "misanocircuit.com",
    "automotodrombrno.cz",
    "ttcircuit.com",
    "adac-motorsport.de",
    "silverstone.co.uk",
    "motorlandaragon.com",
    "redbullring.com",
    "themandalikagp.com",
    "phillipislandcircuit.com.au",
    "sepangcircuit.com",
    "lcsc.qa",
    # Japanese Sanctioning & All-Japan
    "mfj.or.jp",
    "superbike.jp",
    # Nationwide Japanese Major Circuits
    "suzukacircuit.jp",
    "mr-motegi.jp",
    "tsukuba-circuit.jp",
    "sportsland-sugo.co.jp",
    "okayama-international-circuit.jp",
    "fsw.tv",
    "tokachi.msf.ne.jp",
    # Kyushu Circuits & Grassroots Endurance
    "autopolis.jp",
    "spa-naoiri.com",
    "hsr.jp",
    "tetsuma.jp",
    "brow-s.jp",
    "takuma-gp.com",
    "sonicpark.jp",
    # Official Motorcycle Event Navis & Portals
    "event.webike.net",
    "webike.net",
    # Official Technical Standards & Parts Manufacturers (Maintenance Series)
    "jisc.go.jp",
    "iso.org",
    "ecfr.gov",
    "did-daido.co.jp",
    "dunlop.co.jp",
    "bridgestone.co.jp",
    "honda.co.jp",
    "global.honda",
    "kyototool.co.jp",
    "yamaha-motor.co.jp",
    "suzuki.co.jp",
    "kawasaki-motors.com",
    # Official Platforms & Social Media
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
]


def is_allowed_domain(url: str) -> bool:
    """Validate that the URL belongs to an allowed official or social media domain."""
    if not url:
        return False
    match = re.search(r"^https?://([^/:]+)", url.strip(), re.IGNORECASE)
    if not match:
        return False
    host = match.group(1).lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_ALLOWED_DOMAINS)


def validate_existing_articles() -> int:
    """Strict Deterministic Fact & Integrity Gatekeeper for Honda.cat Articles."""
    existing = sorted(ARTICLES_DIR.glob("*.json"))
    print(f"🔍 Running Deterministic Fact & Integrity Audit on {len(existing)} articles in {ARTICLES_DIR}...")
    
    # Load schedules for cross-referencing event IDs
    schedule_events: set[str] = set()
    if SCHEDULES_JSON_PATH.exists():
        try:
            schedules_data = json.loads(SCHEDULES_JSON_PATH.read_text(encoding="utf-8"))
            schedule_events = {ev["id"] for ev in schedules_data.get("events", []) if "id" in ev}
        except Exception:
            schedule_events = set()

    errors: list[str] = []

    for path in existing:
        fname = path.name
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"[{fname}] Invalid JSON syntax: {exc}")
            continue

        # 1. ID matches filename
        doc_id = doc.get("id", "")
        if doc_id != path.stem:
            errors.append(f"[{fname}] ID mismatch: `id` is '{doc_id}' but filename is '{path.stem}'")

        # 2. Schedule Event ID cross-reference
        sched_ids = doc.get("scheduleEventIds", [])
        if sched_ids and schedule_events:
            for sid in sched_ids:
                if sid not in schedule_events:
                    errors.append(f"[{fname}] Referencing non-existent scheduleEventId `{sid}` in schedules.json")

        # 3. FactCheck completeness & Domain verification
        fc = doc.get("factCheck", {})
        if not fc.get("verified"):
            errors.append(f"[{fname}] `factCheck.verified` is not True")
        sources = fc.get("sources", [])
        if not sources or not isinstance(sources, list):
            errors.append(f"[{fname}] `factCheck.sources` is missing or empty")
        else:
            for s_item in sources:
                s_url = s_item if isinstance(s_item, str) else s_item.get("url", "")
                if not s_url or not is_allowed_domain(s_url):
                    errors.append(f"[{fname}] factCheck source URL `{s_url}` is not in OFFICIAL_ALLOWED_DOMAINS")

        basis = fc.get("basis", {})
        if not isinstance(basis, dict) or not all(basis.get(l) for l in ["ja", "ca", "en"]):
            errors.append(f"[{fname}] `factCheck.basis` is missing trilingual explanation (ja, ca, en)")

        # 4. SNS Citations verification
        sns_cites = doc.get("snsCitations", [])
        if not sns_cites or not isinstance(sns_cites, list):
            errors.append(f"[{fname}] `snsCitations` is missing or empty")
        else:
            for idx, cite in enumerate(sns_cites, start=1):
                post_url = cite.get("postUrl") or cite.get("url", "")
                if post_url and not is_allowed_domain(post_url):
                    errors.append(f"[{fname}] snsCitation #{idx} postUrl `{post_url}` is not in OFFICIAL_ALLOWED_DOMAINS")

        # 5. Hero Image Physical Existence
        hero_img = doc.get("heroImage", "")
        if not hero_img:
            errors.append(f"[{fname}] Missing `heroImage` property")
        else:
            # Strip leading slash to check against public/
            rel_path = hero_img.lstrip("/")
            physical_file = PUBLIC_DIR / rel_path
            if not physical_file.exists():
                errors.append(f"[{fname}] heroImage `{hero_img}` does not exist on disk at {physical_file}")

        # 6. Trilingual Locales Completeness
        locales = doc.get("locales", {})
        for lang in ["ja", "ca", "en"]:
            loc_data = locales.get(lang, {})
            if not loc_data:
                errors.append(f"[{fname}] Missing locale data for language `{lang}`")
            else:
                for req_key in ["title", "subtitle", "summary", "sections", "catDialogues"]:
                    if not loc_data.get(req_key):
                        errors.append(f"[{fname}] Locale `{lang}` is missing or has empty `{req_key}`")

        langs = list(locales.keys())
        print(
            f"   ✅ {fname} | category={doc.get('category')} | "
            f"type={doc.get('articleType')} | hero={hero_img} | snsCitations={len(sns_cites)} | sources={len(sources)} | langs={langs}"
        )

    if errors:
        print(f"\n❌ DETERMINISTIC ARTICLE FACT AUDIT FAILED! Found {len(errors)} violation(s):")
        for err in errors:
            print(f"   🚨 {err}")
        print("\n🚫 Aborting pipeline to prevent unverified or broken articles from being published!")
        return 1

    print(f"\n🎯 All {len(existing)} articles passed strict deterministic fact-check verification!")
    return 0


def run_backfill_window(start_date_str: str, end_date_str: str) -> int:
    """Iterate day-by-day over [start_date, end_date] and trigger the exact Thu/Fri/Mon/Wed schedule state machine."""
    start_d = dt.date.fromisoformat(start_date_str)
    end_d = dt.date.fromisoformat(end_date_str)
    cur = start_d
    print(f"🗓️ Running Schedule-Driven Backfill State Machine from {start_d} to {end_d}...")
    while cur <= end_d:
        wd = cur.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        if wd == 3:  # Thursday -> preview_world
            print(f"\n--- [{cur.isoformat()} (Thu)] Checking `preview_world` ---")
            run_schedule_driven_mode("preview_world", ref_date_override=cur)
        elif wd == 4:  # Friday -> preview_japan
            print(f"\n--- [{cur.isoformat()} (Fri)] Checking `preview_japan` ---")
            run_schedule_driven_mode("preview_japan", ref_date_override=cur)
        elif wd == 0:  # Monday -> digest_monday
            print(f"\n--- [{cur.isoformat()} (Mon)] Checking `digest_monday` ---")
            run_schedule_driven_mode("digest_monday", ref_date_override=cur)
        elif wd == 2:  # Wednesday -> digest_wednesday
            print(f"\n--- [{cur.isoformat()} (Wed)] Checking `digest_wednesday` ---")
            run_schedule_driven_mode("digest_wednesday", ref_date_override=cur)
        cur += dt.timedelta(days=1)
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
            "backfill",
        ],
        default="preview_world",
        help="Schedule-driven execution mode",
    )
    parser.add_argument("--date", type=str, default=None, help="Override execution date (YYYY-MM-DD) for retroactive runs")
    parser.add_argument("--start-date", type=str, default="2026-04-01", help="Start date for --mode backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2026-06-30", help="End date for --mode backfill (YYYY-MM-DD)")
    parser.add_argument("--topic", type=str, default=None, help="Custom topic for manual dispatch")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit existing articles and schedule state machine without calling API",
    )
    parser.add_argument(
        "--generate-hero-images",
        action="store_true",
        help="Generate realistic hero photos for existing articles using Imagen 3",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of images to generate when using --generate-hero-images",
    )
    parser.add_argument(
        "--force-images",
        action="store_true",
        help="Force overwrite existing hero images",
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Specific article slug to process for --generate-hero-images",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.dry_run or not api_key:
        if not api_key and not args.dry_run:
            print("ℹ️ GEMINI_API_KEY not set in environment; running local Fact-Check & Schedule State Audit.")
        return validate_existing_articles()

    if args.generate_hero_images:
        return update_hero_images_for_existing(
            limit=args.limit,
            force=args.force_images,
            specific_slug=args.slug,
        )

    if args.mode == "backfill":
        return run_backfill_window(args.start_date, args.end_date)

    ref_date = dt.date.fromisoformat(args.date) if args.date else None
    return run_schedule_driven_mode(mode=args.mode, custom_topic=args.topic, ref_date_override=ref_date)


if __name__ == "__main__":
    sys.exit(main())
