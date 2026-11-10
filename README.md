# 🐾🏁 `honda.cat` — 二足歩行の猫たちが届ける3言語二輪レース＆草耐久情報サイト

`honda.cat` は、`.cat` ドメイン（Fundació .cat）の理念に準拠し、**日本語（デフォルト）・カタルーニャ語（`Català`）・英語（`English`）**の3カ国語で二輪モータースポーツおよび草レース情報を全自動発信するAIメディアプラットフォームです。

---

## ✨ 主な特徴

1. **日本語デフォルト ＋ Web Storage (`localStorage`) による言語記憶**
   - 初回アクセス時は**日本語 (`ja`)** を表示。
   - ヘッダーの言語スイッチャー（`🇯🇵 日本語` / `🏴󠁥󠁳󠁣󠁴󠁿 Català` / `🇬🇧 EN`）で切り替えると `localStorage` (`honda_cat_preferred_lang`) に保存され、次回アクセス時や別ページ遷移時も**再切り替え不要で選択言語が自動維持**されます。
   - `.cat` ドメイン審査クローラー・SEO向けに `/ca/`（カタルーニャ語版エントリー）および `/en/`（英語版エントリー）、`hreflang` タグも標準出力されます。
2. **「なめ猫」風（非ヤンキー・本格レーシング＆ガレージ仕様）二足歩行の猫編集部**
   - 🐱 **マルク (Marc・オス)**: バルセロナ（モンメロ）出身の茶トラ編集長。MotoGP / WorldSBK / スーパーセーブ物理解説担当。
   - 🐾 **スズカ (Suzuka・メス)**: 望遠カメラを構える三毛猫フォトジャーナリスト。全日本ロードレース＆九州3大サーキット担当。
   - 🔧 **ナオコ (Naoko・メス)**: 大分のガレージに棲みつく**やさぐれた黒雌猫メカニック**。普段は辛口で毒づく姐御肌（`mood: "grumpy"`）だが、褒められたり直入のソフトクリームを差し入れされると**ふいに乙女な一面（`mood: "maiden"` 🌸）**が出るギャップ萌えキャラクター。
3. **九州3大サーキット＆「お題付き耐久草レース」手厚いカバー**
   - **SPA直入（大分県竹田市）**、**オートポリス（大分県日田市）**、**HSR九州（熊本県大津町）**の開催情報・攻略・草レース情報を特設ハブ＆記事で重点カバー。
   - ピットインごとにお題（知恵の輪・けん玉・クイズ等）をクリアするレクリエーション耐久**「お題付き耐久草レース」**や**「レン耐」**も専用カテゴリーで発信。
4. **Gemini 3.8 Flash + Google Search Grounding による全自動記事パイプライン**
   - [scripts/generate_articles.py](file:///Users/kat/Projects/honda.cat/scripts/generate_articles.py) が最新のレース情報を検索・検証し、3言語の記事本文・リザルト表・猫たちの掛け合い（ナオコのやさぐれ＆乙女モード含む）を構造化JSONとして自動生成します。

---

## 🚀 ローカル開発・ビルド手順

```bash
# 開発サーバー起動 (http://localhost:4321)
npm run dev

# 本番用静的HTMLビルド (dist/ に出力)
npm run build

# AI記事生成パイプライン検証 (ドライラン)
python3 scripts/generate_articles.py --dry-run

# Gemini API キーを設定して新規3言語記事を全自動生成
export GEMINI_API_KEY="your-api-key"
python3 scripts/generate_articles.py --mode kyushu --topic "SPA直入のお題付き耐久草レースとオートポリス週末情報"
```

---

## 🌐 ゼロコスト本番デプロイ手順 (`honda.cat`)

維持費 **月額 0円** で安定運用できる以下2つのデプロイ方法に対応しています。

### 方法A: Cloudflare Pages（推奨・CDN高速＆帯域完全無料）
1. GitHub リポジトリに本プロジェクトを Push します。
2. Cloudflare ダッシュボード ＞ **Workers & Pages** ＞ **Create application** ＞ **Pages** ＞ リポジトリを接続。
3. ビルド設定：
   - **Framework preset**: `Astro`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
4. **Custom domains** で `honda.cat` および `www.honda.cat` を追加（SSL証明書が自動発行されます）。
5. GitHub リポジトリの **Settings > Secrets and variables > Actions** に `GEMINI_API_KEY` を登録すると、[.github/workflows/auto-generate.yml](file:///Users/kat/Projects/honda.cat/.github/workflows/auto-generate.yml) により週3回自動で新着記事が生成・公開されます。

### 方法B: GitHub Pages（GitHub完結・完全無料）
1. GitHub リポジトリの **Settings > Pages** で Source を **GitHub Actions** に設定。
2. [.github/workflows/deploy.yml](file:///Users/kat/Projects/honda.cat/.github/workflows/deploy.yml) が Push ごとに自動実行され、[public/CNAME](file:///Users/kat/Projects/honda.cat/public/CNAME) (`honda.cat`) 付きでデプロイされます。
3. ドメインのDNS設定で `honda.cat` の Aレコード（または ALIAS/ANAME）を GitHub Pages のIPに向けるだけで公開完了です。
