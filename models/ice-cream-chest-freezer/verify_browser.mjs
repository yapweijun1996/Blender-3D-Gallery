import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(os.homedir(), 'Documents/MallQueue/reports');
await fs.mkdir(out, {recursive:true});
const expected = JSON.parse(await fs.readFile(path.join(dir, 'reports/assets.json')));
const build = JSON.parse(await fs.readFile('dist/build-info.json'));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const results = [];
try {
  for (const [width,height] of [[1440,900],[768,1024],[390,844]]) {
    const context = await browser.newContext({viewport:{width,height}, serviceWorkers:'block', reducedMotion:'reduce'});
    await context.addInitScript(() => {
      window.qa = {draws:0, consumed:[]};
      const original = Response.prototype.arrayBuffer;
      Response.prototype.arrayBuffer = async function(...args) {
        const bytes = await original.apply(this,args);
        if (bytes.byteLength >= 4 && String.fromCharCode(...new Uint8Array(bytes,0,4)) === 'glTF') {
          const digest = await crypto.subtle.digest('SHA-256',bytes);
          window.qa.consumed.push([...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join(''));
        }
        return bytes;
      };
      for (const Type of [WebGLRenderingContext,WebGL2RenderingContext]) {
        const clear = Type.prototype.clear;
        Type.prototype.clear = function(...args) {window.qa.frame = {calls:0,triangles:0};return clear.apply(this,args);};
        for (const method of ['drawElements','drawArrays']) {
          const draw = Type.prototype[method];
          Type.prototype[method] = function(...args) {
            window.qa.draws++;
            window.qa.frame.calls++;
            if (args[0]===this.TRIANGLES) window.qa.frame.triangles += (method==='drawElements'?args[1]:args[2])/3;
            return draw.apply(this,args);
          };
        }
      }
    });
    const page = await context.newPage();
    const errors = [], result = {viewport:[width,height],status:'FAIL',errors};
    results.push(result);
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error') errors.push(m.text());});
    page.on('requestfailed',r=>errors.push(r.url()+' '+r.failure()?.errorText));
    page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});
    const ready = () => page.waitForFunction(() => document.querySelector('#viewer')?.open &&
      document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.qa.draws>0,
      null,{timeout:60000});
    await page.goto(server.url+'?model=ice-cream-chest-freezer',{waitUntil:'domcontentloaded'});
    await ready();
    assert.equal(await page.locator('#viewer-title').innerText(),'Ice Cream Chest Freezer');
    assert.equal(await page.locator('#viewer-download').isVisible(),false);
    const canvas = page.locator('#viewport canvas');
    const shot = async () => {await canvas.evaluate(el=>el.blur());await page.waitForTimeout(150);return createHash('sha256').update(await canvas.screenshot()).digest('hex');};
    const initial = await shot();
    await canvas.press('ArrowRight');
    const orbit = await shot();assert.notEqual(orbit,initial);
    await canvas.press('+');
    const zoom = await shot();assert.notEqual(zoom,orbit);
    await page.getByRole('button',{name:/reset view/i}).click();
    const reset = await shot();assert.equal(reset,initial,'Reset restores the same rendered view');
    const metrics = await page.evaluate(()=>({...window.qa,
      overflow:document.documentElement.scrollWidth>innerWidth,
      label:document.querySelector('#viewport canvas').getAttribute('aria-label')}));
    assert.equal(metrics.overflow,false);
    assert.ok(metrics.label?.length);
    assert.ok(metrics.consumed.includes(expected.sha256));
    assert.equal(metrics.frame.calls,expected.mesh_primitives);
    assert.equal(metrics.frame.triangles,expected.triangles);
    const screenshot=path.join(out,`ice-cream-chest-freezer-${width}-page.png`);
    await page.screenshot({path:screenshot});
    await page.reload({waitUntil:'domcontentloaded'});await ready();
    await page.locator('#close-viewer').click();
    await page.waitForFunction(()=>!document.querySelector('#viewer').open);
    await page.locator('[data-asset-id="ice-cream-chest-freezer"]').first().click();await ready();
    assert.deepEqual(errors,[]);
    Object.assign(result,{status:'PASS',screenshot,metrics,keyboard_orbit:'PASS',keyboard_zoom:'PASS',reset:'PASS',refresh_reopen:'PASS'});
    await context.close();
  }
} finally {
  await fs.writeFile(path.join(dir,'reports/browser.json'),JSON.stringify({result:results.length===3&&results.every(r=>r.status==='PASS')?'PASS':'FAIL',
    renderer:'Desktop Chromium / SwiftShader; viewport emulation only',browser:browser.version(),build,results},null,2)+'\n');
  await browser.close();await server.close();
}
console.log(JSON.stringify(results));
