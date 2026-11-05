// Keyboard and task walkthrough (T1, T2, T4) for the SQI report; make serve first.
// Usage: node artifacts/quality/measure/tasks.js
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
  const r = {};
  // T1: keyboard to first hit row and activate
  await p.focus('#detector-hits-list'); await p.keyboard.press('Tab');
  r.focusedIsHitRow = await p.evaluate(() => document.activeElement.classList.contains('hit-row'));
  const line = await p.evaluate(() => document.activeElement.getAttribute('data-jump-line'));
  await p.keyboard.press('Enter');
  r.flashAfterEnter = await p.evaluate((l) => !!document.querySelector('#wb-line-' + l + '.is-flash'), line);
  // phase tabs: Tab into tablist lands on selected tab only once (roving)
  await p.focus('[data-phase-idx="0"]'); await p.keyboard.press('End');
  r.endSelects = await p.evaluate(() => document.activeElement.getAttribute('data-phase-idx') + ':' + document.activeElement.getAttribute('aria-selected') + ':' + document.getElementById('phase-detail-container').textContent.includes('REPORT'));
  await p.keyboard.press('Tab');
  r.tabLeavesTablistTo = await p.evaluate(() => document.activeElement.id || document.activeElement.className);
  r.panelLabelledBy = await p.evaluate(() => { const pnl = document.getElementById('phase-detail-container'); return pnl.getAttribute('aria-labelledby') + ' -> ' + document.getElementById(pnl.getAttribute('aria-labelledby')).textContent.trim().replace(/\s+/g,' '); });
  // toggle buttons expose pressed state
  await p.click('[data-wb-view="edit"]');
  r.wbPressed = await p.$$eval('[data-wb-view]', els => els.map(e => e.getAttribute('aria-pressed')).join(','));
  // T2: type text and get hits from API
  await p.fill('#sandbox-textarea', '本記事では、キャッシュについて詳しく解説します。参考になれば幸いです！');
  await p.waitForTimeout(400);
  r.typedHits = await p.$eval('#detector-summary-badges', e => e.textContent.trim().replace(/\s+/g, ' '));
  r.source = await p.$eval('#detector-source-label', e => e.textContent);
  // copy: grant clipboard and click, then status text
  await p.context().grantPermissions(['clipboard-read', 'clipboard-write']);
  await p.click('[data-host-tab="all"]'); await p.click('#install-commands-body .copy-chip');
  await p.waitForTimeout(150);
  r.copyStatus = await p.$eval('#copy-status', e => e.textContent);
  r.clipboard = await p.evaluate(() => navigator.clipboard.readText());
  // genre tablist arrow
  await p.focus('[data-genre-id="readme"]'); await p.keyboard.press('ArrowDown');
  r.genreAfterArrow = await p.evaluate(() => document.activeElement.getAttribute('data-genre-id') + ' ' + document.getElementById('genre-detail-card').textContent.includes('--genre reference'));
  console.log(JSON.stringify(r, null, 1)); await b.close();
})();
