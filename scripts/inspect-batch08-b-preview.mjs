import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {serveBuild,launchOptions} from './browser-test-utils.mjs';
const slugs=['roadside-concrete-drain', 'monsoon-drain-section', 'drain-grating', 'pedestrian-refuge-island', 'tactile-paving-tile'];
const out=process.env.PREVIEW_QA_DIR||'docs/verification/batch08-b/browser-preflight';
await fs.mkdir(out,{recursive:true});
const server=await serveBuild(),browser=await chromium.launch(launchOptions),results=[];
try {
 for(const slug of slugs){
  const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce',serviceWorkers:'block'});
  const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>errors.push(r.url()+' '+r.failure()?.errorText));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  await page.goto(server.url+'?model='+slug,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#viewer')?.open&&document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status')?.textContent==='',null,{timeout:60000});
  await page.waitForTimeout(400);
  await page.locator('#viewport canvas').screenshot({path:out+'/'+slug+'.png'});
  assert.deepEqual(errors,[]);results.push({slug,initial_preview_captured:true,errors});
  await context.close();
 }
}finally{await browser.close();await server.close();await fs.writeFile(out+'/results.json',JSON.stringify({purpose:'Initial visual inspection only, not controls or full browser quality gate',browser:browser.version(),results},null,2)+'\n');}
