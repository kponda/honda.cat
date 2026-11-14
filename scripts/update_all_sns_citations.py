#!/usr/bin/env python3
"""
scripts/update_all_sns_citations.py
--------------------------------------------------------------------------------
Upgrades ALL articles in `src/data/articles/*.json` so every article (both
MotoGP/WorldSBK and Japanese domestic/Kyushu/grassroots/maintenance) features
1-2 unique, deterministically verified, photo-attached X posts (`direct_post`
with `/status/{id}` and `mediaUrls` containing `https://pbs.twimg.com/...`).

Preserves existing verified non-X citations (`YouTube`, `OfficialWeb`, etc.)
while replacing old hashtag-only, duplicated, or 404 X citations.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import x_photo_finder  # noqa: E402

ARTICLES_DIR = SCRIPT_DIR.parent / "src" / "data" / "articles"
TRANSLATION_CACHE_PATH = SCRIPT_DIR / ".cache_x_translations.json"

# Per-slug targeted query hints for maximal historical & topic precision
SLUG_QUERY_OVERRIDES: dict[str, dict[str, Any]] = {
    # --- WorldSBK ---
    "2026-02-23-worldsbk-rd1-phillip-island-bulega-sweep-digest": {
        "web": ["site:x.com/WorldSBK Phillip Island 2026", "site:x.com/ArubaRacing Phillip Island 2026", "site:x.com WorldSBK Phillip Island Bulega 2026"],
        "rt": ["WorldSBK Phillip Island", "WorldSBK Bulega"],
        "kw": ["Phillip Island", "AustralianWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-03-30-worldsbk-rd2-portimao-bulega-lecuona-digest": {
        "web": ["site:x.com/WorldSBK Portimao 2026", "site:x.com/ArubaRacing Portimao 2026", "site:x.com WorldSBK Portimao Bulega 2026"],
        "rt": ["WorldSBK Portimao", "WorldSBK"],
        "kw": ["Portimao", "PRTWorldSBK", "Bulega", "Lecuona", "WorldSBK"],
    },
    "2026-04-20-worldsbk-assen-dutch-round-bulega-treble-digest": {
        "web": ["site:x.com/ArubaRacing Assen 2026", "site:x.com/WorldSBK Assen 2026", "site:x.com DutchWorldSBK 2026"],
        "rt": ["WorldSBK Assen"],
        "kw": ["Assen", "DutchWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-05-04-worldsbk-rd4-balaton-park-bulega-record12wins-digest": {
        "web": ["site:x.com/WorldSBK Balaton 2026", "site:x.com/ArubaRacing Balaton 2026", "site:x.com WorldSBK Hungary 2026"],
        "rt": ["WorldSBK Balaton", "WorldSBK Hungary"],
        "kw": ["Balaton", "Hungary", "HUNWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-05-18-worldsbk-rd5-most-bulega-streak-czech-digest": {
        "web": ["site:x.com/WorldSBK Most 2026", "site:x.com/ArubaRacing Most 2026", "site:x.com CzechWorldSBK 2026"],
        "rt": ["WorldSBK Most", "WorldSBK Czech"],
        "kw": ["Most", "CzechWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-06-01-worldsbk-rd6-aragon-bulega-hattrick-digest": {
        "web": ["site:x.com/WorldSBK Aragon 2026", "site:x.com/ArubaRacing Aragon 2026", "site:x.com AragonWorldSBK 2026"],
        "rt": ["WorldSBK Aragon"],
        "kw": ["Aragon", "AragonWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-06-15-worldsbk-misano-bulega-treble-digest": {
        "web": ["site:x.com/WorldSBK Misano 2026", "site:x.com/ArubaRacing Misano 2026", "site:x.com EmiliaRomagnaWorldSBK 2026"],
        "rt": ["WorldSBK Misano"],
        "kw": ["Misano", "EmiliaRomagnaWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-07-13-worldsbk-rd8-donington-lecuona-maiden-win-bulega-digest": {
        "web": ["site:x.com/WorldSBK Donington 2026", "site:x.com/ArubaRacing Donington 2026", "site:x.com UKWorldSBK 2026"],
        "rt": ["WorldSBK Donington"],
        "kw": ["Donington", "UKWorldSBK", "Lecuona", "Bulega", "WorldSBK"],
    },
    "2026-09-07-worldsbk-rd9-magny-cours-bulega-10th-pole-treble-digest": {
        "web": ["site:x.com/WorldSBK Magny-Cours 2026", "site:x.com/ArubaRacing Magny-Cours 2026", "site:x.com FrenchWorldSBK 2026"],
        "rt": ["WorldSBK Magny-Cours", "WorldSBK France"],
        "kw": ["Magny", "FrenchWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-09-28-worldsbk-rd10-cremona-bulega-champion-lecuona-win-digest": {
        "web": ["site:x.com/WorldSBK Cremona 2026", "site:x.com/ArubaRacing Cremona 2026", "site:x.com ItalianWorldSBK 2026"],
        "rt": ["WorldSBK Cremona"],
        "kw": ["Cremona", "ItalianWorldSBK", "Bulega", "Lecuona", "WorldSBK"],
    },
    "2026-10-12-worldsbk-rd11-estoril-bulega-record-points-hattrick-digest": {
        "web": ["site:x.com/WorldSBK Estoril 2026", "site:x.com/ArubaRacing Estoril 2026", "site:x.com EstorilWorldSBK 2026"],
        "rt": ["WorldSBK Estoril"],
        "kw": ["Estoril", "EstorilWorldSBK", "Bulega", "WorldSBK"],
    },
    "2026-10-19-worldsbk-rd12-jerez-finale-bulega-32wins-wet-digest": {
        "web": ["site:x.com/WorldSBK Jerez 2026", "site:x.com/ArubaRacing Jerez 2026", "site:x.com SpanishWorldSBK 2026"],
        "rt": ["WorldSBK Jerez", "WorldSBK スペイン"],
        "kw": ["Jerez", "SpanishWorldSBK", "Bulega", "WorldSBK"],
    },
    # --- MotoGP ---
    "2026-04-27-motogp-rd4-jerez-alex-marquez-victory-digest": {
        "web": ["site:x.com/MotoGP Jerez 2026", "site:x.com MotoGP Jerez Alex Marquez 2026", "site:x.com #SpanishGP MotoGP 2026"],
        "rt": ["MotoGP Jerez"],
        "kw": ["Jerez", "SpanishGP", "Alex Marquez", "MotoGP"],
    },
    "2026-05-11-motogp-rd5-lemans-martin-ogura-podium-digest": {
        "web": ["site:x.com/MotoGP Le Mans 2026", "site:x.com MotoGP Le Mans Ogura 2026", "site:x.com #FrenchGP MotoGP 2026"],
        "rt": ["MotoGP Le Mans", "MotoGP 小椋藍"],
        "kw": ["Le Mans", "FrenchGP", "Ogura", "Martin", "MotoGP"],
    },
    "2026-05-18-motogp-rd6-catalunya-digiannantonio-aldeguer-digest": {
        "web": ["site:x.com/MotoGP Catalunya 2026", "site:x.com/Circuitcat_cat MotoGP 2026", "site:x.com #CatalanGP MotoGP 2026"],
        "rt": ["MotoGP Catalunya", "Circuitcat MotoGP"],
        "kw": ["Catalunya", "CatalanGP", "Montmelo", "Di Giannantonio", "MotoGP"],
    },
    "2026-06-01-motogp-rd7-mugello-bezzecchi-raul-fernandez-digest": {
        "web": ["site:x.com/MotoGP Mugello 2026", "site:x.com MotoGP Mugello Bezzecchi 2026", "site:x.com #ItalianGP MotoGP 2026"],
        "rt": ["MotoGP Mugello"],
        "kw": ["Mugello", "ItalianGP", "Bezzecchi", "MotoGP"],
    },
    "2026-06-08-motogp-rd8-hungary-balaton-marquez-sweep-digest": {
        "web": ["site:x.com/MotoGP Balaton 2026", "site:x.com MotoGP Hungary Balaton 2026", "site:x.com #HungarianGP MotoGP 2026"],
        "rt": ["MotoGP Balaton", "MotoGP Hungary"],
        "kw": ["Balaton", "HungarianGP", "Hungary", "Marquez", "MotoGP"],
    },
    "2026-06-22-motogp-rd9-brno-marquez-ogura-bagnaia-digest": {
        "web": ["site:x.com/MotoGP Brno 2026", "site:x.com MotoGP Brno Czech 2026", "site:x.com #CzechGP MotoGP 2026"],
        "rt": ["MotoGP Brno"],
        "kw": ["Brno", "CzechGP", "Marquez", "Ogura", "MotoGP"],
    },
    "2026-06-29-motogp-rd10-assen-ai-ogura-maiden-win-digest": {
        "web": ["site:x.com/MotoGP Assen Ogura 2026", "site:x.com MotoGP Assen Ai Ogura 2026", "site:x.com #DutchGP MotoGP 2026"],
        "rt": ["MotoGP Assen Ogura", "小椋藍 MotoGP"],
        "kw": ["Assen", "DutchGP", "Ogura", "小椋", "MotoGP"],
    },
    "2026-07-13-motogp-rd11-sachsenring-marquez-fernandez-ogura-digest": {
        "web": ["site:x.com/MotoGP Sachsenring 2026", "site:x.com MotoGP Sachsenring Marquez 2026", "site:x.com #GermanGP MotoGP 2026"],
        "rt": ["MotoGP Sachsenring"],
        "kw": ["Sachsenring", "GermanGP", "Marquez", "MotoGP"],
    },
    "2026-08-10-motogp-rd12-silverstone-raul-fernandez-aprilia-123-digest": {
        "web": ["site:x.com/MotoGP Silverstone 2026", "site:x.com MotoGP Silverstone Fernandez 2026", "site:x.com #BritishGP MotoGP 2026"],
        "rt": ["MotoGP Silverstone"],
        "kw": ["Silverstone", "BritishGP", "Fernandez", "Aprilia", "MotoGP"],
    },
    "2026-08-31-motogp-rd13-aragon-marquez-acosta-bezzecchi-digest": {
        "web": ["site:x.com/MotoGP Aragon 2026", "site:x.com MotoGP Aragon Marquez 2026", "site:x.com #AragonGP MotoGP 2026"],
        "rt": ["MotoGP Aragon"],
        "kw": ["Aragon", "AragonGP", "Marquez", "Acosta", "MotoGP"],
    },
    "2026-09-14-motogp-rd14-misano-marquez-brothers-1-2-acosta-digest": {
        "web": ["site:x.com/MotoGP Misano 2026", "site:x.com MotoGP Misano Marquez 2026", "site:x.com #SanMarinoGP MotoGP 2026"],
        "rt": ["MotoGP Misano"],
        "kw": ["Misano", "SanMarinoGP", "Marquez", "Acosta", "MotoGP"],
    },
    "2026-09-21-motogp-rd15-austria-pedro-acosta-ktm-home-victory-digest": {
        "web": ["site:x.com/MotoGP Austria Acosta 2026", "site:x.com MotoGP Spielberg Acosta 2026", "site:x.com #AustrianGP MotoGP 2026"],
        "rt": ["MotoGP Austria Acosta"],
        "kw": ["Austria", "AustrianGP", "Spielberg", "Acosta", "KTM", "MotoGP"],
    },
    "2026-10-05-motogp-rd16-japan-motegi-marc-marquez-2026-champion-digest": {
        "web": ["site:x.com/MotoGP Motegi 2026", "site:x.com/motegi_official MotoGP 2026", "site:x.com MotoGP 日本GP もてぎ 2026"],
        "rt": ["MotoGP もてぎ", "MotoGP Japan Motegi"],
        "kw": ["Motegi", "JapaneseGP", "もてぎ", "日本GP", "Marquez", "MotoGP"],
    },
    "2026-10-12-motogp-rd17-indonesia-mandalika-bezzecchi-aprilia-123-digest": {
        "web": ["site:x.com/MotoGP Mandalika 2026", "site:x.com MotoGP Mandalika Bezzecchi 2026", "site:x.com #IndonesianGP MotoGP 2026"],
        "rt": ["MotoGP Mandalika", "IndonesianGP"],
        "kw": ["Mandalika", "IndonesianGP", "Bezzecchi", "Aprilia", "MotoGP"],
    },
    "2026-10-26-motogp-rd18-australia-phillip-island-marquez-sprint-weather-digest": {
        "web": ["site:x.com/MotoGP Phillip Island 2026", "site:x.com MotoGP AustralianGP 2026", "site:x.com #AustralianGP MotoGP 2026"],
        "rt": ["MotoGP Phillip Island", "AustralianGP"],
        "kw": ["Phillip Island", "AustralianGP", "Sprint", "Marquez", "MotoGP"],
    },
    "2026-11-02-motogp-rd19-malaysia-sepang-marquez-acosta-alex-digest": {
        "web": ["site:x.com/MotoGP Sepang 2026", "site:x.com MotoGP MalaysianGP 2026", "site:x.com #MalaysianGP MotoGP 2026"],
        "rt": ["MotoGP Sepang", "MalaysianGP", "id:MotoGP Sepang"],
        "kw": ["Sepang", "MalaysianGP", "Marquez", "Acosta", "MotoGP"],
    },
    "2026-11-09-motogp-rd20-qatar-lusail-bezzecchi-marquez-fernandez-digest": {
        "web": ["site:x.com/MotoGP Qatar Lusail 2026", "site:x.com #QatarGP MotoGP 2026"],
        "rt": ["id:MotoGP Qatar", "id:MotoGP Lusail", "QatarGP Bezzecchi"],
        "kw": ["QatarGP", "Lusail", "Bezzecchi", "Marquez", "MotoGP"],
    },
    "2026-11-12-motogp-season-closing-double-header-portimao-valencia-preview": {
        "web": ["site:x.com/MotoGP Portimao 2026", "site:x.com #PortugueseGP MotoGP 2026"],
        "rt": ["id:MotoGP Portimao", "id:MotoGP PortugueseGP", "MotoGP ポルトガルGP"],
        "kw": ["Portimao", "PortugueseGP", "Valencia", "MotoGP"],
    },
    # --- All-Japan ---
    "2026-04-06-mfj-rd1-motegi-2and4-jsb1000-digest": {
        "web": ["site:x.com/MFJ_JRR もてぎ 2026", "site:x.com/motegi_official 2&4 2026", "site:x.com 全日本ロードレース もてぎ 2&4 2026"],
        "rt": ["全日本ロードレース もてぎ", "全日本ロードレース 水野涼"],
        "kw": ["もてぎ", "2&4", "JSB1000", "水野", "長島", "國井", "全日本ロード"],
    },
    "2026-04-27-mfj-rd2-sugo-and-suzuka-sunday-digest": {
        "web": ["site:x.com/MFJ_JRR SUGO 2026", "site:x.com 全日本ロードレース SUGO 2026", "site:x.com 鈴鹿サンデーロードレース 2026"],
        "rt": ["全日本ロードレース SUGO", "鈴鹿サンデーロードレース"],
        "kw": ["SUGO", "全日本ロード", "JSB1000", "水野", "鈴鹿サンデー"],
    },
    "2026-06-08-suzuka-motegi-regional-and-spa-naoiri-presummer-digest": {
        "web": ["site:x.com 鈴鹿サンデーロードレース 2026", "site:x.com もてぎロードレース選手権 2026", "site:x.com/suzuka_event サンデー 2026"],
        "rt": ["鈴鹿サンデーロードレース", "もてぎロードレース"],
        "kw": ["鈴鹿サンデー", "もてぎロード", "SPA直入", "ロードレース"],
    },
    "2026-06-22-mfj-rd4-tsukuba-jgp3-ono-wakamatsu-and-hsr-kyushu-digest": {
        "web": ["site:x.com/MFJ_JRR 筑波 2026", "site:x.com/tsukuba_circuit 全日本 2026", "site:x.com 全日本ロードレース 筑波 J-GP3 2026"],
        "rt": ["全日本ロードレース 筑波", "J-GP3 筑波"],
        "kw": ["筑波", "J-GP3", "尾野", "全日本ロード", "HSR九州"],
    },
    "2026-08-31-mfj-rd5-motegi-mizuno-double-hada-fujita-chishiki-digest": {
        "web": ["site:x.com/MFJ_JRR Round5 もてぎ 2026", "site:x.com/motegi_official 第5戦 2026", "site:x.com 全日本ロードレース 第5戦 もてぎ 2026"],
        "rt": ["全日本ロードレース もてぎ", "MFJ_JRR もてぎ"],
        "kw": ["もてぎ", "Round5", "第5戦", "JSB1000", "水野", "羽田", "全日本ロード"],
    },
    "2026-09-28-mfj-rd6-okayama-nagashima-maiden-jsb1000-win-digest": {
        "web": ["site:x.com/MFJ_JRR 岡山 2026", "site:x.com/oic_pr 全日本 2026", "site:x.com 全日本ロードレース 岡山 長島哲太 2026"],
        "rt": ["全日本ロードレース 岡山", "長島哲太 岡山"],
        "kw": ["岡山", "JSB1000", "長島", "國井", "全日本ロード"],
    },
    "2026-10-26-mfj-rd7-suzuka-mfjgp-mizuno-ducati-title-nakasuga-farewell-digest": {
        "web": ["site:x.com/MFJ_JRR 鈴鹿 2026", "site:x.com/suzuka_event MFJグランプリ 2026", "site:x.com MFJグランプリ 水野涼 中須賀 2026"],
        "rt": ["全日本ロードレース MFJグランプリ", "MFJグランプリ 鈴鹿", "水野涼 中須賀"],
        "kw": ["鈴鹿", "MFJ", "グランプリ", "水野", "中須賀", "全日本ロード"],
    },
    # --- Kyushu ---
    "2026-04-13-kyushu-spa-naoiri-sunday-festa-spring-digest": {
        "web": ["site:x.com/spa_naoiri サンデーフェスタ 2026", "site:x.com/spa_naoiri 4月 2026", "site:x.com SPA直入 サンデーフェスタ 2026"],
        "rt": ["SPA直入 サンデーフェスタ", "SPA直入 バイク"],
        "kw": ["SPA直入", "サンデーフェスタ", "バイク", "レース"],
    },
    "2026-05-04-hsr-kyushu-tetsuma-kassen-digest": {
        "web": ["site:x.com/ihdcsupporters 鉄馬 2026", "site:x.com 鉄馬 合戦の日 HSR九州 2026", "site:x.com HSR九州 鉄馬 5月 2026"],
        "rt": ["HSR九州 鉄馬", "鉄馬 合戦の日"],
        "kw": ["HSR九州", "鉄馬", "合戦の日", "TSK"],
    },
    "2026-05-11-polispa-rd1-autopolis-and-tot-satsuki-digest": {
        "web": ["site:x.com/autopolis2005 POLISPA 2026", "site:x.com/tsukuba_circuit テイスト 2026", "site:x.com テイスト・オブ・ツクバ 皐月 2026"],
        "rt": ["オートポリス バイク", "テイストオブツクバ"],
        "kw": ["オートポリス", "POLISPA", "テイスト", "筑波", "ロードレース"],
    },
    "2026-06-01-mfj-rd3-autopolis-kyushu-superbike-digest": {
        "web": ["site:x.com/MFJ_JRR オートポリス 2026", "site:x.com/autopolis2005 全日本ロードレース 2026", "site:x.com 全日本ロードレース オートポリス 2026"],
        "rt": ["全日本ロードレース オートポリス"],
        "kw": ["オートポリス", "全日本ロード", "JSB1000", "水野", "羽田"],
    },
    "2026-07-13-hsr-kyushu-trophy-rd3-and-dreamcup-summer-digest": {
        "web": ["site:x.com HSR九州 Trophy 2026", "site:x.com HSR九州 ドリームカップ 2026", "site:x.com HSR九州 ロードレース 7月 2026"],
        "rt": ["HSR九州 ドリームカップ", "HSR九州 バイク"],
        "kw": ["HSR九州", "Trophy", "ドリームカップ", "ロードレース"],
    },
    "2026-08-24-hsr-kyushu-trophy-rd4-season-finale-digest": {
        "web": ["site:x.com HSR九州 ロードレース 2026", "site:x.com HSR九州 8月 2026 バイク", "site:x.com HSR九州 最終戦 バイク"],
        "rt": ["HSR九州 ロードレース", "HSR九州 バイク"],
        "kw": ["HSR九州", "Trophy", "最終戦", "ロードレース", "バイク"],
    },
    "2026-09-07-polispa-rd3-spa-naoiri-autumn-and-hsr-4h-digest": {
        "web": ["site:x.com/spa_naoiri 2026 9月", "site:x.com/spa_naoiri 2026", "site:x.com HSR九州 4時間耐久 2026"],
        "rt": ["SPA直入", "HSR九州 耐久"],
        "kw": ["SPA直入", "POLISPA", "HSR九州", "耐久", "バイク"],
    },
    "2026-09-21-hsr-kyushu-tetsuma-kessen-no-hi-september-digest": {
        "web": ["site:x.com/ihdcsupporters 決戦の日 2026", "site:x.com 鉄馬 決戦の日 HSR九州 2026", "site:x.com HSR九州 鉄馬 9月 2026"],
        "rt": ["HSR九州 鉄馬 決戦の日", "HSR九州 鉄馬"],
        "kw": ["HSR九州", "鉄馬", "決戦の日"],
    },
    "2026-10-05-polispa-rd4-autopolis-finale-and-sunday-festa-digest": {
        "web": ["site:x.com/autopolis2005 2026 10月", "site:x.com/autopolis2005 ロードレース 2026", "site:x.com オートポリス ゴールドカップ バイク 2026"],
        "rt": ["オートポリス ロードレース", "オートポリス バイク"],
        "kw": ["オートポリス", "POLISPA", "サンデーフェスタ", "ロードレース", "バイク"],
    },
    "2026-11-09-kyushu-endurance-festa-spa-naoiri-and-tot-kaguraduki-digest": {
        "web": ["site:x.com/spa_naoiri 5時間耐久 2026", "site:x.com/tsukuba_circuit 神楽月 2026"],
        "rt": ["テイストオブツクバ 神楽月", "テイストオブツクバ", "SPA直入 耐久", "SPA直入"],
        "kw": ["SPA直入", "耐久", "テイスト", "神楽月", "KAGURADUKI"],
    },
    # --- Endurance & Fun ---
    "2026-05-25-kyushu-odai-r2-nakakyushu-and-rentai-ajimu-digest": {
        "web": ["site:x.com 中九州カートウェイ バイク", "site:x.com/takumagp 2026", "site:x.com レン耐 2026"],
        "rt": ["中九州カートウェイ", "レン耐"],
        "kw": ["中九州", "お題", "レン耐", "安心院", "耐久"],
    },
    "2026-07-06-ewc-rd3-suzuka-8hours-hrc-5peat-takahashi-digest": {
        "web": ["site:x.com/FIM_EWC Suzuka 2026", "site:x.com/suzuka_event 8耐 2026", "site:x.com 鈴鹿8耐 2026 Honda HRC"],
        "rt": ["鈴鹿8耐", "Suzuka 8 Hours"],
        "kw": ["鈴鹿8耐", "8耐", "EWC", "Honda", "HRC", "Suzuka"],
    },
    "2026-10-12-kyushu-brows-odai-r3-sonic-park-ajimu-finale-digest": {
        "web": ["site:x.com/sonicparkajimu 2026", "site:x.com/BROWs0305", "site:x.com お題付耐久"],
        "rt": ["ソニックパーク安心院", "お題付耐久"],
        "kw": ["ソニックパーク安心院", "安心院", "お題", "耐久", "バイク"],
    },
    "2026-11-13-japan-autumn-circuit-endurance-preview-2026-sugo-hsr-okayama-ake": {
        "web": ["site:x.com/takumagp HSR九州 2026", "site:x.com/oic_pr 2026"],
        "rt": ["スポーツランドSUGO バイク", "HSR九州 レン耐", "岡山国際サーキット バイク"],
        "kw": ["SUGO", "HSR九州", "岡山国際", "耐久", "レン耐"],
    },
    # --- Maintenance ---
    "2026-10-07-circuit-maintenance-naomi-clinic-01-safety-wire-locking": {
        "web": ["site:x.com ワイヤリング バイク サーキット", "site:x.com ワイヤーロック バイク"],
        "rt": ["ワイヤリング バイク", "ワイヤーロック バイク"],
        "kw": ["ワイヤリング", "ワイヤーロック", "バイク", "サーキット"],
    },
    "2026-10-14-circuit-maintenance-naomi-clinic-02-brake-fluid-boiling-point": {
        "web": ["site:x.com ブレーキフルード 交換 バイク", "site:x.com ブレーキ エア抜き バイク"],
        "rt": ["ブレーキフルード バイク", "ブレーキ フルード サーキット バイク"],
        "kw": ["ブレーキフルード", "フルード", "DOT4", "エア抜き", "バイク"],
    },
    "2026-10-21-circuit-maintenance-naomi-clinic-03-tire-pressure-hot-management": {
        "web": ["site:x.com タイヤウォーマー サーキット バイク", "site:x.com 温間 空気圧 バイク"],
        "rt": ["タイヤウォーマー バイク", "サーキット タイヤ 空気圧 バイク"],
        "kw": ["タイヤウォーマー", "空気圧", "温間", "タイヤ", "バイク"],
    },
    "2026-10-28-circuit-maintenance-naomi-clinic-04-drive-chain-slack-geometry": {
        "web": ["site:x.com チェーン調整 バイク 整備", "site:x.com ドライブチェーン バイク"],
        "rt": ["チェーン調整 バイク", "チェーン張り バイク"],
        "kw": ["チェーン", "スプロケ", "調整", "バイク"],
    },
    "2026-11-04-circuit-maintenance-naomi-clinic-05-torque-wrench-bolt-mechanics": {
        "web": ["site:x.com トルクレンチ バイク 整備", "site:x.com アクスル トルク バイク"],
        "rt": ["トルクレンチ バイク", "トルク管理 バイク"],
        "kw": ["トルクレンチ", "トルク", "ボルト", "バイク"],
    },
    "2026-11-11-circuit-maintenance-naomi-clinic-06-race-coolant-pure-water": {
        "web": ["site:x.com バイク クーラント 交換", "site:x.com サーキット 冷却水 純水 バイク"],
        "rt": ["クーラント バイク", "ラジエーター 冷却水 バイク"],
        "kw": ["クーラント", "冷却水", "純水", "ラジエーター", "バイク"],
    },
}


def build_queries_for_article(doc: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    aid = doc.get("id", "")
    if aid in SLUG_QUERY_OVERRIDES:
        ov = SLUG_QUERY_OVERRIDES[aid]
        return ov["rt"], ov["web"], ov["kw"]

    tags = [str(t) for t in (doc.get("tags") or []) if t]
    circuit = str(doc.get("circuit") or "").split("（")[0].strip()
    rt_queries = [" ".join(tags[:2])] if tags else [circuit]
    web_queries = [f"site:x.com {q} 2026" for q in rt_queries if q]
    return rt_queries, web_queries, tags + ([circuit] if circuit else [])


def translate_and_comment_batch(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Use Gemini 3.8 Flash in small batches to produce natural JA/CA/EN quotes & cat editorial commentary."""
    cache = x_photo_finder._load_json_cache(TRANSLATION_CACHE_PATH)
    results: dict[str, dict[str, Any]] = {}
    pending: list[dict[str, Any]] = []

    for item in items:
        key = f"{item['articleId']}:{item['statusId']}"
        if key in cache:
            results[key] = cache[key]
        else:
            pending.append(item)

    if not pending:
        return results

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from google import genai
            client = genai.Client()

            # Process in chunks of 8
            for i in range(0, len(pending), 8):
                chunk = pending[i : i + 8]
                payload_desc = [
                    {
                        "key": f"{c['articleId']}:{c['statusId']}",
                        "articleTitleJa": c["articleTitleJa"],
                        "featuredCat": c["featuredCat"],
                        "authorHandle": f"@{c['screenName']}",
                        "authorName": c["accountName"],
                        "rawTweetText": c["rawText"],
                    }
                    for c in chunk
                ]
                prompt = (
                    "You are the trilingual (Japanese `ja`, Catalan `ca`, English `en`) editorial desk for `honda.cat`.\n"
                    "For each verified X post below, return a JSON object mapping `key` -> "
                    "`{quotedPostText: {ja, ca, en}, editorialCommentary: {ja, ca, en}}`.\n\n"
                    "RULES:\n"
                    "1. `quotedPostText`: Accurate, concise translation/rendering of `rawTweetText` in `ja`, `ca`, and `en` (do NOT invent race results not in the tweet).\n"
                    "2. `editorialCommentary`: 1-2 sentences of motorsport editorial commentary in the character voice of `featuredCat`:\n"
                    "   - `marc`: Male orange tabby editor-in-chief (Catalan/MotoGP/SBK expert; passionate, telemetry-minded; in ja uses energetic editorial tone).\n"
                    "   - `suzuka`: Female calico photojournalist (All-Japan/Kyushu trackside reporter; polite, observant about photos & track action).\n"
                    "   - `naomi`: Female black cat mechanic (maintenance/endurance expert; sharp-tongued veteran mechanic with occasional subtle caring nuance—NEVER label as maiden mode).\n"
                    "3. Return ONLY valid JSON object.\n\n"
                    f"INPUT POSTS:\n{json.dumps(payload_desc, ensure_ascii=False, indent=2)}"
                )
                resp = client.interactions.create(
                    model="gemini-3.8-flash",
                    input=prompt,
                    response_format={"type": "text", "mime_type": "application/json"},
                )
                parsed = json.loads(resp.output_text)
                for k, v in parsed.items():
                    if isinstance(v, dict) and "quotedPostText" in v and "editorialCommentary" in v:
                        cache[k] = v
                        results[k] = v
                x_photo_finder._save_json_cache(TRANSLATION_CACHE_PATH, cache)
                print(f"   🗣️ Translated & commented batch {i // 8 + 1} ({len(chunk)} posts)")
        except Exception as e:
            print(f"   ⚠️ Gemini batch translation error ({e}); using clean fallback for remaining items.")

    # Fallback for any untranslated item
    for item in pending:
        key = f"{item['articleId']}:{item['statusId']}"
        if key in results:
            continue
        raw = item["rawText"]
        sn = item["screenName"]
        cat = item["featuredCat"]
        if cat == "marc":
            comm = {
                "ja": f"@{sn} が現地から発信した写真付きポスト。写真からもマシンのバンク角やパドックの熱気が伝わってくるニャ！",
                "ca": f"Publicació verificada amb fotografies de @{sn} que captura l'ambient real i l'acció a pista.",
                "en": f"Verified photo post from @{sn} capturing authentic trackside speed and paddock atmosphere.",
            }
        elif cat == "suzuka":
            comm = {
                "ja": f"@{sn} の写真付きポストです！サーキット現場ならではの緊張感とマシンの迫力がしっかり捉えられていますね。",
                "ca": f"Publicació fotogràfica de @{sn} que reflecteix amb nitidesa la intensitat del cap de setmana de curses.",
                "en": f"Photo dispatch from @{sn} showcasing genuine trackside atmosphere and racing intensity.",
            }
        else:
            comm = {
                "ja": f"@{sn} の現場写真ポストよ。こういう細部の整備や現場の空気感が、サーキットでの安全とタイムに直結するのよね。",
                "ca": f"Fotografies reals de @{sn} que mostren els detalls tècnics i el treball de box.",
                "en": f"Real trackside garage photos from @{sn} highlighting essential mechanical prep and attention to detail.",
            }
        fallback_obj = {
            "quotedPostText": {"ja": raw, "ca": raw, "en": raw},
            "editorialCommentary": comm,
        }
        results[key] = fallback_obj
        cache[key] = fallback_obj

    x_photo_finder._save_json_cache(TRANSLATION_CACHE_PATH, cache)
    return results


