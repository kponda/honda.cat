#!/usr/bin/env python3
"""
honda.cat — Weekly Official Race Schedule Database Sync
=======================================================
Runs once a week (with enhanced off-season full-calendar discovery from Dec to Feb)
to check for schedule updates across:
  1. FIM MotoGP Official (`motogp.com`) & WorldSBK (`worldsbk.com`) & Montmeló (`circuitcat.com`)
  2. MFJ Official (`mfj.or.jp`) & JRR All-Japan Road Race (`jrr.jp`)
  3. All Nationwide Regional Championships & Major Circuits:
     - Suzuka (`suzukacircuit.jp`), Motegi (`mr-motegi.jp`), Tsukuba (`tsukuba-circuit.jp`),
       SUGO (`sportsland-sugo.co.jp`), Okayama (`okayama-international-circuit.jp`, `ms-event.net/oicweb`),
       Fuji (`fsw.tv`), Tokachi (`tokachi.msf.ne.jp`)
  4. Kyushu 3 Major Circuits & Mini-Bike / Endurance Series:
     - Autopolis (`autopolis.jp/ap/`), SPA Naoiri (`autopolis.jp/spa/`),
       HSR Kyushu (`rms.co.jp/kumamoto/hsr/`, `ms-event.net/hsrweb`, `tetsuuma.com`)
       * MANDATORY COVERAGE: HSR Kyushu Mini-Bike Series (`SuperドリームSunday 8時間耐久レース With J・TRIP` every December,
         `SuperドリームSundayレース`, `ドリームSundayレース`, `SAGA CUP / WORLD SAGA CUP`, `エンジョイ4時間耐久レース`)
  5. Official SNS Accounts (X, YouTube, Facebook, Instagram)

If schedule additions or date changes are detected, updates `src/data/schedules.json`
while preserving existing `publicationState` (`previewPublished`, `resultStatus`).
"""

from __future__ import annotations

import argparse
import codecs
import datetime as dt
import html
import io
import json
import os
import re
import sys
import urllib.parse
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
    # World Championships & Sanctioning Bodies
    "motogp.com",
    "worldsbk.com",
    "fimewc.com",
    "its-results.com",
    "fim-moto.com",
    "fim-europe.com",
    "fim-asia.com",
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
    # Japanese Sanctioning, All-Japan & Timing Portals
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
]

UNTRUSTED_CIRCUIT_DENYLIST = [
    # Defunct / hijacked legacy domains (must NEVER be used)
    "hsr.jp",
    "tetsuma.jp",
    "spa-naoiri.com",
    "superbike.jp",
    # Non-official / social / aggregator domains
    "wikipedia.org",
    "example.com",
    "localhost",
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "ameblo.jp",
    "fc2.com",
    "note.com",
    "hatenablog.com",
    "blogspot.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "instagram.com",
    "facebook.com",
]


def is_domain_trusted(url: str, trusted_domains: list[str]) -> bool:
    """Validate that the URL belongs to a trusted official domain or its subdomains."""
    if not url:
        return False
    match = re.search(r"^https?://([^/:]+)", url.strip(), re.IGNORECASE)
    if not match:
        return False
    host = match.group(1).lower()
    if any(host == d or host.endswith("." + d) for d in UNTRUSTED_CIRCUIT_DENYLIST):
        return False
    return any(host == d or host.endswith("." + d) for d in trusted_domains)


def is_valid_circuit_url(url: str, official_url: str = "") -> bool:
    """Validate circuitWebUrl: accept trusted domains, or valid non-denylisted domains paired with a trusted officialWebUrl."""
    if is_domain_trusted(url, OFFICIAL_TRUSTED_DOMAINS):
        return True
    if not url or not is_domain_trusted(official_url, OFFICIAL_TRUSTED_DOMAINS):
        return False
    match = re.search(r"^https?://([^/:?#\s]+)", url.strip(), re.IGNORECASE)
    if not match:
        return False
    host = match.group(1).lower()
    if "." not in host or ".." in host or "@" in host:
        return False
    if re.match(r"^\d+(?:\.\d+){3}$", host):
        return False
    if any(host == d or host.endswith("." + d) for d in UNTRUSTED_CIRCUIT_DENYLIST):
        return False
    return True


