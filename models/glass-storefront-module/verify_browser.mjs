// Production-gallery flow plus standalone rendering of both packaged variants.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild, launchOptions} from '../../scripts/browser-test-utils.mjs';

const dir = path.dirname(new URL(import.meta.url).pathname);
const measured = JSON.parse(await fs.readFile(path.join(dir,'reports/assets.json')));
const delivery = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(delivery, {recursive:true});
const source = await serveBuild('.');
const build = await serveBuild();
const browser = await chromium.launch(launchOptions);
const results = [], failures = [];
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
    await context.addInitScript(() => {
      window.qaFrame = {calls:0,triangles:0};
      for (const Type of [WebGLRenderingContext, WebGL2RenderingContext]) {
        const clear = Type.prototype.clear;
        Type.prototype.clear = function(...args) {window.qaFrame = {calls:0,triangles:0}; return clear.apply(this,args);};
        for (const method of ['drawArrays','drawElements','drawArraysInstanced','drawElementsInstanced']) {
          const original = Type.prototype[method];
          if (!original) continue;
          Type.prototype[method] = function(...args) {
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
    const errors = [], hashes = [];
    page.on('console', m => {if(m.type()==='error') errors.push(m.text());});
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', async response => {
      if (response.url().endsWith('.glb') && response.ok()) {
        const bytes = await response.body();
        hashes.push(createHash('sha256').update(bytes).digest('hex'));
      }
      if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    });
    await page.goto(build.url + '?model=glass-storefront-module');
    await page.waitForFunction(() => document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.qaFrame.calls > 0);
    await page.locator('#viewport canvas').focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('+');
    await page.getByRole('button', {name:/reset view/i}).click();
    await page.waitForTimeout(400);
    const render = await page.evaluate(() => ({...window.qaFrame, overflow:document.documentElement.scrollWidth>innerWidth,
      canvasLabel:document.querySelector('#viewport canvas').getAttribute('aria-label')}));
    assert.equal(render.overflow, false);
    assert.equal(render.calls, 2);
    assert.equal(render.triangles, measured.variants[0].visible_triangles);
    const screenshot = path.join(delivery, `glass-storefront-module${width===1440 ? '' : '-390'}-page.png`);
    // Capture the requested viewport; the underlying catalog can be taller than
    // Chromium's full-page capture limit and is unrelated to this model check.
    await page.screenshot({path:screenshot});
    assert.deepEqual(errors, []);
    assert.ok(hashes.includes(createHash('sha256').update(await fs.readFile(path.join(dir,'exports/optimized.glb'))).digest('hex')));
    results.push({kind:'production-gallery',width,render,errors,screenshot,hashes});
    // The separate QA page consumes both real GLB scenes, with no gallery edits.
    const qa = await context.newPage();
    const qaErrors = [];
    qa.on('console', m => {if(m.type()==='error') qaErrors.push(m.text());});
    qa.on('pageerror', e => qaErrors.push(e.message));
    await qa.goto(source.url + 'models/glass-storefront-module/reports/runtime-qa.html');
    await qa.waitForFunction(() => window.qaResults?.ready);
    const record = await qa.evaluate(() => window.qaResults);
    assert.deepEqual(qaErrors, []);
    assert.ok(record.records.every(r => r.draw_calls_model_only === 2));
    assert.deepEqual(record.records.map(r => r.rendered_triangles), [0,1,0,1].map(i => measured.variants[i].visible_triangles));
    assert.equal(await qa.locator('main img').count(), 4);
    assert.ok(await qa.locator('main img').evaluateAll(images => images.every(img => img.complete && img.naturalWidth > 0)));
    await qa.screenshot({path:path.join(dir,`previews/contact-${width}.png`),fullPage:true});
    results.push({kind:'variant-contact-sheet',width,...record,errors:qaErrors});
    await context.close();
  }
} catch (e) {
  failures.push(e.stack);
  throw e;
} finally {
  await fs.writeFile(path.join(dir,'reports/browser.json'),JSON.stringify({result:failures.length?'FAIL':'PASS',results,failures},null,2)+'\n');
  await browser.close();
  await source.close();
  await build.close();
}
console.log(JSON.stringify({result:'PASS',results},null,2));
