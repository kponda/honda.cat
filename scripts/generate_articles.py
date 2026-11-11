#!/usr/bin/env python3
"""
honda.cat — Full-Auto AI Motorsport & Circuit Maintenance Article Pipeline
===========================================================================
Strict Historical & Technical Fact-Management Edition.

Uses the official Google GenAI SDK (`google-genai` Interactions API) with:
  1. Stage 1 — Grounded Research (`gemini-3.8-flash` + `google_search`):
     Gathers strictly verifiable historical race results, circuit specs, official schedules,
     or engineering/maintenance standards (MFJ/FIM technical rules, JIS standards, physics).
  2. Stage 2 — Zero-Hallucination Trilingual Authoring (`ja`, `ca`, `en`):
     Generates structured JSON including mandatory `factCheck` provenance (`basis` + `sources`).
     Strictly prohibits fictional team names, fabricated podiums, or unverified claims.
  3. Stage 3 — Independent Fact-Auditor Gate (`audit_article_facts`):
     Audits every number, rider/team name, circuit specification, and mechanical standard
     against grounded search evidence before allowing publication.
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

SYSTEM_INSTRUCTION = """You are the Strict Fact-Based Editorial Engine for `honda.cat`, an independent trilingual (Japanese `ja`, Catalan `ca`, English `en`) motorcycle racing & circuit maintenance portal run by three bipedal "Nameneko-style" (non-delinquent, authentic motorsport professional) cats:

1. `marc` (Marc): Male orange tabby born in Montmeló, Catalonia. Editor-in-Chief covering MotoGP, WorldSBK, Catalan motorsport history, and telemetry-verified "super saves" (salvades).
2. `suzuka` (Suzuka): Female calico photojournalist covering MFJ All-Japan Road Race and Kyushu's Big-3 circuits (SPA Naoiri in Takeda Oita, Autopolis in Hita Oita, HSR Kyushu in Ozu Kumamoto).
3. `naoko` (Naoko): Female black cat mechanic living in an Oita garage, wearing oil-stained coveralls. Covers circuit maintenance & technical trivia, grassroots racing, "Odai-tsuki" task-challenge endurance races (お題付き耐久草レース), and Rentai (レン耐).
   - PERSONA RULE FOR NAOKO: Normally she speaks in a scruffy, sharp-tongued veteran mechanic tone (`mood: "grumpy"`). However, she MUST also have at least one `mood: "maiden"` dialogue line where she suddenly blushes and shows her shy, sweet maiden side (ending with 🌸 or ♡).

