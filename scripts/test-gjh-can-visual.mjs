// Golden-screenshot regression for the four GJH abalone cans in the real gallery viewer.
// Usage: node scripts/test-gjh-can-visual.mjs            compare against models/gjh-abalone-cans/reports/golden
//        node scripts/test-gjh-can-visual.mjs --update   rewrite the goldens (review them before committing)
// Goldens are produced by headless Chromium (software rendering) and are a local regression guard, not a cross-GPU reference.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

const update = process.argv.includes('--update');
const codex = process.argv.includes('--codex');   // the AI flat-label comparison set: fewer views
const goldenDir = codex ? 'models/gjh-abalone-cans/reports/codex/golden' : 'models/gjh-abalone-cans/reports/golden';
const slugs = ['gjh-can-new-zealand-abalone', 'gjh-can-australia-abalone', 'gjh-can-south-africa-abalone', 'gjh-can-mexico-abalone'].map(s => codex ? s + '-codex' : s);
// Arrow-key presses (the viewer rotates exactly 10 degrees per key) give identical camera angles on every run.
const turn = (key, count) => Array(count).fill(key);
const zoom = turn('+', 5);
const views = {
  'r0': [], 'r0-zoom': zoom,
  'r40': turn('ArrowRight', 4), 'r40-zoom': [...turn('ArrowRight', 4), ...zoom],   // the viewer cannot turn exactly 45 degrees
  'r90': turn('ArrowRight', 9), 'r90-zoom': [...turn('ArrowRight', 9), ...zoom],
  'r180': turn('ArrowRight', 18), 'r180-zoom': [...turn('ArrowRight', 18), ...zoom],
  'r270': turn('ArrowLeft', 9), 'r270-zoom': [...turn('ArrowLeft', 9), ...zoom],
  top: turn('ArrowUp', 9), bottom: turn('ArrowDown', 12) };
if (codex) for (const name of Object.keys(views)) if (!['r0', 'r0-zoom', 'r90', 'r180', 'r270'].includes(name)) delete views[name];
const MEAN_LIMIT = 2.0, BAD_PIXEL_LIMIT = 0.01; // mean abs channel difference (0-255) and share of pixels differing by > 40

const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
await fs.mkdir(goldenDir, { recursive: true });
let failures = 0;
try {
  for (const slug of slugs) for (const [view, keys] of Object.entries(views)) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => m.type() === 'error' && errors.push(m.text()));
    await page.goto(`${server.url}?model=${slug}`);
    const canvas = page.locator('canvas').first();
    await canvas.waitFor();
    await page.waitForTimeout(3500);
    await canvas.evaluate(el => el.focus());
    for (const key of keys) await page.keyboard.press(key);
    await page.waitForTimeout(1500);
    const shot = await canvas.screenshot({ type: 'jpeg', quality: 90 });
    const file = path.join(goldenDir, `${slug}-${view}.jpg`);
    if (update) {
      await fs.writeFile(file, shot);
      console.log('UPDATED', slug, view);
    } else {
      const golden = await fs.readFile(file);
      const result = await page.evaluate(async ([a, b]) => {
        const load = async data => { const img = new Image(); img.src = 'data:image/jpeg;base64,' + data; await img.decode(); return img; };
        const [ia, ib] = await Promise.all([load(a), load(b)]);
        if (ia.width !== ib.width || ia.height !== ib.height) return { size: false };
        const read = img => { const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0); return g.getImageData(0, 0, c.width, c.height).data; };
        const da = read(ia), db = read(ib);
        let sum = 0, bad = 0;
        for (let i = 0; i < da.length; i += 4) {
          let max = 0;
          for (let k = 0; k < 3; k++) { const d = Math.abs(da[i + k] - db[i + k]); sum += d; if (d > max) max = d; }
          if (max > 40) bad++;
        }
        return { size: true, mean: sum / (da.length / 4 * 3), bad: bad / (da.length / 4) };
      }, [golden.toString('base64'), shot.toString('base64')]);
      const ok = result.size && result.mean <= MEAN_LIMIT && result.bad <= BAD_PIXEL_LIMIT && !errors.length;
      console.log(ok ? 'PASS' : 'FAIL', slug, view, result.size ? `mean ${result.mean.toFixed(2)} bad ${(result.bad * 100).toFixed(2)}%` : 'size changed', errors.length ? `errors ${errors.length}` : '');
      if (!ok) failures++;
    }
    await context.close();
  }
} finally {
  await browser.close();
  server.close?.();
}
if (failures) { console.error(`${failures} visual regression(s)`); process.exitCode = 1; }
