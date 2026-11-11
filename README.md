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
   - 🔧 **ナオミ (Naomi・メス)**: 九州のガレージに棲みつく黒雌猫メカニック。サーキットメンテナンス・耐久・足回り担当。普段はぶっきらぼうな職人肌だが、セリフの端々にふと可愛らしい一面が滲み出るキャラクター。
3. **全国＆世界の公式スケジュール自動収集 ＋ 九州3大サーキットガイド**
   - MotoGP公式、MFJ公式（全日本＆北海道〜九州の全国地方選）、各サーキット公式サイト＆公式SNSからスケジュールを週次同期。
   - **SPA直入（大分県竹田市）**、**オートポリス（大分県日田市）**、**HSR九州（熊本県大津町）**のサーキットガイドと、週1回のサーキット走行向けバイクメンテナンス講座も連載。
4. **Gemini 3.8 Flash + Google Search Grounding によるスケジュール連動・史実検証パイプライン**
   - [scripts/generate_articles.py](file:///Users/kat/Projects/honda.cat/scripts/generate_articles.py) がスケジュールDBに連動して開催プレビューや結果ダイジェストを3言語で自動生成します。

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
