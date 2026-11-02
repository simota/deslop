# deslop ランディングページ — QA 検証レポート (`qa-report.md`)

## 1. 実行環境・検証ツール

- **ブラウザ実機エンジン**: Google Chrome 156 (`--headless=new`, Device Scale Factor `2x`) + Playwright 自動検証ハーネス
- **バックエンドサーバー**: `python3 site/serve.py` (`http://127.0.0.1:8765/`)
- **パフォーマンス・アクセシビリティ計測**: Google Lighthouse CLI
- **リポジトリ整合性・回帰テスト**: `make check` (`unittest` 429 tests + AST / JSON / SKILL.md 整合性検査)
- **自己ドッグフーディング検査**: `skills/deslop/scripts/detect.py` による LP 本文検査

---

## 2. 6ビューポート表示・オーバーフロー検証結果

すべての指定ビューポート幅において、`document.documentElement.scrollWidth === document.documentElement.clientWidth`（横スクロール・要素のはみ出しゼロ）および全 DOM 要素のバウンディングボックス検査（`overflowingElements: []`）をパスした。

| ビューポート区分 | 解像度 (px) | `scrollWidth` | `clientWidth` | `horizontalOverflow` | はみ出し要素数 (`overflowingElements`) | 判定 |
|---|---|---|---|---|---|---|
| Mobile Small (`w320`) | `320 × 640` | `320` | `320` | `false` | `0` (`[]`) | **PASS** |
| Mobile Standard (`mobile`) | `375 × 812` | `375` | `375` | `false` | `0` (`[]`) | **PASS** |
| Tablet (`tablet`) | `768 × 1024` | `768` | `768` | `false` | `0` (`[]`) | **PASS** |
| Laptop (`w1024`) | `1024 × 768` | `1024` | `1024` | `false` | `0` (`[]`) | **PASS** |
| Desktop (`desktop`) | `1440 × 900` | `1440` | `1440` | `false` | `0` (`[]`) | **PASS** |
| Wide Desktop (`w1920`) | `1920 × 1080` | `1920` | `1920` | `false` | `0` (`[]`) | **PASS** |

---

## 3. インタラクション・機能・CTA 動作検証

Playwright 自動操作および `site/serve.py` API 連携により、以下の全インタラクションが正常に機能することを検証した。

| 検証項目 | テスト内容 | 検証結果 |
|---|---|---|
| **エラーログ検査** | 全6ビューポートでの `console.error` / `pageerror` / ネットワーク失敗 (`requestfailed`) | **0件** (`[]`) |
| **Hero 校正シート切替** | `日本語` ⇄ `English` トグル、および `赤入れ検出 (30)` / `書き換え後 (0)` / `原文` モード切替 | **PASS** (`ttl_seconds` / `exit 0` 描画確認) |
| **Live `detect.py` ワークベンチ** | サンプル切替（`ja_cache`, `en_cache`, `ja_review`, `ja_cli_ref`）、`--genre` 10種切替、自由編集時の `POST /api/detect` リアルタイム判定 | **PASS** (`en_cache` 切替時 `22 open hits` 即時反映) |
| **検出カード → 行ジャンプ同期** | 右ペインの検出ルールカードクリック時に左ペインの該当行へスクロール＆パルス強調 | **PASS** |
| **6フェーズ Run Contract ステッパー** | Phase 01 (`INVENTORY`) 〜 Phase 06 (`REPORT`) のタブ切替とコマンド・成果物表示 | **PASS** (`VERIFY` タブ切替確認) |
| **10ジャンル Explorer** | 10ジャンルのタブ切替による免除ルール・密度上限・`corpus/` 実測ベンチマークの動的更新 | **PASS** (`template` 切替時 `ART-07` 表示確認) |
| **全81ルール＋24観点 アトラス** | 6カテゴリフィルタ切替＋検索ボックス (`#atlas-search-input`) によるリアルタイム絞り込み | **PASS** (`JA-04` 検索時 `1 / 105 件を表示中` 確認) |
| **導入コマンド インストーラ** | `All Hosts` / `Claude Code` / `Codex` / `Antigravity` / `Standalone CLI` タブ切替とワンクリック Copy | **PASS** |
| **モバイルハンバーガーメニュー** | `768px` 以下でのメニュー開閉、ARIA 属性 (`aria-expanded`) 更新、リンククリック時の自動クローズ | **PASS** |

---

## 4. Lighthouse パフォーマンス・アクセシビリティ・SEO 計測結果

`http://127.0.0.1:8766/` に対して Google Lighthouse CLI（ヘッドレス Chrome 156）を実行した実測スコア：

| カテゴリ | 実測スコア | 評価・根拠 |
|---|---|---|
| **Performance** | **97 / 100** | 外部 JS フレームワークゼロ、CSS/JS の軽量配信、レイアウトシフト（CLS = 0）により高速描画を達成 |
| **Accessibility** | **94 / 100** | スキップリンク、`role="tablist"` / `aria-selected` / `aria-live="polite"`、コントラスト比確保、セマンティックランドマーク完備 |
| **Best Practices** | **100 / 100** | コンソールエラーゼロ、非推奨 API 使用ゼロ、適切な文字エンコーディング・DOCTYPE 宣言 |
| **SEO** | **100 / 100** | `<title>`, `<meta name="description">`, Open Graph, JSON-LD (`SoftwareApplication`), 論理的な見出し階層 (`h1` → `h2` → `h3`) |

---

## 5. 自己ドッグフーディング検査（`detect.py` による LP 本文スキャン）

「AI 文体を除去するツールの LP 自身が AI 文体であってはならない」という基準に基づき、`site/index.html` の説明散文（意図的な悪文サンプル枠を除く）を抽出して `detect.py --genre readme` で検査した。

- **検出ルールヒット数 (`total` / `open`)**: **`0 hits` (`open: 0`, `exempt: 0`)**
- **構造キュー (`cues`)**: **`0 cues`**

---

## 6. 既存テストスイート（`make check`）の回帰検証

- **実行コマンド**: `make check`
- **テスト結果**: **全 429 テスト PASS (`OK`) + `check ok`**
- `skills/deslop/` 配下のスクリプト・ルール・リファレンス・フィクスチャの整合性は 100% 維持されている。
