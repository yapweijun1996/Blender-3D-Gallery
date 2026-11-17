import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild,launchOptions} from '../../scripts/browser-test-utils.mjs';

const server=await serveBuild();
const browser=await chromium.launch(launchOptions);
const context=await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block'});
await context.addInitScript(()=>{
  window.qaDrawCalls=0;
  for(const type of [WebGLRenderingContext,WebGL2RenderingContext]) {
    for(const name of ['drawArrays','drawElements','drawArraysInstanced','drawElementsInstanced']) {
      const original=type.prototype[name];
      if(original) type.prototype[name]=function(...args){window.qaDrawCalls++;return original.apply(this,args);};
    }
  }
});
const page=await context.newPage(), errors=[], glbResponses=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
page.on('response',r=>{
  if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);
  if(new URL(r.url()).pathname.endsWith('.glb'))glbResponses.push(r);
});
const hash=b=>createHash('sha256').update(b).digest('hex');
try {
  await page.goto(server.url+'?model=atrium-chandelier',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#viewport canvas') &&
    document.querySelector('#viewer-status')?.textContent==='' && window.qaDrawCalls>0,
    null,{timeout:60000});
  // Vite fingerprints exported filenames. Verify actual response bytes instead.
  assert.equal(glbResponses.length,1);
  const response=glbResponses[0];
  assert.equal(response.status(),200);
  const received=await response.body();
  const expected=await fs.readFile(new URL('exports/optimized.glb',import.meta.url));
  assert.equal(hash(received),hash(expected));
  assert.equal(await page.locator('#viewer-title').textContent(),'Atrium Chandelier');
  assert.equal(await page.locator('#viewport canvas').count(),1);
  assert.equal(await page.locator('#reset-view').isEnabled(),true);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  const canvas=page.locator('#viewport canvas');
  await canvas.focus();
  const before=await page.evaluate(()=>window.qaDrawCalls);
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(n=>window.qaDrawCalls>n,before);
  await page.locator('#reset-view').click();
  await page.waitForTimeout(700);
  const directory=path.join(os.homedir(),'Documents/MallQueue/reports');
  await fs.mkdir(directory,{recursive:true});
  const screenshot=path.join(directory,'atrium-chandelier-page.png');
  await page.screenshot({path:screenshot});
  // Inspect the revised gem facets under the same production page lighting.
  await canvas.focus();
  for(let i=0;i<5;i++) await page.keyboard.press('+');
  await page.waitForTimeout(700);
  const closeup=path.join(directory,'atrium-chandelier-closeup.png');
  await canvas.screenshot({path:closeup});
  assert.deepEqual(errors,[]);
  const result={result:'PASS',viewport:[1440,900],browser:browser.version(),headless:true,
    software_webgl:true,production_build:true,glb_response_path:new URL(response.url()).pathname,
    glb_response_sha256:hash(received),
    actual_glb_loaded:true,webgl_draws_observed:await page.evaluate(()=>window.qaDrawCalls),
    keyboard_orbit_and_reset:'PASS',canvas_count:1,page_errors:errors,screenshot,closeup,
    limitations:['No physical-device, WebKit, assembled-mall lighting or full-scene performance validation.']};
  await fs.writeFile(new URL('reports/browser.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
} finally {
  await context.close();await browser.close();await server.close();
}
