import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

const id = 'mall-floor-direction-sign';
const catalog = JSON.parse(await fs.readFile(new URL('../models/catalog.json', import.meta.url), 'utf8'));
const asset = catalog.collections.flatMap(c => c.assets).find(a => a.id === id);
assert.ok(asset, 'floor direction sign must be registered');
const bytes = await fs.readFile(new URL(`../${asset.file}`, import.meta.url));
const sha256 = createHash('sha256').update(bytes).digest('hex');
const out = process.env.MALL_QA_DIR || '/tmp/blender-mall-floor-direction-sign-qa'; await fs.mkdir(out, { recursive: true });
const externalBase = process.env.MALL_BASE_URL?.replace(/\/$/, '');
const server = externalBase ? null : await serveBuild(); const baseUrl = externalBase || server.url; const browser = await chromium.launch(launchOptions); const results = [];
try {
  for (const [width, height] of [[1440, 900], [768, 1024], [390, 844]]) {
    const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce', serviceWorkers: 'block' });
    const page = await context.newPage(); const errors = []; const responses = [];
    await page.addInitScript(() => {
      window.mallConsumedGlbs = []; window.furnitureDraws = 0;
      const original = Response.prototype.arrayBuffer;
      Response.prototype.arrayBuffer = async function (...args) { const buffer = await original.apply(this, args); const head = new Uint8Array(buffer, 0, 4); if (String.fromCharCode(...head) === 'glTF') { const digest = await crypto.subtle.digest('SHA-256', buffer); window.mallConsumedGlbs.push({ bytes: buffer.byteLength, sha256: [...new Uint8Array(digest)].map(v => v.toString(16).padStart(2, '0')).join('') }); } return buffer; };
      for (const Context of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) for (const name of ['drawArrays', 'drawElements']) { const fn = Context?.prototype[name]; if (fn) Context.prototype[name] = function (...args) { window.furnitureDraws++; return fn.apply(this, args); }; }
    });
    page.on('requestfailed', request => errors.push(`${request.method()} ${request.url()} ${request.failure()?.errorText}`));
    page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('response', response => { if (response.url().endsWith('.glb')) responses.push(response); if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
    await page.goto(`${baseUrl}?model=${id}`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => document.querySelector('#viewer')?.open && document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.furnitureDraws > 0, null, { timeout: 60000 });
    assert.equal(await page.locator('#viewer-title').innerText(), asset.name); assert.equal(await page.locator('#viewer-download').isVisible(), false);
    const canvas = page.locator('#viewport canvas'); await canvas.focus();
    const initial = createHash('sha256').update(await canvas.screenshot({ path: path.join(out, `${width}-initial.png`) })).digest('hex');
    const beforeOrbit = await page.evaluate(() => window.furnitureDraws); await canvas.press('ArrowRight'); await page.waitForFunction(n => window.furnitureDraws > n, beforeOrbit); const orbit = createHash('sha256').update(await canvas.screenshot({ path: path.join(out, `${width}-orbit.png`) })).digest('hex'); assert.notEqual(orbit, initial);
    const beforeZoom = await page.evaluate(() => window.furnitureDraws); await canvas.press('PageUp'); await page.waitForFunction(n => window.furnitureDraws > n, beforeZoom); const zoom = createHash('sha256').update(await canvas.screenshot({ path: path.join(out, `${width}-zoom.png`) })).digest('hex'); assert.notEqual(zoom, orbit);
    await page.locator('#reset-view').click(); assert.equal(await page.locator('#reset-view').isEnabled(), true); const reset = createHash('sha256').update(await canvas.screenshot({ path: path.join(out, `${width}-reset.png`) })).digest('hex'); assert.notEqual(reset, zoom);
    assert.ok(responses.length > 0); for (const response of responses) assert.equal(response.status(), 200);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'no horizontal page overflow'); const consumed = await page.evaluate(() => window.mallConsumedGlbs); assert.ok(consumed.some(item => item.bytes === bytes.length && item.sha256 === sha256)); assert.deepEqual(errors, []);
    results.push({ width, height, passed: true, consumedBytes: bytes.length, sha256, screenshots: 4, controls: ['orbit', 'zoom', 'reset'] }); console.log(`PASS mall-floor-direction-sign ${width}x${height}`); await context.close();
  }
} finally { await browser.close(); await server?.close(); await fs.writeFile(path.join(out, 'results.json'), JSON.stringify({ asset: id, bytes: bytes.length, sha256, results }, null, 2) + '\n'); }
