import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild,launchOptions,openModelFilters} from './browser-test-utils.mjs';
const dir=new URL('../models/mall-fit-finishes/reports/browser/',import.meta.url);await fs.mkdir(dir,{recursive:true});
const ids=['mall-shopfront-fascia-210','mall-shopfront-fascia-120','mall-column-ceiling-collar'];
const catalog=JSON.parse(await fs.readFile(new URL('../models/catalog.json',import.meta.url)));const assets=catalog.collections.find(c=>c.id==='mall-fit-finishes').assets;
const server=await serveBuild(),browser=await chromium.launch(launchOptions),results=[];
try{
 for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  const page=await browser.newPage({viewport});const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});page.on('request',r=>{if(r.url().endsWith('.glb'))requests.push(r.url())});
  await page.addInitScript(()=>{window.assetDraws=0;for(const C of [window.WebGLRenderingContext,window.WebGL2RenderingContext])for(const n of ['drawArrays','drawElements']){const f=C?.prototype[n];if(f)C.prototype[n]=function(...a){window.assetDraws++;return f.apply(this,a)}}});
  await page.goto(server.url,{waitUntil:'networkidle'});
  await openModelFilters(page);
  await page.locator('#model-collection').selectOption('mall-fit-finishes');
  assert.equal(await page.locator('#catalog .asset-card').count(),3);assert.equal(requests.length,0);assert.equal(await page.locator('canvas').count(),0);
  for(const id of ids){
   const a=assets.find(a=>a.id===id);const response=page.waitForResponse(r=>r.url().endsWith('.glb')&&r.status()===200);
   await page.locator(`[data-asset-id="${id}"]`).first().click();
   await page.waitForFunction(()=>document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status').textContent===''&&window.assetDraws>0);
   const loaded=await response,bytes=await loaded.body(),local=await fs.readFile(a.file);assert.equal(createHash('sha256').update(bytes).digest('hex'),createHash('sha256').update(local).digest('hex'));
   assert.equal(await page.locator('#viewer-title').innerText(),a.name);assert.equal(await page.locator('#viewer-download').isVisible(),false);
   await page.screenshot({path:new URL(`${id}-${viewport.width}.png`,dir).pathname});
   const canvas=page.locator('#viewport canvas'),before=await page.evaluate(()=>window.assetDraws);await canvas.press('ArrowRight');await page.waitForFunction(n=>window.assetDraws>n,before);
   await page.locator('#reset-view').click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   results.push({id,viewport,loadedHash:createHash('sha256').update(bytes).digest('hex'),rendered:true,orbitReset:true,passed:true});await page.locator('#close-viewer').click();assert.equal(await page.locator('#viewport canvas').count(),0);
  }assert.deepEqual(errors,[]);await page.close();
 }
}finally{await browser.close();await server.close();await fs.writeFile(new URL('results.json',dir),JSON.stringify(results,null,2)+'\n')}
console.log('Gallery fit finishes',results.length,'viewer cases PASS');
