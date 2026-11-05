// Fixed UI measurements for the SQI report (artifacts/quality/README.md).
// Usage: make serve; AXE_DIR=<dir with node_modules/axe-core> node ui.js <shotdir> <tag>
// Needs Playwright and axe-core 4.10.2; neither is a dependency of the skill.
const { chromium } = require('playwright'); const fs = require('fs');
const [shotDir, tag] = process.argv.slice(2);
const ROOT = require('path').resolve(__dirname, '../../..');
const axeSrc = fs.readFileSync(require.resolve('axe-core/axe.min.js', { paths: [process.env.AXE_DIR || process.cwd()] }), 'utf8');
const skill = fs.readFileSync(ROOT + '/skills/deslop/SKILL.md', 'utf8');
const skillPhases = (skill.split('## Phases')[1].split('## ')[0].match(/^\| ([A-Z]+) \|/gm) || []).map(s => s.slice(2, -2));
const testCount = fs.readdirSync(ROOT + '/tests').filter(f => /^test_.*\.py$/.test(f)).reduce((n, f) => n + (fs.readFileSync(ROOT + '/tests/' + f, 'utf8').match(/^\s*def test_/gm) || []).length, 0);
(async () => {
  const b = await chromium.launch(); const out = { skillPhases, testCount, views: {} };
  for (const [name, vp, scheme] of [['w320', { width: 320, height: 700 }, 'light'], ['w390', { width: 390, height: 844 }, 'light'], ['w768', { width: 768, height: 1024 }, 'light'], ['w1440', { width: 1440, height: 900 }, 'light'], ['w1440-dark', { width: 1440, height: 900 }, 'dark']]) {
    const p = await b.newPage({ viewport: vp, colorScheme: scheme }); const errs = [];
    p.on('console', m => m.type() === 'error' && errs.push(m.text())); p.on('pageerror', e => errs.push(String(e)));
    await p.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
    await p.addScriptTag({ content: axeSrc });
    const axe = await p.evaluate(async () => (await axe.run(document, { resultTypes: ['violations'] })).violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })));
    const hscroll = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const perf = await p.evaluate(() => { const n = performance.getEntriesByType('navigation')[0]; const f = performance.getEntriesByName('first-contentful-paint')[0]; return { dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd), fcp: f && Math.round(f.startTime), transfer: performance.getEntriesByType('resource').reduce((s, r) => s + r.encodedBodySize, 0) + n.encodedBodySize }; });
    const cls = await p.evaluate(() => new Promise(r => { let v = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) v += e.value; }).observe({ type: 'layout-shift', buffered: true }); setTimeout(() => r(Math.round(v * 1000) / 1000), 500); }));
    await p.screenshot({ path: `${shotDir}/${tag}-${name}.png` });
    out.views[name] = { axe, consoleErrors: errs, hscroll, perf, cls };
    if (name === 'w1440') {
      const m = {};
      // stale claims
      m.stepperPhases = await p.$$eval('[data-phase-idx] .phase-title', els => els.map(e => e.textContent.trim()));
      m.phaseMismatch = JSON.stringify(m.stepperPhases) !== JSON.stringify(skillPhases);
      m.testsClaim = await p.$$eval('.strip-number', els => (els.find(e => /tests/.test(e.textContent)) || {}).textContent);
      m.testsClaimWrong = parseInt(m.testsClaim, 10) !== testCount;
      await p.click('[data-host-tab="all"]');
      m.cloneCmd = await p.$eval('#install-commands-body pre', e => e.textContent.split('\n')[0]);
      m.cloneWrong = !m.cloneCmd.includes('github.com/simota/deslop');
      // state exposure for toggle buttons
      m.togglesWithoutState = await p.$$eval('.seg-tab, .phase-step-btn, .genre-btn, .host-tab, [data-atlas-filter], [data-hero-lang]', els => els.filter(e => !e.hasAttribute('aria-selected') && !e.hasAttribute('aria-pressed')).length);
      m.toggles = await p.$$eval('.seg-tab, .phase-step-btn, .genre-btn, .host-tab, [data-atlas-filter], [data-hero-lang]', els => els.length);
      // arrow-key navigation in each tablist
      m.tablists = await p.$$eval('[role=tablist]', ls => ls.length);
      m.tablistArrowOK = 0;
      for (const i of [...Array(m.tablists).keys()]) {
        const ok = await p.evaluate(async (i) => {
          const l = document.querySelectorAll('[role=tablist]')[i]; const tabs = [...l.querySelectorAll('[role=tab]')]; if (tabs.length < 2) return false;
          const sel = tabs.find(t => t.getAttribute('aria-selected') === 'true') || tabs[0]; sel.focus();
          sel.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
          await new Promise(r => setTimeout(r, 50));
          const now = [...l.querySelectorAll('[role=tab]')]; const s2 = now.find(t => t.getAttribute('aria-selected') === 'true');
          const res = s2 && s2 !== sel && document.activeElement === s2; sel.click(); return !!res;
        }, i);
        if (ok) m.tablistArrowOK++;
      }
      // hit rows keyboard-operable
      m.hitRows = await p.$$eval('[data-jump-line]', els => els.length);
      m.hitRowsNotFocusable = await p.$$eval('[data-jump-line]', els => els.filter(e => e.tabIndex < 0).length);
      // genre-aware density limits: select article sample
      await p.selectOption('#sample-select', 'ja_review'); await p.waitForTimeout(300);
      m.articleDen01Label = await p.$eval('#detector-density-grid', e => e.textContent.replace(/\s+/g, ' ').trim());
      m.articleDen01LimitWrong = !/1\.5/.test(m.articleDen01Label);
      // copy feedback announced?
      m.liveRegionForCopy = await p.evaluate(() => !!document.querySelector('[data-copy-status], #copy-status'));
      out.ui = m;
    }
    await p.close();
  }
  console.log(JSON.stringify(out, null, 1)); await b.close();
})();
