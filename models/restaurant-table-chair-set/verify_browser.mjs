// Exercise the built gallery and the delivered GLB without modifying gallery UI.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(output, {recursive:true});
const assets = JSON.parse(await fs.readFile(path.join(dir, 'reports/assets.json')));
const expectedHash = createHash('sha256').update(await fs.readFile(path.join(dir, 'exports/optimized.glb'))).digest('hex');
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const errors = [], responses = [], results = [];
try {
  const context = await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block'});
  await context.addInitScript(() => {
    window.qaFrame = {calls:0,triangles:0};
    window.qaTotalDraws = 0;
    for (const Type of [WebGLRenderingContext, WebGL2RenderingContext]) {
      const clear = Type.prototype.clear;
      Type.prototype.clear = function(...args) {window.qaFrame = {calls:0,triangles:0}; return clear.apply(this,args);};
      for (const method of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = Type.prototype[method];
        if (!original) continue;
        Type.prototype[method] = function(...args) {
          window.qaTotalDraws++;
          window.qaFrame.calls++;
          if (args[0] === this.TRIANGLES) {
            const count = method.startsWith('drawArrays') ? args[2] : args[1];
            const instances = method.endsWith('Instanced') ? args[method.startsWith('drawArrays') ? 3 : 4] : 1;
            window.qaFrame.triangles += count / 3 * instances;
          }
          return original.apply(this,args);
        };
      }
    }
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => {if (m.type() === 'error') errors.push(m.text());});
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    if (new URL(response.url()).pathname.endsWith('.glb') && response.ok()) responses.push(response);
  });
  const ready = () => page.waitForFunction(() => document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent === '' && window.qaFrame.calls > 0, null, {timeout:60000});
  await page.goto(server.url + '?model=restaurant-table-chair-set', {waitUntil:'domcontentloaded'});
  await ready();
  assert.match(await page.locator('#viewer-title').innerText(), /Restaurant Table and Four Chairs/);
  const initial = await page.locator('#viewport canvas').screenshot();
  await page.locator('#viewport canvas').focus();
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(200);
  const orbit = await page.locator('#viewport canvas').screenshot();
  assert.notDeepEqual(orbit, initial, 'Keyboard orbit changes rendered pixels');
  await page.keyboard.press('+');
  await page.waitForTimeout(200);
  const zoom = await page.locator('#viewport canvas').screenshot();
  assert.notDeepEqual(zoom, orbit, 'Keyboard zoom changes rendered pixels');
  await page.getByRole('button', {name:/reset view/i}).click();
  await page.waitForTimeout(200);
  const render = await page.evaluate(() => ({...window.qaFrame,
    overflow:document.documentElement.scrollWidth > innerWidth,
    canvas_label:document.querySelector('#viewport canvas').getAttribute('aria-label')}));
  assert.equal(render.overflow, false);
  assert.ok(render.canvas_label?.length);
  assert.equal(render.calls, assets.mesh_primitives);
  assert.equal(render.triangles, assets.triangles);
  const screenshot = path.join(output, 'restaurant-table-chair-set-page.png');
  await page.screenshot({path:screenshot});
  const hashes = [];
  for (const response of responses) hashes.push(createHash('sha256').update(await response.body()).digest('hex'));
  assert.ok(hashes.includes(expectedHash), 'Browser consumed the exact validated delivery GLB');
  results.push({flow:'direct model page',viewport:[1440,900],render,screenshot,hashes,
    keyboard_orbit:'PASS changed pixels',keyboard_zoom:'PASS changed pixels',reset:'PASS'});
  await page.reload({waitUntil:'domcontentloaded'});
  await ready();
  await page.locator('#close-viewer').click();
  await page.waitForFunction(() => !document.querySelector('#viewer').open);
  await page.locator('[data-asset-id="restaurant-table-chair-set"]').first().click();
  await ready();
  results.push({flow:'refresh, close and reopen from catalog',result:'PASS'});
  assert.deepEqual(errors, []);
  await context.close();
  console.log(JSON.stringify({result:'PASS',results}));
} finally {
  await fs.writeFile(path.join(dir, 'reports/browser.json'), JSON.stringify({result:results.length===2&&!errors.length?'PASS':'FAIL',
    browser:browser.version(),results,errors},null,2)+'\n');
  await browser.close();
  await server.close();
}
