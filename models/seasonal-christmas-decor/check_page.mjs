import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const dir=fileURLToPath(new URL('.',import.meta.url));
const slug='seasonal-christmas-decor';
const output=path.join(os.homedir(),'Documents/MallQueue/reports');
fs.mkdirSync(output,{recursive:true});
const server=await serveBuild();
const browser=await chromium.launch(launchOptions);
const context=await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block'});
const page=await context.newPage();
const errors=[],requests=[],hashes=[],responseTasks=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
page.on('request',r=>{if(r.url().endsWith('.glb'))requests.push(r.url());});
page.on('response',r=>{
  if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);
  // Vite emits hashed filenames; verify the actual GLB response bytes.
  if(new URL(r.url()).pathname.endsWith('.glb')){
    responseTasks.push(r.body().then(bytes=>hashes.push(createHash('sha256').update(bytes).digest('hex'))));
  }
});
await context.addInitScript(()=>{
  window.qaDrawCalls=0;
  window.qaDrawsPerFrame=0;
  window.qaFrameCounts=[];
  for(const type of [WebGLRenderingContext,WebGL2RenderingContext]){
    for(const name of ['drawArrays','drawElements','drawArraysInstanced','drawElementsInstanced']){
      const original=type.prototype[name];
      if(original)type.prototype[name]=function(...args){
        window.qaDrawCalls++;
        window.qaDrawsPerFrame++;
        return original.apply(this,args);
      };
    }
  }
  function frame(){
    window.qaFrameCounts.push(window.qaDrawsPerFrame);
    if(window.qaFrameCounts.length>120)window.qaFrameCounts.shift();
    window.qaDrawsPerFrame=0;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
});
try{
  await page.goto(server.url+`?model=${slug}`,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#viewer')?.open &&
    document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent==='' && window.qaDrawCalls>0,
    null,{timeout:60000});
  assert.equal(await page.locator('#viewer-title').textContent(),'Seasonal Christmas Decor');
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const screenshot=path.join(output,slug+'-page.png');
  await page.screenshot({path:screenshot,fullPage:false});
  const before=await page.evaluate(()=>window.qaDrawCalls);
  await page.locator('#reset-view').click();
  await page.waitForFunction(n=>window.qaDrawCalls>n,before);
  const state=await page.evaluate(()=>({
    overflow:document.documentElement.scrollWidth>innerWidth,
    canvasCount:document.querySelectorAll('#viewport canvas').length,
    canvas:{width:document.querySelector('#viewport canvas').width,height:document.querySelector('#viewport canvas').height},
    renderedDrawCalls:window.qaDrawCalls,
    observedNonemptyFrameDrawCalls:window.qaFrameCounts.filter(n=>n>0)
  }));
  assert.equal(state.overflow,false);
  assert.equal(state.canvasCount,1);
  const expected=createHash('sha256').update(fs.readFileSync(dir+'exports/optimized.glb')).digest('hex');
  await page.waitForFunction(()=>document.querySelector('#viewer-status')?.textContent==='');
  await Promise.all(responseTasks);
  assert.deepEqual(hashes,[expected],'browser consumed the tested GLB');
  assert.equal(requests.length,1,'only the requested model loads');
  assert.deepEqual(errors,[]);
  const report={result:'PASS',viewport:[1440,900],browser:browser.version(),launchOptions,
    screenshot,glb_sha256:expected,requested_glbs:requests.length,request_paths:requests.map(url=>new URL(url).pathname),errors,reset_view:'PASS',...state,
    limitations:'Headless desktop Chromium only. Frame calls include gallery studio/shadow passes; full mall performance, physical phones and WebKit unverified.'};
  fs.writeFileSync(dir+'reports/browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}finally{
  await context.close();
  await browser.close();
  await server.close();
}
