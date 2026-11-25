#!/usr/bin/env python3
"""
scripts/circuit_results_fetcher.py
--------------------------------------------------------------------------------
Circuit-by-Circuit Official Race Result Page Discovery & Direct Parser Engine
for `honda.cat`.

Capabilities:
  1. Resolves whether the host circuit(s) / series organizer(s) of a target race
     publish an official result page (`circuitResultPages` in `sources_config.json`).
  2. Directly fetches live HTML & linked official result sheets (both digital
     timing PDFs like HSR Kyushu / Okayama `ms-event.net` Orbits sheets AND
     scanned signed timing PDFs like SPA Naoiri / Autopolis `autopolis.jp`).
  3. Extracts structured text from digital PDFs via `pypdf` when available, and
     uses Gemini multimodal PDF understanding (`application/pdf`) to transcribe
     scanned image PDFs verbatim so zero rider names, lap counts, or times are
     ever guessed or missed.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import base64
import codecs
import datetime as dt
import html
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SOURCES_CONFIG_PATH = Path(__file__).resolve().parent / "sources_config.json"


def load_sources_config() -> dict[str, Any]:
    if not SOURCES_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(SOURCES_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_decode_bytes(raw: bytes, header_charset: str | None) -> str:
    cs = (header_charset or "").strip()
    if not cs or cs.lower() in ("none", "unknown", "binary"):
        m = re.search(rb"charset=[\"\']?([A-Za-z0-9_-]+)", raw[:4096], re.IGNORECASE)
        cs = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        codecs.lookup(cs)
    except LookupError:
        cs = "utf-8"
    return raw.decode(cs, errors="replace")


def _fetch_url_bytes(url: str, timeout: int = 12) -> tuple[str, str, bytes]:
    """Return (final_url, content_type, raw_bytes)."""
    # Encode non-ASCII path/query characters safely
    parsed = urllib.parse.urlsplit(url.strip())
    safe_path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/:@!$&'()*+,;=-._~")
    safe_query = urllib.parse.quote(urllib.parse.unquote(parsed.query), safe="=&/:@!$'()*+,;-._~?")
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, safe_path, safe_query, ""))

    req = urllib.request.Request(safe_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        final_u = resp.geturl()
        ctype = (resp.headers.get_content_type() or "").lower()
        cs = resp.headers.get_content_charset()
        raw = resp.read()
        if cs:
            ctype = f"{ctype}; charset={cs}"
        return final_u, ctype, raw


def _fetch_html(url: str, timeout: int = 12) -> tuple[str, str]:
    final_u, ctype, raw = _fetch_url_bytes(url, timeout=timeout)
    cs_match = re.search(r"charset=([^\s;]+)", ctype, re.IGNORECASE)
    cs = cs_match.group(1) if cs_match else None
    return final_u, _safe_decode_bytes(raw, cs)


def _strip_html(raw_html: str, max_len: int = 8000) -> str:
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()[:max_len]


def resolve_circuit_result_entries(
    search_text: str,
    sources_cfg: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Identify all matching circuitResultPages entries for an event or prompt text."""
    cfg = sources_cfg or load_sources_config()
    entries = cfg.get("circuitResultPages", [])
    # Normalize SPA Naoiri sub-URL (`autopolis.jp/spa/`) before keyword matching so it doesn't falsely trigger Autopolis main course
    normalized = re.sub(r"https?://autopolis\.jp/spa[^\s]*", "spa直入", search_text or "", flags=re.IGNORECASE)
    lower_text = normalized.lower()

    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in entries:
        cid = item.get("circuitId", "")
        if not cid or cid in seen:
            continue
        kws = item.get("keywords", [])
        if any(kw.lower() in lower_text for kw in kws):
            if cid == "motogp" and "worldsbk" in lower_text and "motogp" not in lower_text:
                continue
            seen.add(cid)
            matched.append(item)
    return matched


