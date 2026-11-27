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
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import circuit_results_fetcher  # noqa: E402
import colab_image_generator  # noqa: E402
import x_photo_finder  # noqa: E402

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
Your mission is to generate a single, highly realistic text-to-image prompt for FLUX.2-klein-4B / Gemini image-conditioned generation featuring our anthropomorphic retro "Nameneko-style" cat reporters in dynamic, varied motorsport scenes.

CRITICAL CHARACTER PROPORTION & IDENTITY RULE (AUTHENTIC NAMENEKO STYLE):
- Keep ONLY the cat's exact face, fur markings, key signature outfit markers, and chubby proportions from the reference image:
  * PROPORTION: Exactly 2.5 to 3 heads tall (a chubby, real domestic cat standing, sitting, or crouching on short hind legs with short cute feline paws).
  * STRICT PROHIBITION: NEVER make the cat an 8-head-tall person, humanoid, or slender human-limbed character. It must look like an authentic Japanese 1980s "Nameneko" style photograph — a real cute chubby domestic cat dressed in miniature motorsport gear.
  * HEAD & FACE: Round fluffy domestic cat head, feline whiskers, realistic fur, expressive cat eyes.

MANDATORY VARIETY & ANTI-COPY-PASTE RULE:
- You will be given an `ASSIGNED SCENE DIRECTIVE` specifying exact shot framing, pose/action, prop rules, and setting/lighting.
- You MUST strictly obey that `ASSIGNED SCENE DIRECTIVE` and ACTIVELY BREAK AWAY from the reference image's dead-center static front-facing standing pose and default background.
- Place the cat off-center (rule of thirds), seated, crouching, leaning over a pit wall, walking mid-stride, or viewed from a dynamic 3/4 or over-the-shoulder angle as directed.
- Explicitly honor the `Prop Rule` so reference props (like Marc's stopwatch/notepad or Naomi's wrench) do not reappear when replaced.

THE THREE CAT REPORTERS:
1. `marc` (Marc): Male orange tabby cat, warm striped fur, amber feline eyes. Signature gear: retro red-white-and-blue zippered racing jacket with PRESS/MARC patches and media lanyard.
2. `suzuka` (Suzuka): Female calico cat, soft tricolor fur (white/black/orange), green eyes. Signature gear: white collared shirt, khaki multi-pocket photographer vest with '87 PRESS SUZUKA badge, small black shoes.
3. `naomi` (Naomi): Female sleek black cat, glossy black fur, sharp green eyes, tiny pink cherry blossom flower clip by left ear. Signature gear: oil-stained navy mechanic coveralls with rolled sleeves and name badge.

SCENARIO SPECIFICATION:
- Incorporate concrete landmarks, bikes, race weather, and story context from the article naturally into the background and lighting.
- Output ONLY the raw English prompt string (around 65-110 words) detailing spatial composition, cat pose, replaced props, background depth, camera lens, natural lighting, and subtle 35mm film grain. No quotes, no prefix, no Markdown.
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
- OFFICIAL CIRCUIT RESULT PAGE GROUNDING (MANDATORY):
  * Before authoring any race result article, each circuit's official result page is explored and parsed directly (e.g., SPA Naoiri `https://autopolis.jp/spa/result/`, HSR Kyushu `https://www1.ms-event.net/hsrweb/user/?a=event_info_data.event_info_data_list`, Autopolis `https://autopolis.jp/ap/result/`, Suzuka `suzukacircuit.jp/result_s/`, Motegi `mr-motegi.jp/result_m/`, Tsukuba `tsukuba-circuit.jp/race/results/results.html`, SUGO `sportsland-sugo.co.jp/results/`, Okayama `ms-event.net/oicweb`, JRR `jrr.jp/results/`).
  * Whenever `OFFICIAL CIRCUIT RESULT PAGE DATA` is present, you MUST reflect those exact official results (class names, winner & podium rider/team names, machine models, lap counts, total times, gaps, best laps, weather/temperature, and penalties) accurately in `locales.{ja,ca,en}.results`, `sections`, `highlightPoint`, `eventMeta`, and `factCheck`. NEVER omit confirmed winners or contradict the official circuit result sheet.
- Only include race results that have been verified online from official sources.
- Always populate `factCheck.basis` (in `ja`, `ca`, `en`) and `factCheck.sources` with real, verifiable reference URLs (including the circuit's official result page URL whenever available).
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
                    "mediaUrls": {"type": "array", "items": {"type": "string"}},
                    "verifiedAt": {"type": "string"},
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
    """Explore circuit official result pages first (HTML & PDF sheets), then combine with Gemini + Google Search."""
    from google import genai

    client = genai.Client()
    sources_cfg = circuit_results_fetcher.load_sources_config()

    print(f"   📡 Exploring official circuit result page(s) for `{ev['id']}`...")
    circuit_res = circuit_results_fetcher.fetch_event_circuit_results(
        ev,
        sources_cfg=sources_cfg,
        client=client,
        max_pdfs=6,
    )
    circuit_dossier = circuit_res.get("dossierText", "")
    verified_circuit_urls = circuit_res.get("verifiedResultUrls", [])
    matched_on_circuit_page = bool(circuit_res.get("matchedResultsOnPage", False))

    if matched_on_circuit_page:
        print(f"   ✅ Official circuit result page matched! Extracted {len(verified_circuit_urls)} official result URL(s).")
    elif circuit_res.get("hasOfficialResultPage"):
        print("   ℹ️ Circuit has an official result page, but no matching final sheet was found yet; checking web/SNS...")
    else:
        print("   ℹ️ No dedicated circuit 2-wheel result index registered; checking organizer web & official SNS...")

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            "Check the directly fetched OFFICIAL CIRCUIT RESULT PAGE DATA below, along with official websites and official SNS accounts, "
            "to determine whether confirmed race results have been published online for the following scheduled event:\n"
            f"- Event: {ev['eventName']['ja']} ({ev['series']})\n"
            f"- Circuit: {ev['circuit']['ja']}\n"
            f"- Dates: {ev.get('startDate')} to {ev.get('endDate')}\n"
            f"- Official URLs: {ev.get('officialWebUrl')} / {ev.get('circuitWebUrl')}\n"
            f"- Official SNS: {ev.get('snsHandle')} ({ev.get('snsUrl')})\n\n"
            f"OFFICIAL CIRCUIT RESULT PAGE DATA (DIRECTLY FETCHED FROM CIRCUIT RESULT SERVER):\n"
            f"{circuit_dossier or '(No matching entry on circuit result page yet)'}\n\n"
            "STRICT RULE:\n"
            "- If `OFFICIAL CIRCUIT RESULT PAGE DATA` above contains confirmed final race classifications / PDF transcriptions for this event, set `resultsFound: true` and preserve ALL exact winners, podiums, rider/team names, machines, lap counts, total times, gaps, best laps, and weather in `verifiedFactsDossier`.\n"
            "- Otherwise set `resultsFound: true` ONLY if actual confirmed race results (winners/podium/timings) for this event are verifiable online. Never guess or fabricate results."
        ),
        tools=[{"type": "google_search"}],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RESULT_AVAILABILITY_SCHEMA,
        },
    )
    parsed = json.loads(interaction.output_text)

    if matched_on_circuit_page and "公式決勝リザルトPDF" in circuit_dossier:
        parsed["resultsFound"] = True

    merged_urls: list[str] = []
    for u in verified_circuit_urls + (parsed.get("sourceUrls") or []):
        if isinstance(u, str) and u and u not in merged_urls:
            merged_urls.append(u)
    parsed["sourceUrls"] = merged_urls

    if circuit_dossier:
        parsed["officialCircuitResultDossier"] = circuit_dossier
        parsed["verifiedFactsDossier"] = (
            f"{parsed.get('verifiedFactsDossier', '')}\n\n"
            f"=== DIRECT OFFICIAL CIRCUIT RESULT PAGE DATA ===\n{circuit_dossier}"
        ).strip()
    parsed["circuitsChecked"] = circuit_res.get("circuitsChecked", [])
    return parsed


