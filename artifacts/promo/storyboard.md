# プロモーション映像 クリエイティブ戦略・絵コンテ (`storyboard.md`)

## 1. Phase 1：プロダクト徹底分析（根拠ベース）

リポジトリ内の `README.md`、`skills/deslop/SKILL.md`、`skills/deslop/scripts/*.py`（`detect.py`, `preserve_check.py`, `contract_check.py`, `snapshot.py`, `cues.py`, `findings.py`, `rules.json`）、`examples/before.*.md` / `after.*.md`、および `site/` を精査し、以下の事実と本質的価値を特定した。

### 1.1 プロダクトの目的と本質的な価値
- **一言での定義**: 日本語・英語の Markdown および平文から、**原文にない事実を1文字も足すことなく、機械生成特有の文体・構造・空疎な主張（AIスロップ）をゼロにするエージェントスキル＆決定論的検査器**。
- **本質的な価値（「なぜ使いたくなるのか」）**:
  1. **「言い換え」ではなく「削除ファースト」**: 従来のプロンプト指示では `重要` → `肝心`、`leverage` → `utilize` のような類語置換でAI臭が残る。`deslop` は4つの内容テスト（Information / Substitution / Reader / Support）に落ちた空疎な文を言い換えず削除する。
  2. **「AIが勝手にコードや数値を書き換える恐怖」の完全解消**: `preserve_check.py` が原本スナップショット（`original/`）と作業コピーの間で、数値（符号・指数・全角数字含む）・URL・リンク先・インラインコード・コードブロック（SHA-256照合）・脚注の5要素を厳密に比較し、1つでも無断で消失・追加されれば `contract_check.py` が `Exit 1` で差し戻す。
  3. **ジャンルごとの正当な慣習を誤爆しない**: 全10ジャンル（`readme`, `reference`, `tutorial`, `article`, `spec`, `pr`, `message`, `changelog`, `template`, `general`）を認識し、API仕様書の太字項目やテンプレートの空欄プレースホルダ等の正当な慣習を自動免除する。
  4. **外部依存ゼロ・1コマンド導入**: Python 3.10+ 標準ライブラリのみで動作し、`make link` 一発で Claude Code (`~/.claude/skills`)、Codex (`~/.codex/skills`)、Antigravity (`~/.gemini/antigravity-cli/skills`) に導入できる。

### 1.2 リポジトリから確認された正確な定量ファクト（誇張・捏造ゼロ）
| 項目 | 検証済みファクト | 根拠ファイル |
|---|---|---|
| 対応言語 | 日本語 (`ja`) / 英語 (`en`) Markdown・プレーンテキスト | `README.md`, `detect.py` |
| 対応ホスト | Claude Code / Codex / Antigravity / Standalone CLI | `Makefile`, `SKILL.md` |
| 決定論的ルール数 | **81 rules** (`ART` 9, `JA` 33, `EN` 27, `EMO` 1, `CNT` 1, `DEN` 10) ※README概要表記は80 rules | `skills/deslop/scripts/rules.json` |
| 内容・構造観点 | **24 perspectives** (`CON-01`..`08` の8種 + `STR-01`..`16` の16種、うち11種を `cues.py` が自動キュー) | `rules.json`, `cues.py` |
| 対応ジャンル | **10 genres** (`general`, `readme`, `reference`, `tutorial`, `article`, `spec`, `pr`, `message`, `changelog`, `template`) | `rules.json`, `reference/rewrite.md` |
| 実行フェーズ | **6 phases** (`INVENTORY → VOICE → DETECT → REWRITE ⇄ VERIFY → REPORT`) | `SKILL.md` |
| 実フィクスチャ実績 | `examples/before.ja.md` (396文字, 30 hits, 3 cues) → `examples/after.ja.md` (105文字, −73%, 0 open hits) | `examples/*.ja.md`, `detect.py` |
| 回帰テスト・依存 | **429 tests** (`make check` パス) / **0 external dependencies** (Python 3.10+ stdlib only) | `Makefile`, `tests/` |

---

## 2. Phase 2：クリエイティブ戦略とコンセプト選定

