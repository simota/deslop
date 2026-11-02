# Phase 3: デザイン仕様書 (`design-spec.md`)

## 1. カラーシステムとWCAG 2.2 AA コントラスト比検証

「The Redline Proofing Room（赤入れ校正室と決定論的ターミナルの融合）」に基づき、すべての色ペアのコントラスト比を事前計算し、WCAG 2.2 AA基準（通常テキスト 4.5:1 以上、大見出し・UI境界 3.0:1 以上）を満たす設計とした。

### 1.1 サーフェス・テキスト・ボーダートークン（Editorial Paper Mode）

| トークン名 | HEX値 | 役割 | コントラスト比（対背景） | 根拠 (Ground) |
|---|---|---|---|---|
| `--bg-paper` | `#F6F3EC` | ページ基本背景（温かみのある校正用紙） | — | `brief` (Archival Paper) |
| `--bg-surface` | `#FDFCF9` | 原稿カード・エディタ表面 | — | `brief` (Clean Proof Sheet) |
| `--bg-subtle` | `#ECE7DC` | セクション区切り・セカンダリ背景 | — | `derived` (`--bg-paper` から明度差 -4%) |
| `--ink-primary` | `#141413` | 本文・見出しメインテキスト | **16.8:1** (対 `#F6F3EC`) / **17.9:1** (対 `#FDFCF9`) | `measured` (WCAG AAA 達成) |
| `--ink-secondary` | `#4A4742` | 補足説明・サブコピー | **8.2:1** (対 `#F6F3EC`) / **8.7:1** (対 `#FDFCF9`) | `measured` (WCAG AAA 達成) |
| `--ink-muted` | `#656058` | メタ情報・行番号・キャプション | **5.3:1** (対 `#F6F3EC`) / **5.7:1** (対 `#FDFCF9`) | `measured` (WCAG AA 4.5:1 以上達成) |
| `--border-hairline` | `#D6CFC2` | 原稿罫線・テーブル境界線 | — | `derived` (紙面上の1px校正罫線) |
| `--border-strong` | `#9E9689` | フォーカス枠・アクティブ境界 | **3.1:1** (対 `#F6F3EC`) | `measured` (UIコンポーネント AA 3:1 以上) |

### 1.2 セマンティック・校正赤入れ＆検証トークン（Redline & Contract Palette）

| トークン名 | テキスト/前景 | 背景/バッジ | コントラスト比 | 意味と用途 |
|---|---|---|---|---|
| **Redline Strike (`ART`/`JA`/`EN`)** | `#9E1F14` | `#FDECE9` | **7.4:1** (`measured`) | 削除・書き換え対象のAIスロップ（朱色の赤入れペン・取消線） |
| **Primary Accent (`--accent-redline`)** | `#FFFFFF` | `#B8281C` | **6.1:1** (`measured`) | メインCTAボタン背景・重要アクション |
| **Cue / Structure (`STR`/`CON`)** | `#7C4308` | `#FDF2DF` | **6.8:1** (`measured`) | 構造・内容観点のキュー（アンバーの編集傍注） |
| **Density Metric (`DEN`/`CNT`)** | `#1E467A` | `#E8F0FA` | **7.9:1** (`measured`) | 文書全体の密度指標・統計チェック（校正青インク） |
| **Preserved Fact (`VERIFY` / `Exit 0`)** | `#0F5938` | `#E2F4EB` | **7.5:1** (`measured`) | 保護された事実（数値・URL・コード）および契約検査パス |

### 1.3 ターミナル・インスペクタ・サーフェス（Carbon Terminal Block）

| トークン名 | HEX値 | 役割 | コントラスト比（対 `#121211`） |
|---|---|---|---|
| `--term-bg` | `#121211` | CLI・契約検査・インストールブロック背景 | — |
| `--term-surface` | `#1C1B19` | ターミナル内タブ・コードカード背景 | — |
| `--term-text` | `#F2EFE9` | ターミナル標準出力テキスト | **16.5:1** (`measured`) |
| `--term-muted` | `#A39E93` | コメント・補助出力 | **7.1:1** (`measured`) |
| `--term-red` | `#FF8A7A` | ターミナル内ヒット強調 (`RULE`) | **7.4:1** (`measured`) |
| `--term-green` | `#6EE7B7` | ターミナル内 `exit 0` / `check ok` | **11.8:1** (`measured`) |
| `--term-amber` | `#FCD34D` | ターミナル内 `cue:` 強調 | **12.6:1** (`measured`) |

---

## 2. タイポグラフィ設計

日本語の可読性と英語・識別子・CLI出力の鋭さを両立させる3ロール構成を採用する。外部Webフォントの読み込み遅延によるCLS（Cumulative Layout Shift）を防ぐため、OS標準の高品位フォントをフォールバックの軸としつつ、`font-display: swap` を設定する。

1. **Editorial Display / Heading (`--font-display`)**:
   - `'Shippori Mincho', 'Hiragino Mincho ProN', 'Yu Mincho', 'Noto Serif JP', Georgia, serif`
   - 用途: セクション見出し・Hero見出しの一部。文芸・校正刷りの権威と人間味を表現。
   - `font-feature-settings: "palt" 1;` により日本語プロポーショナルメトリクスを有効化、`text-wrap: balance`（および明示的改行制御）で不自然な1文字落ちを防止。