def extract_relevant_sources(prompt_context: str, all_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter sources_config.json so only sources directly related to the target event(s) are passed to LLM."""
    cleaned_ctx = re.sub(r"`?(?:featuredCat|category|articleType)\s*:\s*'[^']*'`?", "", prompt_context)
    cleaned_ctx = re.sub(r'"(?:category|previewArticleId|resultArticleId|scope)"\s*:\s*"[^"]*"', "", cleaned_ctx)
    lower_ctx = cleaned_ctx.lower()
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
            if any(w in lower_ctx for w in ["8耐", "鈴鹿", "suzuka circuit", "suzuka 8", "suzuka-circuit"]) and sid == "suzuka-circuit":
                matched.append(src)

        # All-Japan Championships (exclude regional classes/categories mentioning JSB1000 or all-japan)
        if any(w in lower_ctx for w in ["全日本ロード", "全日本選手権", "mfjグランプリ", "mfjgp"]):
            if sid == "mfj-all-japan-official":
                matched.append(src)

        # Specific Circuits
        if any(w in lower_ctx for w in ["鈴鹿", "suzuka circuit", "suzuka 8", "suzuka sunday", "suzuka-circuit"]) and sid == "suzuka-circuit":
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
        if any(w in lower_ctx for w in ["hsr", "hsr九州", "鉄馬", "tetsuma", "tetsuuma", "ドリームカップ", "ドリームsunday", "saga cup", "火の国", "8時間耐久", "エンジョイ4時間"]) and sid == "hsr-kyushu":
            matched.append(src)
        if any(w in lower_ctx for w in ["お題", "ブラウズ", "brow", "安心院", "ソニックパーク", "中九州", "草耐久", "草レース"]) and sid == "brows-odai-endurance":
            matched.append(src)
        if any(w in lower_ctx for w in ["レン耐", "rentai", "青木拓磨"]) and sid == "takuma-gp-rentai":
            matched.append(src)

        # Webike Event NAVI / Grassroots / Endurance Series
        if any(w in lower_ctx for w in ["webike", "ウェビック", "地方選", "走行会", "草耐久", "4耐", "6耐", "エンジョイ", "saga cup", "明智"]) and sid == "webike-event-navi-race":
            matched.append(src)

    # De-duplicate while prioritizing host-circuit/series-specific sources ahead of umbrella aggregators
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for s in matched:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)

    umbrella_ids = {"mfj-all-japan-official", "webike-event-navi-race"}
    unique.sort(key=lambda s: 1 if s.get("id", "").lower() in umbrella_ids else 0)

    if not unique:
        return all_sources[:3]
    return unique


def _build_x_search_params(
    prompt_context: str,
    relevant_sources: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Build prioritized, round-robined X queries, handles, and relevance keywords from event metadata + sources."""
    cleaned_ctx = re.sub(r"`?(?:featuredCat|category|articleType)\s*:\s*'[^']*'`?", "", prompt_context)
    lower_ctx = cleaned_ctx.lower()

    event_queries: list[str] = []
    relevance_keywords: list[str] = []

    def _add_unique(lst: list[str], val: str) -> None:
        v = val.strip()
        if v and v not in lst:
            lst.append(v)

    generic_stop_words = {
        "2026",
        "2027",
        "race",
        "series",
        "finale",
        "round",
        "レース",
        "ロードレース",
        "シリーズ",
        "選手権",
        "最終戦",
        "開幕戦",
        "特別戦",
        "フルコース",
        "西日本シリーズ",
        "東日本シリーズ",
        "年間シリーズ",
        "4時間耐久",
        "8時間耐久",
    }

    event_names = re.findall(r'"eventName"\s*:\s*\{\s*"ja"\s*:\s*"([^"]+)"', cleaned_ctx)
    circuit_names = re.findall(r'"circuit"\s*:\s*\{\s*"ja"\s*:\s*"([^"]+)"', cleaned_ctx)
    raw_sns_handles = re.findall(r'"snsHandle"\s*:\s*"([^"]+)"', cleaned_ctx)

    for cname in circuit_names:
        short_c = re.sub(r"（.*?）|\(.*?\)|【.*?】", "", cname).strip()
        short_c = re.sub(r"\s+(?:国際レーシングコース|ロードコース|インターナショナルレーシングコース)$", "", short_c).strip()
        if short_c:
            _add_unique(relevance_keywords, short_c)
        for token in ["SUGO", "スポーツランドSUGO", "岡山", "OKAYAMA", "岡山国際サーキット", "筑波", "もてぎ", "鈴鹿", "HSR九州", "オートポリス", "SPA直入", "明智", "安心院", "中九州", "十勝", "富士"]:
            if token.lower() in cname.lower():
                _add_unique(relevance_keywords, token)

    for ename in event_names:
        clean_e = re.sub(r"（.*?）|\(.*?\)|【.*?】", "", ename).strip()
        clean_e = re.sub(r"^20\d\d\s+(?:FIM\s+)?", "", clean_e).strip()
        parts = [p.strip() for p in re.split(r"[／/]", clean_e) if p.strip()]
        for p in parts[:2]:
            p_short = re.sub(r"^20\d\d\s+", "", p).strip()
            p_short = re.sub(
                r"^(?:[^\s]+(?:シリーズ|選手権))?\s*(?:最終戦|開幕戦|特別戦|第\d+戦|Rd\.?\s*\d+|Round\s*\d+|R-\d+)\s*",
                "",
                p_short,
                flags=re.I,
            ).strip()
            p_short = re.sub(
                r"\s*(?:シリーズ・地方選手権|地方選手権|Rd\.?\s*\d+|Round\s*\d+|R-\d+|第\d+戦).*$",
                "",
                p_short,
                flags=re.I,
            ).strip()
            if len(p_short) >= 4:
                _add_unique(event_queries, p_short)
                if "fun&run" in p_short.lower():
                    _add_unique(event_queries, "鈴鹿 FUN&RUN")
                if "レン耐" in p_short:
                    _add_unique(event_queries, "Let'sレン耐")
                for tok in re.split(r"[\s・]+", p_short):
                    if len(tok) >= 3 and tok.lower() not in generic_stop_words:
                        _add_unique(relevance_keywords, tok)

    # Combine circuit + event keyword queries for higher hit rate
    if circuit_names and event_names:
        c_short = re.sub(r"（.*?）|\(.*?\)|【.*?】", "", circuit_names[0]).strip()
        c_short = re.sub(r"\s+(?:国際レーシングコース|ロードコース|インターナショナルレーシングコース)$", "", c_short).strip()
        if c_short and not any(c_short in eq for eq in event_queries):
            _add_unique(event_queries, f"{c_short} ロードレース")

    # Round-robin queries and handles across relevant_sources so multi-event digests hit all circuits
    umbrella_ids = {"mfj-all-japan-official", "webike-event-navi-race"}
    primary_sources = [s for s in relevant_sources if s.get("id") not in umbrella_ids]
    secondary_sources = [s for s in relevant_sources if s.get("id") in umbrella_ids]
    ordered_sources = primary_sources + secondary_sources

    is_all_japan = any(w in lower_ctx for w in ["全日本ロード", "全日本選手権", "all-japan", "jsb1000", "st1000", "j-gp3", "mfjgp"])
    is_fuji = any(w in lower_ctx for w in ["富士", "fuji", "ミニろく"])

    src_queries: list[str] = []
    max_q_len = max((len(s.get("searchQueries", [])) for s in ordered_sources), default=0)
    for q_idx in range(min(max_q_len, 2)):
        for s in ordered_sources:
            qs = s.get("searchQueries", [])
            if q_idx < len(qs):
                q = qs[q_idx]
                if "全日本ロードレース" in q and not is_all_japan:
                    continue
                if "富士" in q and not is_fuji:
                    continue
                _add_unique(src_queries, q)

    x_handles: list[str] = []
    max_h_len = max((len([sn for sn in s.get("sns", []) if sn.get("platform") == "X"]) for s in primary_sources or ordered_sources), default=0)
    for h_idx in range(max_h_len):
        for s in primary_sources or ordered_sources:
            x_sns = [sn for sn in s.get("sns", []) if sn.get("platform") == "X"]
            if h_idx < len(x_sns):
                h = x_sns[h_idx].get("handle", "").lstrip("@")
                if h.lower() == "fswpress" and not is_fuji:
                    continue
                _add_unique(x_handles, h)

    for raw_h in raw_sns_handles:
        for part in re.split(r"[/,\s]+", raw_h):
            if part.startswith("@"):
                cand_h = part.lstrip("@").strip()
                if re.match(r"^[A-Za-z0-9_]{1,15}$", cand_h):
                    if cand_h.lower() == "fswpress" and not is_fuji:
                        continue
                    _add_unique(x_handles, cand_h)

    if any(w in lower_ctx for w in ["サーキット整備塾", "naomi clinic", "ワイヤリング", "ブレーキフルード", "タイヤ空気圧", "ドライブチェーン", "トルクレンチ", "冷却水"]):
        x_queries = ["バイク サーキット 整備", "レース 整備 バイク", "サーキット メンテナンス"]
        relevance_keywords.extend(["整備", "サーキット", "タイヤ", "ブレーキ", "チェーン", "トルク", "冷却水", "ワイヤリング"])
    else:
        x_queries = []
        for q in event_queries + src_queries:
            _add_unique(x_queries, q)

    if not x_queries:
        x_queries = ["MotoGP 2026", "全日本ロードレース", "バイク サーキット 整備"]

    return x_queries, x_handles, relevance_keywords


def _make_verified_x_citation(top_v: dict[str, Any], today_str: str) -> dict[str, Any]:
    """Build a schema-valid SnsCiteItem dict from a verified tweet metadata record."""
    return {
        "platform": "X",
        "citationType": "direct_post",
        "accountName": top_v["accountName"],
        "handle": f"@{top_v['screenName']}",
        "url": top_v["url"],
        "postUrl": top_v["postUrl"],
        "publishedDate": top_v["publishedDate"],
        "mediaUrls": top_v["mediaUrls"],
        "verifiedAt": today_str,
        "quotedPostText": {
            "ja": top_v["rawText"],
            "ca": top_v["rawText"],
            "en": top_v["rawText"],
        },
        "editorialCommentary": {
            "ja": f"現地・公式X（@{top_v['screenName']}）から発信された写真付きポスト。リアルな現場の熱気とマシンの様子が伝わります。",
            "ca": f"Publicació amb fotografies des de @{top_v['screenName']} mostrant l'ambient real del circuit.",
            "en": f"Verified photo post from @{top_v['screenName']} capturing authentic trackside action.",
        },
    }


def _ground_and_sanitize_sns_citations(
    draft_json: dict[str, Any],
    verified_x_posts: list[dict[str, Any]],
    relevant_sources: list[dict[str, Any]],
    relevance_keywords: list[str],
    research_notes: str,
    prompt_context: str,
    today_str: str,
    rejected_handles: set[str] | None = None,
    rejected_status_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically verify X/non-X citations, purge fabricated status/video IDs, and ensure a verified X photo post."""
    rej_h = {h.lower() for h in (rejected_handles or set())}
    rej_ids = set(rejected_status_ids or set())

    eligible_x = [
        v for v in verified_x_posts
        if v.get("screenName", "").lower() not in rej_h
        and v.get("statusId") not in rej_ids
        and not x_photo_finder._is_noise_post(
            str(v.get("rawText") or ""),
            str(v.get("screenName") or ""),
            str(v.get("accountName") or ""),
        )
    ]
    by_id = {str(v["statusId"]): v for v in eligible_x if v.get("statusId")}

    official_x_by_handle: dict[str, dict[str, str]] = {}
    official_channels_by_platform: dict[str, list[dict[str, str]]] = {}
    for src in relevant_sources:
        for sn in src.get("sns") or []:
            plat = sn.get("platform", "")
            handle_raw = str(sn.get("handle") or "")
            url_val = str(sn.get("url") or "")
            if plat == "X" and handle_raw:
                official_x_by_handle[handle_raw.lstrip("@").lower()] = {
                    "accountName": str(src.get("name", {}).get("ja") or handle_raw),
                    "handle": f"@{handle_raw.lstrip('@')}",
                    "url": url_val,
                }
            if plat and url_val:
                official_channels_by_platform.setdefault(plat, []).append(
                    {"handle": handle_raw, "url": url_val}
                )

    allowed_context_blob = "\n".join([
        research_notes or "",
        prompt_context or "",
        json.dumps(relevant_sources, ensure_ascii=False),
    ])

    cleaned_cites: list[dict[str, Any]] = []
    has_verified_photo_x = False

    for cite in draft_json.get("snsCitations") or []:
        if not isinstance(cite, dict):
            continue
        platform = str(cite.get("platform") or "")
        handle_clean = str(cite.get("handle") or "").lstrip("@").lower()
        account_name = str(cite.get("accountName") or "")
        post_url = str(cite.get("postUrl") or "")
        chan_url = str(cite.get("url") or "")
        qt_obj = cite.get("quotedPostText") if isinstance(cite.get("quotedPostText"), dict) else {}
        qt_blob = " ".join(str(qt_obj.get(l, "")) for l in ("ja", "en", "ca"))

        if handle_clean and handle_clean in rej_h:
            continue
        if x_photo_finder._is_noise_post(qt_blob, handle_clean, account_name):
            continue

        if platform == "X":
            m_id = re.search(r"/status/(\d+)", post_url) or re.search(r"/status/(\d+)", chan_url)
            if m_id:
                sid = m_id.group(1)
                if sid in rej_ids or sid in FORBIDDEN_FAKE_STATUS_IDS:
                    continue
                v = by_id.get(sid) or x_photo_finder.verify_tweet_with_syndication(sid)
                if v and v["screenName"].lower() not in rej_h and v["statusId"] not in rej_ids:
                    cite["citationType"] = "direct_post"
                    cite["accountName"] = v["accountName"]
                    cite["handle"] = f"@{v['screenName']}"
                    cite["url"] = v["url"]
                    cite["postUrl"] = v["postUrl"]
                    cite["mediaUrls"] = v["mediaUrls"]
                    cite["publishedDate"] = v["publishedDate"]
                    cite["verifiedAt"] = today_str

                    raw_text = str(v.get("rawText") or "").strip()
                    if raw_text:
                        ja_text = str(qt_obj.get("ja") or "").strip()
                        overlap = sum(1 for ch in set(ja_text) if not ch.isspace() and ch in raw_text)
                        if not ja_text or overlap < 8:
                            qt_obj["ja"] = raw_text
                        for loc_k in ("ca", "en"):
                            if not str(qt_obj.get(loc_k) or "").strip():
                                qt_obj[loc_k] = raw_text
                        cite["quotedPostText"] = qt_obj

                    has_verified_photo_x = True
                    cleaned_cites.append(cite)
                else:
                    # Never leave an unverified/fabricated /status/<id> URL
                    off_info = official_x_by_handle.get(handle_clean)
                    if off_info and off_info.get("url"):
                        cite["citationType"] = "official_channel"
                        cite["url"] = off_info["url"]
                        cite["handle"] = off_info["handle"]
                        cite.pop("postUrl", None)
                        cite.pop("mediaUrls", None)
                        cleaned_cites.append(cite)
            else:
                if chan_url and is_allowed_domain(chan_url):
                    cite.pop("postUrl", None)
                    cite.pop("mediaUrls", None)
                    cleaned_cites.append(cite)
        else:
            # Non-X citations: strip fabricated deep-link IDs not grounded in research/sources
            deep_id_match = (
                re.search(r"watch\?v=([A-Za-z0-9_-]{11})", post_url)
                or re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", post_url)
                or re.search(r"/(?:posts|reel|p)/([A-Za-z0-9_.-]+)", post_url)
            )
            if deep_id_match and deep_id_match.group(1) not in allowed_context_blob:
                cite.pop("postUrl", None)
                if not chan_url or deep_id_match.group(1) in chan_url:
                    fallbacks = official_channels_by_platform.get(platform) or []
                    if fallbacks:
                        cite["url"] = fallbacks[0]["url"]
                cite["citationType"] = "official_web" if platform == "OfficialWeb" else "official_channel"
            cleaned_cites.append(cite)

    if not has_verified_photo_x and eligible_x:
        relevant_fallback = [
            v for v in eligible_x
            if not relevance_keywords
            or any(kw.lower() in v["rawText"].lower() for kw in relevance_keywords)
        ]
        top_v = (relevant_fallback or eligible_x)[0]
        cleaned_cites.insert(0, _make_verified_x_citation(top_v, today_str))

    draft_json["snsCitations"] = cleaned_cites
    return cleaned_cites


def author_and_audit_article(
    prompt_context: str,
    today_str: str,
    image_backend: str = "auto",
) -> dict[str, Any]:
    """Run Stage 1/2/3 grounded authoring + strict independent fact audit and save the article JSON."""
    from google import genai

    client = genai.Client()
    sources_cfg: dict[str, Any] = {}
    all_sources: list[dict[str, Any]] = []
    if SOURCES_CONFIG_PATH.exists():
        try:
            sources_cfg = json.loads(SOURCES_CONFIG_PATH.read_text(encoding="utf-8"))
            all_sources = sources_cfg.get("sources", [])
        except Exception:
            sources_cfg = {}
            all_sources = []

    relevant_sources = extract_relevant_sources(prompt_context, all_sources)
    sources_context = json.dumps(relevant_sources, ensure_ascii=False, indent=2)

    # Explore & fetch official circuit result pages automatically unless this is a pre-race preview or maintenance clinic,
    # or unless `check_online_results_for_event` already embedded `DIRECT OFFICIAL CIRCUIT RESULT PAGE DATA`.
    is_preview_or_maint = any(
        marker in prompt_context
        for marker in ("articleType: 'preview'", "articleType: 'maintenance'", "category: 'maintenance'")
    )
    direct_circuit_results_dossier = ""
    direct_circuit_result_urls: list[str] = []
    if "DIRECT OFFICIAL CIRCUIT RESULT PAGE DATA" in prompt_context:
        direct_circuit_results_dossier = "(Embedded in event payload above — treat all `DIRECT OFFICIAL CIRCUIT RESULT PAGE DATA` sections as highest-priority ground truth.)"
    elif not is_preview_or_maint:
        date_matches = re.findall(r"(20\d\d-\d\d-\d\d)", prompt_context)
        inferred_start = min(date_matches) if date_matches else None
        inferred_end = max(date_matches) if date_matches else None
        print("[0/3] 📡 Exploring circuit official result page(s) for accurate race result reflection...")
        fetched_cr = circuit_results_fetcher.fetch_circuit_results_for_target(
            search_text=prompt_context,
            start_date=inferred_start,
            end_date=inferred_end,
            sources_cfg=sources_cfg,
            client=client,
            max_pdfs=6,
        )
        direct_circuit_results_dossier = fetched_cr.get("dossierText", "")
        direct_circuit_result_urls = fetched_cr.get("verifiedResultUrls", [])
        if fetched_cr.get("matchedResultsOnPage"):
            print(f"   ✅ Extracted official circuit result data ({len(direct_circuit_result_urls)} verified result URL(s)).")

    circuit_results_block = (
        f"\n\nOFFICIAL CIRCUIT RESULT PAGE DATA (HIGHEST-PRIORITY GROUND TRUTH — REFLECT EXACT WINNERS, PODIUMS, MACHINES, LAPS & TIMES):\n"
        f"{direct_circuit_results_dossier}\n"
        if direct_circuit_results_dossier
        else ""
    )

    # Discover & deterministically verify real photo-attached X posts before authoring
    x_queries, x_handles, relevance_keywords = _build_x_search_params(prompt_context, relevant_sources)

    verified_x_posts = x_photo_finder.find_verified_photo_tweets(
        queries=x_queries[:6],
        relevance_keywords=relevance_keywords or None,
        web_queries=x_queries[:4],
        handles=x_handles[:8],
        target_date=today_str,
        count=6,
    )
    if not verified_x_posts:
        broader_queries = [f"{kw} バイク" for kw in relevance_keywords[:3]] + [
            "全日本ロードレース",
            "鈴鹿サーキット バイク",
            "HSR九州 バイク",
            "サーキット バイク 走行",
        ]
        verified_x_posts = x_photo_finder.find_verified_photo_tweets(
            queries=broader_queries[:6],
            relevance_keywords=relevance_keywords or None,
            web_queries=broader_queries[:4],
            handles=x_handles[:8],
            target_date=today_str,
            count=6,
        )
    verified_x_context = json.dumps(verified_x_posts, ensure_ascii=False, indent=2)

    print(f"[1/3] Scouting verified historical & technical facts ({len(relevant_sources)} target sources, {len(verified_x_posts)} verified X photo posts) with Gemini 3.8 Flash + Google Search...")
    research_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            f"{prompt_context}"
            f"{circuit_results_block}\n\n"
            "TARGETED OFFICIAL & SOCIAL MEDIA DISCOVERY INSTRUCTIONS:\n"
            "Search for confirmed race facts, podium results, and authentic social posts following STRICT platform priority:\n"
            "Priority: X > YouTube > OfficialWeb > Facebook > Instagram\n"
            "- If `OFFICIAL CIRCUIT RESULT PAGE DATA` (or `DIRECT OFFICIAL CIRCUIT RESULT PAGE DATA`) is present above, preserve EVERY official class winner, podium finisher, rider/team name, bike number, machine model, lap count, total time, gap, best lap, weather/temperature, and official URL verbatim in your dossier.\n"
            "- Targeted X search: `site:x.com/{handle} ...` or `site:x.com \"#{hashtag}\"`\n"
            "- Targeted YouTube search: `site:youtube.com ... \"公式\"`\n"
            "- Official Web result pages & official Facebook posts.\n"
            "- STRICT RELEVANCE: Search ONLY for sources directly connected to this event/circuit/riders.\n\n"
            f"VERIFIED PHOTO-ATTACHED X POSTS (USE RELEVANT DIRECT POSTS & MEDIA URLS FIRST):\n{verified_x_context}\n\n"
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
            f"Using ONLY the verified facts in the research dossier and official circuit result data below (Date: {today_str}), "
            "generate a complete trilingual article JSON (`ja`, `ca`, `en`).\n\n"
            "STRICT RULES:\n"
            "1. ACCURATE REFLECTION OF OFFICIAL CIRCUIT RESULTS (MANDATORY): Whenever official circuit result page data is present, you MUST accurately reflect the exact class winners, podium finishers, rider/team names, machine models, lap counts, total times, gaps, fastest laps, and weather/track conditions in `locales.{ja,ca,en}.results`, `sections`, `highlightPoint`, and `eventMeta`. Do NOT invent any fictional team names, rider names, or unverified race results, and NEVER write vague filler omitting winners when official results are available.\n"
            "2. Populate `factCheck` with `verified: true`, `verifiedAt`, trilingual `basis`, and real `sources` URLs (including the circuit's official result page URL(s) whenever available). "
            "In `factCheck.sources`, cite ONLY official governing bodies (`fim-moto.com`, `mfj.or.jp`, `jrr.jp`, `jisc.go.jp`, `iso.org`), "
            "official race/circuit/timing sites (`motogp.com`, `worldsbk.com`, `autopolis.jp`, `ms-event.net`, `rms.co.jp`, `tetsuuma.com`, `suzukacircuit.jp`, `mr-motegi.jp`, `tsukuba-circuit.jp`, `sportsland-sugo.co.jp`, `okayama-international-circuit.jp`, `fsw.tv`, `tokachi.msf.ne.jp`, `brow-s.jp`, `takuma-gp.com`, etc.), "
            "or established OEM/parts manufacturer domains (`honda.co.jp`, `brembo.com`, `ohlins.com`, `motul.com`, `did-daido.co.jp`, etc.). "
            "NEVER cite defunct domains (`hsr.jp`, `tetsuma.jp`, `spa-naoiri.com`, `superbike.jp`), personal blogs, wikis, or unverified third-party mirrors.\n"
            "3. Populate `snsCitations` following the strict platform priority: X > YouTube > OfficialWeb > Facebook > Instagram.\n"
            "   - Every citation MUST be directly relevant to this specific race event, host circuit, or podium riders.\n"
            "   - VERIFIED PHOTO X POSTS: From `VERIFIED PHOTO-ATTACHED X POSTS` below, select ONLY the verified photo-attached X posts directly related to the featured event(s), host circuit(s), or competing riders, using `citationType: 'direct_post'`, exact `postUrl`, `publishedDate`, and `mediaUrls`.\n"
            "   - If any item in `VERIFIED PHOTO-ATTACHED X POSTS` is about an unrelated race/circuit, SKIP it instead of citing it.\n"
            "   - ZERO HALLUCINATION: Do NOT fabricate status IDs. Only use status URLs verified in the list below or verified online.\n"
            "   - NEVER cite unrelated accounts (e.g., citing MotoGP or Suzuka for a Kyushu local or grassroots race is strictly forbidden).\n"
            "4. In `catDialogues`, convey Naomi's (`naomi`) scruffy garage mechanic voice and her occasional shy, maidenly phrasing naturally through the text itself without any explicit mode labels.\n"
            f"{circuit_results_block}\n"
            f"VERIFIED PHOTO-ATTACHED X POSTS:\n{verified_x_context}\n\n"
            f"VERIFIED RESEARCH DOSSIER:\n{research_notes}"
        ),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ARTICLE_JSON_SCHEMA,
        },
    )
    draft_json = json.loads(author_interaction.output_text)

    def _normalize_and_ground(doc_obj: dict[str, Any], rej_h: set[str], rej_ids: set[str]) -> None:
        if isinstance(doc_obj.get("slug"), str):
            stripped_slug = re.sub(r"^(?:\d{4}-\d{2}-\d{2}-)+", "", doc_obj["slug"].strip())
            if stripped_slug:
                doc_obj["slug"] = stripped_slug

        if direct_circuit_result_urls:
            fc_obj = doc_obj.setdefault("factCheck", {})
            fc_sources = fc_obj.setdefault("sources", [])
            existing_fc_urls = {
                (s if isinstance(s, str) else s.get("url", "")) for s in fc_sources
            }
            for r_url in direct_circuit_result_urls[:2]:
                if r_url not in existing_fc_urls and is_allowed_domain(r_url):
                    fc_sources.append({"title": "Official Circuit Race Results", "url": r_url})
                    existing_fc_urls.add(r_url)

        _ground_and_sanitize_sns_citations(
            draft_json=doc_obj,
            verified_x_posts=verified_x_posts,
            relevant_sources=relevant_sources,
            relevance_keywords=relevance_keywords,
            research_notes=research_notes,
            prompt_context=prompt_context,
            today_str=today_str,
            rejected_handles=rej_h,
            rejected_status_ids=rej_ids,
        )
        _sanitize_article_domains(doc_obj, relevant_sources)

    rejected_handles: set[str] = set()
    rejected_status_ids: set[str] = set()
    _normalize_and_ground(draft_json, rejected_handles, rejected_status_ids)

    print("[3/3] Running Independent Fact-Auditor Gate...")

    def _run_audit(candidate_doc: dict[str, Any]) -> dict[str, Any]:
        audit_interaction = client.interactions.create(
            model="gemini-3.8-flash",
            input=(
                "You are a strict Motorsport & Mechanical Engineering Fact Auditor.\n"
                "Audit the following generated article JSON against the research dossier, verified X posts, and real-world history.\n"
                "Fail (`passed: false`) if you find ANY of the following:\n"
                "1. Unrelated or incorrect circuit-to-event pairings (e.g., claiming a race series is held at a circuit where it was never held).\n"
                "2. Fictional team names in results, fabricated race winners, OR any discrepancy/omission against `OFFICIAL CIRCUIT RESULT PAGE DATA` (winners, podium positions, rider/team names, machines, lap counts, or times MUST match the official circuit result sheet when provided).\n"
                "3. Incorrect circuit lengths or false technical/physics claims.\n"
                "4. Unrelated SNS/Web citations: Official series, organizer, host circuit (including recent 2-wheel motorcycle road/minibike posts at the host circuit for pre-race previews), and competing 2-wheel riders/teams ARE valid; fail Rule 4 if a citation is about 4-wheel racing (Super Formula, Super GT, F1, Caterham, etc.) or an unrelated circuit/championship.\n"
                "5. Hallucinated / Fabricated post URLs: Status IDs and texts listed in `VERIFIED PHOTO-ATTACHED X POSTS` are HTTP-verified directly from X Syndication API — do NOT mark them as fabricated. Fail Rule 5 only if a status URL/post URL or quoted text is fabricated and absent from both `VERIFIED PHOTO-ATTACHED X POSTS` and `RESEARCH DOSSIER`.\n"
                f"{circuit_results_block}\n"
                f"VERIFIED PHOTO-ATTACHED X POSTS (HTTP-VERIFIED REAL TWEETS WITH PHOTOS):\n{verified_x_context}\n\n"
                f"TARGET RELEVANT OFFICIAL SOURCES:\n{sources_context}\n\n"
                f"RESEARCH DOSSIER:\n{research_notes}\n\n"
                f"CANDIDATE ARTICLE JSON:\n{json.dumps(candidate_doc, ensure_ascii=False)}"
            ),
            tools=[{"type": "google_search"}],
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": AUDIT_JSON_SCHEMA,
            },
        )
        return json.loads(audit_interaction.output_text)

    audit_result = _run_audit(draft_json)
    for attempt in range(1, 3):
        if audit_result.get("passed", False):
            break
        issues_list = audit_result.get("issues", ["Unknown fact check failure"])
        issues_str = "; ".join(issues_list)
        print(f"⚠️ [3/3] Audit failed (round {attempt}): {issues_str}")

        for h in re.findall(r"@([A-Za-z0-9_]+)", issues_str):
            rejected_handles.add(h.lower())
        for sid in re.findall(r"\b(\d{15,20})\b", issues_str):
            rejected_status_ids.add(sid)

        prev_cites_json = json.dumps(draft_json.get("snsCitations") or [], sort_keys=True, ensure_ascii=False)
        _normalize_and_ground(draft_json, rejected_handles, rejected_status_ids)
        new_cites_json = json.dumps(draft_json.get("snsCitations") or [], sort_keys=True, ensure_ascii=False)

        non_sns_issue = any(
            marker in issues_str.lower()
            for marker in ["rule 1", "rule 2", "rule 3", "discrepancy", "omission", "circuit", "fictional", "incorrect"]
        )
        if non_sns_issue or new_cites_json == prev_cites_json:
            print(f"🛠️ [3/3] Requesting LLM revision to resolve audit issues (round {attempt})...")
            revise_interaction = client.interactions.create(
                model="gemini-3.8-flash",
                system_instruction=SYSTEM_INSTRUCTION,
                input=(
                    f"Revise the article JSON below to resolve EVERY issue reported by the Fact Auditor while strictly preserving verified facts, official results, and valid verified X posts.\n\n"
                    f"AUDIT ISSUES TO FIX:\n{issues_str}\n\n"
                    f"CURRENT ARTICLE JSON:\n{json.dumps(draft_json, ensure_ascii=False)}\n\n"
                    f"{circuit_results_block}\n"
                    f"VERIFIED PHOTO-ATTACHED X POSTS:\n{verified_x_context}\n\n"
                    f"VERIFIED RESEARCH DOSSIER:\n{research_notes}"
                ),
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ARTICLE_JSON_SCHEMA,
                },
            )
            draft_json = json.loads(revise_interaction.output_text)
            _normalize_and_ground(draft_json, rejected_handles, rejected_status_ids)
        else:
            print(f"🧹 [3/3] Pruned/re-grounded SNS citation(s); re-running Independent Fact Audit (round {attempt})...")

        audit_result = _run_audit(draft_json)

    if not audit_result.get("passed", False):
        issues = "; ".join(audit_result.get("issues", ["Unknown fact check failure"]))
        raise FactCheckError(f"❌ Fact Audit Rejected Article: {issues}")

    print(f"[3/3] ✅ Fact Audit Passed: {audit_result.get('summary')}")
    print("[4/4] 📸 Generating authentic motorsport hero photo...")
    hero_image_url = generate_and_save_hero_image(draft_json, client, image_backend=image_backend)
    article = finalize_article_record(draft_json, today_str, hero_image=hero_image_url)
    _sanitize_article_domains(article, relevant_sources)

    pre_write_errors = validate_article_record(
        article,
        fname=f"{article['id']}.json",
        expected_stem=article["id"],
    )
    if pre_write_errors:
        raise FactCheckError("❌ Pre-Write Deterministic Validation Failed: " + "; ".join(pre_write_errors))

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
    existing_files = sorted(articles_dir.glob("*.json"))
    covered_keywords: set[str] = set()
    highest_issue = 0

    for path in existing_files:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("category") != "maintenance" and doc.get("articleType") != "maintenance":
                continue
            slug = str(doc.get("slug", ""))
            doc_id = str(doc.get("id", ""))
            locales = doc.get("locales") or {}
            ja_title = str(locales.get("ja", {}).get("title", ""))
            en_title = str(locales.get("en", {}).get("title", ""))

            for title_txt in (ja_title, en_title):
                m = re.search(r"#(\d+)", title_txt)
                if m:
                    highest_issue = max(highest_issue, int(m.group(1)))

            for slug_txt in (slug, doc_id):
                m_slug = re.search(r"(?:clinic|maintenance)[-_]0*(\d+)", slug_txt, flags=re.IGNORECASE)
                if m_slug:
                    highest_issue = max(highest_issue, int(m_slug.group(1)))

            for word in slug.split("-"):
                if len(word) > 2:
                    covered_keywords.add(word.lower())
            for tag in doc.get("tags") or []:
                if isinstance(tag, str) and len(tag.strip()) > 2:
                    covered_keywords.add(tag.strip().lower())
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


HERO_SCENE_DIRECTIVES: dict[str, list[dict[str, Any]]] = {
    "marc": [
        {
            "id": "marc_paddock_cafe_map",
            "preferred_types": ("preview",),
            "shot_framing": "Medium wide environmental shot framed off-center (rule of thirds, Marc seated on the left third at an outdoor cafe table)",
            "pose_action": "Sitting relaxed on a wooden paddock cafe chair, leaning forward with one paw tracing a corner on a spread-out circuit map",
            "prop_rule": "Hold ONLY a white espresso cup near a folded paper circuit map and sunglasses on the table. Do NOT hold the reference stopwatch or paper notepad.",
            "setting_lighting": "Bright Mediterranean morning sunlight at an outdoor paddock terrace cafe with parasols, parked paddock scooters, and sunlit grandstands in soft background bokeh.",
        },
        {
            "id": "marc_pitwall_over_shoulder",
            "preferred_types": ("digest", "preview"),
            "shot_framing": "Dynamic 3/4 rear-side over-the-shoulder shot from the pit wall, Marc placed on the right third looking toward the track",
            "pose_action": "Leaning both front paws on the concrete pit-wall rail, peering intently past a hanging timing monitor onto the main straight",
            "prop_rule": "Wear radio headset over his ears and lean on the pit wall rail beside a mounted pit timing screen. Do NOT hold a stopwatch or notepad.",
            "setting_lighting": "High-contrast afternoon race light with two MotoGP-style superbikes motion-blurred at high speed along the asphalt straight and pit boards ahead.",
        },
        {
            "id": "marc_grid_walk_mic",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Candid eye-level medium shot angled diagonally along a crowded starting grid, Marc off-center on the left",
            "pose_action": "Walking mid-stride along the starting grid asphalt while turning his head slightly toward the camera with a lively expression",
            "prop_rule": "Hold a handheld broadcast reporter microphone with a wind foam cap in one paw while the other paw gestures toward the grid bikes. Do NOT hold the stopwatch or notepad.",
            "setting_lighting": "Crisp pre-race daylight on the starting grid with painted white grid boxes, racing bikes on rear stands under umbrellas, and blurred mechanics in background.",
        },
        {
            "id": "marc_media_center_dusk",
            "preferred_types": ("digest",),
            "shot_framing": "Warm indoor-to-outdoor window composition, Marc seated at a press desk in the foreground left looking toward a wide glass window",
            "pose_action": "Seated upright on an office chair behind a press room desk, typing on a sleek silver laptop while glancing out at the dusk circuit",
            "prop_rule": "Paws resting on a compact open laptop beside a stack of printed lap-time sheets. Do NOT hold the reference stopwatch or notepad.",
            "setting_lighting": "Blue-hour twilight and warm tungsten press-room desk lamp glow contrasting against the illuminated pit lane and circuit floodlights outside the window.",
        },
        {
            "id": "marc_corner_apex_watch",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Low-angle wide shot from behind red-and-white corner kerbs, Marc positioned on the left foreground observing the apex",
            "pose_action": "Crouching slightly on short hind legs beside a trackside marshal barrier, leaning forward to study riders' cornering lean angles",
            "prop_rule": "Hold compact black binoculars raised near his eyes with both paws. Do NOT hold the stopwatch or paper notepad.",
            "setting_lighting": "Dramatic late-afternoon side sunlight casting long shadows across dark rubbered-in asphalt, striped kerbs, and leaning motorcycles blurred through the corner.",
        },
        {
            "id": "marc_parc_ferme_recorder",
            "preferred_types": ("digest",),
            "shot_framing": "Candid side-angle documentary shot at Parc Fermé barriers, Marc framed in the right foreground",
            "pose_action": "Standing on short hind legs turned 3/4 toward a victorious race bike parked behind metal barricades, extending one paw forward",
            "prop_rule": "Hold a compact digital voice recorder forward in one paw while gesturing with the other. Do NOT hold the reference stopwatch or notepad.",
            "setting_lighting": "Energetic post-race golden afternoon light with confetti-dusted tarmac, podium backdrop structures, and photographers clustered around parked race bikes.",
        },
        {
            "id": "marc_garage_doorway_stride",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Medium full-body shot framed through an open team pit garage doorway, Marc walking out toward pit lane on the left third",
            "pose_action": "Stepping out mid-stride from a shaded pit box onto sunlit pit lane asphalt, glancing back toward a race machine inside",
            "prop_rule": "Carry a sleek horizontal telemetry tablet tucked under one arm while checking a pit-lane credential wristband. Do NOT hold the stopwatch or paper notepad.",
            "setting_lighting": "Dramatic doorway rim lighting transitioning from cool LED pit-box interior (toolbox cabinets, spare fairings) to bright sunlit pit apron.",
        },
        {
            "id": "marc_grandstand_golden_hour",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Wide cinematic 3/4 profile shot from an elevated grandstand terrace looking down at the circuit",
            "pose_action": "Standing beside a metal terrace railing turned in 3/4 profile, pointing one paw out toward a sweeping S-curve below",
            "prop_rule": "No stopwatch and no notepad; rest one paw on the terrace railing and hold a folded race weekend program booklet in the other.",
            "setting_lighting": "Warm golden-hour sunset rays across tiered grandstands, sweeping ribbon of distant racetrack, and dramatic clouds.",
        },
    ],
    "suzuka": [
        {
            "id": "suzuka_low_kerb_crouch",
            "preferred_types": ("digest", "preview"),
            "shot_framing": "Dynamic low-angle ground-level tracking shot, Suzuka crouched on the right third near red-and-white corner kerbs",
            "pose_action": "Crouching low on short hind legs in the grass verge, twisting her torso in 3/4 profile to pan horizontally with passing bikes",
            "prop_rule": "Hold a compact black rangefinder camera with a short fast prime lens (no giant white bazooka telephoto lens) close to her face.",
            "setting_lighting": "Bright crisp daylight with blurred green grass blades in foreground, fast panning motion blur on a leaning superbike right behind her.",
        },
        {
            "id": "suzuka_pitlane_lcd_check",
            "preferred_types": ("digest",),
            "shot_framing": "Candid over-the-shoulder medium close-up from the left, showing Suzuka's profile and the glowing rear LCD screen of her camera",
            "pose_action": "Tilting her calico head downward in concentration, holding her DSLR at chest height to inspect the rear photo review screen",
            "prop_rule": "Camera hangs on her neck strap while both paws hold the camera body angled up so the rear LCD preview is visible. No lens aimed forward.",
            "setting_lighting": "Overcast soft pit-lane daylight with race mechanics wheeling tire stacks and glowing pit garage lights softly out of focus behind her.",
        },
        {
            "id": "suzuka_rainy_awning_lens_wipe",
            "preferred_types": ("digest", "preview"),
            "shot_framing": "Atmospheric medium shot under a paddock tent awning on the left third, looking out toward rain-soaked asphalt",
            "pose_action": "Standing sheltered under a pit canopy in a bright yellow rain poncho, gently wiping raindrops off her camera lens with a microfiber cloth",
            "prop_rule": "Hold a small microfiber lens cloth in one paw and her camera cradled against her chest in the other, wearing a translucent yellow rain poncho over her vest.",
            "setting_lighting": "Moody rainy Japanese circuit weather with falling rain streaks, shimmering puddles reflecting pit lights, and wet bikes spraying mist on track.",
        },
        {
            "id": "suzuka_podium_wide_angle",
            "preferred_types": ("digest",),
            "shot_framing": "Low wide-angle upward shot from the front of the podium celebration crowd, Suzuka positioned on the left foreground",
            "pose_action": "Looking upward at a 45-degree angle toward an elevated circuit podium, raising a wide-angle DSLR overhead to capture the celebration",
            "prop_rule": "Hold a compact black DSLR with a wide-angle hood tilted steeply upward with both paws; no long white telephoto lens.",
            "setting_lighting": "Vibrant celebratory afternoon light with champagne spray mist catching sunbeams above a blurred podium backdrop and cheering team crew.",
        },
        {
            "id": "suzuka_paddock_stool_review",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Relaxed eye-level environmental portrait framed off-center on the left, seated beside stacked Pelican camera cases",
            "pose_action": "Sitting on a folding canvas paddock stool with knees tucked, resting both paws on a rugged silver laptop on her lap",
            "prop_rule": "Camera rests inside an open padded black camera case beside her stool; her paws hold an open silver laptop showing photo thumbnails. Do NOT hold a camera up.",
            "setting_lighting": "Clear Japanese mountain circuit afternoon (lush cedar hills or Ferris wheel in distance) with warm dappled sunlight across paddock asphalt.",
        },
        {
            "id": "suzuka_endurance_twilight_pit",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Cinematic 3/4 side shot from pit lane apron at dusk, Suzuka kneeling on one knee on the right third",
            "pose_action": "Kneeling beside a pit lane line marker, angling her camera low toward an endurance racer entering pit box for refueling",
            "prop_rule": "Hold a black DSLR equipped with a medium 24-70mm zoom lens and glowing hotshoe flash trigger; no giant white telephoto lens.",
            "setting_lighting": "Deep cobalt twilight sky mixed with warm tungsten pit-box floodlights, glowing motorcycle headlights, and blurred pit crew in fireproof suits.",
        },
        {
            "id": "suzuka_hillside_over_shoulder",
            "preferred_types": ("preview",),
            "shot_framing": "Elevated scenic 3/4 back-angle shot from a grassy spectator bank, Suzuka on the left third overlooking sweeping bends",
            "pose_action": "Standing on a sloped grassy hillside, leaning slightly forward with camera slung across her shoulder while pointing toward a downhill hairpin",
            "prop_rule": "Let the camera hang loosely at her hip on its strap while she raises a paper circuit map and points one paw toward the track below.",
            "setting_lighting": "Bright morning sunshine over green hillside circuit, distant valley hairpin curves with tiny colorful racing bikes and safety barriers.",
        },
        {
            "id": "suzuka_grid_morning_aperture",
            "preferred_types": ("preview", "digest"),
            "shot_framing": "Crisp medium shot angled down pit lane at dawn/morning, Suzuka standing off-center right in side profile",
            "pose_action": "Standing in 3/4 profile adjusting the aperture ring on a vintage silver-and-black 35mm film camera held at waist level",
            "prop_rule": "Hold a classic compact metallic SLR camera at waist level while adjusting its lens dial, with a small press notebook tucked in her vest pocket.",
            "setting_lighting": "Fresh early-morning golden rim light with long shadows across pit lane asphalt, mist rising off distant hills, and bikes warming up.",
        },
    ],
    "naomi": [
        {
            "id": "naomi_tire_warmer_gauge",
            "preferred_types": ("preview", "maintenance", "digest"),
            "shot_framing": "Dynamic low-angle outdoor paddock shot, Naomi crouched on the left third beside a sportbike wrapped in red tire warmers",
            "pose_action": "Crouching beside the rear wheel of a racing motorcycle on a paddock stand, pressing a brass dial tire pressure gauge onto the valve stem",
            "prop_rule": "Hold ONLY a round analog tire pressure gauge with rubber hose against the rear tire valve. Do NOT hold the reference wrench.",
            "setting_lighting": "Bright sunlit outdoor paddock canopy tent with blue sky, circuit paddock trucks, and warm sunlight glinting off racing slicks and alloy wheels.",
        },
        {
            "id": "naomi_workbench_caliper",
            "preferred_types": ("maintenance",),
            "shot_framing": "Tight medium close-up across a cluttered metal workshop bench, Naomi framed slightly right behind foreground brake components",
            "pose_action": "Leaning over a steel garage workbench, carefully measuring a drilled stainless steel brake rotor with stainless vernier calipers",
            "prop_rule": "Hold precision stainless steel vernier calipers in both paws measuring a brake disc on the bench. Do NOT hold the reference open-end wrench.",
            "setting_lighting": "Focused warm overhead task lamp illuminating metallic brake rotors, sintered brake pads, and clean shop rags in a sunlit open garage bay.",
        },
        {
            "id": "naomi_front_fork_torque",
            "preferred_types": ("maintenance", "digest"),
            "shot_framing": "3/4 side-angle medium shot inside an active race pit box, Naomi standing off-center right next to the front wheel",
            "pose_action": "Standing in 3/4 profile beside the front forks of a superbike on a front head-lift stand, tightening a caliper pinch bolt",
            "prop_rule": "Hold a long chrome micrometer click-type torque wrench horizontally with both paws on the front brake caliper. Do NOT hold the reference flat spanner.",
            "setting_lighting": "Cool white pit-box LED strips mixed with daylight from the open pit lane behind, carbon front fender, gold fork tubes, and pit wall visible.",
        },
        {
            "id": "naomi_pitwall_signboard",
            "preferred_types": ("digest", "preview"),
            "shot_framing": "Energetic candid 3/4 shot from pit lane looking toward the pit wall fence, Naomi standing on the left third",
            "pose_action": "Holding up a black-and-yellow pit board with chalk lap numbers over the pit wall opening as an endurance bike flashes past",
            "prop_rule": "Grip a rectangular pit signboard with chalk numbers ('P1' / 'IN') in both paws; no wrench.",
            "setting_lighting": "Bright afternoon trackside sunlight with heat haze, blurred motorcycle streaking past on the main straight, and race team canopies behind.",
        },
        {
            "id": "naomi_outdoor_canopy_checklist",
            "preferred_types": ("preview", "maintenance"),
            "shot_framing": "Sunlit outdoor grassy paddock shot, Naomi sitting on a stacked set of racing slick tires on the right third",
            "pose_action": "Seated casually on a stack of black racing tires under a team pop-up tent, jotting setup notes on an aluminum clipboard",
            "prop_rule": "Hold an aluminum setup clipboard and pen in her paws; no wrench in hand.",
            "setting_lighting": "Warm late-morning sunshine at a Japanese grassroots endurance paddock with colorful team tents, mini-bikes, and green circuit hills behind.",
        },
        {
            "id": "naomi_chain_slack_low_angle",
            "preferred_types": ("maintenance", "digest"),
            "shot_framing": "Extreme low-angle shot from floor level looking along the swingarm and gold drive chain, Naomi kneeling on the left",
            "pose_action": "Kneeling on one knee on rubber pit mats, holding a small steel millimeter ruler up against the lower run of a gold racing chain",
            "prop_rule": "Hold a 150mm stainless steel ruler and safety-wire pliers beside the rear sprocket. Do NOT hold the reference large wrench.",
            "setting_lighting": "Dramatic low-key pit bay lighting with bright daylight spilling from the open pit door onto the gold chain and anodized sprocket.",
        },
        {
            "id": "naomi_fluid_clinic_bench",
            "preferred_types": ("maintenance",),
            "shot_framing": "Medium environmental shot inside a bright clean technical bay, Naomi positioned on the left third behind clear fluid bottles",
            "pose_action": "Wearing clear safety goggles pushed up on her forehead near her sakura clip, squeezing a transparent brake-bleeder bottle tube",
            "prop_rule": "Hold a clear silicone brake bleeder hose and catch bottle connected to a caliper bleed nipple. Do NOT hold a wrench.",
            "setting_lighting": "Crisp bright daylight pouring through wide open garage bay doors onto clean concrete floor, aluminum paddock stand, and tool trolley.",
        },
        {
            "id": "naomi_sunset_garage_cooldown",
            "preferred_types": ("digest", "maintenance"),
            "shot_framing": "Warm atmospheric back-lit wide shot from outside looking into an open pit garage at sunset, Naomi slightly off-center right",
            "pose_action": "Sitting on a low rolling mechanic creeper stool wiping grease off her paws with a red shop rag while admiring a parked race bike",
            "prop_rule": "Hold ONLY a folded red cotton shop rag wiping her paws, with an open helmet resting on a work mat nearby. No wrench.",
            "setting_lighting": "Golden-orange sunset rays streaming diagonally across the concrete apron and illuminating warm glowing silhouettes inside the pit bay.",
        },
    ],
}


def _pick_preferred_directives(
    directives: list[dict[str, Any]],
    article_data: dict[str, Any],
) -> list[dict[str, Any]]:
    article_type = str(article_data.get("articleType") or "").lower()
    category = str(article_data.get("category") or "").lower()
    weather_raw = json.dumps(article_data.get("eventMeta", {}).get("weather", {}), ensure_ascii=False).lower()

    if any(w in weather_raw for w in ("rain", "wet", "雨", "pluja")):
        wet_matches = [d for d in directives if "rain" in d["id"] or "rain" in d["setting_lighting"].lower()]
        if wet_matches:
            return wet_matches

    if any(w in weather_raw for w in ("night", "floodlight", "ナイター", "夜", "dusk", "twilight")):
        night_matches = [d for d in directives if any(k in d["id"] for k in ("dusk", "twilight", "sunset", "media_center"))]
        if night_matches:
            return night_matches

    target_type = "maintenance" if category == "maintenance" or article_type == "maintenance" else article_type
    if target_type:
        typed = [d for d in directives if target_type in d.get("preferred_types", ())]
        if typed:
            return typed

    return directives


def select_hero_scene_directive(
    article_data: dict[str, Any],
    variant_index: int = 0,
    exclude_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Deterministically choose a varied visual scene directive for the featured cat."""
    featured_cat = article_data.get("featuredCat", "naomi")
    directives = HERO_SCENE_DIRECTIVES.get(featured_cat, HERO_SCENE_DIRECTIVES["naomi"])
    candidates = _pick_preferred_directives(directives, article_data)
    if len(candidates) < 2:
        candidates = directives

    if exclude_ids:
        filtered = [d for d in candidates if d["id"] not in exclude_ids]
        if not filtered:
            filtered = [d for d in directives if d["id"] not in exclude_ids]
        if filtered:
            candidates = filtered

    slug = str(article_data.get("slug") or article_data.get("id") or "default")
    pub = str(article_data.get("publishedAt") or "")
    digest = hashlib.sha256(f"{slug}:{pub}:{featured_cat}:{variant_index}".encode("utf-8")).hexdigest()
    idx = (int(digest[:8], 16) + variant_index) % len(candidates)
    return candidates[idx]


def compute_hero_seed(slug: str, variant_index: int = 0) -> int:
    digest = hashlib.sha256(f"{slug}:seed:{variant_index}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def get_fallback_image_prompt(
    featured_cat: str,
    category: str,
    circuit: str,
    weather: str = "Dry",
    directive: dict[str, Any] | None = None,
) -> str:
    """Generate a high-realism, varied cat reporter action prompt if dynamic LLM generation fails."""
    if directive is None:
        directives = HERO_SCENE_DIRECTIVES.get(featured_cat, HERO_SCENE_DIRECTIVES["naomi"])
        digest = hashlib.sha256(f"{featured_cat}:{category}:{circuit}".encode("utf-8")).hexdigest()
        directive = directives[int(digest[:8], 16) % len(directives)]

    cat_identity = {
        "marc": (
            "Marc, a chubby anthropomorphic orange tabby domestic cat (2.5 to 3 heads tall on short feline legs) "
            "wearing his retro red-white-and-blue zippered motorsport paddock jacket with PRESS/MARC patches and media lanyard"
        ),
        "suzuka": (
            "Suzuka, a chubby anthropomorphic calico domestic cat (2.5 to 3 heads tall on short feline legs) "
            "wearing a white collared shirt, khaki multi-pocket photographer vest with '87 PRESS SUZUKA badge, and black shoes"
        ),
        "naomi": (
            "Naomi, a chubby anthropomorphic sleek black domestic cat (2.5 to 3 heads tall on short feline legs) "
            "with green eyes, a tiny pink cherry blossom flower clip by her left ear, and oil-stained navy mechanic coveralls"
        ),
    }.get(featured_cat, "Naomi, a chubby black domestic cat mechanic in navy coveralls")

    circuit_txt = circuit or "a Japanese road racing circuit"
    weather_txt = weather or "natural daylight"
    return (
        f"{directive['shot_framing']} featuring {cat_identity} at {circuit_txt}. "
        f"{directive['pose_action']}. {directive['prop_rule']} "
        f"Environment & atmosphere: {directive['setting_lighting']} Weather condition: {weather_txt}. "
        f"Authentic 1980s Japanese Nameneko documentary photography style, crisp fur texture, natural depth of field, subtle 35mm film grain."
    )


def build_hero_image_prompt(
    article_data: dict[str, Any],
    client: Any,
    directive: dict[str, Any] | None = None,
    exclude_ids: set[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Construct a varied photographic prompt featuring the cat reporter in action."""
    featured_cat = article_data.get("featuredCat", "naomi")
    category = article_data.get("category", "")
    circuit = article_data.get("circuit", "")
    ja_title = article_data.get("locales", {}).get("ja", {}).get("title", "")
    ja_summary = article_data.get("locales", {}).get("ja", {}).get("summary", "")
    highlight = article_data.get("locales", {}).get("ja", {}).get("highlightPoint", "")
    weather_info = article_data.get("eventMeta", {}).get("weather", {})
    weather = weather_info.get("en") or weather_info.get("ja") or "Dry / Clear"

    if directive is None:
        directive = select_hero_scene_directive(article_data, exclude_ids=exclude_ids)

    cat_desc = {
        "marc": "Marc (male orange tabby cat, editor-in-chief, retro red-white-and-blue racing jacket with PRESS/MARC patches and media lanyard)",
        "suzuka": "Suzuka (female calico cat, trackside photojournalist, white shirt, khaki multi-pocket vest with '87 PRESS SUZUKA badge, black shoes)",
        "naomi": "Naomi (female sleek black cat, veteran mechanic, tiny pink cherry blossom clip by left ear, oil-stained navy coveralls)",
    }.get(featured_cat, "Naomi (female black cat mechanic)")

    context_desc = (
        f"Featured Cat Reporter (PROTAGONIST): {cat_desc}\n"
        f"Article Category: {category}\n"
        f"Circuit / Location: {circuit}\n"
        f"Weather / Atmosphere: {weather}\n"
        f"Japanese Title: {ja_title}\n"
        f"Summary: {ja_summary}\n"
        f"Key Highlight: {highlight}\n\n"
        f"ASSIGNED SCENE DIRECTIVE (MANDATORY — DO NOT REPEAT DEFAULT CENTERED POSE):\n"
        f"- Directive ID: {directive['id']}\n"
        f"- Shot Framing: {directive['shot_framing']}\n"
        f"- Pose & Action: {directive['pose_action']}\n"
        f"- Prop Rule: {directive['prop_rule']}\n"
        f"- Setting & Lighting: {directive['setting_lighting']}\n"
    )

    if client is not None:
        try:
            interaction = client.interactions.create(
                model="gemini-3.8-flash",
                system_instruction=IMAGE_PROMPT_SYSTEM_INSTRUCTION,
                input=(
                    "Generate a vivid, realistic text-to-image prompt following the ASSIGNED SCENE DIRECTIVE "
                    f"for this specific motorsport article:\n\n{context_desc}"
                ),
            )
            prompt = (interaction.output_text or "").strip()
            prompt = re.sub(r'^["\'`]+|["\'`]+$', '', prompt).strip()
            if prompt and len(prompt) > 20:
                return prompt, directive
        except Exception as e:
            print(f"⚠️ Dynamic prompt generation via Gemini failed ({e}). Using varied directive fallback.")

    return get_fallback_image_prompt(featured_cat, category, circuit, weather, directive=directive), directive


def compose_final_hero_prompt(
    featured_cat: str,
    prompt_body: str,
    directive: dict[str, Any],
) -> str:
    """Wrap the scene prompt with identity preservation + anti-copy-paste framing rules."""
    return (
        f"Generate a 16:9 photographic hero image featuring the character identity from the reference image ({featured_cat}). "
        f"KEEP ONLY the cat's exact face, fur markings, signature outfit identity, and chubby 2.5-to-3-heads-tall domestic cat proportions "
        f"(NOT an 8-head-tall humanoid). "
        f"COMPLETELY CHANGE the camera angle, pose, framing, background location, lighting, and held props from the reference photo "
        f"to match this specific scene ({directive['id']}): "
        f"{prompt_body}"
    )


def _generate_hero_with_gemini(
    slug: str,
    featured_cat: str,
    ref_image_path: Path,
    prompt: str,
    target_webp: Path,
    client: Any,
) -> bool:
    """Generate hero image via `gemini-2.5-flash-image` and save optimized 1200px WebP."""
    from google.genai import types
    import io
    import time
    from PIL import Image

    print(f"🎨 Generating realistic Nameneko-style hero photo with Gemini Image for '{slug}' ({featured_cat})...")
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
                if im.width > 1200:
                    target_height = int(im.height * (1200 / im.width))
                    im = im.resize((1200, target_height), Image.Resampling.LANCZOS)
                im.save(target_webp, format="WEBP", quality=85, method=6)

            size_kb = target_webp.stat().st_size // 1024
            print(f"✅ Successfully generated and saved Gemini hero photo: {target_webp} ({size_kb} KB)")
            return True
        except Exception as e:
            print(f"⚠️ Gemini image generation attempt {attempt} failed: {e}")
            time.sleep(5 * attempt)

    return False


def generate_and_save_hero_image(
    article_data: dict[str, Any],
    client: Any,
    force: bool = False,
    image_backend: str = "auto",
) -> str | None:
    """Generate a photojournalistic hero image (Colab FLUX.2-klein-4B primary, Gemini fallback) as WebP."""
    raw_slug = article_data.get("slug")
    if not raw_slug:
        return None
    slug = slugify(raw_slug)

    HERO_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    target_webp = HERO_IMAGES_DIR / f"{slug}.webp"
    public_url = f"/images/articles/{slug}.webp"

    if target_webp.exists() and not force:
        print(f"📷 Hero image already exists at {target_webp}, reusing.")
        return public_url

    featured_cat = article_data.get("featuredCat", "naomi")
    ref_image_path = CAT_IMAGES_DIR / f"{featured_cat}.png"

    prompt_body, directive = build_hero_image_prompt(article_data, client)
    prompt = compose_final_hero_prompt(featured_cat, prompt_body, directive)
    seed = compute_hero_seed(slug)
    print(f"🎬 Scene directive [{directive['id']}] | seed={seed}")
    print(f"📝 Prompt: {prompt}")

    use_colab = image_backend in ("auto", "colab") and colab_image_generator.is_colab_configured()
    if image_backend == "colab" and not use_colab:
        print("⚠️ `--image-backend colab` requested, but Colab CLI/ADC credentials are not configured.")

    if use_colab:
        try:
            print(f"☁️ Generating varied hero photo via Colab T4 FLUX.2-klein-4B for '{slug}' ({featured_cat})...")
            if colab_image_generator.generate_hero_image(
                slug=slug,
                featured_cat=featured_cat,
                ref_image_path=ref_image_path,
                prompt=prompt,
                output_webp_path=target_webp,
                seed=seed,
            ):
                return public_url
            print("⚠️ Colab FLUX.2-klein-4B generation did not produce output.")
        except Exception as colab_err:
            print(f"⚠️ Colab FLUX.2-klein-4B generation failed ({colab_err}).")

    if image_backend != "colab" and client is not None:
        if _generate_hero_with_gemini(slug, featured_cat, ref_image_path, prompt, target_webp, client):
            return public_url

    if article_data.get("category") == "maintenance":
        print("⚠️ Hero image generation failed for maintenance article; falling back to technical SVG hero.")
        return generate_technical_svg_hero(article_data)

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
    image_backend: str = "auto",
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
        article = author_and_audit_article(prompt, today_str, image_backend=image_backend)
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
        article = author_and_audit_article(prompt, today_str, image_backend=image_backend)
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
                image_backend=image_backend,
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
                image_backend=image_backend,
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
                image_backend=image_backend,
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
                image_backend=image_backend,
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
        author_and_audit_article(prompt, today_str, image_backend=image_backend)
        return 0

    # 6. Manual Custom Dispatch (`workflow_dispatch`)
    prompt = custom_topic or "Create a strictly fact-verified motorsport or circuit maintenance article."
    author_and_audit_article(prompt, today_str, image_backend=image_backend)
    return 0


def update_hero_images_for_existing(
    limit: int | None = None,
    force: bool = False,
    specific_slug: str | None = None,
    image_backend: str = "auto",
) -> int:
    """Generate realistic hero photos for existing articles (batching via Colab T4 when configured)."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = None
    if api_key:
        from google import genai
        client = genai.Client()

    existing = sorted(ARTICLES_DIR.glob("*.json"), reverse=True)
    print(f"🔍 Checking hero images for {len(existing)} existing articles...")

    targets: list[tuple[Path, dict[str, Any]]] = []
    for path in existing:
        if limit is not None and len(targets) >= limit:
            print(f"⏹️ Reached generation limit ({limit}).")
            break

        doc = json.loads(path.read_text(encoding="utf-8"))
        slug = slugify(doc.get("slug", ""))
        if specific_slug and doc.get("slug") != specific_slug and slug != specific_slug:
            continue

        current_hero = doc.get("heroImage", "")
        if not force and current_hero.startswith("/images/articles/") and (HERO_IMAGES_DIR / f"{slug}.webp").exists():
            continue

        targets.append((path, doc))

    if not targets:
        print("✨ All matching articles already have up-to-date hero images.")
        return 0

    use_colab = image_backend in ("auto", "colab") and colab_image_generator.is_colab_configured()
    if image_backend == "colab" and not use_colab:
        print("❌ `--image-backend colab` requested, but Colab CLI/ADC credentials are not configured.")
        return 1

    HERO_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    updated_count = 0

    if use_colab:
        jobs: list[colab_image_generator.HeroImageJob] = []
        pending_by_slug: dict[str, tuple[Path, dict[str, Any], str, Path]] = {}
        used_directives_by_cat: dict[str, set[str]] = {}

        for path, doc in targets:
            slug = slugify(doc.get("slug", ""))
            featured_cat = doc.get("featuredCat", "naomi")
            ref_image_path = CAT_IMAGES_DIR / f"{featured_cat}.png"
            target_webp = HERO_IMAGES_DIR / f"{slug}.webp"
            used_for_cat = used_directives_by_cat.setdefault(featured_cat, set())
            prompt_body, directive = build_hero_image_prompt(doc, client, exclude_ids=used_for_cat)
            used_for_cat.add(directive["id"])
            prompt = compose_final_hero_prompt(featured_cat, prompt_body, directive)
            seed = compute_hero_seed(slug)
            print(f"\n🎬 Queued [{slug}] ({featured_cat}) | directive={directive['id']} | seed={seed}")
            print(f"📝 Prompt: {prompt}")
            jobs.append(
                colab_image_generator.HeroImageJob(
                    slug=slug,
                    featured_cat=featured_cat,
                    ref_image_path=ref_image_path,
                    prompt=prompt,
                    output_webp_path=target_webp,
                    seed=seed,
                )
            )
            pending_by_slug[slug] = (path, doc, prompt, target_webp)

        colab_succeeded: dict[str, Path] = {}
        try:
            colab_succeeded = colab_image_generator.generate_hero_images_batch(jobs)
        except Exception as exc:
            print(f"⚠️ Colab batch hero generation failed ({exc}).")

        for slug, (path, doc, prompt, target_webp) in pending_by_slug.items():
            new_hero_url: str | None = None
            if slug in colab_succeeded:
                new_hero_url = f"/images/articles/{slug}.webp"
            elif image_backend != "colab" and client is not None:
                featured_cat = doc.get("featuredCat", "naomi")
                ref_image_path = CAT_IMAGES_DIR / f"{featured_cat}.png"
                if _generate_hero_with_gemini(slug, featured_cat, ref_image_path, prompt, target_webp, client):
                    new_hero_url = f"/images/articles/{slug}.webp"
            if not new_hero_url and doc.get("category") == "maintenance":
                new_hero_url = generate_technical_svg_hero(doc)

            if new_hero_url:
                doc["heroImage"] = new_hero_url
                path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"💾 Updated {path.name} with new heroImage: {new_hero_url}")
                updated_count += 1
            else:
                print(f"⏩ Skipped updating {path.name} (image generation failed).")
    else:
        for path, doc in targets:
            slug = doc.get("slug")
            current_hero = doc.get("heroImage", "")
            print(f"\n📸 Processing hero image for [{slug}] (current: {current_hero})...")
            new_hero_url = generate_and_save_hero_image(doc, client, force=force, image_backend=image_backend)
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
    # World Championships & Sanctioning Bodies
    "motogp.com",
    "worldsbk.com",
    "fimewc.com",
    "its-results.com",
    "fim-moto.com",
    "fim-europe.com",
    "fim-asia.com",
    "mylaps.com",
    "tsl-timing.com",
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
    "balatonparkcircuit.com",
    "cremonacircuit.it",
    "circuitoestoril.pt",
    "circuit-magnycours.com",
    "donington-park.co.uk",
    "autodrom-most.cz",
    "circuitricardotormo.com",
    "circuitofamericas.com",
    "bric.co.th",
    "changinternationalcircuit.com",
    # Japanese Sanctioning, All-Japan & Official Timing Portals
    "mfj.or.jp",
    "jrr.jp",
    "ms-event.net",
    # Nationwide Japanese Major Circuits
    "suzukacircuit.jp",
    "mr-motegi.jp",
    "tsukuba-circuit.jp",
    "sportsland-sugo.co.jp",
    "okayama-international-circuit.jp",
    "fsw.tv",
    "tokachi.msf.ne.jp",
    # Japanese Regional / Mini-bike / Kart Circuits
    "msl-hobby.jp",
    "akigase.co.jp",
    "akechi-ht.com",
    "coocan.jp",
    "osl.vc",
    "mobara-tc.com",
    "yrp-kota.com",
    "kinspo.com",
    "sakaikartland.com",
    "nkw.jp",
    "shiraito-speedland.com",
    "twc.ne.jp",
    "meihan-sl.com",
    "takasucircuit.com",
    "central-circuit.co.jp",
    "sodegaura-forest-raceway.com",
    "ebisu-circuit.com",
    "nihonkai-maze.com",
    "sp-nakayama.jp",
    "bihoku-highland.com",
    # Kyushu Circuits & Grassroots Endurance
    "autopolis.jp",
    "rms.co.jp",
    "tetsuuma.com",
    "brow-s.jp",
    "seesaa.net",
    "takuma-gp.com",
    "sonicpark.co.jp",
    # Official Motorcycle Event Navis & Portals
    "event.webike.net",
    "webike.net",
    # Official Technical Standards, Regulatory Agencies & Parts Manufacturers (Maintenance Series)
    "jisc.go.jp",
    "jsa.or.jp",
    "kikakurui.com",
    "iso.org",
    "sae.org",
    "jalos.or.jp",
    "api.org",
    "jatma.or.jp",
    "jmca.gr.jp",
    "mlit.go.jp",
    "jaf.or.jp",
    "ecfr.gov",
    "brembo.com",
    "hitachiastemo.com",
    "nissin-kogyo.co.jp",
    "daytona.co.jp",
    "vesrah.com",
    "ebcbrakes.com",
    "sbs.dk",
    "project-mu.co.jp",
    "rk-japan.co.jp",
    "ferodo.com",
    "galfer.eu",
    "sunstar-kc.jp",
    "ohlins.com",
    "carrozzeriajapan.co.jp",
    "showa1.com",
    "kyb.co.jp",
    "wp-suspension.com",
    "nitron.jp",
    "yss.co.th",
    "motul.com",
    "wako-chemical.co.jp",
    "castrol.com",
    "shell.com",
    "totalenergies.com",
    "mobil.com",
    "sunoco.co.jp",
    "motorex.com",
    "pirelli.com",
    "michelin.com",
    "michelin.co.jp",
    "metzeler.com",
    "ircmoto.com",
    "continental-tires.com",
    "did-daido.co.jp",
    "ekchain.jp",
    "dunlop.co.jp",
    "bridgestone.co.jp",
    "stmitaly.com",
    "suterproducts.com",
    "fcc-net.co.jp",
    "acv.co.jp",
    "yoshimura-jp.com",
    "moriwaki.co.jp",
    "babyface.co.jp",
    "striker.co.jp",
    "magicalracing.co.jp",
    "a-tech.org",
    "southco.com",
    "ngk-sparkplugs.jp",
    "niterra-group.com",
    "ngk.co.jp",
    "tohnichi.co.jp",
    "tonetool.co.jp",
    "ktc.jp",
    "kyototool.co.jp",
    "honda.co.jp",
    "global.honda",
    "yamaha-motor.co.jp",
    "suzuki.co.jp",
    "kawasaki-motors.com",
    "ducati.com",
    "aprilia.com",
    "ktm.com",
    "bmw-motorrad.com",
    "triumphmotorcycles.com",
    "triumphmotorcycles.jp",
    # Official Platforms & Social Media
    "x.com",
    "twitter.com",
    "twimg.com",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
]

FORBIDDEN_FAKE_STATUS_IDS = {
    "1844000000000000001",
    "2119468112345678901",
    "2119582109876543210",
    "2119695420112233445",
    "2119803456789123456",
    "2119914567890123456",
}


def is_allowed_domain(url: str) -> bool:
    """Validate that the URL belongs to an allowed official or social media domain."""
    if not url:
        return False
    match = re.search(r"^https?://([^/:]+)", url.strip(), re.IGNORECASE)
    if not match:
        return False
    host = match.group(1).lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_ALLOWED_DOMAINS)


def _sanitize_article_domains(
    draft_json: dict[str, Any],
    relevant_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Filter out disallowed source/citation URLs and ensure trusted fallback sources before writing."""
    fc = draft_json.get("factCheck")
    if not isinstance(fc, dict):
        fc = {}
        draft_json["factCheck"] = fc

    kept_sources: list[Any] = []
    for s_item in fc.get("sources") or []:
        s_url = s_item if isinstance(s_item, str) else s_item.get("url", "")
        if s_url and is_allowed_domain(s_url):
            kept_sources.append(s_item)
        else:
            print(f"⚠️ Pruned disallowed factCheck source URL before publishing: `{s_url}`")

    if not kept_sources:
        if draft_json.get("category") == "maintenance":
            kept_sources = [
                "https://www.mfj.or.jp/national/road-race/",
                "https://www.jisc.go.jp/",
            ]
        else:
            for src in relevant_sources or []:
                for u in (src.get("calendarUrls") or []) + (src.get("resultUrls") or []):
                    if is_allowed_domain(u) and u not in kept_sources:
                        kept_sources.append(u)
                        break
                if len(kept_sources) >= 2:
                    break
            if not kept_sources:
                kept_sources = ["https://www.mfj.or.jp/calendar/"]
        print(f"ℹ️ Populated fallback official factCheck source(s): {kept_sources}")

    fc["sources"] = kept_sources

    cleaned_cites: list[dict[str, Any]] = []
    for cite in draft_json.get("snsCitations") or []:
        post_url = str(cite.get("postUrl") or "")
        chan_url = str(cite.get("url") or "")
        target_url = post_url or chan_url

        if any(bad_id in u for u in (post_url, chan_url) for bad_id in FORBIDDEN_FAKE_STATUS_IDS):
            print(f"⚠️ Pruned known fake status ID from snsCitations: `{target_url}`")
            continue

        if target_url and not is_allowed_domain(target_url):
            print(f"⚠️ Pruned disallowed snsCitation URL before publishing: `{target_url}`")
            continue

        if cite.get("platform") == "X":
            media_urls = cite.get("mediaUrls") or []
            if media_urls:
                valid_media = [
                    m for m in media_urls
                    if isinstance(m, str) and "pbs.twimg.com/" in m and is_allowed_domain(m)
                ]
                cite["mediaUrls"] = valid_media

        cleaned_cites.append(cite)

    draft_json["snsCitations"] = cleaned_cites
    return draft_json


def validate_article_record(
    doc: dict[str, Any],
    fname: str,
    schedule_events: set[str] | None = None,
    expected_stem: str | None = None,
) -> list[str]:
    """Deterministically validate a single article JSON document and return violation strings."""
    errors: list[str] = []

    # 1. ID matches filename stem
    doc_id = doc.get("id", "")
    if expected_stem is not None and doc_id != expected_stem:
        errors.append(f"[{fname}] ID mismatch: `id` is '{doc_id}' but filename is '{expected_stem}'")

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

    # 4. SNS Citations verification (including verified photo-attached X post check)
    sns_cites = doc.get("snsCitations", [])
    if not sns_cites or not isinstance(sns_cites, list):
        errors.append(f"[{fname}] `snsCitations` is missing or empty")
    else:
        has_verified_photo_x = False
        for idx, cite in enumerate(sns_cites, start=1):
            post_url = cite.get("postUrl") or cite.get("url", "")
            if post_url and not is_allowed_domain(post_url):
                errors.append(f"[{fname}] snsCitation #{idx} postUrl `{post_url}` is not in OFFICIAL_ALLOWED_DOMAINS")

            for url_field in (cite.get("postUrl", ""), cite.get("url", "")):
                for bad_id in FORBIDDEN_FAKE_STATUS_IDS:
                    if bad_id in str(url_field):
                        errors.append(f"[{fname}] snsCitation #{idx} contains known 404/fabricated status ID `{bad_id}`")

            if cite.get("platform") == "X":
                has_status = bool(re.search(r"^https?://(?:www\.)?(?:x\.com|twitter\.com)/[^/]+/status/\d+", str(cite.get("postUrl", ""))))
                media_urls = cite.get("mediaUrls") or []
                valid_media = [
                    m for m in media_urls
                    if isinstance(m, str) and "pbs.twimg.com/" in m and is_allowed_domain(m)
                ]
                if media_urls and len(valid_media) != len(media_urls):
                    errors.append(f"[{fname}] snsCitation #{idx} has invalid or disallowed domain in `mediaUrls`")
                if has_status and len(valid_media) >= 1:
                    has_verified_photo_x = True

        if not has_verified_photo_x:
            errors.append(
                f"[{fname}] Missing verified photo-attached X post (`platform: 'X'` with `/status/<id>` postUrl and >=1 `pbs.twimg.com/` URL in `mediaUrls`)"
            )

    # 5. Hero Image Physical Existence
    hero_img = doc.get("heroImage", "")
    if not hero_img:
        errors.append(f"[{fname}] Missing `heroImage` property")
    else:
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

    return errors


def validate_existing_articles() -> int:
    """Strict Deterministic Fact & Integrity Gatekeeper for Honda.cat Articles."""
    existing = sorted(ARTICLES_DIR.glob("*.json"))
    print(f"🔍 Running Deterministic Fact & Integrity Audit on {len(existing)} articles in {ARTICLES_DIR}...")

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

        errors.extend(
            validate_article_record(
                doc,
                fname=fname,
                schedule_events=schedule_events,
                expected_stem=path.stem,
            )
        )

        fc = doc.get("factCheck", {})
        sources = fc.get("sources", []) if isinstance(fc, dict) else []
        sns_cites = doc.get("snsCitations", []) or []
        hero_img = doc.get("heroImage", "")
        langs = list((doc.get("locales") or {}).keys())
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
    parser.add_argument(
        "--image-backend",
        choices=["auto", "colab", "gemini"],
        default=os.environ.get("HERO_IMAGE_BACKEND", "auto"),
        help="Hero image generation backend (auto=Colab T4 FLUX.2-klein-4B primary with Gemini fallback)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.dry_run:
        return validate_existing_articles()

    if args.generate_hero_images:
        if not api_key and not colab_image_generator.is_colab_configured():
            print("ℹ️ Neither GEMINI_API_KEY nor Colab ADC credentials are configured; running Fact-Check Audit.")
            return validate_existing_articles()
        return update_hero_images_for_existing(
            limit=args.limit,
            force=args.force_images,
            specific_slug=args.slug,
            image_backend=args.image_backend,
        )

    if not api_key:
        print("ℹ️ GEMINI_API_KEY not set in environment; running local Fact-Check & Schedule State Audit.")
        return validate_existing_articles()

    if args.mode == "backfill":
        return run_backfill_window(args.start_date, args.end_date)

    ref_date = dt.date.fromisoformat(args.date) if args.date else None
    return run_schedule_driven_mode(
        mode=args.mode,
        custom_topic=args.topic,
        ref_date_override=ref_date,
        image_backend=args.image_backend,
    )


if __name__ == "__main__":
    sys.exit(main())