def validate_schedule_event(
    ev: dict[str, Any],
    seen_ids: set[str] | None = None,
    ref_date: dt.date | None = None,
    idx: int = 0,
) -> list[str]:
    """Deterministically validate one schedule event dict and return a list of violation strings."""
    errors: list[str] = []
    eid = ev.get("id", f"unknown-entry-#{idx}")
    today_d = ref_date or dt.date.today()

    # 1. Unique ID
    if seen_ids is not None and eid in seen_ids:
        errors.append(f"[{eid}] Duplicate event ID found in schedules.json")

    # 2. Required fields
    for field in [
        "id",
        "scope",
        "category",
        "series",
        "startDate",
        "endDate",
        "circuit",
        "eventName",
        "scheduleWindow",
        "officialWebUrl",
        "circuitWebUrl",
    ]:
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

    # 5. Date format, validity, range, and dynamic season boundary
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

        # Dynamic Zero-Hallucination Season Boundary Check:
        # Allow 2026 through next calendar year (e.g. official 2027 season announced in late 2026)
        if start_d.year < 2026 or start_d.year > today_d.year + 1:
            errors.append(
                f"[{eid}] Date {start_d} is outside confirmed season window (2026 - {today_d.year + 1}). "
                "Unannounced far-future schedules are prohibited."
            )

    # 6. Official & Circuit Domain Integrity
    off_url = ev.get("officialWebUrl", "")
    if not is_domain_trusted(off_url, OFFICIAL_TRUSTED_DOMAINS):
        errors.append(f"[{eid}] officialWebUrl `{off_url}` is not in OFFICIAL_TRUSTED_DOMAINS")

    circ_url = ev.get("circuitWebUrl", "")
    if not is_valid_circuit_url(circ_url, off_url):
        errors.append(f"[{eid}] circuitWebUrl `{circ_url}` is invalid or untrusted")

    return errors


def _safe_decode_http_bytes(raw: bytes, header_charset: str | None) -> str:
    """Safely decode HTTP response bytes even when servers send bogus charsets like `charset=none`."""
    cs = (header_charset or "").strip()
    if not cs or cs.lower() in ("none", "unknown", "binary"):
        m = re.search(rb"charset=[\"\x27]?([A-Za-z0-9_-]+)", raw[:4096], re.IGNORECASE)
        cs = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        codecs.lookup(cs)
    except LookupError:
        cs = "utf-8"
    return raw.decode(cs, errors="replace")


def _extract_pdf_text_snippet(raw_pdf: bytes, max_len: int = 12000) -> str:
    """Extract text from an official PDF schedule (e.g., HSR Kyushu annual event_schedule PDF) if pypdf is installed."""
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(raw_pdf))
        pages_txt: list[str] = []
        for p in reader.pages[:6]:
            t = p.extract_text() or ""
            if t.strip():
                pages_txt.append(re.sub(r"\s+", " ", t).strip())
        return "\n".join(pages_txt)[:max_len]
    except Exception:
        return ""


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


def extract_structured_hsr_event_links(raw_html: str, base_url: str) -> list[str]:
    """Discover all HSR Kyushu 2-wheel road/minibike event detail URLs from `/kumamoto/hsr/event/`."""
    cards = re.findall(
        r'<a[^>]+href=[\"\'](https?://www\.rms\.co\.jp/kumamoto/hsr/event/\d{4}/\d{2}/\d+/|/kumamoto/hsr/event/\d{4}/\d{2}/\d+/)[\"\'][^>]*>(.*?)</a>',
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    skip_keywords = ("4輪", "クルマ", "K-CAR", "サイクル", "モトクロス", "エンデューロ", "オフロード", "オフスク", "スクール", "走行会")
    keep_keywords = ("8時間耐久", "ドリームSunday", "SAGA CUP", "4時間耐久", "Trophy", "ドリームカップ", "火の国", "鉄馬")
    discovered: list[str] = []
    for href, inner in cards:
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
        if any(k in label for k in keep_keywords) or ("ミニバイク" in label and not any(s in label for s in skip_keywords)):
            full_u = urllib.parse.urljoin(base_url, href)
            if full_u not in discovered:
                discovered.append(full_u)
    return discovered


def strip_html_tags(raw_html: str, max_len: int = 15000) -> str:
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len]


