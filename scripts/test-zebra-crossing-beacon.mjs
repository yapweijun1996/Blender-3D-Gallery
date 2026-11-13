import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild,launchOptions} from './browser-test-utils.mjs';
const catalog=JSON.parse(await fs.readFile(new URL('../models/catalog.json',import.meta.url),'utf8'));
const assets=catalog.collections.find(c=>c.id==='zebra-crossing-beacon').assets;
const out=process.env.MALL_QA_DIR||'/tmp/blender-zebra-crossing-beacon-config-qa';await fs.mkdir(out,{recursive:true});
const server=await serveBuild(),browser=await chromium.launch(launchOptions),results=[];
try{
for(const asset of assets)for(const [width,height] of [[1440,900],[768,1024],[390,844]]){
 const bytes=await fs.readFile(new URL('../'+asset.file,import.meta.url)),sha256=createHash('sha256').update(bytes).digest('hex');
 const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',serviceWorkers:'block'}),page=await context.newPage();
 const errors=[],responses=[],result={asset:asset.id,width,height,runtime:'Desktop Chromium with viewport emulation, not Android/iOS',sha256,bytes:bytes.length,passed:false,requestConsolePageErrors:errors};
 try{
  await page.addInitScript(()=>{
   window.mallConsumedGlbs=[];window.mallDraws=0;const original=Response.prototype.arrayBuffer;
   Response.prototype.arrayBuffer=async function(...args){const buffer=await original.apply(this,args);if(buffer.byteLength>=4&&String.fromCharCode(...new Uint8Array(buffer,0,4))==='glTF'){const digest=await crypto.subtle.digest('SHA-256',buffer);window.mallConsumedGlbs.push({bytes:buffer.byteLength,sha256:[...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('')});}return buffer;};
   for(const Context of [window.WebGLRenderingContext,window.WebGL2RenderingContext])for(const name of ['drawArrays','drawElements']){const fn=Context?.prototype[name];if(fn)Context.prototype[name]=function(...args){window.mallDraws++;return fn.apply(this,args);};}
  });
  page.on('requestfailed',r=>errors.push(r.method()+' '+r.url()+' '+r.failure()?.errorText));
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('response',r=>{if(r.url().endsWith('.glb'))responses.push(r);if(r.status()>=400)errors.push(r.status()+' '+r.url());});
  await page.goto(server.url+'?model='+asset.id,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#viewer')?.open&&document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status')?.textContent===''&&window.mallDraws>0,null,{timeout:60000});
  assert.equal(await page.locator('#viewer-title').innerText(),asset.name);assert.equal(await page.locator('#viewer-download').isVisible(),false);
  const canvas=page.locator('#viewport canvas');await canvas.focus();const shot=async(label)=>{await canvas.evaluate(el=>el.blur());await page.waitForTimeout(350);return createHash('sha256').update(await canvas.screenshot({path:path.join(out,asset.id+'-'+width+'-'+label+'.png')})).digest('hex');}; // Same focus/modality for every complete screenshot; no masking.
  const initial=await shot('initial');
  let draws=await page.evaluate(()=>window.mallDraws);await canvas.press('ArrowRight');await page.waitForFunction(n=>window.mallDraws>n,draws);const orbit=await shot('orbit');assert.notEqual(orbit,initial);
  draws=await page.evaluate(()=>window.mallDraws);await canvas.press('PageUp');await page.waitForFunction(n=>window.mallDraws>n,draws);const zoom=await shot('zoom');assert.notEqual(zoom,orbit);
  await page.locator('#reset-view').click();const reset=await shot('reset');assert.equal(reset,initial,'reset restores configured asset initial view');
  for(let i=0;i<8;i++)await canvas.press('ArrowDown');const rear=await shot('rear');assert.notEqual(rear,initial);
  await page.locator('#reset-view').click();assert.equal(await shot('final-reset'),initial);
  result.initialConsumed=await page.evaluate(()=>window.mallConsumedGlbs);assert.ok(result.initialConsumed.some(x=>x.bytes===bytes.length&&x.sha256===sha256));
  await page.locator('#close-viewer').click();assert.equal(await canvas.count(),0);
  await page.goto(server.url+'?model='+asset.id,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#viewer')?.open&&document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status')?.textContent===''&&window.mallDraws>0,null,{timeout:60000});
  const reopened=await shot('reopened');assert.equal(reopened,initial,'reopen restores configured asset initial view');
  result.pixels={initial,orbit,zoom,reset,rear,reopened};result.resetMatchesInitial=true;result.reopenMatchesInitial=true;
  await page.screenshot({path:path.join(out,asset.id+'-'+width+'-page.png')});
  result.consumed=await page.evaluate(()=>window.mallConsumedGlbs);assert.ok(result.consumed.some(x=>x.bytes===bytes.length&&x.sha256===sha256));
  result.glbResponses=responses.map(r=>({path:new URL(r.url()).pathname,status:r.status()}));assert.ok(responses.length>0);for(const r of responses)assert.equal(r.status(),200);
  result.horizontalOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(result.horizontalOverflow,false);
  result.renderDrawCalls=await page.evaluate(()=>window.mallDraws);result.controls=['orbit','zoom','exact reset','additional orbit','close and exact reopen'];result.defaultView='Configured street asset camera; static gallery orbit controls only';
  assert.deepEqual(errors,[]);result.passed=true;console.log('PASS',asset.id,width);
 }catch(e){result.failure=e.message;await page.screenshot({path:path.join(out,asset.id+'-'+width+'-failure.png')}).catch(()=>{});console.error('FAIL',asset.id,width,e.message);}
 finally{results.push(result);await context.close();}
}
}finally{await browser.close();await server.close();await fs.writeFile(path.join(out,'results.json'),JSON.stringify({browserVersion:browser.version(),policy:'No requestfailed or ERR_ABORTED filtering; one fixed pass of all three cases',android:'NOT TESTED',ios:'NOT TESTED',results},null,2)+'\n');}
if(results.some(r=>!r.passed))process.exitCode=1;
