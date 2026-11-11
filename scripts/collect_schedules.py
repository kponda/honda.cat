#!/usr/bin/env python3
"""
honda.cat — Weekly Official Race Schedule Database Sync
=======================================================
Runs once a week (with enhanced off-season full-calendar discovery from Dec to Feb)
to check for schedule updates across:
  1. FIM MotoGP Official (`motogp.com`) & WorldSBK (`worldsbk.com`) & Montmeló (`circuitcat.com`)
  2. MFJ Official (`mfj.or.jp`) & JRR All-Japan Road Race (`superbike.jp`)
  3. All Nationwide Regional Championships & Major Circuits:
     - Suzuka (`suzukacircuit.jp`), Motegi (`mr-motegi.jp`), Tsukuba (`tsukuba-circuit.jp`),
       SUGO (`sportsland-sugo.co.jp`), Okayama (`okayama-international-circuit.jp`),
       Fuji (`fsw.tv`), Tokachi (`tokachi.msf.ne.jp`)
  4. Kyushu 3 Major Circuits:
     - Autopolis (`autopolis.jp`), SPA Naoiri (`spa-naoiri.com`), HSR Kyushu (`hsr.jp`, `tetsuma.jp`)
  5. Official SNS Accounts (X, Instagram, Facebook)

If schedule additions or date changes are detected, updates `src/data/schedules.json`
while preserving existing `publicationState` (`previewPublished`, `resultStatus`).
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCES_CONFIG_PATH = Path(__file__).resolve().parent / "sources_config.json"
SCHEDULES_JSON_PATH = ROOT_DIR / "src" / "data" / "schedules.json"

SCHEDULE_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "id",
        "scope",
        "category",
        "series",
        "startDate",
        "endDate",
        "circuit",
        "eventName",
        "scheduleWindow",
        "classes",
        "officialWebUrl",
        "circuitWebUrl",
        "snsHandle",
        "snsUrl",
        "verifiedSource",
    ],
    "properties": {
        "id": {"type": "string"},
        "scope": {"type": "string", "enum": ["world", "japan"]},
        "category": {
            "type": "string",
            "enum": ["world", "all-japan", "kyushu", "endurance-fun"],
        },
        "series": {"type": "string"},
        "startDate": {"type": "string", "description": "YYYY-MM-DD start date of the race event"},
        "endDate": {"type": "string", "description": "YYYY-MM-DD end date (Sunday final) of the race event"},
        "circuit": {
            "type": "object",
            "required": ["ja", "ca", "en"],
            "properties": {
                "ja": {"type": "string"},
                "ca": {"type": "string"},
                "en": {"type": "string"},
            },
        },
        "eventName": {
            "type": "object",
            "required": ["ja", "ca", "en"],
            "properties": {
                "ja": {"type": "string"},
                "ca": {"type": "string"},
                "en": {"type": "string"},
            },
        },
        "scheduleWindow": {
            "type": "object",
            "required": ["ja", "ca", "en"],
            "properties": {
                "ja": {"type": "string"},
                "ca": {"type": "string"},
                "en": {"type": "string"},
            },
        },
        "classes": {"type": "string"},
        "officialWebUrl": {"type": "string"},
        "circuitWebUrl": {"type": "string"},
        "snsHandle": {"type": "string"},
        "snsUrl": {"type": "string"},
        "verifiedSource": {"type": "string"},
    },
}

SCHEDULES_COLLECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["hasUpdates", "events"],
    "properties": {
        "hasUpdates": {"type": "boolean"},
        "events": {
            "type": "array",
            "items": SCHEDULE_ITEM_SCHEMA,
        },
    },
}


def strip_html_tags(raw_html: str, max_len: int = 2000) -> str:
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len]


def fetch_official_site_snippets(sources: list[dict[str, Any]], timeout: int = 8) -> list[dict[str, Any]]:
    """Fetch live HTML snippets from MotoGP, MFJ, and nationwide circuit calendar URLs."""
    results: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; HondaCatScheduleCollector/2.0; +https://honda.cat)"
    }
    for src in sources:
        fetched_pages: list[dict[str, str]] = []
        for url in src.get("calendarUrls", []):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    body = resp.read().decode(charset, errors="replace")
                    snippet = strip_html_tags(body)
                    fetched_pages.append({"url": url, "status": "ok", "snippet": snippet})
            except Exception as exc:
                fetched_pages.append({"url": url, "status": f"deferred_to_search ({type(exc).__name__})", "snippet": ""})
        results.append(
            {
                "id": src["id"],
                "scope": src.get("scope", "japan"),
                "category": src["category"],
                "name": src["name"]["ja"],
                "sns": src.get("sns", []),
                "pages": fetched_pages,
            }
        )
    return results


def sync_schedules_with_gemini(
    sources_cfg: dict[str, Any],
    existing_db: dict[str, Any],
    scraped_data: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    """Check official calendars & SNS via Gemini 3.8 Flash + Google Search and merge updates into DB."""
    from google import genai

    client = genai.Client()
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    today_iso = now.isoformat(timespec="seconds")
    is_offseason_window = now.month in sources_cfg.get("offSeasonFocusMonths", [12, 1, 2])

    season_focus_note = (
        "IMPORTANT OFF-SEASON FULL-YEAR INGESTION (Dec–Feb): Official annual race calendars for the new season "
        "are typically announced during December–February. Thoroughly search all official websites and SNS "
        "for newly released annual schedules and provisional/official dates."
        if is_offseason_window
        else "Perform a weekly differential check across all official calendars and SNS for new race dates or schedule updates."
    )

    prompt = (
        f"Current timestamp: {today_iso}\n"
        f"{season_focus_note}\n\n"
        "You are the Official Race Schedule Database Maintainer for `honda.cat`.\n"
        "Using Google Search Grounding (`google_search`) and the scraped official website snippets below, "
        "verify and update the annual race schedule database across:\n"
        "1. `scope: 'world'`: FIM MotoGP (`motogp.com/en/calendar`), FIM WorldSBK (`worldsbk.com/en/calendar`), "
        "and Circuit de Barcelona-Catalunya (`circuitcat.com`).\n"
        "2. `scope: 'japan'`: MFJ Official (`mfj.or.jp/calendar/`), All-Japan Road Race (`superbike.jp/calendar/`), "
        "all nationwide MFJ Regional Championships (Suzuka, Motegi, Tsukuba, SUGO, Okayama, Fuji, Tokachi), "
        "and Kyushu's 3 major circuits (SPA Naoiri, Autopolis, HSR Kyushu) + recreational endurance series.\n\n"
        "STRICT FACT POLICY:\n"
        "- Never fabricate dates. Set `startDate` and `endDate` (YYYY-MM-DD) from verified official calendars.\n"
        "- Set `hasUpdates: true` if any event date, name, or schedule window changed compared to `EXISTING_DB`.\n\n"
        f"EXISTING_DB:\n{json.dumps(existing_db, ensure_ascii=False)}\n\n"
        f"SCRAPED OFFICIAL SOURCES:\n{json.dumps(scraped_data, ensure_ascii=False)}"
    )

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=prompt,
        tools=[{"type": "google_search"}],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": SCHEDULES_COLLECTION_SCHEMA,
        },
    )

    parsed = json.loads(interaction.output_text)
    has_updates = bool(parsed.get("hasUpdates", False))

    existing_states = {
        ev["id"]: ev.get(
            "publicationState",
            {"previewPublished": False, "resultStatus": "pending", "lastCheckedAt": today_iso},
        )
        for ev in existing_db.get("events", [])
    }

    merged_events: list[dict[str, Any]] = []
    for ev in parsed.get("events", []):
        prev_state = existing_states.get(
            ev["id"],
            {"previewPublished": False, "resultStatus": "pending", "lastCheckedAt": today_iso},
        )
        ev["publicationState"] = {
            **prev_state,
            "lastCheckedAt": today_iso,
        }
        merged_events.append(ev)

    updated_db = {
        "lastUpdated": today_iso,
        "season": now.year if now.month < 12 else now.year + 1,
        "collectionMethod": "Weekly Official Calendar Database Sync (Dec–Feb Off-Season Full-Year Ingestion + Weekly Differential Check)",
        "events": merged_events,
    }
    return has_updates, updated_db


def verify_schedule_registry() -> int:
    if not SOURCES_CONFIG_PATH.exists():
        print(f"❌ Missing {SOURCES_CONFIG_PATH}")
        return 1
    if not SCHEDULES_JSON_PATH.exists():
        print(f"❌ Missing {SCHEDULES_JSON_PATH}")
        return 1

    sources_cfg = json.loads(SOURCES_CONFIG_PATH.read_text(encoding="utf-8"))
    schedules_data = json.loads(SCHEDULES_JSON_PATH.read_text(encoding="utf-8"))

    sources = sources_cfg.get("sources", [])
    events = schedules_data.get("events", [])
    print(f"📡 Registered Official Websites & SNS Sources: {len(sources)}")
    for s in sources:
        urls = ", ".join(s.get("calendarUrls", []))
        sns_list = ", ".join(f"{x['platform']}:{x['handle']}" for x in s.get("sns", []))
        print(f"   - [{s['id']}] ({s.get('scope')}) {s['name']['ja']} | Web: {urls} | SNS: {sns_list}")

    print(f"\n🗓️ Verified Schedule Entries in {SCHEDULES_JSON_PATH.name}: {len(events)}")
    for ev in events:
        state = ev.get("publicationState", {})
        print(
            f"   ✅ {ev['id']} ({ev.get('scope')}) | {ev.get('startDate')}..{ev.get('endDate')} | "
            f"preview={state.get('previewPublished')} | result={state.get('resultStatus')}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly sync of official race schedule database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify official source registry and schedule DB state without calling API",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.dry_run or not api_key:
        if not api_key and not args.dry_run:
            print("ℹ️ GEMINI_API_KEY not set; verifying registered official sources and schedule DB.")
        return verify_schedule_registry()

    sources_cfg = json.loads(SOURCES_CONFIG_PATH.read_text(encoding="utf-8"))
    existing_db = json.loads(SCHEDULES_JSON_PATH.read_text(encoding="utf-8"))

    print("🌐 Running weekly official race schedule check across MotoGP, MFJ, nationwide circuits, and SNS...")
    scraped = fetch_official_site_snippets(sources_cfg["sources"])
    has_updates, updated_db = sync_schedules_with_gemini(sources_cfg, existing_db, scraped)

    if has_updates:
        SCHEDULES_JSON_PATH.write_text(json.dumps(updated_db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✅ Schedule updates detected! Updated {SCHEDULES_JSON_PATH} ({len(updated_db['events'])} entries).")
    else:
        print("⏭️ No schedule changes detected this week; database is already up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