def fetch_official_site_snippets(sources: list[dict[str, Any]], timeout: int = 8) -> list[dict[str, Any]]:
    """Fetch live HTML/PDF snippets from MotoGP, MFJ/JRR, Webike, HSR Kyushu mini-bike pages, and nationwide circuits."""
    results: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; HondaCatScheduleCollector/2.1; +https://honda.cat)"
    }
    cur_year = dt.date.today().year

    for src in sources:
        fetched_pages: list[dict[str, str]] = []
        urls_to_fetch = list(src.get("calendarUrls", []))

        # Dynamically check next-season HSR Kyushu PDF schedule (e.g. event_schedule2027.pdf during off-season)
        if src.get("id") == "hsr-kyushu":
            for y in (cur_year, cur_year + 1):
                dyn_pdf = f"https://www.rms.co.jp/kumamoto/hsr/pdf/event_schedule{y}.pdf"
                if dyn_pdf not in urls_to_fetch:
                    urls_to_fetch.append(dyn_pdf)

        seen_urls: set[str] = set()
        idx = 0
        while idx < len(urls_to_fetch):
            url = urls_to_fetch[idx]
            idx += 1
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    ctype = (resp.headers.get_content_type() or "").lower()
                    raw = resp.read()

                    if url.lower().endswith(".pdf") or "pdf" in ctype:
                        pdf_txt = _extract_pdf_text_snippet(raw)
                        fetched_pages.append(
                            {
                                "url": url,
                                "status": "ok_pdf",
                                "snippet": pdf_txt or f"[Official PDF Schedule Verified Online: {url}]",
                            }
                        )
                        continue

                    body = _safe_decode_http_bytes(raw, resp.headers.get_content_charset())

                    # Auto-discover any newly added HSR Kyushu 2-wheel / mini-bike event detail pages
                    if src.get("id") == "hsr-kyushu" and url.rstrip("/").endswith("/kumamoto/hsr/event"):
                        for extra_u in extract_structured_hsr_event_links(body, url):
                            if extra_u not in seen_urls and extra_u not in urls_to_fetch:
                                urls_to_fetch.append(extra_u)

                    structured_text = ""
                    if "event.webike.net" in url:
                        structured_text = extract_structured_webike_events(body)

                    # Focus on <main> content if available so nav chrome doesn't crowd out dates
                    main_match = re.search(r"<main\b[^>]*>(.*?)</main>", body, flags=re.DOTALL | re.IGNORECASE)
                    snippet = strip_html_tags(main_match.group(1) if main_match else body)
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
        "2. `scope: 'japan'`: MFJ Official (`mfj.or.jp`), JRR All-Japan Road Race (`jrr.jp/calendar/`), "
        "all nationwide MFJ Regional Championships (Suzuka, Motegi, Tsukuba, SUGO, Okayama, Fuji, Tokachi), "
        "and Kyushu's 3 major circuits (SPA Naoiri `autopolis.jp/spa/`, Autopolis `autopolis.jp/ap/`, HSR Kyushu `rms.co.jp/kumamoto/hsr/`) + recreational endurance series.\n\n"
        "MANDATORY HSR KYUSHU MINI-BIKE & ENDURANCE COVERAGE RULE (NEVER OMIT!):\n"
        "- HSR Kyushu (`https://www.rms.co.jp/kumamoto/hsr/event/` & `ms-event.net/hsrweb`) hosts a rich calendar of mini-bike sprints and endurance races across both its Circuit Course (2,350m) and Dream Course (695m).\n"
        "- You MUST NEVER miss or omit HSR Kyushu mini-bike races, especially:\n"
        "  1) Every December's season-closing flagship `SuperドリームSunday 8時間耐久レース With J・TRIP` (8-Hour Mini-Bike Endurance Championship Finale on HSR Kyushu Circuit Course, 2st-SP50 / 4st-SP100 / 4st-SF100 / 4st-ST125).\n"
        "  2) `SuperドリームSundayレース` (all rounds on HSR Kyushu Circuit Course).\n"
        "  3) `ドリームSundayレース` (all 4 rounds on HSR Kyushu Dream Course, AM Sprint & PM Endurance / HRC GROM Cup / NSF100 HRC Trophy).\n"
        "  4) `SAGA CUP` (all 4 Dream Course rounds) & `WORLD SAGA CUP` (Circuit Course 3h endurance).\n"
        "  5) `エンジョイ4時間耐久レース` (year-end mini-bike 4-hour endurance on HSR Kyushu Circuit Course).\n"
        "  6) Plus `HSR九州 Trophy ロードレース選手権`, `ドリームカップフェスティバル`, `S250火の国耐久レース`, and `鉄馬 with TSK` (`tetsuuma.com`).\n\n"
        "STRICT FACT & DOMAIN POLICY:\n"
        "- Never fabricate dates. Set `startDate` and `endDate` (YYYY-MM-DD) from verified official calendars.\n"
        "- NEVER use defunct/hijacked domains `hsr.jp`, `tetsuma.jp`, `spa-naoiri.com`, or `superbike.jp`. Always use `rms.co.jp/kumamoto/hsr/` or `ms-event.net/hsrweb` for HSR Kyushu, `tetsuuma.com` for Tetsuma, `autopolis.jp/spa/` for SPA Naoiri, and `jrr.jp` for All-Japan Road Race.\n"
        "- `officialWebUrl` MUST use an official sanctioning, circuit, or organizer domain (`motogp.com`, `worldsbk.com`, `mfj.or.jp`, `jrr.jp`, `rms.co.jp`, `ms-event.net`, `tetsuuma.com`, `autopolis.jp`, `suzukacircuit.jp`, `mr-motegi.jp`, `tsukuba-circuit.jp`, `sportsland-sugo.co.jp`, `okayama-international-circuit.jp`, `fsw.tv`, `tokachi.msf.ne.jp`, `brow-s.jp`, `takuma-gp.com`, `event.webike.net`).\n"
        "- `circuitWebUrl` MUST be the real official circuit domain (never Wikipedia, blogs, or social media profiles); if unavailable, set it equal to `officialWebUrl`.\n"
        "- Set `hasUpdates: true` if any event date, name, or schedule window changed or new events were added compared to `EXISTING_DB`.\n\n"
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
    today_date = now.date()

    existing_events = existing_db.get("events", [])
    existing_by_id = {ev["id"]: ev for ev in existing_events if ev.get("id")}
    existing_states = {
        ev["id"]: ev.get(
            "publicationState",
            {"previewPublished": False, "resultStatus": "pending", "lastCheckedAt": today_iso},
        )
        for ev in existing_events
        if ev.get("id")
    }

    merged_events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _sanitize_and_accept(ev: dict[str, Any], idx: int) -> bool:
        eid = ev.get("id", "")
        prev_ev = existing_by_id.get(eid)

        if not is_domain_trusted(ev.get("officialWebUrl", ""), OFFICIAL_TRUSTED_DOMAINS):
            if prev_ev and is_domain_trusted(prev_ev.get("officialWebUrl", ""), OFFICIAL_TRUSTED_DOMAINS):
                print(f"⚠️ [{eid}] Restoring trusted officialWebUrl from existing DB (got `{ev.get('officialWebUrl')}`).")
                ev["officialWebUrl"] = prev_ev["officialWebUrl"]

        if not is_valid_circuit_url(ev.get("circuitWebUrl", ""), ev.get("officialWebUrl", "")):
            if prev_ev and is_valid_circuit_url(prev_ev.get("circuitWebUrl", ""), ev.get("officialWebUrl", "")):
                print(f"⚠️ [{eid}] Restoring valid circuitWebUrl from existing DB (got `{ev.get('circuitWebUrl')}`).")
                ev["circuitWebUrl"] = prev_ev["circuitWebUrl"]
            elif is_domain_trusted(ev.get("officialWebUrl", ""), OFFICIAL_TRUSTED_DOMAINS):
                print(f"⚠️ [{eid}] Replacing invalid circuitWebUrl `{ev.get('circuitWebUrl')}` with trusted officialWebUrl.")
                ev["circuitWebUrl"] = ev["officialWebUrl"]

        ev_errors = validate_schedule_event(ev, seen_ids=seen_ids, ref_date=today_date, idx=idx)
        if ev_errors:
            if prev_ev and eid not in seen_ids:
                fallback_ev = {
                    **prev_ev,
                    "publicationState": {**prev_ev.get("publicationState", {}), "lastCheckedAt": today_iso},
                }
                if not validate_schedule_event(fallback_ev, seen_ids=seen_ids, ref_date=today_date, idx=idx):
                    print(f"⚠️ [{eid}] Proposed update failed validation ({'; '.join(ev_errors)}); keeping existing valid entry.")
                    merged_events.append(fallback_ev)
                    seen_ids.add(eid)
                    return True
            print(f"⚠️ Skipping invalid proposed schedule entry [{eid}]: {'; '.join(ev_errors)}")
            return False

        prev_state = existing_states.get(
            eid,
            {"previewPublished": False, "resultStatus": "pending", "lastCheckedAt": today_iso},
        )
        ev["publicationState"] = {
            **prev_state,
            "lastCheckedAt": today_iso,
        }
        merged_events.append(ev)
        seen_ids.add(eid)
        return True

    for idx, ev in enumerate(parsed.get("events", []), start=1):
        _sanitize_and_accept(ev, idx)

    # Never drop existing verified events if omitted by the model response
    for idx, prev_ev in enumerate(existing_events, start=1):
        eid = prev_ev.get("id", "")
        if eid and eid not in seen_ids:
            restored = {
                **prev_ev,
                "publicationState": {**prev_ev.get("publicationState", {}), "lastCheckedAt": today_iso},
            }
            if not validate_schedule_event(restored, seen_ids=seen_ids, ref_date=today_date, idx=idx):
                merged_events.append(restored)
                seen_ids.add(eid)

    merged_events.sort(key=lambda e: (e.get("startDate", ""), e.get("id", "")))

    if len(merged_events) != len(existing_events):
        has_updates = True

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
    circuit_res_pages = sources_cfg.get("circuitResultPages", [])
    events = schedules_data.get("events", [])
    print(f"📡 Registered Official Websites & SNS Sources: {len(sources)} (Circuit Result Registry: {len(circuit_res_pages)} circuits)")
    for s in sources:
        urls = ", ".join(s.get("calendarUrls", [])[:3])
        res_urls = ", ".join(s.get("resultUrls", [])) or "none"
        sns_list = ", ".join(f"{x['platform']}:{x['handle']}" for x in s.get("sns", []))
        print(f"   - [{s['id']}] ({s.get('scope')}) {s['name']['ja']} | Cal: {urls} | Results: {res_urls} | SNS: {sns_list}")

    print(f"\n🗓️ Running Deterministic Fact & Integrity Verification on {SCHEDULES_JSON_PATH.name} ({len(events)} entries)...")
    errors: list[str] = []
    seen_ids: set[str] = set()
    ref_date = dt.date.today()

    # Deterministic check: ensure HSR Kyushu mini-bike 8-hour endurance finale is never missing
    has_hsr_8h = any(
        "hsr" in (ev.get("id", "") + ev.get("circuit", {}).get("ja", "")).lower()
        and ("8時間耐久" in ev.get("eventName", {}).get("ja", "") or "8h" in ev.get("id", "").lower())
        for ev in events
    )
    if not has_hsr_8h:
        errors.append("[hsr-kyushu-8h] Mandatory December HSR Kyushu Mini-Bike 8-Hour Endurance (`SuperドリームSunday 8時間耐久レース`) is missing from schedules.json!")

    for idx, ev in enumerate(events, start=1):
        eid = ev.get("id", f"unknown-entry-#{idx}")
        ev_errors = validate_schedule_event(ev, seen_ids=seen_ids, ref_date=ref_date, idx=idx)
        errors.extend(ev_errors)
        seen_ids.add(eid)

        state = ev.get("publicationState", {})
        print(
            f"   ✅ {eid} ({ev.get('scope')}) | {ev.get('startDate', '')}..{ev.get('endDate', '')} | "
            f"preview={state.get('previewPublished')} | result={state.get('resultStatus')}"
        )

    if errors:
        print(f"\n❌ DETERMINISTIC INTEGRITY AUDIT FAILED! Found {len(errors)} violation(s):")
        for err in errors:
            print(f"   🚨 {err}")
        print("\n🚫 Aborting pipeline to prevent fabricated, incomplete, or untrusted schedules from being published!")
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

    print("🌐 Running weekly official race schedule check across MotoGP, MFJ, nationwide circuits, HSR Kyushu mini-bike series, and SNS...")
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