def _build_date_variants(start_date: str | None, end_date: str | None) -> dict[str, set[str]]:
    """Build multiple Japanese & ISO date string representations for deterministic HTML matching."""
    iso_dates: set[str] = set()
    jp_dates: set[str] = set()
    slash_mmdd: set[str] = set()
    compact_mmdd: set[str] = set()
    dot_dates: set[str] = set()
    years: set[str] = set()

    for ds in (start_date, end_date):
        if not ds:
            continue
        try:
            d = dt.date.fromisoformat(ds[:10])
        except ValueError:
            continue
        iso_dates.add(d.isoformat())
        years.add(str(d.year))
        jp_dates.add(f"{d.year}年{d.month}月{d.day}日")
        jp_dates.add(f"{d.year}年{d.month:02d}月{d.day:02d}日")
        jp_dates.add(f"{d.month}月{d.day}日")
        slash_mmdd.add(f"{d.month:02d}/{d.day:02d}")
        slash_mmdd.add(f"{d.month}/{d.day}")
        compact_mmdd.add(f"{d.month:02d}{d.day:02d}")
        dot_dates.add(f"{d.year}.{d.month:02d}.{d.day:02d}")
        dot_dates.add(f"{d.year}.{d.month}.{d.day}")

    # Also include intermediate days if multi-day event
    if start_date and end_date:
        try:
            sd = dt.date.fromisoformat(start_date[:10])
            ed = dt.date.fromisoformat(end_date[:10])
            cur = sd
            while cur <= ed and (ed - sd).days <= 6:
                iso_dates.add(cur.isoformat())
                jp_dates.add(f"{cur.year}年{cur.month}月{cur.day}日")
                jp_dates.add(f"{cur.year}年{cur.month:02d}月{cur.day:02d}日")
                slash_mmdd.add(f"{cur.month:02d}/{cur.day:02d}")
                compact_mmdd.add(f"{cur.month:02d}{cur.day:02d}")
                dot_dates.add(f"{cur.year}.{cur.month:02d}.{cur.day:02d}")
                cur += dt.timedelta(days=1)
        except ValueError:
            pass

    return {
        "iso": iso_dates,
        "jp": jp_dates,
        "slash_mmdd": slash_mmdd,
        "compact_mmdd": compact_mmdd,
        "dot": dot_dates,
        "years": years,
    }


def _extract_event_keywords(event_name: str, series_name: str = "") -> list[str]:
    """Extract distinctive title tokens for matching an event block on a circuit result page."""
    combined = f"{event_name} {series_name}"
    cleaned = re.sub(r"（.*?）|【.*?】|\(.*?\)", " ", combined)
    tokens: list[str] = []
    special_phrases = [
        "スーパーサンデーフェスタ",
        "Super Sunday Festa",
        "九州エンデュランスフェスタ",
        "5耐",
        "POLISPA",
        "ゴールドカップ",
        "SuperドリームSunday",
        "superドリームSunday",
        "8時間耐久",
        "ドリームSunday",
        "Saga Cup",
        "SAGA CUP",
        "WORLD SAGA CUP",
        "鉄馬",
        "火の国",
        "ドリームカップ",
        "Trophy",
        "エンジョイ4時間耐久",
        "テイスト・オブ・ツクバ",
        "ツーリスト・トロフィー",
        "MINI BIKE 6時間耐久",
        "ST150 6時間耐久",
        "JP-SPORT 4時間耐久",
        "OPEN 4時間耐久",
        "モトレボリューション",
        "MOTO Revolution",
        "サンデーロードレース",
        "FUN&RUN",
        "お題付耐久",
        "レン耐",
    ]
    for sp in special_phrases:
        if sp.lower() in combined.lower() and sp not in tokens:
            tokens.append(sp)

    for raw_tok in re.split(r"[\s・／/「」『』\-]+", cleaned):
        t = raw_tok.strip()
        if len(t) >= 3 and t.lower() not in {
            "2026",
            "2027",
            "hsr九州",
            "spa直入",
            "オートポリス",
            "レース",
            "シリーズ",
            "選手権",
            "ロードレース",
            "耐久レース",
        }:
            if t not in tokens:
                tokens.append(t)
    return tokens


