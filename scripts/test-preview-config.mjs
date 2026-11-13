import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

// Freeze baseline screenshots before the implementation; compare exact PNG bytes
// in the same browser/GPU configuration. No request/console failure is filtered.
const [build = 'dist', out = '/tmp/gallery-preview-config', baseline] = process.argv.slice(2);
await fs.mkdir(out); // Never overwrite evidence from an earlier run.
const old = baseline ? JSON.parse(await fs.readFile(path.join(baseline, 'results.json'), 'utf8')) : null;
const catalog = JSON.parse(await fs.readFile('models/catalog.json', 'utf8'));
const all = catalog.collections.flatMap(c => c.assets);
const ids = ['pool-table', 'ball-08', 'solar-earth', 'proton-saga-1985', 'mall-ceiling-panel-module'];
for (const collection of ['mall-floor-tile', 'mall-glass-railing']) ids.push(catalog.collections.find(c => c.id === collection).assets[0].id);
const server = await serveBuild(build), browser = await chromium.launch(launchOptions), results = [];
try {
  for (const id of ids) for (const [width, height] of [[1440,900], [390,844]]) {
    const asset = all.find(a => a.id === id), errors = [];
    const result = {id, width, height, errors, passed:false};
    const context = await browser.newContext({viewport:{width,height}, reducedMotion:'reduce', serviceWorkers:'block'});
    const page = await context.newPage();
    try {
      await page.addInitScript(() => {
        window.previewDraws = 0; window.previewConsumed = [];
        const original = Response.prototype.arrayBuffer;
        Response.prototype.arrayBuffer = async function(...args) {
          const b = await original.apply(this,args);
          if (b.byteLength >= 4 && String.fromCharCode(...new Uint8Array(b,0,4)) === 'glTF') {
            const digest = await crypto.subtle.digest('SHA-256',b);
            window.previewConsumed.push({bytes:b.byteLength, sha256:[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('')});
          }
          return b;
        };
        for (const Context of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) for (const name of ['drawArrays','drawElements']) {
          const original = Context?.prototype[name];
          if (original) Context.prototype[name] = function(...args) {window.previewDraws++; return original.apply(this,args);};
        }
      });
      page.on('requestfailed',r=>errors.push('request: '+r.url()+' '+r.failure()?.errorText));
      page.on('pageerror',e=>errors.push('page: '+e.message));
      page.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text());});
      page.on('response',r=>{if(r.status()>=400)errors.push('HTTP '+r.status()+' '+r.url());});
      await page.goto(server.url+'?model='+id, {waitUntil:'networkidle'});
      await page.waitForFunction(()=>document.querySelector('#viewer')?.open && document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent==='' && window.previewDraws>0, null, {timeout:60000});
      const canvas = page.locator('#viewport canvas');
      const shot = async label => {
        // Wait for OrbitControls damping to settle before an exact reset comparison.
        await page.waitForTimeout(350);
        return createHash('sha256').update(await canvas.screenshot({path:path.join(out,`${id}-${width}-${label}.png`)})).digest('hex');
      };
      result.initial = await shot('initial');
      await canvas.focus(); await canvas.press('ArrowRight');
      result.orbit = await shot('orbit'); assert.notEqual(result.orbit,result.initial);
      await canvas.press('PageUp'); result.zoom = await shot('zoom'); assert.notEqual(result.zoom,result.orbit);
      await page.locator('#reset-view').click(); result.reset = await shot('reset');
      result.resetMatchesInitial = result.reset === result.initial;
      // The baseline vehicle toolbar changes the narrow viewport's fit after first
      // layout. Preserve and compare that existing behavior, do not conceal/fix it.
      if (id === 'proton-saga-1985' && width === 390) result.preExistingResetFitDifference = !result.resetMatchesInitial;
      else assert.equal(result.reset,result.initial,'reset must restore the exact per-model initial view');
      if (id === 'mall-ceiling-panel-module' && !old) {
        for (let i=0;i<8;i++) await canvas.press('ArrowDown');
        result.underside = await shot('underside');
      }
      const bytes = await fs.readFile(asset.file), sha256 = createHash('sha256').update(bytes).digest('hex');
      result.consumed = await page.evaluate(()=>window.previewConsumed);
      assert.ok(result.consumed.some(x=>x.bytes===bytes.length && x.sha256===sha256));
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      if (old) {
        const before = old.results.find(r=>r.id===id && r.width===width);
        assert.ok(before?.passed,'baseline must pass');
        if (id === 'mall-ceiling-panel-module') assert.notEqual(result.initial,before.initial,'configured ceiling changes');
        else for (const state of ['initial','orbit','zoom','reset']) assert.equal(result[state],before[state],`${id} ${state} must be byte-identical to baseline`);
        result.baselineComparison = id === 'mall-ceiling-panel-module' ? 'changed (configured)' : 'byte-identical initial/orbit/zoom/reset';
      }
      await page.locator('#close-viewer').click(); assert.equal(await canvas.count(),0);
      await page.goto(server.url+'?model='+id, {waitUntil:'networkidle'});
      await page.waitForFunction(()=>document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent==='' && window.previewDraws>0);
      result.reopened = await shot('reopened'); assert.equal(result.reopened,result.initial);
      assert.deepEqual(errors,[]); result.passed = true; console.log('PASS',id,width);
    } catch (e) {result.failure=e.message; console.error('FAIL',id,width,e.message);}
    finally {results.push(result);await context.close();}
  }
} finally {
  await browser.close(); await server.close();
  await fs.writeFile(path.join(out,'results.json'),JSON.stringify({browser:browser.version(),runtime:'Ubuntu desktop Chromium / SwiftShader, viewport emulation only',android:'NOT TESTED',ios:'NOT TESTED',results},null,2)+'\n');
}
if(results.some(r=>!r.passed))process.exitCode=1;