def main() -> int:
    files = sorted(ARTICLES_DIR.glob("*.json"))
    print(f"🔍 Discovering & verifying photo-attached X posts across {len(files)} articles...")

    used_status_ids: set[str] = set()
    article_matches: list[tuple[Path, dict[str, Any], list[dict[str, Any]]]] = []
    translation_queue: list[dict[str, Any]] = []
    missing: list[str] = []

    for idx, path in enumerate(files, start=1):
        doc = json.loads(path.read_text(encoding="utf-8"))
        aid = doc.get("id", path.stem)
        pub_date = doc.get("publishedAt", "")
        rt_q, web_q, kw = build_queries_for_article(doc)

        found = x_photo_finder.find_verified_photo_tweets(
            queries=rt_q,
            web_queries=web_q,
            relevance_keywords=kw,
            target_date=pub_date,
            count=2,
            exclude_ids=used_status_ids,
        )

        # Broad fallback if an article came up empty
        if not found:
            cat = doc.get("category", "")
            broad_rt = {
                "motogp": ["id:MotoGP", "MotoGP Marquez"],
                "sbk": ["WorldSBK", "WorldSBK Bulega"],
                "all-japan": ["全日本ロードレース", "JSB1000"],
                "kyushu": ["HSR九州 バイク", "オートポリス バイク", "SPA直入"],
                "endurance-fun": ["レン耐", "ミニバイク 耐久"],
                "maintenance": ["バイク 整備 サーキット"],
            }.get(cat, ["バイク ロードレース"])
            broad_web = [f"site:x.com {q} 2026" for q in broad_rt]
            found = x_photo_finder.find_verified_photo_tweets(
                queries=broad_rt,
                web_queries=broad_web,
                relevance_keywords=kw,
                target_date=pub_date,
                count=1,
                exclude_ids=used_status_ids,
            )

        if not found:
            missing.append(aid)
            print(f"   ❌ [{idx}/{len(files)}] {aid}: NO verified photo tweet found")
            continue

        for f in found:
            used_status_ids.add(f["statusId"])
            translation_queue.append(
                {
                    "articleId": aid,
                    "statusId": f["statusId"],
                    "articleTitleJa": doc.get("locales", {}).get("ja", {}).get("title", aid),
                    "featuredCat": doc.get("featuredCat", "suzuka"),
                    "screenName": f["screenName"],
                    "accountName": f["accountName"],
                    "rawText": f["rawText"],
                }
            )

        article_matches.append((path, doc, found))
        summary_str = ", ".join(
            f"@{f['screenName']}/status/{f['statusId']} ({len(f['mediaUrls'])} imgs)"
            for f in found
        )
        print(f"   ✅ [{idx}/{len(files)}] {aid} -> {summary_str}")

    print(f"\n🌐 Generating trilingual quotes & cat commentaries for {len(translation_queue)} X posts...")
    translations = translate_and_comment_batch(translation_queue)

    today_str = dt.date.today().isoformat()
    updated_count = 0
    for path, doc, found in article_matches:
        aid = doc.get("id", path.stem)
        new_x_cites: list[dict[str, Any]] = []
        for f in found:
            key = f"{aid}:{f['statusId']}"
            t = translations[key]
            new_x_cites.append(
                {
                    "platform": "X",
                    "citationType": "direct_post",
                    "accountName": f["accountName"],
                    "handle": f"@{f['screenName']}",
                    "url": f["url"],
                    "postUrl": f["postUrl"],
                    "publishedDate": f["publishedDate"],
                    "mediaUrls": f["mediaUrls"],
                    "verifiedAt": today_str,
                    "quotedPostText": t["quotedPostText"],
                    "editorialCommentary": t["editorialCommentary"],
                }
            )

        # Keep existing valid non-X citations (YouTube, OfficialWeb, Facebook, Instagram)
        non_x_cites = [
            c for c in (doc.get("snsCitations") or [])
            if c.get("platform") != "X"
        ]
        doc["snsCitations"] = new_x_cites + non_x_cites
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated_count += 1

    print(f"\n🎉 Updated {updated_count}/{len(files)} articles with verified photo-attached X posts!")
    if missing:
        print(f"⚠️ Missing ({len(missing)}): {missing}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
