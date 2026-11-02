/* ==========================================================================
   deslop — Interactive Proofing & Detector Engine (Client + Live API)
   ========================================================================== */
(function () {
  "use strict";

  const DATA = window.DESLOP_DATA || { rules: [], perspectives: [], genres: [], samples: {} };

  const GENRE_DETAILS = {
    general: {
      title: "General prose (一般散文)",
      keep: "内容が必要とする段落・見出し・根拠ある主張のみ",
      remove: "81ルールおよび24観点に該当するすべての機械生成表現・水増し構造",
      adjust: "デフォルト密度上限（太字 3.0/1000字、見出し 5.0/1000字、リスト比率 0.6）",
      corpus: "corpus/general/weekly-meeting-minutes-ja.md (2,389字: 6 hits → 6 open, 0 exempt)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre general corpus/general/weekly-meeting-minutes-ja.md"
    },
    readme: {
      title: "README (リポジトリ導入文書)",
      keep: "インストール・実行手順の番号付きリスト、機能インベントリの箇条書き、コードブロック",
      remove: "抽象的なタグライン、形容詞を並べた「Why X?」節、末尾の勧誘文",
      adjust: "DEN-06（リスト比率）免除 / DEN-05（見出し密度）上限を 8.0/1000字へ緩和",
      corpus: "corpus/readme/date-utils-readme-ja.md (554字: 2 hits → 2 open, リスト比率は自動免除)",
      cmd: "python3 skills/deslop/scripts/detect.py README.md"
    },
    reference: {
      title: "API / CLI Reference (仕様・リファレンス)",
      keep: "表、パラメータ一覧、太字のパラメータ名・オプション名、簡潔な体言止め・断片文",
      remove: "物語調の導入文、重要性の主張（「重要な役割を果たします」）、未確認仕様の無断断定",
      adjust: "DEN-01（太字）、DEN-04（太字ラベル箇条書き）、DEN-05（見出し）、DEN-06（リスト）、DEN-08（文長均一性）を免除",
      corpus: "corpus/reference/deploy-cli-reference-ja.md (878字: 4 hits → 3 open, 1 genre-exempt)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre reference corpus/reference/deploy-cli-reference-ja.md"
    },
    tutorial: {
      title: "Tutorial (手順を追う入門記事)",
      keep: "番号付き手順、ステップごとの見出し、冒頭での到達結果の短い明示",
      remove: "ステップ間の道案内（「次に〜を見ていきましょう」）、読者への賞賛、まとめ節での反復",
      adjust: "DEN-05（見出し）・DEN-06（リスト）を免除 / DEN-03（感嘆符）上限を 0 に厳格化",
      corpus: "corpus/tutorial/github-actions-ci-tutorial-ja.md (1,682字: 4 hits → 3 open, 1 genre-exempt)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre tutorial corpus/tutorial/github-actions-ci-tutorial-ja.md"
    },
    article: {
      title: "Blog / Article (技術記事・論考)",
      keep: "数段落ごとの見出し、記事が答える課題と著者の立場（それぞれ1回ずつ明記）",
      remove: "SEO型見出し（「〜とは？」）、FAQ水増し、本文を繰り返すだけの「## まとめ」",
      adjust: "DEN-01 上限 1.5 / DEN-04 上限 0 / DEN-05 上限 3.0 / DEN-06 上限 0.3（散文中心を強制）",
      corpus: "corpus/article/code-review-ja.md (1,728字: 8 hits → 8 open, 太字箇条書きとまとめ反復を検出)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre article corpus/article/code-review-ja.md"
    },
    spec: {
      title: "Spec / RFC (要件定義・設計書)",
      keep: "MUST / SHOULD、番号付き要件定義、設計判断の根拠（Rationale）節",
      remove: "要件に対する曖昧なぼかし、宣伝調の導入",
      adjust: "DEN-05・DEN-06・DEN-08 を免除 / DEN-03（感嘆符）上限を 0 に厳格化",
      corpus: "corpus/spec/equipment-requirements-ja.md (2,609字: 6 hits → 4 open, 2 genre-exempt)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre spec corpus/spec/equipment-requirements-ja.md"
    },
    pr: {
      title: "PR Description (プルリクエスト説明文)",
      keep: "何を変えたか、なぜ変えたか、どう検証したか",
      remove: "空欄のまま残されたテンプレート節、1文だけの節に対する見出し、装飾絵文字",
      adjust: "DEN-06（変更点の箇条書き）免除 / DEN-03（感嘆符）・DEN-10（水平線）上限を 0 に厳格化",
      corpus: "corpus/pr/login-validation-pr-ja.md (465字: 0 hits → 0 open, 簡潔な変更箇条書きを正当と判定)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre pr corpus/pr/login-validation-pr-ja.md"
    },
    message: {
      title: "Email / Message (人宛ての連絡・メール)",
      keep: "言語ごとの慣習的な挨拶・結び（「いつもお世話になっております」）、返信への誘い",
      remove: "AIチャットの結び（「参考になれば幸いです」）、依頼内容のくどい言い直し、過剰な謝罪の重ね掛け",
      adjust: "EN-20・JA-21（問い合わせへの誘い）を免除 / DEN-04 上限 0、DEN-05 上限 0、DEN-06 上限 0.3",
      corpus: "corpus/message/invoice-misdelivery-apology-ja.md (986字: 0 hits → 0 open, 業務連絡の慣習を保持)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre message corpus/message/invoice-misdelivery-apology-ja.md"
    },
    changelog: {
      title: "Changelog (リリースノート・変更履歴)",
      keep: "変更点1件につき1つの箇条書き、リリースごとの見出し",
      remove: "変更点に添えられた宣伝形容詞（「革新的な」「強力な新機能」）",
      adjust: "DEN-05（見出し）・DEN-06（リスト）・DEN-08（文長均一性）を免除（CHANGELOG* 等はファイル名で自動判定）",
      corpus: "corpus/changelog/app-store-release-notes-ja.md (539字: 0 hits → 0 open)",
      cmd: "python3 skills/deslop/scripts/detect.py CHANGELOG.md"
    },
    template: {
      title: "Template (利用者が埋める様式・下書き)",
      keep: "利用者が入力するフィールド（`[氏名]`, `[HH:MM]`, `[取引先会社名]`）と太字ラベル",
      remove: "チャット応答の残骸、入力欄の周囲の水増し文、勝手に埋められた架空の値",
      adjust: "ART-07（未入力プレースホルダ：唯一ジャンル免除が許されるartifactルール）・DEN-04（太字ラベル）を免除",
      corpus: "corpus/template/checkout-postmortem-en.md (3,081字: 54 hits → 2 open, 52個の入力欄とラベルを正当免除)",
      cmd: "python3 skills/deslop/scripts/detect.py --genre template corpus/template/checkout-postmortem-en.md"
    }
  };

  const PHASES = [
    {
      num: "PHASE 01",
      id: "INVENTORY",
      title: "INVENTORY — 対象文書の特定とSHA-256スナップショット",
      desc: "編集を始める前に、対象ファイル・言語・ジャンルを特定し、原本を `<out>/original/` に退避して SHA-256 ハッシュを記録します。Git管理外や未コミット変更がある場合は自動的にコピーモード（`--copy`）を選択し、元のファイルを傷つけません。",
      points: [
        "snapshot.py が全対象ファイルの SHA-256 と指定ジャンルを snapshot.json に固定",
        "以降の detect.py / preserve_check.py / contract_check.py はすべてこの原本と比較",
        "ファイル名から README* は readme、CHANGELOG* は changelog を自動推論"
      ],
      code: `$ python3 skills/deslop/scripts/snapshot.py /tmp/deslop-run \\
    --root . --genre article examples/before.ja.md

# /tmp/deslop-run/snapshot.json
{
  "version": 1,
  "root": "/Users/you/project",
  "mode": "in-place",
  "files": [
    {
      "path": "examples/before.ja.md",
      "sha256": "a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447",
      "genre": "article"
    }
  ]
}`
    },
    {
      num: "PHASE 02",
      id: "VOICE",
      title: "VOICE — 著者の文体・表記規則の抽出と固定",
      desc: "1語でも書き換える前に、スタイルガイドや著者の過去文書、または対象文書内の人間らしい段落から 3〜8 個の文体ルール（`voice.rules`）を抽出・記録します。別のAI風文体へのすり替わり（STR-16 Voice drift）を防ぎます。",
      points: [
        "文末の敬体・常体（です・ます調 / だ・である調）と読者への呼びかけ有無を固定",
        "製品名・設定キーを英語コード書式のまま保つかを明文化",
        "日本語特有の表記（欧文前後の空白、全角・半角括弧、カタカナ長音「サーバー/サーバ」）を保持"
      ],
      code: `// findings.json 内の voice レコード
"voice": {
  "source": "samples",
  "rules": [
    "です・ます調、読者を「あなた」と呼ばない",
    "製品名（tilecache）と設定名（ttl_seconds, max_entries）は英語のままコード書式で書く",
    "欧文・数値の前後には半角空白を1つ入れる（TTL は 300 秒です）",
    "見出しは疑問形にせず、節の対象を名詞句で置く"
  ]
}`
    },
    {
      num: "PHASE 03",
      id: "DETECT",
      title: "DETECT — 81ルール走査＋11種の構造キュー＋24観点の全文読解",
      desc: "`detect.py` を実行して `detect.before.json` を出力します。フロントマター・コードブロック・URLを正確にマスクした上で、チャット残骸・語彙・無出典統計・文書密度を検出し、さらに文書の骨格から構造観点のキュー（`cues`）を提示します。",
      points: [
        "81の決定論的ルール（ART 9 / EN 27 / JA 33 / EMO 1 / CNT 1 / DEN 10）を一括検査",
        "文書形状から11種の構造・内容観点（予告開幕、まとめ反復、3項目リスト偏重など）を自動キュー出し",
        "「どこがAIっぽいか教えて」とだけ聞かれた場合はこのフェーズで停止し、ファイルを一切変更しない"
      ],
      code: `$ python3 skills/deslop/scripts/detect.py \\
    --snapshot /tmp/deslop-run --out /tmp/deslop-run/detect.before.json

examples/before.ja.md:1:22 JA-06 最大限に引き出
examples/before.ja.md:1:30 JA-14 完全ガイド
examples/before.ja.md:1:36 EMO-01 🚀
examples/before.ja.md:7:65 CNT-01 30%
examples/before.ja.md:13:25 JA-04 することができます
examples/before.ja.md:3 STR-01 cue: the opening sentence announces what the document will do
examples/before.ja.md:5 STR-14 cue: heading phrased as the reader's question: ## キャッシュとは？
1 files, 30 hits, 30 open, 0 exempt, 3 cues (exit 1)`
    },
    {
      num: "PHASE 04",
      id: "REWRITE",
      title: "REWRITE — 内容 → 構造 → 文 → 語のトップダウン推敲",
      desc: "表面的な類語置換（`重要` → `肝心`、`leverage` → `utilize`）は行いません。まず内容パス（4つのテスト）で空疎な文を削除し、次に構造（予告・まとめ・過剰箇条書き）を整理し、最後に残った文と語を文書内の事実だけで直接書き直します。",
      points: [
        "1. Content: 情報・置換・読者・裏づけの4テストに落ちる主張を言い換えず削除",
        "2. Structure: 予告開幕（STR-01）と反復まとめ（STR-02）を削り、細切れの箇条書きを散文に戻す",
        "3. Sentences & Words: 残った文の冗長表現（JA-04 〜することができます 等）を簡潔化",
        "すべての変更をルールIDとともに findings.json（T-001...）へマージ記録"
      ],
      code: `# Before (examples/before.ja.md — 396 prose chars, 30 hits)
現代のWebアプリケーションにおいて、キャッシュは重要な役割を果たしています。
多くの企業がキャッシュを導入しており、導入企業の約30%がレスポンス改善を
実感していると言われています。(...)

# After (examples/after.ja.md — 105 prose chars, 0 hits)
\`tilecache\` のキャッシュ設定は TTL、容量、退避方式の3項目です。
TTL は \`ttl_seconds\` で指定し、既定値は 300 秒です。
容量は \`max_entries\` で指定し、既定値は 10000 件です。`
    },
    {
      num: "PHASE 05",
      id: "VERIFY",
      title: "VERIFY — 残存ヒット0・事実保存検査・コールドリード",
      desc: "書き換え後に再度 `detect.py` と `preserve_check.py` を実行します。1件でも未処理ヒットや未申告の事実変更（数値・URL・コード・脚注の消失または追加）があれば Exit 1 となり、REWRITE へ差し戻されます。",
      points: [
        "detect.py --exempt findings.json が Exit 0（未処理ヒット 0）であること",
        "preserve_check.py が Exit 0（数値・URL・コードブロックの無断変更 0）であること",
        "全文を通し読みする Cold Read と、サブエージェント利用可能時のブラインド独立読解を実施"
      ],
      code: `$ python3 skills/deslop/scripts/detect.py --snapshot /tmp/deslop-run \\
    --exempt /tmp/deslop-run/findings.json --out /tmp/deslop-run/detect.after.json
1 files, 0 hits, 0 open, 0 exempt, 0 cues (exit 0)

$ python3 skills/deslop/scripts/preserve_check.py /tmp/deslop-run
# 数値 (300, 10000)、URL (https://example.com/tilecache/docs)、
# インラインコード (tilecache, ttl_seconds, max_entries)、TOMLコードブロックの生存を確認
# 削除した装飾統計「30」は preservation の理由記録と照合 → exit 0`
    },
    {
      num: "PHASE 06",
      id: "REPORT",
      title: "REPORT — 監査レポート生成と contract_check.py による最終証明",
      desc: "`findings.py report` が SHA-256 署名付きの `report.md` を生成し、最後に `contract_check.py` が原本スナップショットから全検査を再計算します。記録漏れやキュー無視（cued観点のN/A記録）があれば契約違反として失敗します。",
      points: [
        "findings.json の SHA-256 スタンプを埋め込んだ report.md を自動レンダリング",
        "contract_check.py はキャッシュを信用せず original/ と作業コピーをゼロから再スキャン",
        "全81ルール・全24観点・全事実保存の整合性が取れたときのみ `contract ok` (exit 0)"
      ],
      code: `$ python3 skills/deslop/scripts/findings.py report /tmp/deslop-run
report.md written; 0 open hits

$ python3 skills/deslop/scripts/contract_check.py /tmp/deslop-run
contract ok`
    }
  ];

  const HOST_COMMANDS = {
    all: {
      label: "すべての導入済みエージェントに一括リンク（Claude Code / Codex / Antigravity）",
      install: `git clone https://github.com/shingoimota/deslop.git
cd deslop
make link`,
      verify: `make status
make check`
    },
    claude: {
      label: "Claude Code (~/.claude/skills/deslop) のみにリンク",
      install: `make link AGENT=claude
# または特定リポジトリの .claude/skills に導入する場合:
make link PROJECT=/path/to/your/repo`,
      verify: `# Claude Code チャット内で実行:
/deslop docs/ README.md`
    },
    codex: {
      label: "Codex (~/.codex/skills/deslop) のみにリンク",
      install: `make link AGENT=codex`,
      verify: `# Codex 実行時に指示:
"README.md と docs/ から AI 文体を除去して"`
    },
    agy: {
      label: "Antigravity (~/.gemini/antigravity-cli/skills/deslop) のみにリンク",
      install: `make link AGENT=agy`,
      verify: `# Antigravity チャット内で指示:
"deslop スキルで docs/ の記事を推敲して"`
    },
    cli: {
      label: "エージェントを使わず、検出器 (detect.py) を単体CLI・CIとして実行",
      install: `# Python 3.10+ 標準ライブラリのみで即実行可能（pip install 不要）
make detect TARGET=docs/
python3 skills/deslop/scripts/detect.py --root . README.md docs/`,
      verify: `# ジャンル指定付き実行（終了コード 0 = ヒットなし / 1 = ヒットあり）:
python3 skills/deslop/scripts/detect.py --genre article --genre docs/api.md=reference docs/`
    }
  };

  /* --------------------------------------------------------------------------
     Utility: HTML Escape & Copy to Clipboard
     -------------------------------------------------------------------------- */
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setupCopyButtons() {
    document.addEventListener("click", function (e) {
      const btn = e.target.closest("[data-copy-target], [data-copy-text]");
      if (!btn) return;
      let text = btn.getAttribute("data-copy-text");
      if (!text) {
        const targetId = btn.getAttribute("data-copy-target");
        const targetEl = document.getElementById(targetId);
        if (targetEl) text = targetEl.textContent.trim();
      }
      if (!text) return;

      const originalLabel = btn.getAttribute("data-orig-label") || btn.textContent;
      btn.setAttribute("data-orig-label", originalLabel);

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(showCopied, fallbackCopy);
      } else {
        fallbackCopy();
      }

      function fallbackCopy() {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          showCopied();
        } catch (_) {}
        document.body.removeChild(ta);
      }

      function showCopied() {
        btn.classList.add("is-copied");
        btn.textContent = "Copied!";
        setTimeout(function () {
          btn.classList.remove("is-copied");
          btn.textContent = originalLabel;
        }, 1600);
      }
    });
  }

  /* --------------------------------------------------------------------------
     Hero Proof Sheet Interactive Viewer
     -------------------------------------------------------------------------- */
  let heroLang = "ja";
  let heroMode = "redline"; // "redline" | "after" | "before"

  function renderHeroProof() {
    const container = document.getElementById("hero-proof-body");
    const statsBar = document.getElementById("hero-proof-stats");
    const fileLabel = document.getElementById("hero-file-label");
    if (!container || !statsBar) return;

    if (heroLang === "ja") {
      fileLabel.textContent = heroMode === "after" ? "examples/after.ja.md" : "examples/before.ja.md";
      statsBar.innerHTML = `
        <div class="proof-stat-cell">
          <span class="proof-stat-label">検出ヒット数</span>
          <span class="proof-stat-val"><span class="bad">30 hits</span><span class="arrow">→</span><span class="good">0 open</span></span>
        </div>
        <div class="proof-stat-cell">
          <span class="proof-stat-label">散文文字数 (Prose)</span>
          <span class="proof-stat-val">396字<span class="arrow">→</span><span class="good">105字 (−73%)</span></span>
        </div>
        <div class="proof-stat-cell">
          <span class="proof-stat-label">保護された事実</span>
          <span class="proof-stat-val"><span class="good">数値2・URL1・TOML1</span></span>
        </div>
      `;

      if (heroMode === "redline") {
        container.innerHTML = `
          <div class="proof-line"><span class="proof-line-num">01</span># キャッシュ設定<span class="mark-slop">ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀</span><span class="rule-pill tier-lexical">JA-06</span><span class="rule-pill tier-lexical">JA-14</span><span class="rule-pill tier-lexical">EMO-01</span></div>
          <div class="proof-line"><span class="proof-line-num">03</span><span class="mark-slop">本記事では、\`tilecache\` のキャッシュ設定について詳しく解説します。</span><span class="rule-pill tier-lexical">JA-08</span><span class="rule-pill tier-cue">STR-01</span></div>
          <div class="proof-line"><span class="proof-line-num">05</span><span class="mark-cue">## キャッシュとは？</span> <span class="rule-pill tier-lexical">JA-17</span><span class="rule-pill tier-cue">STR-14</span> <span class="mark-slop">重要な役割を果たし... 導入企業の約30%が実感していると言われています... システム全体の安定性を支える基盤と言っても過言ではありません。</span><span class="rule-pill tier-lexical">JA-03</span><span class="rule-pill tier-content">CNT-01</span><span class="rule-pill tier-lexical">JA-31</span><span class="rule-pill tier-lexical">JA-02</span></div>
          <div class="proof-line"><span class="proof-line-num">11</span><span class="mark-slop">設定のポイントとしては、以下の3つが挙げられます。</span><span class="rule-pill tier-lexical">JA-13</span><span class="rule-pill tier-density">DEN-04</span> / - **TTL**: 有効期限を設定<span class="mark-slop">することができます</span>。<span class="rule-pill tier-lexical">JA-04</span></div>
          <div class="proof-line"><span class="proof-line-num">17</span>TTL は <span class="mark-keep">\`ttl_seconds\`</span> (既定値 <span class="mark-keep">300</span> 秒)、容量は <span class="mark-keep">\`max_entries\`</span> (既定値 <span class="mark-keep">10000</span> 件) で指定します。</div>
          <div class="proof-line"><span class="proof-line-num">27</span><span class="mark-cue">## まとめ</span> <span class="rule-pill tier-lexical">JA-09</span><span class="rule-pill tier-cue">STR-02</span> <span class="mark-slop">いかがでしたか？... 飛躍的に向上させることが期待されます。</span>詳細は <span class="mark-keep">https://example.com/tilecache/docs</span> を参照。<span class="mark-slop">参考になれば幸いです！</span><span class="rule-pill tier-artifact">ART-04</span></div>
          <div class="hero-after-dock">
            <div class="hero-after-dock-head">
              <span>✓ REWRITTEN RESULT (examples/after.ja.md · 396字 → 105字)</span>
              <span>0 open hits · preserve_check OK</span>
            </div>
            <div><span class="mark-keep">\`tilecache\`</span> のキャッシュ設定は TTL、容量、退避方式の3項目です。TTL は <span class="mark-keep">\`ttl_seconds\`</span> で指定し、既定値は <span class="mark-keep">300</span> 秒です。容量は <span class="mark-keep">\`max_entries\`</span> で指定し、既定値は <span class="mark-keep">10000</span> 件です。（＋ <code>[cache]</code> TOMLブロック ＆ 公式URL完全保持）</div>
          </div>
        `;
      } else if (heroMode === "after") {
        container.innerHTML = `
          <div class="proof-line"><span class="proof-line-num">01</span><strong># キャッシュ設定</strong></div>
          <div class="proof-line"><span class="proof-line-num">03</span><span class="mark-keep">\`tilecache\`</span> のキャッシュ設定は TTL、容量、退避方式の3項目です。TTL は <span class="mark-keep">\`ttl_seconds\`</span> で指定し、既定値は <span class="mark-keep">300</span> 秒です。容量は <span class="mark-keep">\`max_entries\`</span> で指定し、既定値は <span class="mark-keep">10000</span> 件です。</div>
          <div class="proof-code-block">[cache]\nttl_seconds = 300\nmax_entries = 10000</div>
          <div class="proof-line"><span class="proof-line-num">11</span>詳細は <span class="mark-keep">https://example.com/tilecache/docs</span> を参照してください。</div>
          <div style="margin-top: 18px; padding: 12px; background: var(--preserve-bg); border: 1px solid var(--preserve-border); border-radius: 4px; color: var(--preserve-fg); font-family: var(--font-mono); font-size: 0.78rem;">
            ✓ detect.py: 0 open hits, 0 cues (exit 0)<br>
            ✓ preserve_check.py: 300, 10000, ttl_seconds, max_entries, TOML block, URL すべて生存確認 (exit 0)<br>
            ✓ 削除された「30%」は出典なき装飾統計 (CNT-01 / CON-03) として preservation に理由を記録済み
          </div>
        `;
      } else {
        const raw = DATA.samples.ja_cache ? DATA.samples.ja_cache.before : "";
        container.innerHTML = raw
          .split("\n")
          .map(function (line, idx) {
            return `<div class="proof-line"><span class="proof-line-num">${String(idx + 1).padStart(2, "0")}</span>${escapeHtml(line) || "&nbsp;"}</div>`;
          })
          .join("");
      }
    } else {
      fileLabel.textContent = heroMode === "after" ? "examples/after.en.md" : "examples/before.en.md";
      statsBar.innerHTML = `
        <div class="proof-stat-cell">
          <span class="proof-stat-label">Detected Hits</span>
          <span class="proof-stat-val"><span class="bad">22 hits</span><span class="arrow">→</span><span class="good">0 open</span></span>
        </div>
        <div class="proof-stat-cell">
          <span class="proof-stat-label">Prose Chars</span>
          <span class="proof-stat-val">634 chars<span class="arrow">→</span><span class="good">176 (−72%)</span></span>
        </div>
        <div class="proof-stat-cell">
          <span class="proof-stat-label">Facts Preserved</span>
          <span class="proof-stat-val"><span class="good">2 nums · 1 URL · 1 TOML</span></span>
        </div>
      `;

      if (heroMode === "redline") {
        container.innerHTML = `
          <div class="proof-line"><span class="proof-line-num">01</span># <span class="mark-slop">Unlocking the Power of</span> Tile Caching: <span class="mark-slop">A Comprehensive Guide</span><span class="rule-pill tier-lexical">EN-03</span><span class="rule-pill tier-lexical">EN-14</span></div>
          <div class="proof-line"><span class="proof-line-num">03</span><span class="mark-slop">Certainly! Here's a revised overview of caching in \`tilecache\`.</span><span class="rule-pill tier-artifact">ART-01</span><span class="rule-pill tier-artifact">ART-08</span></div>
          <div class="proof-line"><span class="proof-line-num">05</span><span class="mark-slop">In today's fast-paced digital landscape, performance plays a crucial role in user experience. Let's dive into how tilecache can help you leverage caching to deliver a seamless experience — whether you're a seasoned engineer or just getting started.</span><span class="rule-pill tier-lexical">EN-07</span><span class="rule-pill tier-lexical">EN-05</span><span class="rule-pill tier-lexical">EN-12</span><span class="rule-pill tier-lexical">EN-03</span><span class="rule-pill tier-lexical">EN-04</span><span class="rule-pill tier-lexical">EN-15</span></div>
          <div class="proof-line"><span class="proof-line-num">13</span>TTL is set with <span class="mark-keep">\`ttl_seconds\`</span>; the default is <span class="mark-keep">300</span> seconds. Capacity is set with <span class="mark-keep">\`max_entries\`</span>; the default is <span class="mark-keep">10000</span> entries.</div>
          <div class="proof-code-block">[cache]\nttl_seconds = 300\nmax_entries = 10000</div>
          <div class="proof-line"><span class="proof-line-num">21</span><span class="mark-slop">It's important to note that caching isn't just about speed — it's about reliability, scalability, and peace of mind. Moreover, a robust cache configuration underscores the importance of thoughtful system design.</span><span class="rule-pill tier-lexical">EN-06</span><span class="rule-pill tier-lexical">EN-10</span><span class="rule-pill tier-lexical">EN-09</span><span class="rule-pill tier-lexical">EN-04</span><span class="rule-pill tier-lexical">EN-13</span></div>
          <div class="proof-line"><span class="proof-line-num">23</span><span class="mark-cue">## Conclusion</span><span class="rule-pill tier-cue">STR-02</span></div>
          <div class="proof-line"><span class="proof-line-num">25</span><span class="mark-slop">In conclusion, tuning TTL and capacity can potentially transform your application.</span> See <span class="mark-keep">https://example.com/tilecache/docs</span> for details. <span class="mark-slop">I hope this helps!</span><span class="rule-pill tier-lexical">EN-08</span><span class="rule-pill tier-lexical">EN-16</span><span class="rule-pill tier-artifact">ART-03</span></div>
        `;
      } else if (heroMode === "after") {
        container.innerHTML = `
          <div class="proof-line"><span class="proof-line-num">01</span><strong># Tile caching</strong></div>
          <div class="proof-line"><span class="proof-line-num">03</span><span class="mark-keep">\`tilecache\`</span> has three cache settings: TTL, capacity and eviction. TTL is set with <span class="mark-keep">\`ttl_seconds\`</span>; the default is <span class="mark-keep">300</span> seconds. Capacity is set with <span class="mark-keep">\`max_entries\`</span>; the default is <span class="mark-keep">10000</span> entries.</div>
          <div class="proof-code-block">[cache]\nttl_seconds = 300\nmax_entries = 10000</div>
          <div class="proof-line"><span class="proof-line-num">11</span>See <span class="mark-keep">https://example.com/tilecache/docs</span> for details.</div>
          <div style="margin-top: 18px; padding: 12px; background: var(--preserve-bg); border: 1px solid var(--preserve-border); border-radius: 4px; color: var(--preserve-fg); font-family: var(--font-mono); font-size: 0.78rem;">
            ✓ detect.py: 0 open hits, 0 cues (exit 0)<br>
            ✓ preserve_check.py: 300, 10000, ttl_seconds, max_entries, TOML block, URL all verified (exit 0)
          </div>
        `;
      } else {
        const raw = DATA.samples.en_cache ? DATA.samples.en_cache.before : "";
        container.innerHTML = raw
          .split("\n")
          .map(function (line, idx) {
            return `<div class="proof-line"><span class="proof-line-num">${String(idx + 1).padStart(2, "0")}</span>${escapeHtml(line) || "&nbsp;"}</div>`;
          })
          .join("");
      }
    }
  }

  function setupHeroControls() {
    document.querySelectorAll("[data-hero-mode]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        heroMode = btn.getAttribute("data-hero-mode");
        document.querySelectorAll("[data-hero-mode]").forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
          b.setAttribute("aria-selected", b === btn ? "true" : "false");
        });
        renderHeroProof();
      });
    });

    document.querySelectorAll("[data-hero-lang]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        heroLang = btn.getAttribute("data-hero-lang");
        document.querySelectorAll("[data-hero-lang]").forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });
        renderHeroProof();
      });
    });

    renderHeroProof();
  }

  /* --------------------------------------------------------------------------
     Live Detector Sandbox (#live-detector)
     -------------------------------------------------------------------------- */
  let currentSampleKey = "ja_cache";
  let currentGenre = "general";
  let workbenchView = "annotated"; // "annotated" | "edit" | "after"
  let currentText = DATA.samples.ja_cache ? DATA.samples.ja_cache.before : "";

  function clientSideDetect(text, genreId) {
    const genreObj = DATA.genres.find(function (g) { return g.id === genreId; }) || { id: "general", exempt: {}, limits: {} };
    const hasKana = /[\u3040-\u30ff]/.test(text);
    const kanaCount = (text.match(/[\u3040-\u30ff]/g) || []).length;
    const kanjiCount = (text.match(/[\u4e00-\u9fff]/g) || []).length;
    const latinCount = (text.match(/[A-Za-z]+/g) || []).length;
    const lang = hasKana && (kanaCount + kanjiCount > latinCount) ? "ja" : "en";

    // Mask fenced code blocks so code is not flagged as prose
    const masked = text.replace(/```[\s\S]*?```/g, function (m) {
      return m.replace(/[^\n]/g, " ");
    });

    const lines = text.split("\n");
    const starts = [0];
    for (let i = 0; i < lines.length - 1; i++) {
      starts.push(starts[starts.length - 1] + lines[i].length + 1);
    }

    function lineColAt(offset) {
      let lo = 0, hi = starts.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (starts[mid] <= offset) lo = mid + 1;
        else hi = mid - 1;
      }
      const lineIdx = Math.max(0, hi);
      return { line: lineIdx + 1, col: offset - starts[lineIdx] + 1 };
    }

    const hits = [];
    DATA.rules.forEach(function (rule) {
      if (!rule.pattern) return;
      if (rule.lang !== "any" && rule.lang !== lang) return;
      try {
        let pat = rule.pattern.replace(/\(\?-i:([^)]+)\)/g, "$1");
        let flags = "g";
        if (rule.flags && rule.flags.indexOf("i") !== -1) flags += "i";
        if (rule.flags && rule.flags.indexOf("m") !== -1) flags += "m";
        if (pat.indexOf("\\U") !== -1) {
          pat = pat.replace(/\\U000([0-9A-Fa-f]{5})/g, "\\u{$1}");
          flags += "u";
        }
        const rx = new RegExp(pat, flags);
        let m;
        while ((m = rx.exec(masked)) !== null) {
          if (!m[0] || !m[0].trim()) {
            rx.lastIndex++;
            continue;
          }
          const loc = lineColAt(m.index);
          const exemptReason = genreObj.exempt && genreObj.exempt[rule.id];
          hits.push({
            line: loc.line,
            col: loc.col,
            rule: rule.id,
            tier: rule.tier,
            text: m[0].trim(),
            exempt: Boolean(exemptReason),
            exempt_reason: exemptReason ? `genre:${genreId}: ${exemptReason}` : null,
            note: rule.note
          });
        }
      } catch (_) {}
    });

    const bodyLines = masked.split("\n").filter(function (l) {
      const s = l.trim();
      return s && !/^#{1,6}\s/.test(s) && !s.startsWith("|");
    });
    const chars = bodyLines.reduce(function (acc, l) { return acc + l.trim().length; }, 0);
    const boldCount = (masked.match(/\*\*[^*\n]+\*\*|__[^_\n]+__/g) || []).length;
    const boldleadCount = (masked.match(/^[^\S\r\n]*(?:[-*+]|\d+[.)])\s+\*\*[^*\n]+(?:\*\*\s*[:：]|[:：]\*\*)/gm) || []).length;
    const dashCount = (masked.match(/—/g) || []).length;
    const per = chars ? 1000 / chars : 0;

    const metrics = {
      chars: chars,
      sentences: Math.max(1, (masked.match(/[。！？!?]|\.(?:\s|$)/g) || []).length),
      bold_per_1000: +(boldCount * per).toFixed(2),
      dash_per_1000: +(dashCount * per).toFixed(2),
      boldlead_items: boldleadCount,
      heading_per_1000: +((masked.match(/^#{1,6}\s/gm) || []).length * per).toFixed(2)
    };

    hits.sort(function (a, b) {
      return a.line - b.line || a.col - b.col;
    });

    const openCount = hits.filter(function (h) { return !h.exempt; }).length;
    return {
      lang: lang,
      genre: genreId,
      metrics: metrics,
      hits: hits,
      cues: [],
      summary: {
        total: hits.length,
        open: openCount,
        exempt: hits.length - openCount,
        cues: 0
      }
    };
  }

  // Each scan gets a generation; a response renders only if no newer scan started.
  let scanGeneration = 0;

  function runSandboxScan() {
    const generation = ++scanGeneration;
    const text = currentText;
    const genre = currentGenre;
    const sample = DATA.samples[currentSampleKey];
    if (sample && text === sample.before && genre === sample.genre && sample.before_scan) {
      renderSandboxResult(sample.before_scan);
      return;
    }

    fetch("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text, genre: genre, markdown: true })
    })
      .then(function (res) {
        if (!res.ok) throw new Error("fallback");
        return res.json();
      })
      .then(function (data) {
        if (generation === scanGeneration) renderSandboxResult(data);
      })
      .catch(function () {
        if (generation !== scanGeneration) return;
        const partial = clientSideDetect(text, genre);
        partial.fallback = true;
        renderSandboxResult(partial);
      });
  }

  function renderAnnotatedText(text, scanResult) {
    const lineHits = {};
    (scanResult.hits || []).forEach(function (h) {
      if (h.tier === "density") return;
      if (!lineHits[h.line]) lineHits[h.line] = [];
      lineHits[h.line].push(h);
    });
    const lineCues = {};
    (scanResult.cues || []).forEach(function (c) {
      if (!lineCues[c.line]) lineCues[c.line] = [];
      lineCues[c.line].push(c);
    });

    return text
      .split("\n")
      .map(function (line, idx) {
        const lineNum = idx + 1;
        let html = escapeHtml(line);
        const hitsOnLine = lineHits[lineNum] || [];
        hitsOnLine.forEach(function (h) {
          if (!h.text) return;
          const escapedTarget = escapeHtml(h.text);
          if (escapedTarget && html.indexOf(escapedTarget) !== -1) {
            const cls = h.exempt ? "mark-keep" : "mark-slop";
            html = html.replace(
              escapedTarget,
              `<span class="${cls}" title="${escapeHtml(h.rule + ": " + (h.note || ""))}">${escapedTarget}</span><span class="rule-pill tier-${h.tier}">${h.rule}</span>`
            );
          }
        });
        const cuesOnLine = lineCues[lineNum] || [];
        cuesOnLine.forEach(function (c) {
          html += ` <span class="rule-pill tier-cue" title="${escapeHtml(c.why)}">${c.perspective} cue</span>`;
        });
        return `<div class="proof-line" id="wb-line-${lineNum}"><span class="proof-line-num">${String(lineNum).padStart(2, "0")}</span>${html || "&nbsp;"}</div>`;
      })
      .join("");
  }

  function renderSandboxResult(result) {
    const leftContainer = document.getElementById("workbench-left-content");
    const badgesEl = document.getElementById("detector-summary-badges");
    const hitsListEl = document.getElementById("detector-hits-list");
    const densityGridEl = document.getElementById("detector-density-grid");
    const cliCmdEl = document.getElementById("workbench-cli-cmd");
    const sample = DATA.samples[currentSampleKey];

    if (cliCmdEl) {
      const targetPath = sample ? sample.shortLabel : "docs/target.md";
      cliCmdEl.textContent = `python3 skills/deslop/scripts/detect.py --genre ${currentGenre} ${targetPath}`;
    }

    if (leftContainer) {
      if (workbenchView === "edit") {
        // Keep an existing textarea so focus, selection and IME composition survive a scan.
        const existing = document.getElementById("sandbox-textarea");
        if (existing) {
          // Only a sample switch makes these differ; typing keeps them equal.
          if (existing.value !== currentText) existing.value = currentText;
        } else {
          leftContainer.innerHTML = `<textarea id="sandbox-textarea" class="editor-textarea" aria-label="検査対象のMarkdownテキスト">${escapeHtml(currentText)}</textarea>`;
          const ta = document.getElementById("sandbox-textarea");
          ta.addEventListener("input", function () {
            currentText = ta.value;
            runSandboxScan();
          });
        }
      } else if (workbenchView === "after") {
        if (sample && sample.after) {
          leftContainer.innerHTML = `<div class="annotated-preview">${renderAnnotatedText(sample.after, sample.after_scan || { hits: [], cues: [] })}</div>`;
        } else {
          leftContainer.innerHTML = `<div class="annotated-preview" style="color: var(--ink-secondary);">このコーパス文書は入力専用サンプル（<code>corpus/</code>）です。エージェントで <code>/deslop</code> を実行すると、右ペインの検出ヒットと構造キューに基づき、事実を保持したまま推敲された文書が出力されます。</div>`;
        }
      } else {
        leftContainer.innerHTML = `<div class="annotated-preview">${renderAnnotatedText(currentText, result)}</div>`;
      }
    }

    const sourceLabelEl = document.getElementById("detector-source-label");
    if (sourceLabelEl) {
      sourceLabelEl.textContent = result.fallback ? "BROWSER FALLBACK (INCOMPLETE)" : "DETECT.PY OUTPUT";
    }

    if (badgesEl) {
      const openCount = result.summary ? result.summary.open : 0;
      const exemptCount = result.summary ? result.summary.exempt : 0;
      const cueCount = result.summary ? result.summary.cues : 0;
      const exitCode = openCount === 0 ? 0 : 1;
      const skipped = DATA.rules.filter(function (r) { return !r.pattern; }).map(function (r) { return r.id; });
      badgesEl.innerHTML = result.fallback ? `
        <span class="term-badge is-fail" title="Not checked: ${escapeHtml(skipped.join(", "))}, structural cues">detect.py unavailable · ${openCount} pattern hits, ${skipped.length} rules and cues not checked</span>
      ` : `
        <span class="term-badge ${openCount === 0 ? "is-pass" : "is-fail"}">exit ${exitCode} · ${openCount} open hits</span>
        ${exemptCount > 0 ? `<span class="term-badge is-pass">${exemptCount} genre-exempt</span>` : ""}
        <span class="term-badge is-cue">${cueCount} cues</span>
      `;
    }

    if (hitsListEl) {
      const rows = [];
      const allHits = (result.hits || []).slice().sort(function (a, b) {
        const aDen = a.tier === "density" ? 1 : 0;
        const bDen = b.tier === "density" ? 1 : 0;
        if (aDen !== bDen) return aDen - bDen;
        return a.line - b.line || a.col - b.col;
      });
      allHits.forEach(function (h) {
        const cls = h.exempt ? "is-exempt" : (h.tier === "density" ? "is-density" : "");
        rows.push(`
          <div class="hit-row ${cls}" data-jump-line="${h.line}">
            <div class="hit-row-top">
              <span class="hit-rule-id">${escapeHtml(h.rule)} (${escapeHtml(h.tier)})${h.exempt ? " [EXEMPT]" : ""}</span>
              <span class="hit-loc">${h.tier === "density" ? "document metric" : `line ${h.line}:col ${h.col}`}</span>
            </div>
            <div class="hit-text">${escapeHtml(h.text)}</div>
            <div class="hit-note">${escapeHtml(h.exempt_reason || h.note || "")}</div>
          </div>
        `);
      });
      (result.cues || []).forEach(function (c) {
        rows.push(`
          <div class="hit-row is-cue" data-jump-line="${c.line}">
            <div class="hit-row-top">
              <span class="hit-rule-id">${escapeHtml(c.perspective)} CUE (${escapeHtml(c.name || "")})</span>
              <span class="hit-loc">line ${c.line}</span>
            </div>
            <div class="hit-text">${escapeHtml(c.why)}</div>
            <div class="hit-note">${escapeHtml(c.text)}</div>
          </div>
        `);
      });

      if (rows.length === 0) {
        hitsListEl.innerHTML = result.fallback
          ? `<div style="padding: 18px; color: var(--term-muted);">No pattern hits. detect.py is unavailable, so statistics, density rules and structural cues were not checked.</div>`
          : `<div style="padding: 18px; color: var(--term-green);">✓ No open hits or cues found (exit 0).</div>`;
      } else {
        hitsListEl.innerHTML = rows.join("");
        hitsListEl.querySelectorAll("[data-jump-line]").forEach(function (rowEl) {
          rowEl.addEventListener("click", function () {
            const lineNum = rowEl.getAttribute("data-jump-line");
            const targetLine = document.getElementById("wb-line-" + lineNum);
            if (targetLine) {
              targetLine.scrollIntoView({ behavior: "smooth", block: "center" });
              targetLine.classList.add("is-flash");
              setTimeout(function () {
                targetLine.classList.remove("is-flash");
              }, 1200);
            }
          });
        });
      }
    }

    if (densityGridEl && result.metrics) {
      const m = result.metrics;
      densityGridEl.innerHTML = `
        <div class="density-cell">
          <span class="density-cell-label">散文文字数 (chars)</span>
          <span class="density-cell-val">${m.chars || 0}</span>
        </div>
        <div class="density-cell ${m.bold_per_1000 > 3.0 ? "is-over" : ""}">
          <span class="density-cell-label">DEN-01 太字/1000字</span>
          <span class="density-cell-val">${(m.bold_per_1000 || 0).toFixed(2)} (上限 3.0)</span>
        </div>
        <div class="density-cell ${m.boldlead_items > 2 ? "is-over" : ""}">
          <span class="density-cell-label">DEN-04 太字ラベル箇条書き</span>
          <span class="density-cell-val">${m.boldlead_items || 0}件 (上限 2)</span>
        </div>
        <div class="density-cell ${(m.ending_run || 0) > 3 ? "is-over" : ""}">
          <span class="density-cell-label">DEN-07 同一文末連続</span>
          <span class="density-cell-val">${m.ending_run || 0}回 (上限 3)</span>
        </div>
      `;
    }
  }

  function setupWorkbench() {
    const sampleSelect = document.getElementById("sample-select");
    const genreSelect = document.getElementById("genre-select");

    if (sampleSelect) {
      sampleSelect.addEventListener("change", function () {
        currentSampleKey = sampleSelect.value;
        const s = DATA.samples[currentSampleKey];
        if (s) {
          currentText = s.before;
          currentGenre = s.genre;
          if (genreSelect) genreSelect.value = currentGenre;
        }
        runSandboxScan();
      });
    }

    if (genreSelect) {
      genreSelect.addEventListener("change", function () {
        currentGenre = genreSelect.value;
        runSandboxScan();
      });
    }

    document.querySelectorAll("[data-wb-view]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        workbenchView = btn.getAttribute("data-wb-view");
        document.querySelectorAll("[data-wb-view]").forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });
        runSandboxScan();
      });
    });

    runSandboxScan();
  }

  /* --------------------------------------------------------------------------
     6-Phase Run Contract Stepper (#pipeline)
     -------------------------------------------------------------------------- */
  function setupPhaseStepper() {
    const detailContainer = document.getElementById("phase-detail-container");
    const buttons = document.querySelectorAll("[data-phase-idx]");
    if (!detailContainer || !buttons.length) return;

    function renderPhase(idx) {
      const p = PHASES[idx] || PHASES[0];
      detailContainer.innerHTML = `
        <div>
          <h3 class="phase-detail-title">${escapeHtml(p.title)}</h3>
          <p class="phase-detail-desc">${escapeHtml(p.desc)}</p>
          <ul class="phase-contract-points">
            ${p.points.map(function (pt) { return `<li>${escapeHtml(pt)}</li>`; }).join("")}
          </ul>
        </div>
        <div>
          <pre class="phase-code-pre"><code>${escapeHtml(p.code)}</code></pre>
        </div>
      `;
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const idx = parseInt(btn.getAttribute("data-phase-idx"), 10);
        buttons.forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
          b.setAttribute("aria-selected", b === btn ? "true" : "false");
        });
        renderPhase(idx);
      });
    });

    renderPhase(0);
  }

  /* --------------------------------------------------------------------------
     10-Genre Explorer (#genres)
     -------------------------------------------------------------------------- */
  function setupGenreExplorer() {
    const detailEl = document.getElementById("genre-detail-card");
    const buttons = document.querySelectorAll("[data-genre-id]");
    if (!detailEl || !buttons.length) return;

    function renderGenre(gid) {
      const info = GENRE_DETAILS[gid] || GENRE_DETAILS.general;
      detailEl.innerHTML = `
        <div style="display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:8px; border-bottom:1px solid var(--border-hairline); padding-bottom:14px;">
          <h3 style="margin:0; font-family:var(--font-display); font-size:1.3rem;">${escapeHtml(info.title)}</h3>
          <code style="font-family:var(--font-mono); font-size:0.82rem; background:var(--bg-subtle); padding:3px 8px; border-radius:3px;">--genre ${escapeHtml(gid)}</code>
        </div>
        <div class="genre-spec-grid">
          <div class="genre-spec-box">
            <span class="genre-spec-label" style="color:var(--preserve-fg);">✓ 保持する慣習 (Keep)</span>
            <div style="font-size:0.88rem;">${escapeHtml(info.keep)}</div>
          </div>
          <div class="genre-spec-box">
            <span class="genre-spec-label" style="color:var(--strike-fg);">✕ 除去する対象 (Remove)</span>
            <div style="font-size:0.88rem;">${escapeHtml(info.remove)}</div>
          </div>
          <div class="genre-spec-box">
            <span class="genre-spec-label" style="color:var(--density-fg);">⚙ 検出器の自動調整</span>
            <div style="font-size:0.88rem;">${escapeHtml(info.adjust)}</div>
          </div>
        </div>
        <div style="margin-top:14px; padding:10px 12px; background:var(--preserve-bg); border:1px solid var(--preserve-border); border-radius:4px; font-family:var(--font-mono); font-size:0.78rem; color:var(--preserve-fg);">
          <strong>実コーパス検証結果 (corpus/):</strong> ${escapeHtml(info.corpus || "")}
        </div>
        <div class="quick-command-box" style="margin-top:14px;">
          <div class="quick-command-row">
            <code class="quick-command-code">${escapeHtml(info.cmd)}</code>
            <button type="button" class="copy-chip" data-copy-text="${escapeHtml(info.cmd)}">Copy</button>
          </div>
        </div>
      `;
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const gid = btn.getAttribute("data-genre-id");
        buttons.forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });
        renderGenre(gid);
      });
    });

    renderGenre("readme");
  }

  /* --------------------------------------------------------------------------
     Rule & Perspective Atlas (#rule-atlas)
     -------------------------------------------------------------------------- */
  let atlasFilter = "all";
  let atlasQuery = "";

  function renderAtlas() {
    const grid = document.getElementById("atlas-grid");
    const countEl = document.getElementById("atlas-count");
    if (!grid) return;

    const items = [];
    DATA.rules.forEach(function (r) {
      items.push({
        id: r.id,
        tier: r.tier,
        lang: r.lang,
        note: r.note,
        doc: r.doc || ""
      });
    });
    DATA.perspectives.forEach(function (p) {
      items.push({
        id: p.id,
        tier: "perspective",
        lang: "any",
        note: p.name,
        doc: p.doc || ""
      });
    });

    const filtered = items.filter(function (item) {
      if (atlasFilter === "artifact" && item.tier !== "artifact") return false;
      if (atlasFilter === "ja" && !item.id.startsWith("JA-")) return false;
      if (atlasFilter === "en" && !item.id.startsWith("EN-")) return false;
      if (atlasFilter === "density" && item.tier !== "density" && item.tier !== "content" && item.id !== "EMO-01") return false;
      if (atlasFilter === "perspective" && item.tier !== "perspective") return false;

      if (atlasQuery) {
        const q = atlasQuery.toLowerCase();
        const hay = (item.id + " " + item.note + " " + item.doc).toLowerCase();
        return hay.indexOf(q) !== -1;
      }
      return true;
    });

    if (countEl) {
      countEl.textContent = `${filtered.length} / ${items.length} 件を表示中`;
    }

    grid.innerHTML = filtered
      .map(function (it) {
        return `
        <article class="atlas-card">
          <div class="atlas-card-head">
            <span class="atlas-id">${escapeHtml(it.id)}</span>
            <span class="atlas-tier t-${escapeHtml(it.tier)}">${escapeHtml(it.tier)} · ${escapeHtml(it.lang)}</span>
          </div>
          <h4 class="atlas-note">${escapeHtml(it.note)}</h4>
          <p class="atlas-doc">${escapeHtml(it.doc.slice(0, 140))}${it.doc.length > 140 ? "…" : ""}</p>
        </article>
      `;
      })
      .join("");
  }

  function setupAtlas() {
    document.querySelectorAll("[data-atlas-filter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        atlasFilter = btn.getAttribute("data-atlas-filter");
        document.querySelectorAll("[data-atlas-filter]").forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });
        renderAtlas();
      });
    });

    const searchInput = document.getElementById("atlas-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        atlasQuery = searchInput.value.trim();
        renderAtlas();
      });
    }

    renderAtlas();
  }

  /* --------------------------------------------------------------------------
     Install Host Switcher (#install)
     -------------------------------------------------------------------------- */
  function setupInstallTabs() {
    const container = document.getElementById("install-commands-body");
    const tabs = document.querySelectorAll("[data-host-tab]");
    if (!container || !tabs.length) return;

    function renderHost(key) {
      const h = HOST_COMMANDS[key] || HOST_COMMANDS.all;
      container.innerHTML = `
        <p style="margin:0 0 12px; font-size:0.88rem; color:var(--term-muted);">${escapeHtml(h.label)}</p>
        <div class="cmd-block">
          <div class="cmd-block-head">
            <span>1. インストール / 実行コマンド</span>
            <button type="button" class="copy-chip" data-copy-text="${escapeHtml(h.install)}">Copy</button>
          </div>
          <pre class="cmd-pre"><code>${escapeHtml(h.install)}</code></pre>
        </div>
        <div class="cmd-block" style="margin-bottom:0;">
          <div class="cmd-block-head">
            <span>2. ステータス確認 / 呼び出し方法</span>
            <button type="button" class="copy-chip" data-copy-text="${escapeHtml(h.verify)}">Copy</button>
          </div>
          <pre class="cmd-pre"><code>${escapeHtml(h.verify)}</code></pre>
        </div>
      `;
    }

    tabs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const key = btn.getAttribute("data-host-tab");
        tabs.forEach(function (b) {
          b.classList.toggle("is-active", b === btn);
        });
        renderHost(key);
      });
    });

    renderHost("all");
  }

  /* --------------------------------------------------------------------------
     Mobile Navigation Menu
     -------------------------------------------------------------------------- */
  function setupMobileMenu() {
    const btn = document.getElementById("mobile-menu-toggle");
    const nav = document.getElementById("main-nav-links");
    if (!btn || !nav) return;

    btn.addEventListener("click", function () {
      const isOpen = nav.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("is-open");
        btn.setAttribute("aria-expanded", "false");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupCopyButtons();
    setupHeroControls();
    setupWorkbench();
    setupPhaseStepper();
    setupGenreExplorer();
    setupAtlas();
    setupInstallTabs();
    setupMobileMenu();
  });
})();
