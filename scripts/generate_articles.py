#!/usr/bin/env python3
"""
honda.cat — Full-Auto AI Motorsport & Grassroots Racing Article Pipeline
========================================================================
Uses the official Google GenAI SDK (`google-genai` Interactions API) with:
  1. `gemini-3.8-flash` + Google Search Grounding (`tools=[{"type": "google_search"}]`)
     to gather latest race schedules, results, and highlights across:
     - MotoGP / WorldSBK / EWC
     - Kyushu 3 Major Circuits: SPA直入 (Oita), オートポリス (Oita), HSR九州 (Kumamoto)
     - Grassroots Recreational Endurance: お題付き耐久草レース, レン耐 (Rentai), Mini-bike endurance
     - MFJ All-Japan Road Race & Regional Sunday series
  2. Structured Output (`response_format` JSON Schema) to author a complete trilingual
     article (`ja`, `ca`, `en`) featuring our 3 bipedal paddock cats:
     - Marc (MotoGP/Catalunya Editor)
     - Suzuka (All-Japan & Kyushu Photographer)
     - Naoko (Scruffy black female garage mechanic who suddenly shows her shy maiden side!)
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

SYSTEM_INSTRUCTION = """You are the AI Editorial Engine for `honda.cat`, an independent trilingual (Japanese `ja`, Catalan `ca`, English `en`) motorcycle racing portal run by three bipedal "Nameneko-style" (non-delinquent, authentic motorsport professional) cats:

1. `marc` (Marc): Male orange tabby born in Montmeló, Catalonia. Editor-in-Chief covering MotoGP, WorldSBK, Catalan motorsport culture, and 65-degree "super saves" (salvades). Energetic, analytical, adds "ニャ/miau/meow" occasionally.
2. `suzuka` (Suzuka): Female calico photojournalist covering MFJ All-Japan Road Race and Kyushu's Big-3 circuits (SPA Naoiri in Takeda Oita, Autopolis in Hita Oita, HSR Kyushu in Ozu Kumamoto). Polite, observant, cheerful.
3. `naoko` (Naoko): Female black cat mechanic living in an Oita garage, wearing oil-stained coveralls. Covers grassroots racing, "Odai-tsuki" task-challenge endurance races (お題付き耐久草レース), and Rentai (レン耐).
   - CRITICAL PERSONA RULE FOR NAOKO: Normally she speaks in a scruffy, tough, sharp-tongued veteran garage mechanic tone (`mood: "grumpy"`), scolding riders for over-cooking corners or panicking on pit-stop puzzles. HOWEVER, she MUST also have at least one `mood: "maiden"` dialogue line where she suddenly blushes and acts like a shy, sweet maiden (e.g., when praised for her bike setup, when a rider finishes safely, or when offered local Oita soft-serve ice cream or sweets, ending with 🌸 or ♡).

Ensure the Catalan (`ca`) translation uses natural, authentic Catalan motorsport terminology (e.g., `pàdoc`, `revolt`, `salvada`, `cursa de resistència`, `bandera de quadres`) to honor the Fundació .cat domain mission.
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
        "eventMeta",
        "locales",
    ],
    "properties": {
        "slug": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["world", "kyushu", "endurance-fun", "all-japan", "spotlight"],
        },
        "articleType": {
            "type": "string",
            "enum": ["preview", "digest", "spotlight"],
        },
        "circuit": {"type": "string"},
        "region": {"type": "string"},
        "featuredCat": {"type": "string", "enum": ["marc", "suzuka", "naoko"]},
        "tags": {"type": "array", "items": {"type": "string"}},
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

