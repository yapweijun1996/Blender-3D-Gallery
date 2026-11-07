import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

// By default the exact gallery asset is tested. The opt-in prototype mode is
// useful during development before the new GLB is installed in the gallery.
const source = process.env.SAGA_DOOR_TEST_PROTOTYPE
  ? 'output/saga-door-polish/exports/proton-saga-1985.glb'
  : 'models/proton-saga-1985/exports/proton-saga-1985.glb';
const bytes = await fs.readFile(source);
const jsonLength = bytes.readUInt32LE(12);
const gltf = JSON.parse(bytes.subarray(20, 20 + jsonLength));
for (const code of ['FL', 'FR', 'RL', 'RR']) {
  assert.ok(gltf.nodes.some(node => node.name === `Door_${code}_Hinge`), `actual GLB contains ${code} pivot`);
}
const server = await serveBuild();
if (process.env.SAGA_DOOR_TEST_PROTOTYPE) server.setFault(({relative}) => relative.endsWith('.glb') ? {bytes} : null);
const browser = await chromium.launch(launchOptions);
async function ready(page) {
  await page.waitForFunction(() => document.querySelector('#viewer')?.open &&
    document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.sagaDrawCalls > 0,
  null, {timeout: 60000});
  await page.waitForLoadState('networkidle');
}
async function changedCanvas(page, act, label) {
  const canvas = page.locator('#viewport canvas');
  const before = await canvas.screenshot();
  const draws = await page.evaluate(() => window.sagaDrawCalls);
  await act();
  await page.waitForFunction(previous => window.sagaDrawCalls > previous, draws);
  await page.waitForTimeout(200);
  const after = await canvas.screenshot();
  assert.equal(before.equals(after), false, `${label} changes the real rendered GLB`);
}
async function contextFor(width, height) {
  const context = await browser.newContext({ viewport: {width, height}, hasTouch: width < 1000, serviceWorkers: 'block' });
  await context.addInitScript(() => {
    window.sagaDrawCalls = 0;
    for (const type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = type.prototype[name];
        if (original) type.prototype[name] = function (...args) { window.sagaDrawCalls++; return original.apply(this, args); };
      }
    }
  });
  return context;
}
try {
  for (const [width, height] of [[1440,900], [390,844], [320,720]]) {
    const context = await contextFor(width, height), page = await context.newPage(), errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('requestfailed', r => errors.push(`${r.url()} ${r.failure()?.errorText}`));
    try {
      await page.goto(server.url);
      await page.locator('#catalog [data-asset-id="proton-saga-1985"]').first().click();
      await ready(page);
      const doors = page.locator('.vehicle-door-buttons button');
      assert.equal(await doors.count(), 4, 'real GLB exposes exactly four controls');
      for (const code of ['FL','FR','RL','RR']) {
        await page.locator('#reset-view').click();
        await page.locator(`[data-vehicle-view="${code.endsWith('L') ? 'left' : 'right'}"]`).click();
        const button = page.locator(`[data-vehicle-door="${code}"]`);
        const box = await button.boundingBox();
        assert.ok(box.width >= 44 && box.height >= 44, 'doors retain touch targets');
        await changedCanvas(page, () => button.click(), `${code} opening`);
        assert.equal(await button.getAttribute('aria-pressed'), 'true');
        await changedCanvas(page, () => button.click(), `${code} closing`);
        assert.equal(await button.getAttribute('aria-pressed'), 'false');
      }
      const leftFront = page.locator('[data-vehicle-door="FL"]'), leftRear = page.locator('[data-vehicle-door="RL"]');
      await leftFront.focus(); await page.keyboard.press('Enter');
      assert.equal(await leftFront.getAttribute('aria-pressed'), 'true', 'keyboard activates door');
      await leftRear.click();
      assert.equal(await leftFront.getAttribute('aria-pressed'), 'true', 'door states are independent');
      await page.locator('[data-vehicle-view="rear"]').click();
      assert.equal(await leftFront.getAttribute('aria-pressed'), 'true', 'view selection preserves door state');
      await page.locator('#reset-view').click();
      for (const door of await doors.all()) assert.equal(await door.getAttribute('aria-pressed'), 'false', 'reset closes all doors');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'no horizontal overflow');
      assert.deepEqual(errors, [], 'no errors while using door controls');
      await page.locator('#close-viewer').click();
      assert.equal(await page.locator('.vehicle-door-controls').count(), 0, 'closing disposes door controls');
      assert.deepEqual(errors, [], 'no errors after closing viewer');
      console.log(`PASS Saga doors ${width}: independent toggles, actual GLB rendering, keyboard, view preservation, reset and cleanup`);
    } finally { await context.close(); }
  }
  // Keep a valid GLB but remove one hinge name to exercise the graceful fallback.
  const modified = Buffer.from(bytes), original = Buffer.from('Door_FL_Hinge'), replacement = Buffer.from('Gone_FL_Hinge');
  const offset = modified.indexOf(original, 20);
  assert.ok(offset >= 20 && offset < 20 + jsonLength && original.length === replacement.length);
  replacement.copy(modified, offset);
  server.setFault(({relative}) => relative.endsWith('.glb') ? {bytes: modified} : null);
  const context = await contextFor(390,844), page = await context.newPage(), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto(server.url);
    await page.locator('#catalog [data-asset-id="proton-saga-1985"]').first().click();
    await ready(page);
    assert.equal(await page.locator('.vehicle-door-buttons button').count(), 0);
    assert.match(await page.locator('.vehicle-door-unavailable').innerText(), /unavailable/i);
    assert.equal(await page.locator('.vehicle-view-buttons button').count(), 4, 'viewing still works');
    assert.deepEqual(errors, []);
    console.log('PASS Saga missing-pivot fallback: viewer remains available without misleading controls');
  } finally { await context.close(); }

  // A failed model fetch must retain the poster and offer a working retry.
  server.setFault(({relative}) => relative.endsWith('.glb') ? {status: 503} : null);
  const errorContext = await contextFor(390,844), errorPage = await errorContext.newPage(), pageErrors = [];
  errorPage.on('pageerror', error => pageErrors.push(error.message));
  try {
    await errorPage.goto(server.url);
    await errorPage.locator('#catalog [data-asset-id="proton-saga-1985"]').first().click();
    await errorPage.locator('#retry-view').waitFor({state:'visible',timeout:60000});
    assert.equal(await errorPage.locator('#viewer-poster').isVisible(), true);
    assert.match(await errorPage.locator('#viewer-status').innerText(), /unavailable/i);
    assert.equal(await errorPage.locator('.vehicle-door-controls').count(), 0);
    server.setFault(null);
    await errorPage.locator('#retry-view').click();
    await ready(errorPage);
    assert.equal(await errorPage.locator('.vehicle-door-buttons button').count(), 4);
    assert.deepEqual(pageErrors, []);
    console.log('PASS Saga failed fetch: poster fallback and retry load the real door controls');
  } finally { await errorContext.close(); }

  // Closing during the native fetch must not leave a late model or toolbar.
  const cancelContext = await contextFor(390,844), cancelPage = await cancelContext.newPage(), cancelErrors = [];
  cancelPage.on('pageerror', error => cancelErrors.push(error.message));
  let unblock, intercepted;
  const gate = new Promise(resolve => { unblock = resolve; });
  const seen = new Promise(resolve => { intercepted = resolve; });
  await cancelPage.route('**/*.glb', async route => {
    intercepted();
    await gate;
    await route.fulfill({status:200,contentType:'model/gltf-binary',body:bytes}).catch(() => {});
  });
  try {
    await cancelPage.goto(server.url);
    await cancelPage.locator('#catalog [data-asset-id="proton-saga-1985"]').first().click();
    let timeout;
    try { await Promise.race([seen,new Promise((_,reject)=>{ timeout=setTimeout(()=>reject(new Error('GLB request not intercepted')),10000); })]); }
    finally { clearTimeout(timeout); }
    await cancelPage.locator('#close-viewer').click();
    unblock();
    await cancelPage.waitForTimeout(500);
    assert.equal(await cancelPage.locator('#viewer').evaluate(element => element.open), false);
    assert.equal(await cancelPage.locator('#viewport canvas').count(), 0);
    assert.equal(await cancelPage.locator('.vehicle-door-controls').count(), 0);
    assert.deepEqual(cancelErrors, []);
    console.log('PASS Saga canceled fetch: closed viewer cannot regain a late model or toolbar');
  } finally { unblock(); await cancelContext.close(); }
} finally { await browser.close(); await server.close(); }
