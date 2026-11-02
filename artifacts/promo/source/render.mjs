#!/usr/bin/env node
/**
 * Deterministic Frame-by-Frame Promo Video Renderer (Playwright + FFmpeg)
 *
 * Renders artifacts/promo/source/stage.html at 1920x1080, 60fps (or configurable fps),
 * pipes frames in order into FFmpeg with artifacts/promo/assets/soundtrack.wav,
 * and outputs H.264 MP4 (yuv420p, +faststart).
 */
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const require = createRequire(
  fs.existsSync('/Users/shingoimota/code/muse/node_modules/playwright/package.json')
    ? '/Users/shingoimota/code/muse/node_modules/playwright/package.json'
    : import.meta.url
);
const { chromium } = require('playwright');

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const outPath = process.argv[2] || path.join(REPO_ROOT, 'artifacts/promo/final-promo.mp4');
const previewDir = process.argv[3] || path.join(REPO_ROOT, 'artifacts/promo/previews/v1');
const fps = Number(process.argv[4] || 60);
const duration = 38.0;
const totalFrames = Math.round(duration * fps);
const concurrency = 6;

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.mkdirSync(previewDir, { recursive: true });

const stageUrl = 'file://' + path.join(__dirname, 'stage.html');
const audioPath = path.join(REPO_ROOT, 'artifacts/promo/assets/soundtrack.wav');

// Key timestamps (in seconds) to save as PNG inspection frames in previewDir
const KEY_TIMESTAMPS = [
  { t: 0.4, name: '01_hook_start.png' },
  { t: 1.8, name: '02_hook_redline_strikes.png' },
  { t: 3.0, name: '03_hook_full_3s.png' },
  { t: 4.5, name: '04_transition_s1_s2.png' },
  { t: 7.5, name: '05_scene2_problem_solution.png' },
  { t: 11.2, name: '06_scene3_before_redline.png' },
  { t: 13.6, name: '07_scene3_morph_mid.png' },
  { t: 15.8, name: '08_scene3_after_crystallized.png' },
  { t: 21.5, name: '09_scene4_layers_and_genres.png' },
  { t: 29.8, name: '10_scene5_climax_contract_ok.png' },
  { t: 35.5, name: '11_scene6_finale_cta.png' },
];
const keyFrameMap = new Map(
  KEY_TIMESTAMPS.map((k) => [Math.min(totalFrames - 1, Math.round(k.t * fps)), k.name])
);

async function main() {
  const t0 = Date.now();
  console.log(`[render] Launching Chrome (${concurrency} workers) for ${totalFrames} frames @ ${fps}fps -> ${outPath}`);

  const browser = await chromium.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--disable-gpu-vsync', '--font-render-hinting=none'],
  });

  const pages = [];
  for (let i = 0; i < concurrency; i++) {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    await page.goto(stageUrl, { waitUntil: 'load' });
    pages.push(page);
  }

  const ffmpegArgs = [
    '-y',
    '-f', 'image2pipe',
    '-vcodec', 'mjpeg',
    '-framerate', String(fps),
    '-i', '-',
    '-i', audioPath,
    '-map', '0:v:0',
    '-map', '1:a:0',
    '-vf', 'format=yuv420p',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '17',
    '-pix_fmt', 'yuv420p',
    '-color_range', 'tv',
    '-r', String(fps),
    '-c:a', 'aac',
    '-b:a', '192k',
    '-ar', '48000',
    '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11',
    '-shortest',
    '-movflags', '+faststart',
    outPath,
  ];

  const ffmpeg = spawn('ffmpeg', ffmpegArgs, { stdio: ['pipe', 'ignore', 'pipe'] });
  let ffmpegErr = '';
  ffmpeg.stderr.on('data', (chunk) => {
    ffmpegErr += chunk.toString();
  });

  for (let base = 0; base < totalFrames; base += concurrency) {
    const batchCount = Math.min(concurrency, totalFrames - base);
    const buffers = await Promise.all(
      Array.from({ length: batchCount }, async (_, offset) => {
        const frameIdx = base + offset;
        const timeSec = frameIdx / fps;
        const page = pages[offset];
        await page.evaluate((t) => window.setTime(t), timeSec);
        const jpegBuf = await page.screenshot({ type: 'jpeg', quality: 94 });
        if (keyFrameMap.has(frameIdx)) {
          const pngPath = path.join(previewDir, keyFrameMap.get(frameIdx));
          await page.screenshot({ path: pngPath, type: 'png' });
        }
        return jpegBuf;
      })
    );

    for (const buf of buffers) {
      if (!ffmpeg.stdin.write(buf)) {
        await new Promise((resolve) => ffmpeg.stdin.once('drain', resolve));
      }
    }

    if ((base / concurrency) % 25 === 0 || base + batchCount === totalFrames) {
      const pct = (((base + batchCount) / totalFrames) * 100).toFixed(1);
      process.stdout.write(`\r[render] ${base + batchCount}/${totalFrames} frames (${pct}%)`);
    }
  }
  console.log('');

  ffmpeg.stdin.end();
  const exitCode = await new Promise((resolve) => ffmpeg.on('close', resolve));
  await browser.close();

  if (exitCode !== 0) {
    console.error('[render] FFmpeg failed:\n', ffmpegErr);
    process.exit(1);
  }

  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`[render] Completed ${outPath} in ${elapsed}s`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
