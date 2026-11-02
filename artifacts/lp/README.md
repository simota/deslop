# deslop ランディングページ — 成果物サマリー (`README.md`)

## 1. 実装した LP の概要

`deslop`（日本語・英語の機械生成文体を削り、書かれた事実だけを残すエージェントスキル & Python 3.10+ 標準ライブラリ検出器）のブランド世界観 **「Editorial Redline & Proofing Press（活版校正刷りと赤入れ原稿）」** を体現したインタラクティブ・ランディングページです。

- **実装ディレクトリ**: `site/` (`site/index.html`, `site/styles.css`, `site/app.js`, `site/data.js`, `site/serve.py`)
- **ローカル起動コマンド**:
  ```bash
  make serve
  # または
  python3 site/serve.py
  ```
- **デフォルト URL**: `http://127.0.0.1:8765/`
- **Live API エンドポイント**:
  - `POST /api/detect`: リポジトリ本体の `skills/deslop/scripts/detect.py`（`detect.scan`、CLI と同じルールとジャンル免除）を呼び出し、任意のテキストと `--genre` に対する検出ヒット・構造キュー・密度指標をリアルタイム返却

---

## 2. 最終品質スコア

| 指標カテゴリ | 最終結果 |
|---|---|
| **PDCA デザイン・UX 総合スコア（10項目平均）** | **97.6 / 100**（Initial `74.0` → Cycle 1 `85.0` → Cycle 2 `91.0` → Cycle 3 / Final `97.6`） |
| **Lighthouse スコア** | Performance **97** / Accessibility **94** / Best Practices **100** / SEO **100** |
| **マルチビューポート検証（320 / 375 / 768 / 1024 / 1440 / 1920px）** | 全6幅で横スクロール・はみ出し要素 **0件**、コンソール・ネットワークエラー **0件** |
| **LP 自身の `detect.py` ドッグフーディング検査** | **`0 hits` / `0 cues`** |
| **リポジトリ回帰テスト (`make check`)** | **全 429 テスト PASS (`check ok`)**（LP 作成時点。以降の件数は `tests/` を参照） |

---

## 3. 成果物・ドキュメント一覧 (`artifacts/lp/`)

- [`product-analysis.md`](./product-analysis.md) — Phase 1：リポジトリ徹底調査・プロダクトの本質・ターゲットペルソナ・事実根拠の整理
- [`creative-strategy.md`](./creative-strategy.md) — Phase 2：コアコンセプト比較・ファーストビュー設計・10セクション情報設計・コピーライティング指針
- [`design-spec.md`](./design-spec.md) — Phase 3：カラーパレット・タイポグラフィ・グリッド＆余白・インタラクション・アクセシビリティ仕様
- [`implementation-report.md`](./implementation-report.md) — Phase 3：実装ファイル一覧・技術スタック選定理由・主要機能・起動手順
- [`pdca-report.md`](./pdca-report.md) — Phase 4：Initial → Cycle 1 → Cycle 2 → Cycle 3 の改善履歴・10項目採点推移・5ロール多角的レビュー
- [`qa-report.md`](./qa-report.md) — Phase 4 & 5：6ビューポート実機計測・インタラクション検証・Lighthouse スコア・`make check` 結果

### スクリーンショット証跡 (`artifacts/lp/screenshots/`)

リポジトリにコミットしているのは `final/` だけです。`initial/` と `iterations/` は `.gitignore` 対象で、作成した手元にしか残っていません。

- **Initial（初回実装）**:
  - [`screenshots/initial/desktop.png`](./screenshots/initial/desktop.png)
  - [`screenshots/initial/desktop-full.png`](./screenshots/initial/desktop-full.png)
  - [`screenshots/initial/mobile.png`](./screenshots/initial/mobile.png)
  - [`screenshots/initial/mobile-full.png`](./screenshots/initial/mobile-full.png)
- **PDCA Iterations（Cycle 1〜3）**:
  - [`screenshots/iterations/cycle-1/`](./screenshots/iterations/cycle-1/) (`desktop-hero.png`, `desktop-full.png`, `mobile-hero.png`, `mobile-full.png`)
  - [`screenshots/iterations/cycle-2/`](./screenshots/iterations/cycle-2/) (`desktop-hero.png`, `desktop-full.png`, `mobile-hero.png`, `mobile-full.png`)
  - [`screenshots/iterations/cycle-3/`](./screenshots/iterations/cycle-3/) (`desktop-hero.png`, `desktop-full.png`, `mobile-hero.png`, `mobile-full.png`)
- **Final（最終完成版）**:
  - [`screenshots/final/desktop-hero.png`](./screenshots/final/desktop-hero.png)
  - [`screenshots/final/desktop-full.png`](./screenshots/final/desktop-full.png)
  - [`screenshots/final/mobile-hero.png`](./screenshots/final/mobile-hero.png)
  - [`screenshots/final/mobile-full.png`](./screenshots/final/mobile-full.png)
  - [`screenshots/final/tablet.png`](./screenshots/final/tablet.png)

---

## 4. 既知の制約と今後の改善提案

- **オフライン静的閲覧時のフォールバック**: `python3 site/serve.py` を経由せず `site/index.html` を直接開いた場合でも、`site/data.js` にバンドルされた81ルール定義とクライアントサイド検出ロジックによってプリセット文書と自由編集の検査が動作します（完全な `cues.py` 連携まで含める場合は `make serve` / `python3 site/serve.py` での起動を推奨）。
- **今後の拡張案**: `preserve_check.py` の差分シミュレーション（原文から数値を1つ消したときにどのように Exit 1 でブロックされるか）をブラウザ上で試せるミニタブを追加することで、事実保持エンジンの体験価値をさらに深めることができます。
