# deslop ランディングページ — 実装レポート (`implementation-report.md`)

## 1. 実装概要

`deslop`（日本語・英語の機械生成文体を除去するエージェントスキル & Python 標準ライブラリ CLI）の魅力と技術的根拠をブラウザ上で直接体験できるインタラクティブ・ランディングページを `site/` ディレクトリに実装した。

本リポジトリの最重要制約である **「外部パッケージ依存ゼロ（Python 3.10+ 標準ライブラリのみ）・既存の `make check`（429テスト）を一切壊さない」** を厳守しつつ、ブラウザ上から実際の `skills/deslop/scripts/detect.py` を呼び出してリアルタイム検証できる構成としている。

---

## 2. 追加・変更ファイル一覧

| ファイルパス | 役割・内容 |
|---|---|
| `site/index.html` | ランディングページ本体（セマンティック HTML5、全10セクション、ARIA ランドマーク・タブ・ライブリージョン完備） |
| `site/styles.css` | Editorial Redline & Proofing Press デザインシステム（CSS Custom Properties、レスポンシブ 6 ブレークポイント、`prefers-reduced-motion` 対応） |
| `site/app.js` | インタラクション制御（Hero 校正シート切替、Live `detect.py` ワークベンチ、行ジャンプ同期、6フェーズ Run Contract ステッパー、10ジャンル Explorer、81ルール＋24観点検索アトラス、4ホスト別インストーラ） |
| `site/data.js` | リポジトリ実データバンドル（`rules.json` の全81ルール、`reference/structure.md` の24観点、10ジャンル設定、`examples/before.*`・`examples/after.*` 実テキストと実スキャン結果、`corpus/` 12ペアの実測ベンチマーク） |
| `site/serve.py` | Python 3.10+ 標準ライブラリ（`http.server`）によるローカル Web サーバー兼 Live API（`POST /api/detect` で `skills/deslop/scripts/detect.py` を直接実行、`GET /api/rules` で `rules.json` を返却） |
| `Makefile` | `make serve` ターゲット（`python3 site/serve.py` 起動ショートカット）の追加。既存の `test` / `lint` / `eval` / `check` ターゲットは無変更 |

> **既存スキルへの影響ゼロの確認**: `skills/deslop/` 配下のスクリプト・ルール・リファレンス・`examples/`・`tests/` は一切変更しておらず、`make check` の全 429 テストがそのままパスする。

---

## 3. 使用技術スタックと選定理由

1. **Frontend**: Vanilla HTML5 + Modern CSS (Grid / Subgrid / Custom Properties / `clamp()`) + Vanilla ES2022 JavaScript
   - **選定理由**: `AGENTS.md` / `CLAUDE.md` の「標準ライブラリのみ・外部依存なし」の思想を Web フロントエンドにも貫徹。ビルドステップや `node_modules` を一切必要とせず、どの環境でも即座に配信・閲覧可能。
2. **Backend / Live Detection API**: Python 3.10+ `http.server` (`site/serve.py`)
   - **選定理由**: `skills/deslop/scripts/detect.py` を直接 `import` し、`POST /api/detect` リクエストに対して本物の `scan_text()`・`density_points()`・`compile_rules()` を実行してミリ秒単位で JSON レスポンスを返す。サーバー未起動（静的ファイル閲覧時）でも `site/data.js` のプリコンパイル済み81ルールとクライアントサイド正規表現エンジンに自動フォールバックするハイブリッド設計。
3. **Typography**:
   - 見出し・思想表現: `Shippori Mincho B1` / `Newsreader`（活版校正刷りの品格）
   - 本文・UI: `IBM Plex Sans JP`（高い可読性と技術文書の明快さ）
   - コード・ルールID・数値: `JetBrains Mono` (`font-variant-numeric: tabular-nums`)

---

## 4. 実装した主要機能・インタラクション