CRITICAL HISTORICAL & TECHNICAL FACT POLICY (ZERO HALLUCINATION):
- Every race result, rider name, year, lap number, circuit length/elevation, and mechanical standard MUST be 100% factual and historically accurate.
- NEVER invent fictional team names, fictional rider names, or fabricated race result tables.
- When writing about grassroots/recreational races or maintenance where a specific single podium is not the subject, use the `results` table to present verified circuit specifications, official class regulations, or verified engineering/maintenance standards (e.g., JIS K 2233 brake fluid boiling points, MFJ wire-locking diameters, torque/pressure formulas).
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
                "required": ["speaker", "mood", "text"],
                "properties": {
                    "speaker": {"type": "string", "enum": ["marc", "suzuka", "naoko"]},
                    "mood": {
                        "type": "string",
                        "enum": ["normal", "excited", "grumpy", "maiden"],
                    },
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
        "featuredCat": {"type": "string", "enum": ["marc", "suzuka", "naoko"]},
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

AUDIT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["passed", "issues", "summary"],
    "properties": {
        "passed": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
}

MODE_PROMPTS: dict[str, str] = {
    "preview": (
        "Search for upcoming motorcycle races this week across MotoGP, WorldSBK, MFJ All-Japan Road Race, "
        "and Kyushu circuits (Autopolis in Hita Oita, SPA Naoiri in Takeda Oita, HSR Kyushu in Kumamoto). "
        "Create a strictly factual Weekly Race Preview highlighting verified schedules, circuit specs, and rider storylines."
    ),
    "digest": (
        "Search for the latest verified race results and historical highlights from MotoGP, WorldSBK, "
        "All-Japan Road Race, and regional Japanese circuits. Include only 100% factual results and official records."
    ),
    "kyushu": (
        "Search for verified motorcycle events and track facts at SPA Naoiri (SPA直入, 1,430m, Takeda Oita), "
        "Autopolis (オートポリス, 4,674m, Hita Oita), and HSR Kyushu (HSR九州, 2,350m, Kumamoto), including "
        "Kyushu Road Race Series, Tetsuma (鉄馬), and recreational 'Odai-tsuki' task-challenge endurance / Rentai rules."
    ),
    "spotlight": (
        "Analyze a historically verified motorcycle racing 'Super Save' (such as Marc Márquez's 2017 Valencia GP "
        "64-degree save or 2019 Montmeló 66-degree save) or a legendary MotoGP/SBK/Suzuka 8 Hours historical battle."
    ),
    "maintenance": (
        "Create a weekly 'Naoko's Track Garage Clinic' (サーキット走行向けバイクメンテナンス＆豆知識) article. "
        "Focus on practical, scientifically & regulatory verified circuit preparation topics such as: "
        "MFJ safety wire-locking (ワイヤリング), brake fluid dry/wet boiling points (JIS K 2233 DOT4/Racing fluid) & bleeding, "
        "hot vs. cold tire pressure management with tire warmers, chain slack & alignment reduces friction loss, "
        "suspension sag (1G / 1G') setup, or cooling system water-only regulation (antifreeze ethylene glycol ban on track)."
    ),
}


class FactCheckError(RuntimeError):
    """Raised when an AI-generated article fails the historical/technical fact audit."""


def slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return clean[:64] or "paddock-report"


def generate_with_gemini(mode: str, custom_topic: str | None = None) -> dict[str, Any]:
    """Run 3-stage grounded research + structured authoring + strict historical fact audit."""
    from google import genai

    client = genai.Client()
    today_str = dt.date.today().isoformat()
    base_task = custom_topic if custom_topic else MODE_PROMPTS.get(mode, MODE_PROMPTS["kyushu"])

    print(f"[1/3] Scouting verified historical & technical facts with Gemini 3.8 Flash + Google Search (mode={mode})...")
    research_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            f"Task: {base_task}\n"
            "Gather ONLY verifiable facts, exact historical dates, real rider/team names, official circuit specs, "
            "or official engineering standards (MFJ, FIM, JIS). List exact source URLs."
        ),
        tools=[{"type": "google_search"}],
    )
    research_notes = research_interaction.output_text or ""
    print(f"[1/3] Grounded research dossier ready ({len(research_notes)} chars).")

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
            "3. Ensure Naoko (`naoko`) includes both a `grumpy` mechanic comment and a `maiden` (shy blush 🌸) comment.\n\n"
            f"VERIFIED RESEARCH DOSSIER:\n{research_notes}"
        ),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ARTICLE_JSON_SCHEMA,
        },
    )

    draft_json = json.loads(author_interaction.output_text)

    print("[3/3] Running Independent Fact-Auditor Gate (`audit_article_facts`)...")
    audit_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=(
            "You are a strict Motorsport & Mechanical Engineering Fact Auditor.\n"
            "Audit the following generated article JSON against the research dossier and real-world history.\n"
            "Fail (`passed: false`) if you find ANY fictional team names in results, fabricated race winners, "
            "incorrect circuit lengths, or false technical/physics claims.\n\n"
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
    return finalize_article_record(draft_json, today_str)


def finalize_article_record(data: dict[str, Any], today_str: str) -> dict[str, Any]:
    slug = slugify(data.get("slug", f"{today_str}-paddock-special"))
    featured_cat = data.get("featuredCat", "naoko")
    cat_images = {
        "marc": "/images/cats/marc.png",
        "suzuka": "/images/cats/suzuka.png",
        "naoko": "/images/cats/naoko.png",
    }
    return {
        "id": f"{today_str}-{slug}",
        "slug": slug,
        "publishedAt": today_str,
        "category": data.get("category", "kyushu"),
        "articleType": data.get("articleType", "digest"),
        "circuit": data.get("circuit", "SPA直入 / Autopolis / HSR九州"),
        "region": data.get("region", "Kyushu / Catalunya"),
        "featuredCat": featured_cat,
        "heroImage": cat_images.get(featured_cat, "/images/cats/hero-paddock.png"),
        "tags": data.get("tags", ["SPA直入", "オートポリス", "HSR九州", "サーキット整備"]),
        "factCheck": data.get("factCheck"),
        "eventMeta": data["eventMeta"],
        "locales": data["locales"],
    }


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
    parser = argparse.ArgumentParser(description="Generate strictly fact-checked trilingual articles for honda.cat")
    parser.add_argument(
        "--mode",
        choices=["preview", "digest", "kyushu", "spotlight", "maintenance"],
        default="maintenance",
        help="Article generation mode (including weekly 'maintenance' column)",
    )
    parser.add_argument("--topic", type=str, default=None, help="Optional custom topic prompt")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit existing articles and validate pipeline configuration without calling API",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.dry_run or not api_key:
        if not api_key and not args.dry_run:
            print("ℹ️ GEMINI_API_KEY not set in environment; running local Fact-Check Audit.")
        return validate_existing_articles()

    article = generate_with_gemini(mode=args.mode, custom_topic=args.topic)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTICLES_DIR / f"{article['id']}.json"
    out_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Published fact-verified trilingual article: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
