# `deslop` プロモーション動画 成果物 & 再生成ガイド

本ディレクトリ（`artifacts/promo/`）には、`deslop`（日英 Markdown・平文から機械生成特有の文体を削り、書かれた事実だけを残すエージェントスキル＆決定論的検査器）のプロモーション映像および制作ソース・検証記録一式が含まれています。

---

## 1. ディレクトリ構成と成果物一覧

```text
artifacts/promo/
├── final-promo.mp4          # 完成プロモーション動画 (1920x1080, 60fps, H.264 yuv420p + AAC 48kHz Stereo, 38.0s)
├── storyboard.md            # Phase 1 プロダクト分析・Phase 2 クリエイティブ戦略・6シーン絵コンテ
├── pdca-report.md           # Phase 4 PDCA品質改善サイクル記録 (v1 -> v2 -> v3 -> v4) & Phase 5 独立レビュー
├── README.md                # 本ドキュメント（仕様説明・再生成手順）
├── source/                  # 映像・音響制作ソースコード
│   ├── stage.html           # 1920x1080 決定論的タイムライン＆モーショングラフィックス・ステージ (window.setTime)
│   ├── render.mjs           # Playwright (マルチワーカー) + FFmpeg image2pipe 60fps レンダラー
│   └── generate_audio.py    # Python 3.10+ 標準ライブラリのみによる 120 BPM 完全同期 BGM & 効果音合成スクリプト
├── assets/                  # stage.html が読み込む素材
│   ├── bg-editorial-paper.jpg   # 校正紙面＆真紅ルーラー背景ビジュアル (agy image-generator 生成)
│   ├── bg-redline-abstract.jpg  # 決定論的レーザー＆カーボンターミナル背景 (agy image-generator 生成)
│   ├── ui-workbench.png         # 実際の Live Detector Workbench UI キャプチャ
│   └── ui-workbench-after.png   # 同 Workbench の書き直し後キャプチャ
└── previews/
    └── contact-sheet.png    # 全6シーン代表フレーム一覧グリッド
```

次のファイルは `.gitignore` 対象で、リポジトリにはありません。

- `assets/soundtrack.wav`：レンダリングの前に Step 1 で生成する
- `assets/ui-*.png` のうち上の2枚以外（ヒーロー、校正カード、事実保護マトリクス、ジャンル別エクスプローラ、インストールカードなどのキャプチャ）：`stage.html` は読み込まない
- `previews/v1/`〜`v4/`：各 PDCA サイクル（76 / 85 / 90 / 96 点）の検証動画と代表フレーム。Step 2 で `previews/v4` を作り直せる

---

## 2. 完成動画 (`final-promo.mp4`) の技術仕様

| 項目 | 仕様値 |
|---|---|
| ファイルパス | `artifacts/promo/final-promo.mp4` |
| 解像度 | `1920 × 1080` (Full HD 1080p, 16:9) |
| フレームレート | `60 fps` (`r_frame_rate=60/1`, 総フレーム数 2,280 frames) |
| 再生時間 | `38.00 秒` |
| 映像コーデック | H.264 (`libx264`, `yuv420p`, TV color range, `-movflags +faststart`) |
| 音声コーデック | AAC LC (`48,000 Hz`, Stereo 2ch, EBU R128 ラウドネス正規化 `-15 LUFS` / `-1.5 dBTP`) |

---

## 3. 再現・再生成手順

リポジトリルートから以下のコマンドでサウンドトラックと動画のすべてを決定論的に再生成できます。

### Step 1: サウンドトラック（BGM＋効果音）の生成
Python 3.10+ 標準ライブラリのみで動作します（外部パッケージ不要）。

```sh
python3 artifacts/promo/source/generate_audio.py artifacts/promo/assets/soundtrack.wav
```

### Step 2: 60fps フルHD動画のレンダリング
Playwright（Google Chrome）と `ffmpeg` を使用して `stage.html` の `window.setTime(t)` を 1/60 秒刻みで呼び出し、`final-promo.mp4` と検証用フレームを生成します。

```sh
node artifacts/promo/source/render.mjs \
  artifacts/promo/final-promo.mp4 \
  artifacts/promo/previews/v4 \
  60
```

高速プレビュー（30fps）でレンダリングする場合は第3引数に `30` を指定してください：

```sh
node artifacts/promo/source/render.mjs \
  artifacts/promo/previews/test.mp4 \
  artifacts/promo/previews/test-frames \
  30
```

### Step 3: 動画仕様と品質の検証（FFprobe / 黒画面・無音検査）

```sh
ffprobe -v error \
  -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,color_range,sample_rate,channels \
  -of default=noprint_wrappers=1 \
  artifacts/promo/final-promo.mp4

# 黒画面（blackdetect）および無音・クリッピング検査
ffmpeg -i artifacts/promo/final-promo.mp4 -vf "blackdetect=d=0.1:pix_th=0.05" -af "volumedetect" -f null /dev/null
```
