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
            "enum": ["world", "motogp", "sbk", "all-japan", "kyushu", "endurance-fun"],
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


OFFICIAL_TRUSTED_DOMAINS = [
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
]


def is_domain_trusted(url: str, trusted_domains: list[str]) -> bool:
    """Validate that the URL belongs to a trusted official domain or its subdomains."""
    if not url:
        return False
    match = re.search(r"^https?://([^/:]+)", url.strip(), re.IGNORECASE)
    if not match:
        return False
    host = match.group(1).lower()
    return any(host == d or host.endswith("." + d) for d in trusted_domains)


def extract_structured_webike_events(raw_html: str) -> str:
    """Extract structured race event records directly from Webike Event NAVI HTML."""
    pattern = re.compile(
        r'<h4[^>]*class=[\"\'][^\"\']*title[^\"\']*[\"\'][^>]*>\s*<a[^>]+href=[\"\'](https://event\.webike\.net/event/\d+/)[\"\'][^>]*>(.*?)</a>.*?'
        r'<td[^>]*class=[\"\'][^\"\']*address[^\"\']*[\"\'][^>]*>(.*?)</td>.*?'
        r'開催日\s*</td>\s*<td[^>]*>\s*<span>(.*?)</span>',
        re.DOTALL,
    )
    items = pattern.findall(raw_html)
    if not items:
        return ""
    lines = ["【Webike イベントNAVI レースカレンダー公認抽出データ】"]
    for url, title, addr, dates in items:
        title_clean = re.sub(r"\s+", " ", html.unescape(title)).strip()
        addr_clean = re.sub(r"\s+", " ", html.unescape(addr)).strip()
        dates_clean = dates.strip()
        lines.append(f"- 開催日: {dates_clean} | 大会名: {title_clean} | 開催場所: {addr_clean} | URL: {url}")
    return "\n".join(lines)


def strip_html_tags(raw_html: str, max_len: int = 15000) -> str:
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len]


def fetch_official_site_snippets(sources: list[dict[str, Any]], timeout: int = 8) -> list[dict[str, Any]]:
    """Fetch live HTML snippets from MotoGP, MFJ, Webike, and nationwide circuit calendar URLs."""
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
                    
                    # If this is Webike Event NAVI, extract structured events first
                    structured_text = ""
                    if "event.webike.net" in url:
                        structured_text = extract_structured_webike_events(body)
                    
                    snippet = strip_html_tags(body)
                    if structured_text:
                        snippet = f"{structured_text}\n\n[Raw Page Snippet]:\n{snippet}"
                    
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
    """Strict Deterministic Fact & Integrity Gatekeeper for Race Schedule Database."""
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

    print(f"\n🗓️ Running Deterministic Fact & Integrity Verification on {SCHEDULES_JSON_PATH.name} ({len(events)} entries)...")
    errors: list[str] = []
    seen_ids: set[str] = set()

    for idx, ev in enumerate(events, start=1):
        eid = ev.get("id", f"unknown-entry-#{idx}")
        # 1. Unique ID
        if eid in seen_ids:
            errors.append(f"[{eid}] Duplicate event ID found in schedules.json")
        seen_ids.add(eid)

        # 2. Required fields
        for field in ["id", "scope", "category", "series", "startDate", "endDate", "circuit", "eventName", "scheduleWindow", "officialWebUrl", "circuitWebUrl"]:
            if not ev.get(field):
                errors.append(f"[{eid}] Missing required field: `{field}`")

        # 3. Scope & Category Enum
        if ev.get("scope") not in ["world", "japan"]:
            errors.append(f"[{eid}] Invalid scope: `{ev.get('scope')}` (expected 'world' or 'japan')")
        if ev.get("category") not in ["world", "motogp", "sbk", "all-japan", "kyushu", "endurance-fun"]:
            errors.append(f"[{eid}] Invalid category: `{ev.get('category')}`")

        # 4. Trilingual structures
        for tri_field in ["circuit", "eventName", "scheduleWindow"]:
            tri_obj = ev.get(tri_field, {})
            if not isinstance(tri_obj, dict):
                errors.append(f"[{eid}] Field `{tri_field}` must be an object with ja/ca/en")
            else:
                for lang in ["ja", "ca", "en"]:
                    if not tri_obj.get(lang):
                        errors.append(f"[{eid}] Field `{tri_field}.{lang}` is missing or empty")

        # 5. Date format, validity, range, and season boundary
        start_str = ev.get("startDate", "")
        end_str = ev.get("endDate", "")
        start_d: dt.date | None = None
        end_d: dt.date | None = None

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", start_str):
            errors.append(f"[{eid}] Invalid startDate format: `{start_str}` (expected YYYY-MM-DD)")
        else:
            try:
                start_d = dt.date.fromisoformat(start_str)
            except ValueError:
                errors.append(f"[{eid}] Non-existent calendar date for startDate: `{start_str}`")

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", end_str):
            errors.append(f"[{eid}] Invalid endDate format: `{end_str}` (expected YYYY-MM-DD)")
        else:
            try:
                end_d = dt.date.fromisoformat(end_str)
            except ValueError:
                errors.append(f"[{eid}] Non-existent calendar date for endDate: `{end_str}`")

        if start_d and end_d:
            if start_d > end_d:
                errors.append(f"[{eid}] startDate ({start_d}) is after endDate ({end_d})")
            diff_days = (end_d - start_d).days
            if diff_days < 0 or diff_days > 6:
                errors.append(f"[{eid}] Event duration of {diff_days} days is abnormal for a race event (expected 0-6 days)")
            
            # Zero-Hallucination Season Boundary Check:
            # Events must be within the verified 2026 season or official 2027 early test/pre-season (Jan-Feb 2027)
            if start_d.year < 2026 or (start_d.year == 2027 and start_d.month > 2) or start_d.year > 2027:
                errors.append(f"[{eid}] Date {start_d} is outside confirmed season window (2026 - Feb 2027). Unannounced future schedules are prohibited.")

        # 6. Official Domain Integrity
        off_url = ev.get("officialWebUrl", "")
        if not is_domain_trusted(off_url, OFFICIAL_TRUSTED_DOMAINS):
            errors.append(f"[{eid}] officialWebUrl `{off_url}` is not in OFFICIAL_TRUSTED_DOMAINS")

        circ_url = ev.get("circuitWebUrl", "")
        if not is_domain_trusted(circ_url, OFFICIAL_TRUSTED_DOMAINS):
            errors.append(f"[{eid}] circuitWebUrl `{circ_url}` is not in OFFICIAL_TRUSTED_DOMAINS")

        state = ev.get("publicationState", {})
        print(
            f"   ✅ {eid} ({ev.get('scope')}) | {start_str}..{end_str} | "
            f"preview={state.get('previewPublished')} | result={state.get('resultStatus')}"
        )

    if errors:
        print(f"\n❌ DETERMINISTIC INTEGRITY AUDIT FAILED! Found {len(errors)} violation(s):")
        for err in errors:
            print(f"   🚨 {err}")
        print("\n🚫 Aborting pipeline to prevent fabricated or hallucinated schedules from being published!")
        return 1

    print(f"\n🎯 All {len(events)} schedule entries passed strict deterministic integrity audit!")
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