### 4.1 ファーストビュー：Interactive Proofing Sheet (`#hero-proof`)
- **言語トグル**: `日本語 (examples/before.ja.md)` と `English (examples/before.en.md)` をワンクリックで切替。
- **3モード表示**:
  1. `Redline 差分校正`: `detect.py` が検出した箇所をルールIDバッジ付きでインライン赤線表示し、下部に `after` への差分テーブルと `preserve_check.py` の全5項目 `ok: true` ステータスを表示。
  2. `Before (17 hits)`: 元の AI 生成テキストとヒット内訳。
  3. `After (0 hits)`: 事実と構造を100%保持したまま再構成された完了テキスト。

### 4.2 Live `detect.py` ワークベンチ (`#live-detector`)
- **4種のプリセット + 自由入力**: `examples/before.ja.md`、`examples/after.ja.md`、`examples/before.en.md`、`examples/after.en.md` の実ファイルをワンクリックでロード、または任意の Markdown テキストを直接ペーストして即座に検証可能。
- **10ジャンル切替**: `general` / `readme` / `reference` / `tutorial` / `article` / `spec` / `pr` / `message` / `changelog` / `template` を切り替えると、ジャンル別の免除ルール（`exempt`）と密度閾値（`limits`）が即座に反映される。
- **インライン赤線ハイライト & 行ジャンプ同期**: 右ペインの検出ルールカードをクリックすると、左ペインのハイライト表示に自動で切り替わり、該当行へスムーズスクロール＆パルス強調表示する。
- **実行 CLI コマンド生成バー**: 選択中のサンプルとジャンルに対応する実行コマンド（例: `python3 skills/deslop/scripts/detect.py examples/before.ja.md --genre readme`）を下部にリアルタイム生成し、ワンクリックでコピー可能。

### 4.3 3層構造＆4つの内容テスト (`#three-layers`)
- Layer 1（機械的検出 `detect.py`）、Layer 2（24構造・内容観点 `cues.py` + `findings.py`）、Layer 3（事実保持・収束ゲート `preserve_check.py` + `contract_check.py`）の役割分担を図解。
- どんな言い換えでも逃れられない4つの内容テスト（Test A: 反転テスト / Test B: 固有名詞テスト / Test C: 削除テスト / Test D: 根拠テスト）を実例つきで提示。

### 4.4 6フェーズ Run Contract ステッパー & 5つの保全保証 (`#how-it-works`)
- Phase 1 (Init) から Phase 6 (Final Verification) までの実行契約をインタラクティブなタブステッパーで解説。各フェーズの実行コマンド、生成アーティファクト（`target.txt`, `pass-N.detect.json`, `pass-N.preserve.json` 等）、`contract_check.py` の検証項目を確認可能。
- `preserve_check.py` が強制する5つの不変条件（見出し階層、コードブロック完全一致、URL・リンク不変、数値・日付・識別子保全、コロンリスト構造維持）を明示。

### 4.5 10ジャンル別プロファイル & `corpus/` 実測ベンチマーク (`#genres`)
- 10ジャンルをクリックで切り替え、各ジャンルの「免除ルール一覧」「上書きされる密度閾値」「絶対不変の `ART-01`〜`ART-09` 保護」「対象ファイル例」を動的に表示。
- さらに `corpus/` に収録された実データ12ペア（`before` 合計 265 ヒット → `after` 合計 0 ヒット）のジャンル別実測スコアをバッジ表示。

### 4.6 全81ルール＋24観点 インタラクティブ・アトラス (`#rule-atlas`)
- 全105項目（81ルール + 24観点）をカテゴリフィルタ（`ALL`, `ART`, `JA`, `EN`, `DEN`, `EMO/CNT`, `CON`, `STR`）およびフリーワード検索（ルールID・名称・説明・修正方針）でリアルタイムに絞り込み可能。

### 4.7 マルチホスト導入インストーラ (`#install`)
- `All Hosts` / `Claude Code` / `Codex` / `Antigravity` / `Standalone CLI` の5タブで導入コマンドを切り替え、ワンクリックでクリップボードへコピー可能。

---

## 5. 起動方法・ビルド手順

ビルドステップやパッケージインストールは不要。以下のコマンドのみで起動できる。

```bash
# ローカルサーバー起動（デフォルト: http://127.0.0.1:8765）
python3 site/serve.py

# またはポート番号を指定して起動
python3 site/serve.py --port 8080
```

既存テストスイートの検証：

```bash
make check
```