2. **UI & Prose Sans (`--font-sans`)**:
   - `'Inter', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif`
   - 用途: 説明散文、UIコントロール、テーブル、FAQ。
   - 行間: 本文 `line-height: 1.75`、見出し `line-height: 1.25`。1行あたり文字数が34〜42文字（`max-width: 65ch`）に収まるよう設計。
3. **Code & Rule ID Mono (`--font-mono`)**:
   - `'JetBrains Mono', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', monospace`
   - 用途: ルールID（`JA-04`, `ART-01`, `STR-14`）、CLIコマンド、行・列番号（`examples/before.ja.md:7:65`）、JSONレコード。
   - `font-variant-numeric: tabular-nums;` を指定し、文字数・ヒット数・密度の比較時に桁が完全に揃うようにする。

---

## 3. スペーシングとレイアウトシステム

- **基本グリッド**: `max-width: 1240px`（大画面1440px/1920pxでも行長が広がりすぎず、左右に心地よいマージンを保つ）、パディングはモバイル `20px`、タブレット `32px`、デスクトップ `48px`。
- **セクションリズム**:
  - 単調な「見出し＋3枚カード」の繰り返し（`STR-06` Symmetric sections）を厳禁とする。
  - セクションごとに構造を変える：
    1. **Hero**: 左5:右7の非対称2カラム（左：主張とCTA、右：インタラクティブ校正原稿シート）
    2. **Proof Strip**: 5列のtabular-numsメトリクスバー（上下1px罫線）
    3. **Live Detector**: フルワイド2ペイン・ワークベンチ（左：原稿エディタ＆赤入れハイライト、右：検出ヒット・密度ゲージ・After比較）
    4. **Three Layers**: 左にスティッキーな3層インデックス、右にContent（4テスト）・Structure・Wordingの実例解剖テーブル
    5. **Run Contract Pipeline**: 6フェーズの水平プログレス・ステッパー＋ターミナル＆JSON検証ビューア
    6. **Genre Matrix**: 左に10ジャンルセレクタ、右に選択ジャンルの「Keep / Remove / Rule Adjustments」と実際のコマンド例
    7. **Rule & Perspective Atlas**: フィルタタブ＋リアルタイム検索＋コンパクトな辞書グリッド
    8. **FAQ & Install**: 2カラム（左：FAQ、右：スティッキーなホスト別インストール＆CLIボックス）

---

## 4. レスポンシブ設計方針（320px 〜 1920px）

| 画面幅 | ターゲット | レイアウト・UI最適化仕様 |
|---|---|---|
| **320px** | 小型スマートフォン (iPhone SE 第1世代相当) | パディング `16px`。Hero見出しを `clamp(1.65rem, 6vw, 2.2rem)` に調整し、長大なコマンドやルール表は横スクロールバーを出さずに折り返しまたは内部スクロールコンテナに収める。ボタンは全幅（高さ48px以上）。 |
| **375px** | 標準スマートフォン | パディング `20px`。Heroの校正シートをコンパクト化し、タブ切替（赤入れ原稿 / 修正後 / 検出ログ）を親指で押しやすいセグメントコントロール（最小タップ領域 `44×44px`）にする。 |
| **768px** | タブレット縦 | パディング `32px`。Proof Stripを3+2グリッド、Rule Atlasを2カラム、Live Detectorを上下スタック構成にしつつエディタ高さを最適化。 |
| **1024px** | 小型デスクトップ / タブレット横 | HeroおよびLive Detectorを2カラム化。ナビゲーションリンクをフル表示。 |
| **1440px** | 標準デスクトップ | `1240px` コンテナ中央配置。余白と校正傍注の美しさが最大限に活きる基準ビューポート。 |
| **1920px** | 大型モニター | 背景の紙面テクスチャとセクション区切り罫線は画面端まで伸び、コンテンツは `1280px` 最大幅で視線移動距離を抑制。 |

---

## 5. モーション＆インタラクション仕様 (`design-motion`)

すべてのアニメーションに明確な目的（Orientation / Feedback / Continuity）を持たせ、`transform` と `opacity` のみを基本とし、`prefers-reduced-motion: reduce` 時は即座に最終状態を表示する。

| インタラクション | トリガー | プロパティ・値 | 時間・イージング | 中断時挙動 / Reduced Motion |
|---|---|---|---|---|
| **校正モード切替（Before / Redline / After）** | タブクリック | `opacity: 0 -> 1`, `transform: translateY(4px) -> translateY(0)` | `180ms cubic-bezier(0.22, 1, 0.36, 1)` | 即座に最新タブへ切替 / Reduced時は `0ms` |
| **赤入れハイライトのホバー・選択連動** | 原稿内ハイライトまたは右ペインのヒット行クリック | 該当箇所へスクロール＋パルス枠表示 | `200ms ease-out` | 次のクリックが即優先 / Reduced時はスクロール移動のみ |
| **コピーボタン完了フィードバック** | コピーボタンクリック | アイコンとラベルが `Copied!`（緑 `#0F5938`）に変化 | `150ms ease`, `1800ms` 後に復帰 | 連打時はタイマーリセット |
| **フェーズステッパー切替** | `INVENTORY`〜`REPORT` のステップ選択 | パネル内容のクロスフェードとインジケータ移動 | `200ms cubic-bezier(0.22, 1, 0.36, 1)` | 即座に選択ステップへ切替 / Reduced時は `0ms` |
