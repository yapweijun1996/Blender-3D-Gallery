// Exercise the existing gallery against the production build, without UI edits.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {homedir} from 'node:os';
import path from 'node:path';
import {chromium} from 'playwright';
import {serveBuild,launchOptions} from '../../scripts/browser-test-utils.mjs';

const server=await serveBuild();
const browser=await chromium.launch(launchOptions);
const errors=[], failures=[], loaded=[];
const screenshot=path.join(homedir(),'Documents/MallQueue/reports/elevator-interior-page.png');
try {
  const context=await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block'});
  await context.addInitScript(()=>{
    window.qaDrawCalls=0;
    window.qaDrawsByFrame=[];
    const raf=window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame=callback=>raf(t=>{
      const before=window.qaDrawCalls;
      callback(t);
      const count=window.qaDrawCalls-before;
      if(count) window.qaDrawsByFrame.push(count);
    });
    for(const type of [WebGLRenderingContext,WebGL2RenderingContext]) {
      for(const name of ['drawArrays','drawElements','drawArraysInstanced','drawElementsInstanced']) {
        const original=type.prototype[name];
        if(original) type.prototype[name]=function(...args){window.qaDrawCalls++;return original.apply(this,args);};
      }
    }
  });
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error') errors.push(m.text());});
  page.on('requestfailed',r=>failures.push({url:r.url(),error:r.failure()}));
  page.on('response',r=>{if(r.status()>=400) failures.push({url:r.url(),status:r.status()});});
  // Vite hashes delivery filenames; this page lazily requests its one GLB.
  const response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('.glb'));
  await page.goto(server.url+'?model=elevator-interior',{waitUntil:'domcontentloaded'});
  const modelResponse=await response;
  const servedBytes=await modelResponse.body();
  const expected=await fs.readFile(new URL('exports/optimized.glb',import.meta.url));
  const hash=b=>createHash('sha256').update(b).digest('hex');
  assert.equal(hash(servedBytes),hash(expected),'browser received the measured GLB');
  loaded.push({sha256:hash(servedBytes),bytes:servedBytes.length,status:modelResponse.status()});
  const ready=()=>page.waitForFunction(()=>document.querySelector('#viewer')?.open &&
    document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent==='' &&
    window.qaDrawCalls>0,null,{timeout:60000});
  await ready();
  assert.equal(await page.locator('#viewer-title').innerText(),'Elevator Interior');
  assert.equal(await page.locator('#viewport canvas').count(),1);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('#viewport canvas').focus();
  const before=await page.evaluate(()=>window.qaDrawCalls);
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(n=>window.qaDrawCalls>n,before);
  await page.locator('#reset-view').click();
  // Allow damped controls to settle before recording the default view.
  await page.waitForTimeout(1000);
  await fs.mkdir(path.dirname(screenshot),{recursive:true});
  await page.screenshot({path:screenshot});
  const canvasSize=await page.locator('#viewport canvas').evaluate(c=>[c.clientWidth,c.clientHeight]);
  const draws=await page.evaluate(()=>({draw_calls:window.qaDrawCalls,draw_calls_by_frame:window.qaDrawsByFrame}));
  assert.ok(draws.draw_calls_by_frame.some(n=>n===10),'10 model primitives rendered in a frame');
  await page.reload({waitUntil:'domcontentloaded'});
  await ready();
  await page.locator('#close-viewer').click();
  assert.equal(await page.locator('#viewport canvas').count(),0);
  assert.equal(await page.locator('#viewer').evaluate(o=>o.open),false);
  assert.deepEqual(errors,[]);
  assert.deepEqual(failures,[]);
  const report={result:'PASS',viewport:[1440,900],canvas_size:canvasSize,browser:browser.version(),loaded,screenshot,
    checks:['production page opens','GLB hash matches','WebGL draws','one canvas','keyboard orbit',
      'reset','refresh','close disposes canvas','no horizontal overflow','no console or network errors'],
    draws,errors,failures,scope:'Headless Chromium software WebGL only; no physical mobile, WebKit or full mall assembly.'};
  await fs.writeFile(new URL('reports/browser.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
  await context.close();
} finally {
  await browser.close();
  await server.close();
}