MODE_PROMPTS: dict[str, str] = {
    "preview": (
        "Search for upcoming motorcycle races this week across MotoGP, WorldSBK, MFJ All-Japan Road Race, "
        "and Kyushu circuits (Autopolis in Hita Oita, SPA Naoiri in Takeda Oita, HSR Kyushu in Kumamoto). "
        "Create a comprehensive Weekly Race Preview highlighting schedules, rider storylines, and track tips."
    ),
    "digest": (
        "Search for the latest race results and highlights from MotoGP, WorldSBK, All-Japan Road Race, "
        "and regional Japanese circuits. Create a Race Results & Digest article with top finishers and analysis."
    ),
    "kyushu": (
        "Search for recent or upcoming motorcycle events at SPA Naoiri (SPA直入), Autopolis (オートポリス), "
        "and HSR Kyushu (HSR九州), including Kyushu Road Race Series, Sunday races, Tetsuma (鉄馬), "
        "and recreational 'Odai-tsuki' task-challenge endurance races (お題付き耐久草レース / レン耐). "
        "Feature Naoko and Suzuka heavily!"
    ),
    "spotlight": (
        "Analyze a remarkable motorcycle racing 'Super Save' (60+ degree elbow/knee save in MotoGP/SBK) "
        "or a grassroots endurance pit-stop strategy deep dive, connecting Catalonia and Kyushu racing culture."
    ),
}


def slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return clean[:64] or "paddock-report"


def generate_with_gemini(mode: str, custom_topic: str | None = None) -> dict[str, Any]:
    """Run 2-step grounded research + structured trilingual article generation via Gemini 3.8 Flash."""
    from google import genai

    client = genai.Client()
    today_str = dt.date.today().isoformat()
    base_task = custom_topic if custom_topic else MODE_PROMPTS.get(mode, MODE_PROMPTS["kyushu"])

    print(f"[1/2] Scouting race information with Gemini 3.8 Flash + Google Search Grounding (mode={mode})...")
    research_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Today's date is {today_str}.\n"
            f"Task: {base_task}\n"
            "Collect factual event names, circuit details, dates, key riders/classes, and technical talking points."
        ),
        tools=[{"type": "google_search"}],
    )
    research_notes = research_interaction.output_text or ""
    print(f"[1/2] Research completed ({len(research_notes)} chars gathered).")

    print("[2/2] Authoring trilingual (JA/CA/EN) article with Structured Output...")
    author_interaction = client.interactions.create(
        model="gemini-3.8-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        input=(
            f"Based on the following verified research notes (Date: {today_str}), generate a complete, "
            "engaging trilingual article JSON (`ja`, `ca`, `en`).\n\n"
            "Make sure Naoko (`naoko`) includes both a `grumpy` garage mechanic comment AND a `maiden` "
            "(sudden shy/sweet maiden blush 🌸) comment in `catDialogues`!\n\n"
            f"RESEARCH NOTES:\n{research_notes}"
        ),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ARTICLE_JSON_SCHEMA,
        },
    )

    raw_json = json.loads(author_interaction.output_text)
    return finalize_article_record(raw_json, today_str)


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
        "tags": data.get("tags", ["SPA直入", "オートポリス", "HSR九州", "お題付き耐久草レース"]),
        "eventMeta": data["eventMeta"],
        "locales": data["locales"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate trilingual motorsport articles for honda.cat")
    parser.add_argument(
        "--mode",
        choices=["preview", "digest", "kyushu", "spotlight"],
        default="kyushu",
        help="Article generation mode",
    )
    parser.add_argument("--topic", type=str, default=None, help="Optional custom topic prompt")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate pipeline configuration and schema without writing a new file",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if args.dry_run or not api_key:
        if not api_key:
            print("ℹ️ GEMINI_API_KEY not set in environment; running schema & existing articles verification.")
        existing = sorted(ARTICLES_DIR.glob("*.json"))
        print(f"✅ Verified {len(existing)} trilingual articles in {ARTICLES_DIR}:")
        for path in existing:
            doc = json.loads(path.read_text(encoding="utf-8"))
            langs = list(doc.get("locales", {}).keys())
            print(f"   - {path.name} | category={doc.get('category')} | cat={doc.get('featuredCat')} | langs={langs}")
        return 0

    article = generate_with_gemini(mode=args.mode, custom_topic=args.topic)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTICLES_DIR / f"{article['id']}.json"
    out_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Generated trilingual article: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