def _strip_nav_chrome(raw_html: str) -> str:
    """Prefer <main> or strip <header>/<nav>/<footer> so navigation menus don't pollute extracted text/links."""
    main_m = re.search(r"<main\b[^>]*>(.*?)</main>", raw_html, flags=re.DOTALL | re.IGNORECASE)
    if main_m:
        return main_m.group(1)
    cleaned = re.sub(r"<header\b[^>]*>.*?</header>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<nav\b[^>]*>.*?</nav>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<footer\b[^>]*>.*?</footer>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned


def _is_final_race_label(label: str, url: str = "") -> bool:
    low_lbl = label.lower()
    fname = url.split("/")[-1].lower() if url else ""
    combined = f"{low_lbl} {fname}"
    # Exclude non-result documents (schedules, regulations, entry forms, lap charts, practice/qualifying)
    if any(
        skip in combined
        for skip in [
            "schedule",
            "スケジュール",
            "規則",
            "プログラム",
            "program",
            "エントリー",
            "entry",
            "hason",
            "装具",
            "lapchart",
            "laptimechart",
            "フリー走行",
            "練習",
            "_q.pdf",
            "_g.pdf",
        ]
    ):
        return False
    if any(q in low_lbl for q in ["予選", "タイムアタック", "セミファイナル"]) and not any(
        f in low_lbl for f in ["決勝", "ファイナル", "総合結果", "総合正式"]
    ):
        return False
    return any(
        keep in combined
        for keep in [
            "決勝",
            "ファイナル",
            "総合",
            "正式",
            "暫定",
            "_f.pdf",
            "final",
            "耐久",
            "リザルト",
        ]
    )


def _parse_autopolis_spa_sections(
    raw_html: str,
    base_url: str,
    date_vars: dict[str, set[str]],
    kw_tokens: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse SPA Naoiri (`autopolis.jp/spa/result/`) & Autopolis (`autopolis.jp/ap/result/`) `<section>` blocks."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []

    sections = re.findall(r"<section\b[^>]*>(.*?)</section>", raw_html, flags=re.DOTALL | re.IGNORECASE)
    for idx, sec in enumerate(sections):
        h2_m = re.search(r"<h2[^>]*>(.*?)</h2>", sec, flags=re.DOTALL | re.IGNORECASE)
        if not h2_m:
            continue
        heading_text = _strip_html(h2_m.group(1), max_len=300)

        date_hit = any(d in heading_text for d in date_vars["jp"] | date_vars["iso"] | date_vars["dot"])
        kw_hit = any(k.lower() in heading_text.lower() for k in kw_tokens[:5]) if kw_tokens else False
        # Match if exact date hits, OR if no date was given (custom mode) and keywords hit on recent sections
        if not date_hit and not (not date_vars["iso"] and kw_hit) and not (date_hit or (kw_hit and idx < 4 and not date_vars["iso"])):
            if not (kw_hit and any(y in heading_text for y in (date_vars["years"] or {"2026", "2027"})) and not date_vars["iso"]):
                continue

        dls = re.findall(r"<dl\b[^>]*>(.*?)</dl>", sec, flags=re.DOTALL | re.IGNORECASE)
        class_lines: list[str] = []
        for dl in dls:
            dt_m = re.search(r"<dt[^>]*>(.*?)</dt>", dl, flags=re.DOTALL | re.IGNORECASE)
            cls_name = _strip_html(dt_m.group(1), max_len=120) if dt_m else "Class"
            links = re.findall(
                r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>',
                dl,
                flags=re.DOTALL | re.IGNORECASE,
            )
            final_links_for_cls: list[tuple[str, str]] = []
            all_links_for_cls: list[tuple[str, str]] = []
            for href, ltxt in links:
                full_u = urllib.parse.urljoin(base_url, html.unescape(href).strip())
                lbl = _strip_html(ltxt, max_len=80)
                all_links_for_cls.append((full_u, lbl))
                if _is_final_race_label(lbl, full_u):
                    final_links_for_cls.append((full_u, lbl))

            chosen = final_links_for_cls or all_links_for_cls[:1]
            for full_u, lbl in chosen:
                pdf_items.append(
                    {
                        "label": f"{heading_text} | {cls_name} ({lbl})",
                        "url": full_u,
                    }
                )
                class_lines.append(f"  - {cls_name} [{lbl}]: {full_u}")

        summaries.append(f"■ 公式リザルト掲載イベント: {heading_text}\n" + "\n".join(class_lines))

    return summaries, pdf_items


def _parse_ms_event_blocks(
    raw_html: str,
    base_url: str,
    date_vars: dict[str, set[str]],
    kw_tokens: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse HSR Kyushu & Okayama `ms-event.net/.../?a=event_info_data.event_info_data_list` event blocks."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []

    # Split by <h1 class="sub_title"> blocks
    parts = re.split(r'(<h1[^>]*class=[\"\'][^\"\']*sub_title[^\"\']*[\"\'][^>]*>.*?</h1>)', raw_html, flags=re.DOTALL | re.IGNORECASE)
    for i in range(1, len(parts), 2):
        h1_html = parts[i]
        body_html = parts[i + 1] if i + 1 < len(parts) else ""
        heading_text = _strip_html(h1_html, max_len=300)

        date_hit = any(d in heading_text for d in date_vars["iso"] | date_vars["dot"] | date_vars["jp"])
        kw_hit = any(k.lower() in heading_text.lower() for k in kw_tokens[:6])
        # Skip 4-wheel / motocross / offroad when looking for road/minibike unless explicitly matched by keywords
        if any(skip in heading_text for skip in ["クルマでEnjoy", "モトクロス", "エンデューロ", "スーパーモト"]) and not kw_hit:
            continue

        if date_vars["iso"]:
            # Require date match (or keyword match within +/- 1 day if multi-day)
            if not date_hit and not (kw_hit and any(y in heading_text for y in date_vars["years"])):
                continue
            if not date_hit and kw_hit:
                # Check if heading has a completely different date
                m_iso = re.search(r"20\d\d-\d\d-\d\d", heading_text)
                if m_iso and m_iso.group(0) not in date_vars["iso"]:
                    continue
        else:
            if not kw_hit:
                continue

        # Parse <h3> sub-sections inside body_html
        sec_chunks = re.split(r"(<h3[^>]*>.*?</h3>)", body_html, flags=re.DOTALL | re.IGNORECASE)
        current_sec = "Result"
        link_lines: list[str] = []
        block_finals: list[dict[str, str]] = []
        block_all: list[dict[str, str]] = []

        for ch in sec_chunks:
            if ch.lower().startswith("<h3"):
                current_sec = _strip_html(ch, max_len=100)
                continue
            links = re.findall(
                r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>',
                ch,
                flags=re.DOTALL | re.IGNORECASE,
            )
            for href, ltxt in links:
                full_u = urllib.parse.urljoin(base_url, html.unescape(href).strip())
                lbl = _strip_html(ltxt, max_len=100)
                combined_lbl = f"{current_sec} / {lbl}"
                entry = {"label": f"{heading_text} | {combined_lbl}", "url": full_u}
                block_all.append(entry)
                if _is_final_race_label(combined_lbl, full_u):
                    block_finals.append(entry)
                    link_lines.append(f"  - {combined_lbl}: {full_u}")

        chosen = block_finals or block_all[:3]
        pdf_items.extend(chosen)
        if not link_lines:
            link_lines = [f"  - {e['label']}: {e['url']}" for e in chosen]
        summaries.append(f"■ 公式リザルト掲載イベント: {heading_text}\n" + "\n".join(link_lines))

    return summaries, pdf_items


def _parse_okayama_php_results(
    raw_html: str,
    base_url: str,
    date_vars: dict[str, set[str]],
    kw_tokens: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse Okayama International Circuit `result_out1.php` -> `result_out2.php?head_line=XX` 2-wheel final PDFs."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []
    years = date_vars["years"] or {str(dt.date.today().year)}

    hl_links = re.findall(
        r'<a[^>]+href=[\"\'](result_out2\.php\?head_line=\d+)[\"\'][^>]*>(.*?)</a>',
        raw_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    target_sub_urls: list[str] = []
    for href, ltxt in hl_links:
        clean_l = _strip_html(ltxt, max_len=200)
        if any(y in clean_l for y in years) and any(
            w in clean_l for w in ["ロードレース", "モトレヴォ", "ミニバイク", "2輪"]
        ):
            u = urllib.parse.urljoin(base_url, html.unescape(href).strip())
            if u not in target_sub_urls:
                target_sub_urls.append(u)

    for sub_u in target_sub_urls[:2]:
        try:
            final_u, sub_html = _fetch_html(sub_u, timeout=10)
        except Exception:
            continue
        blocks = re.split(r'(<p[^>]*class=[\"\']t2[\"\'][^>]*>.*?</p>)', sub_html, flags=re.DOTALL | re.IGNORECASE)
        for i in range(1, len(blocks), 2):
            title_txt = _strip_html(blocks[i], max_len=250)
            body_chunk = blocks[i + 1] if i + 1 < len(blocks) else ""
            date_hit = any(d in title_txt for d in date_vars["dot"] | date_vars["iso"] | date_vars["jp"])
            kw_hit = any(k.lower() in title_txt.lower() for k in kw_tokens[:5])
            if date_vars["dot"]:
                if not date_hit:
                    continue
            elif not kw_hit:
                continue

            rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", body_chunk, flags=re.DOTALL | re.IGNORECASE)
            cls_lines: list[str] = []
            for row in rows:
                tds = re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)
                if not tds:
                    continue
                cls_name = _strip_html(tds[0], max_len=150)
                for p_href in re.findall(r'<a[^>]+href=[\"\']([^\"\']+final\.pdf[^\"\']*)[\"\']', row, flags=re.IGNORECASE):
                    full_p = urllib.parse.urljoin(final_u, html.unescape(p_href).strip())
                    pdf_items.append({"label": f"{title_txt} | {cls_name} (決勝)", "url": full_p})
                    cls_lines.append(f"  - {cls_name} [決勝]: {full_p}")
            if cls_lines:
                summaries.append(f"■ 岡山国際サーキット公式リザルト ({title_txt}):\n" + "\n".join(cls_lines))

    return summaries, pdf_items


def _parse_tsukuba_results(
    raw_html: str,
    base_url: str,
    date_vars: dict[str, set[str]],
    kw_tokens: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse Tsukuba Circuit `/race/results/results.html` and follow matched event detail page."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []

    items = re.findall(
        r'<div[^>]*class=[\"\'][^\"\']*rsltList[^\"\']*[\"\'][^>]*>\s*<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>\s*<dl>\s*<dt>(.*?)</dt>\s*<dd>(.*?)</dd>',
        raw_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for href, dt_raw, dd_raw in items:
        dt_txt = _strip_html(dt_raw, max_len=40)
        dd_txt = _strip_html(dd_raw, max_len=200)
        date_hit = any(mmdd in dt_txt for mmdd in date_vars["slash_mmdd"])
        kw_hit = any(k.lower() in dd_txt.lower() for k in kw_tokens[:5])
        if date_vars["slash_mmdd"]:
            if not date_hit:
                continue
        elif not kw_hit:
            continue

        detail_url = urllib.parse.urljoin(base_url, html.unescape(href).strip())
        try:
            final_detail_u, detail_html = _fetch_html(detail_url, timeout=10)
            body_only = _strip_nav_chrome(detail_html)
            detail_snippet = _strip_html(body_only, max_len=5000)
            links = re.findall(
                r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>',
                body_only,
                flags=re.DOTALL | re.IGNORECASE,
            )
            finals: list[dict[str, str]] = []
            for p_href, p_txt in links:
                p_url = urllib.parse.urljoin(final_detail_u, html.unescape(p_href).strip())
                p_lbl = _strip_html(p_txt, max_len=100)
                if _is_final_race_label(p_lbl, p_url):
                    finals.append({"label": f"{dd_txt} | {p_lbl}", "url": p_url})
            pdf_items.extend(finals[:6])
            summaries.append(
                f"■ 筑波サーキット公式リザルト詳細 ({dt_txt} {dd_txt}): {final_detail_u}\n"
                f"  抜粋: {detail_snippet[:2500]}"
            )
        except Exception:
            summaries.append(f"■ 筑波サーキット公式リザルト項目 ({dt_txt} {dd_txt}): {detail_url}")

    return summaries, pdf_items


def _parse_sugo_results(
    raw_html: str,
    base_url: str,
    date_vars: dict[str, set[str]],
    kw_tokens: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse Sportsland SUGO `/results/two/` or `/results/big-race/` rows and follow matched post detail page."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []

    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", raw_html, flags=re.DOTALL | re.IGNORECASE)
    for row in rows:
        row_txt = _strip_html(row, max_len=400)
        date_hit = any(d in row_txt for d in date_vars["jp"] | date_vars["iso"])
        kw_hit = any(k.lower() in row_txt.lower() for k in kw_tokens[:5])
        if date_vars["jp"]:
            if not date_hit:
                continue
        elif not kw_hit:
            continue

        m_link = re.search(r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', row, flags=re.DOTALL | re.IGNORECASE)
        if not m_link:
            continue
        detail_url = urllib.parse.urljoin(base_url, html.unescape(m_link.group(1)).strip())
        ev_title = _strip_html(m_link.group(2), max_len=200)
        try:
            final_detail_u, detail_html = _fetch_html(detail_url, timeout=10)
            body_only = _strip_nav_chrome(detail_html)
            detail_snippet = _strip_html(body_only, max_len=5000)
            links = re.findall(
                r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>',
                body_only,
                flags=re.DOTALL | re.IGNORECASE,
            )
            for p_href, p_txt in links:
                p_url = urllib.parse.urljoin(final_detail_u, html.unescape(p_href).strip())
                p_lbl = _strip_html(p_txt, max_len=100)
                if _is_final_race_label(p_lbl, p_url):
                    pdf_items.append({"label": f"{ev_title} | {p_lbl}", "url": p_url})
            summaries.append(
                f"■ スポーツランドSUGO公式リザルト詳細 ({ev_title}): {final_detail_u}\n"
                f"  抜粋: {detail_snippet[:2500]}"
            )
        except Exception:
            summaries.append(f"■ スポーツランドSUGO公式リザルト項目 ({ev_title}): {detail_url}")

    return summaries, pdf_items


def _parse_suzuka_or_motegi_pdfs(
    circuit_id: str,
    base_url: str,
    raw_html: str,
    date_vars: dict[str, set[str]],
    search_text: str,
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse Suzuka (`/result_s/`) & Motegi (`/result_m/`) date-prefixed `MMDD_*_f.pdf` final result sheets."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []
    years = sorted(date_vars["years"]) or [str(dt.date.today().year)]

    candidate_subpages: list[str] = []
    if circuit_id == "suzuka-circuit":
        low = search_text.lower()
        sub_dirs = ["sundayr", "funandrun", "2r", "8tai", "mini-moto", "moto-challenge"]
        if "サンデー" in low or "sunday" in low:
            sub_dirs = ["sundayr", "2r"]
        elif "fun&run" in low or "funrun" in low:
            sub_dirs = ["funandrun"]
        elif "8耐" in low or "8 hours" in low:
            sub_dirs = ["8tai"]
        elif "全日本" in low or "mfj" in low:
            sub_dirs = ["2r"]
        for y in years:
            for sd in sub_dirs:
                candidate_subpages.append(f"https://www.suzukacircuit.jp/result_s/{y}/{sd}/")
    else:
        for y in years:
            candidate_subpages.append(f"https://www.mr-motegi.jp/result_m/{y}/2wheel/")

    for sub_u in candidate_subpages[:3]:
        try:
            final_u, sub_html = _fetch_html(sub_u, timeout=10)
        except Exception:
            continue
        links = re.findall(
            r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>',
            sub_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        matched_lines: list[str] = []
        for href, ltxt in links:
            fname = href.split("/")[-1].lower()
            if date_vars["compact_mmdd"] and not any(mmdd in fname for mmdd in date_vars["compact_mmdd"]):
                continue
            full_u = urllib.parse.urljoin(final_u, html.unescape(href).strip())
            lbl = _strip_html(ltxt, max_len=100) or fname
            if _is_final_race_label(lbl, fname):
                pdf_items.append({"label": f"{final_u} | {lbl}", "url": full_u})
                matched_lines.append(f"  - {lbl}: {full_u}")
        if matched_lines:
            summaries.append(f"■ 公式リザルトページ ({final_u}):\n" + "\n".join(matched_lines[:12]))

    return summaries, pdf_items


def _parse_generic_result_page(
    raw_html: str,
    base_url: str,
    date_vars: dict[str, set[str]],
    kw_tokens: list[str],
    fmt: str,
) -> tuple[list[str], list[dict[str, str]]]:
    """Parse JRR HTML tables, Rentai `/report/YYYY/MMDD.html`, or generic circuit PDF result indexes."""
    summaries: list[str] = []
    pdf_items: list[dict[str, str]] = []

    if fmt == "rentai_report_html":
        report_links = re.findall(
            r'<a[^>]+href=[\"\']([^\"\']*report/\d{4}/[^\"\']+\.html)[\"\'][^>]*>(.*?)</a>',
            raw_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        for href, ltxt in report_links:
            if date_vars["compact_mmdd"] and not any(mmdd in href for mmdd in date_vars["compact_mmdd"]):
                continue
            rep_url = urllib.parse.urljoin(base_url, html.unescape(href).strip())
            try:
                final_rep_u, rep_html = _fetch_html(rep_url, timeout=10)
                summaries.append(
                    f"■ Let's レン耐！公式レースレポート＆リザルト ({final_rep_u}):\n"
                    f"  {_strip_html(rep_html, max_len=4500)}"
                )
            except Exception:
                pass
        return summaries, pdf_items

    # Generic HTML text + PDF links
    main_m = re.search(r"<main\b[^>]*>(.*?)</main>", raw_html, flags=re.DOTALL | re.IGNORECASE)
    target_html = main_m.group(1) if main_m else raw_html
    snippet = _strip_html(target_html, max_len=5000)

    # Check if snippet actually mentions the date or event keywords when date_vars are specified
    has_signal = True
    if date_vars["iso"]:
        has_signal = any(
            d in snippet
            for d in (date_vars["jp"] | date_vars["iso"] | date_vars["slash_mmdd"] | date_vars["dot"])
        ) or any(k.lower() in snippet.lower() for k in kw_tokens[:4])

    links = re.findall(
        r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>',
        target_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for href, ltxt in links:
        full_u = urllib.parse.urljoin(base_url, html.unescape(href).strip())
        decoded_u = urllib.parse.unquote(full_u)
        lbl = _strip_html(ltxt, max_len=120) or decoded_u.split("/")[-1]
        if date_vars["compact_mmdd"]:
            if not (
                any(mmdd in decoded_u for mmdd in date_vars["compact_mmdd"])
                or any(k.lower() in (lbl + " " + decoded_u).lower() for k in kw_tokens[:4])
            ):
                continue
        if _is_final_race_label(lbl, decoded_u):
            pdf_items.append({"label": lbl, "url": full_u})

    if has_signal and snippet:
        summaries.append(f"■ 公式リザルトページ ({base_url}) 抽出データ:\n  {snippet[:3500]}")

    return summaries, pdf_items


def _extract_or_transcribe_pdf(
    pdf_url: str,
    label: str,
    client: Any = None,
) -> str:
    """
    Download an official race result PDF and extract exact classification text:
      1. Try deterministic digital PDF extraction (`pypdf`) first.
      2. If scanned image PDF (e.g. SPA Naoiri / Autopolis signed timing sheets)
         or `pypdf` is unavailable, transcribe verbatim via Gemini (`application/pdf`).
    """
    try:
        _, _, raw_pdf = _fetch_url_bytes(pdf_url, timeout=14)
    except Exception as exc:
        return f"[PDF Fetch Failed ({type(exc).__name__}): {pdf_url}]"

    if not raw_pdf or not raw_pdf.startswith(b"%PDF"):
        return ""

    extracted_txt = ""
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(raw_pdf))
        pages: list[str] = []
        for p in reader.pages[:5]:
            t = (p.extract_text() or "").strip()
            if t:
                pages.append(t)
        extracted_txt = "\n".join(pages).strip()
    except Exception:
        extracted_txt = ""

    # Digital PDF with rich text (e.g., MyLaps Orbits exports on HSR Kyushu / Okayama / Suzuka)
    if len(extracted_txt) >= 80:
        compact = re.sub(r"[ \t]+", " ", extracted_txt)
        compact = re.sub(r"\n{3,}", "\n\n", compact)
        return f"【公式決勝リザルトPDF全文抽出: {label} ({pdf_url})】\n{compact[:6000]}"

    # Scanned image PDF (e.g., SPA Naoiri / Autopolis signed official sheets) -> Gemini multimodal transcription
    if client is None:
        return f"【公式決勝リザルトPDF確認済（スキャンPDF）: {label} ({pdf_url})】"

    prompt_txt = (
        f"This is an official motorcycle race result sheet PDF from `{pdf_url}` ({label}).\n"
        "Transcribe the EXACT factual race results from this official sheet without guessing or omitting anything:\n"
        "- Event Name, Date, Circuit, Class Name, Laps, Weather / Temperature / Track Condition, Starters / Finishers\n"
        "- Top 10 (or all finishers if <=15) in exact order: Pos, No., Rider Name(s), Team Name, Machine/Model, Laps, Total Time, Gap, Best Lap\n"
        "- Fastest Lap holder, lap time, speed, and any official penalties or DNF/DNS notes.\n"
        "Output plain structured text in Japanese preserving exact numbers and names."
    )

    # Primary: Interactions API with DocumentContentParam (`type: "document"`, `mime_type: "application/pdf"`)
    try:
        b64_pdf = base64.b64encode(raw_pdf).decode("ascii")
        interaction = client.interactions.create(
            model="gemini-3.8-flash",
            input=[
                {"type": "text", "text": prompt_txt},
                {
                    "type": "document",
                    "mime_type": "application/pdf",
                    "data": b64_pdf,
                },
            ],
        )
        out = (interaction.output_text or "").strip()
        if out:
            return f"【公式決勝リザルトPDF高精度読取: {label} ({pdf_url})】\n{out[:6000]}"
    except Exception:
        pass

    # Fallback: models.generate_content with types.Part.from_bytes
    try:
        from google.genai import types

        resp = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[
                types.Part.from_bytes(data=raw_pdf, mime_type="application/pdf"),
                prompt_txt,
            ],
        )
        out2 = (resp.text or "").strip()
        if out2:
            return f"【公式決勝リザルトPDF高精度読取: {label} ({pdf_url})】\n{out2[:6000]}"
    except Exception as exc:
        return f"【公式決勝リザルトPDF確認済: {label} ({pdf_url}) ※読取エラー: {type(exc).__name__}】"

    return f"【公式決勝リザルトPDF確認済: {label} ({pdf_url})】"


def fetch_circuit_results_for_target(
    search_text: str,
    start_date: str | None = None,
    end_date: str | None = None,
    event_name: str = "",
    series_name: str = "",
    sources_cfg: dict[str, Any] | None = None,
    client: Any = None,
    max_pdfs: int = 6,
) -> dict[str, Any]:
    """
    Explore circuit result page availability for the target event/context, and if
    a circuit result page exists, fetch & parse matching HTML blocks and official
    final result PDFs.

    Returns:
      {
        "circuitsChecked": [ { "circuitId", "name", "hasResultPage", "resultUrls" }, ... ],
        "hasOfficialResultPage": bool,
        "matchedResultsOnPage": bool,
        "verifiedResultUrls": [str, ...],
        "dossierText": str,
      }
    """
    cfg = sources_cfg or load_sources_config()
    matched_circuits = resolve_circuit_result_entries(search_text, cfg)
    date_vars = _build_date_variants(start_date, end_date)
    kw_tokens = _extract_event_keywords(event_name or search_text, series_name)

    circuits_checked: list[dict[str, Any]] = []
    all_summaries: list[str] = []
    all_pdf_items: list[dict[str, str]] = []
    verified_urls: list[str] = []
    has_any_result_page = False

    for c_entry in matched_circuits:
        cid = c_entry.get("circuitId", "")
        cname = c_entry.get("name", cid)
        has_rp = bool(c_entry.get("hasResultPage", False))
        r_urls = c_entry.get("resultUrls", [])
        fmt = c_entry.get("resultFormat", "generic_pdf_index")

        circuits_checked.append(
            {
                "circuitId": cid,
                "name": cname,
                "hasResultPage": has_rp,
                "resultUrls": r_urls,
            }
        )

        if not has_rp or not r_urls:
            all_summaries.append(f"ℹ️ [{cname}] サーキット固有の2輪リザルト一覧ページなし（主催者公式サイト・公式SNSを参照）")
            continue

        has_any_result_page = True
        if fmt == "official_web_search":
            for u in r_urls:
                if u not in verified_urls:
                    verified_urls.append(u)
            all_summaries.append(f"ℹ️ [{cname}] 公式リザルトURL: {', '.join(r_urls)}")
            continue

        # Suzuka & Motegi date-prefixed PDF directories
        if fmt in ("suzuka_pdf", "motegi_pdf"):
            sums, pdfs = _parse_suzuka_or_motegi_pdfs(cid, r_urls[0], "", date_vars, search_text)
            if sums:
                all_summaries.extend(sums)
                if r_urls[0] not in verified_urls:
                    verified_urls.append(r_urls[0])
            all_pdf_items.extend(pdfs)
            continue

        for r_url in r_urls:
            try:
                final_u, raw_html = _fetch_html(r_url, timeout=12)
            except Exception as exc:
                all_summaries.append(f"⚠️ [{cname}] リザルトページ接続スキップ ({r_url}): {type(exc).__name__}")
                continue

            if fmt == "autopolis_wp_pdf":
                sums, pdfs = _parse_autopolis_spa_sections(raw_html, final_u, date_vars, kw_tokens)
                if sums:
                    all_summaries.extend(sums)
                    if final_u not in verified_urls:
                        verified_urls.append(final_u)
                    all_pdf_items.extend(pdfs)
                    break  # Avoid duplicating between ?kind=2輪 and /result/
            elif fmt == "ms_event_pdf":
                if "result_out1.php" in final_u:
                    sums, pdfs = _parse_okayama_php_results(raw_html, final_u, date_vars, kw_tokens)
                else:
                    sums, pdfs = _parse_ms_event_blocks(raw_html, final_u, date_vars, kw_tokens)
                if sums:
                    all_summaries.extend(sums)
                    if final_u not in verified_urls:
                        verified_urls.append(final_u)
                    all_pdf_items.extend(pdfs)
                    break
            elif fmt == "tsukuba_html_pdf":
                sums, pdfs = _parse_tsukuba_results(raw_html, final_u, date_vars, kw_tokens)
                if sums:
                    all_summaries.extend(sums)
                    if final_u not in verified_urls:
                        verified_urls.append(final_u)
                    all_pdf_items.extend(pdfs)
            elif fmt == "sugo_html_pdf":
                sums, pdfs = _parse_sugo_results(raw_html, final_u, date_vars, kw_tokens)
                if sums:
                    all_summaries.extend(sums)
                    if final_u not in verified_urls:
                        verified_urls.append(final_u)
                    all_pdf_items.extend(pdfs)
            else:
                sums, pdfs = _parse_generic_result_page(raw_html, final_u, date_vars, kw_tokens, fmt)
                if sums:
                    all_summaries.extend(sums)
                    if final_u not in verified_urls:
                        verified_urls.append(final_u)
                    all_pdf_items.extend(pdfs)

    # Deduplicate PDF URLs and extract/transcribe up to `max_pdfs` official final sheets
    unique_pdfs: list[dict[str, str]] = []
    seen_pdf_urls: set[str] = set()
    for p in all_pdf_items:
        u = p["url"]
        if u not in seen_pdf_urls:
            seen_pdf_urls.add(u)
            unique_pdfs.append(p)

    pdf_transcriptions: list[str] = []
    for p in unique_pdfs[:max_pdfs]:
        if p["url"] not in verified_urls:
            verified_urls.append(p["url"])
        txt = _extract_or_transcribe_pdf(p["url"], p["label"], client=client)
        if txt:
            pdf_transcriptions.append(txt)

    matched_on_page = bool(unique_pdfs) or any(
        s.startswith("■ ") for s in all_summaries
    )

    dossier_parts: list[str] = []
    if circuits_checked:
        dossier_parts.append("【サーキット別公式リザルトページ探索結果】")
        for cc in circuits_checked:
            status_lbl = (
                f"公式リザルトページあり ({', '.join(cc['resultUrls'])})"
                if cc["hasResultPage"]
                else "サーキット専用リザルトページなし（主催者発表参照）"
            )
            dossier_parts.append(f"- {cc['name']}: {status_lbl}")

    if all_summaries:
        dossier_parts.append("\n".join(all_summaries))
    if pdf_transcriptions:
        dossier_parts.append("\n\n".join(pdf_transcriptions))

    return {
        "circuitsChecked": circuits_checked,
        "hasOfficialResultPage": has_any_result_page,
        "matchedResultsOnPage": matched_on_page,
        "verifiedResultUrls": verified_urls,
        "dossierText": "\n\n".join(dossier_parts).strip(),
    }


def fetch_event_circuit_results(
    ev: dict[str, Any],
    sources_cfg: dict[str, Any] | None = None,
    client: Any = None,
    max_pdfs: int = 6,
) -> dict[str, Any]:
    """Fetch official circuit result page data for a specific schedule DB event `ev`."""
    search_blob = " ".join(
        [
            ev.get("id", ""),
            ev.get("series", ""),
            ev.get("eventName", {}).get("ja", ""),
            ev.get("eventName", {}).get("en", ""),
            ev.get("circuit", {}).get("ja", ""),
            ev.get("circuit", {}).get("en", ""),
            ev.get("officialWebUrl", ""),
            ev.get("circuitWebUrl", ""),
        ]
    )
    return fetch_circuit_results_for_target(
        search_text=search_blob,
        start_date=ev.get("startDate"),
        end_date=ev.get("endDate"),
        event_name=ev.get("eventName", {}).get("ja", ""),
        series_name=ev.get("series", ""),
        sources_cfg=sources_cfg,
        client=client,
        max_pdfs=max_pdfs,
    )