### 2.1 コンセプト案の比較と選定
| 案 | 概要 | 評価・採否 |
|---|---|---|
| 案A：機能カタログ型 | 81ルール・24観点・10ジャンル・6フェーズを順番に説明するスライド型動画 | **不採用**：機能一覧の説明に終始し、視聴者が「自分のドキュメントの痛み」として自分事化しにくい。 |
| 案B：CLIログ再生型 | 黒いターミナル画面で `detect.py` と `contract_check.py` の出力だけを流す動画 | **不採用**：正確だが視覚的な抑揚に乏しく、「冗長なAI文章が端正な散文へ結晶化する快感」が直感的に伝わらない。 |
| **案C（採用）：「The Redline Proofing Room — 赤入れ校正室と決定論的ターミナルの融合」** | **冒頭0.5秒で誰もが身に覚えのあるAI生成文に朱色の赤入れレーザーを走らせ、実フィクスチャが396文字→105文字（0 hits）へ劇的に研ぎ澄まされる体験と、事実を1つも失わない `preserve_check.py` / `contract_check.py` の鉄壁保証をシネマティックに描く** | **採用**：開始3秒のインパクト、課題から解決へのカタルシス、ブランドの独自世界観（Editorial Paper × Carbon Terminal）のすべてを最高水準で満たす。 |

### 2.2 アートディレクション＆デザインシステム
- **カラーパレット（WCAG AA/AAA準拠・ブランド統一）**:
  - **Editorial Light Scene**: Archival Paper `#F6F3EC`、Proof Sheet `#FDFCF9`、Primary Ink `#141413`、Redline Crimson `#B8281C`（背景 `#FDECE9`）、Structure Cue Amber `#7C4308`（背景 `#FDF2DF`）、Density Blue `#1E467A`（背景 `#E8F0FA`）、Preserved Fact Emerald `#0F5938`（背景 `#E2F4EB`）。
  - **Carbon Terminal Scene**: Carbon Black `#121211`、Surface `#1C1B19`、Terminal Red `#FF8A7A`、Emerald `#6EE7B7`、Amber `#FCD34D`。
- **タイポグラフィ**:
  - 見出し（Editorial Display）: `'Hiragino Mincho ProN', 'YuMincho', serif`（権威と編集室の美意識）
  - UI・本文（Clean Sans）: `'Hiragino Sans', 'Inter', -apple-system, sans-serif`（高視認性・瞬間理解）
  - コード・ルールID・数値（Tabular Mono）: `'SFMono-Regular', 'JetBrains Mono', 'Menlo', monospace`（`tabular-nums` 徹底）
- **サウンドデザイン（120 BPM 完全同期）**:
  - 120 BPM（1拍 = 0.5秒、1小節 = 2.0秒）のパルスに映像トランジション・赤入れストローク・カウンタ・検証パス音をフレーム単位で同期。
  - 温かみのあるミニマル・エレクトロニカ調のコード進行（Am9 → Fmaj7 → Cmaj9 → G6/E7）に、校正ペンの鋭いスラッシュ音、メカニカルなタイピング・ロックオン音、クライマックスの澄んだチャイム（`contract ok`）を重ねる。

---

## 3. シーン別構成・タイムライン設計（全38.0秒 / 60fps / 2,280フレーム）

| Scene | 時間 (秒) | フレーム (60fps) | シーンタイトル | 映像・モーション演出 | ナレーション / 画面テキスト（日本語中心） | 音響・SEシンクロ |
|---:|---|---|---|------|------|---|
| **01** | `0.0s – 4.5s` | `0 – 270` | **THE HOOK: AIスロップへの赤入れ** | 校正用紙（`bg-editorial-paper.jpg`）上に浮かぶ典型的なAI生成文（「🚀 完全ガイド」「本記事では詳しく解説します」「約30%が実感していると言われています」「〜と言っても過言ではありません」「いかがでしたか？」）。`0.6s` から真紅の校正レーザーが次々と打ち抜き、`EMO-01` `JA-08` `CNT-01` `JA-02` `ART-04` バッジが炸裂。`2.4s` で画面中央に巨大明朝体コピーが出現。 | **「その技術文書、AIの『水増し』が透けていませんか。」**<br>サブ：`deslop` — 機械生成の文体を削り、書かれた事実だけを残す。 | `0.0s` 低域パルス起動<br>`0.6s/1.0s/1.4s/1.8s` 鋭い赤入れペン・スラッシュ音×4<br>`2.4s` 重厚なタイトルインパクト音 |
| **02** | `4.5s – 9.5s` | `270 – 570` | **THE PROBLEM: 言い換えの罠と事実改変リスク** | 左右2分割比較カード。左カード：「口頭プロンプトの限界」— `重要 → 肝心`、`leverage → utilize` の類語ループと、`ttl_seconds = 300` が勝手に消える警告。右カード：「`deslop` の解決」— 言い換えではなく**削除ファースト**＋**事実の機械的ロック**。 | **「『AIっぽさを消して』では、別のAI語彙に置き換わるだけ。」**<br>空疎な文は言い換えず**削除**し、数値・URL・コードは**機械的に保護**する。 | `4.5s` トランジション・ウーッシュ<br>`6.0s` 警告ビープ（左）→ `7.2s` クリーンなロックオン音（右） |
| **03** | `9.5s – 17.5s` | `570 – 1050` | **LIVE REDLINE: 396文字 → 105文字 (−73%) の結晶化** | 実際のフィクスチャ `examples/before.ja.md` と `site/` の校正UIが登場。前半（`9.5s–13.5s`）：`detect.py` が **30 hits + 3 cues** をハイライト。後半（`13.5s–17.5s`）：赤入れ箇所が一斉に折りたたまれ、緑色でロックされた `ttl_seconds = 300`、`max_entries = 10000`、TOMLブロック、URLだけが残る `examples/after.ja.md`（**105文字・0 open hits**）へモーフィング。 | **「30件のノイズを削ぎ落とし、事実だけを結晶化する。」**<br>`examples/before.ja.md` → `after.ja.md`<br>**396文字 → 105文字 (−73%) / 30 hits → 0 open / 事実欠落 0** | `9.5s` スキャン起動音<br>`10.2s–12.5s` 高速タataタッ（検出カウントアップ）<br>`13.5s` 折りたたみスナップ音＋澄んだハーモニックコード |
| **04** | `17.5s – 25.0s` | `1050 – 1500` | **ARCHITECTURE: 3層の除去原理 × 10種のジャンル認識** | 上段：3層フィルタ（`PASS 1: Content 4 Tests` → `PASS 2: Structure 16 Perspectives` → `PASS 3: Wording & Density 81 Rules`）が立体カードで展開。下段：`--genre` の10ジャンルバッジ（`readme`, `reference`, `spec`, `article`, `pr`, `message`, `changelog`, `template` 等）が点灯し、API仕様の太字やテンプレート空欄を誤爆せず免除する様子を表示。 | **「単語の前に、内容と構造を問う。文書のジャンルも理解する。」**<br>1. **Content** (4つのテスト) → 2. **Structure** (24観点) → 3. **Wording** (81ルール)<br>＋ **全10ジャンル (`--genre`)** の正当な慣習を自動免除 | `17.5s / 19.0s / 20.5s` 3段階のレイヤー展開チャイム<br>`22.0s` 10ジャンル・セレクタの軽快なクリック連打音 |
| **05** | `25.0s – 32.5s` | `1500 – 1950` | **CLIMAX: 6フェーズ実行契約と `preserve_check` / `contract_check`** | ダークモード（`bg-redline-abstract.jpg` ベース）へ劇的にシフト。6フェーズ（`INVENTORY → VOICE → DETECT → REWRITE ⇄ VERIFY → REPORT`）が光り、`preserve_check.py` の5大保護シールド（`code_block` SHA-256 / `inline_code` / `number` / `url` / `footnote`）が全て `VERIFIED` に点灯。最後に `contract_check.py` が `Exit 0 · contract ok` を刻印し、5つの定量指標（`81 Rules` / `24 Perspectives` / `10 Genres` / `429 Tests` / `0 Deps`）が輝く。 | **「事実は一文字も捏造しない。コードは一行も壊さない。」**<br>`preserve_check.py` × `contract_check.py` → **`Exit 0: contract ok`**<br>`81 Rules` · `24 Perspectives` · `10 Genres` · `429 Tests` · `0 Deps` | `25.0s` ドラマチックなモードシフト・サブベース<br>`26.5s–28.5s` 5つのシールドロック音<br>`29.5s` クライマックスの「Contract OK」レゾナンスチャイム |
| **06** | `32.5s – 38.0s` | `1950 – 2280` | **FINALE & CTA: 責任ある著者が署名できる散文へ** | エディトリアル・ペーパーとターミナルカードが融合した美しいフィナーレ画面。ブランドロゴ `deslop`、タグライン、対応ホスト（Claude Code / Codex / Antigravity）、そして即座に試せる2行のコマンド `make link` と `make detect TARGET=docs/` を鮮明に提示。 | **「責任ある人間の著者が、そのまま署名できる散文へ。」**<br>**`deslop`** — Agent Skill & Deterministic Prose Linter<br>`make link` &nbsp;/&nbsp; `make detect TARGET=docs/` | `32.5s` 温かいピアノ＆パッドの解決和音（Amadd9 → Asus2）<br>`34.0s` コマンド確定音と美しい余韻フェードアウト |
