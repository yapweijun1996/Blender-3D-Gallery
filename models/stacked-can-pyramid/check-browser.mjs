// Real production-gallery flow and contact sheets for both independently registered GLBs.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from '../../scripts/browser-test-utils.mjs';

const here = fileURLToPath(new URL('.', import.meta.url));
const delivery = path.join(os.homedir(),'Documents/MallQueue/reports');
await fs.mkdir(delivery,{recursive:true});
const variants = [
 {id:'stacked-can-pyramid',file:'optimized.glb',suffix:''},
 {id:'stacked-can-pyramid-variant-b',file:'optimized-variant-b.glb',suffix:'-variant-b'},
];
const sha256 = buffer => createHash('sha256').update(buffer).digest('hex');
for (const v of variants) v.hash = sha256(await fs.readFile(here+'exports/'+v.file));
const build = await serveBuild(), source = await serveBuild('.');
const browser = await chromium.launch(launchOptions);
const results = [], failures = [];
try {
 for (const width of [1440,390]) {
  const context = await browser.newContext({viewport:{width,height:900},serviceWorkers:'block',reducedMotion:'reduce'});
  await context.addInitScript(() => {
   window.qaFrame={calls:0,triangles:0};
   for (const Type of [WebGLRenderingContext,WebGL2RenderingContext]) {
    const clear=Type.prototype.clear;
    Type.prototype.clear=function(...args){window.qaFrame={calls:0,triangles:0};return clear.apply(this,args);};
    for (const method of ['drawElements','drawArrays']) {
     const original=Type.prototype[method];
     Type.prototype[method]=function(...args){
      window.qaFrame.calls++;
      if(args[0]===this.TRIANGLES) window.qaFrame.triangles+=(method==='drawElements'?args[1]:args[2])/3;
      return original.apply(this,args);
     };
    }
   }
  });
  for (const variant of variants) {
   const page=await context.newPage(), errors=[], hashes=[], pending=[];
   page.on('pageerror',e=>errors.push(e.message));
   page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
   page.on('response',r=>{
    if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);
    if(new URL(r.url()).pathname.endsWith('.glb')&&r.ok())pending.push(r.body().then(b=>hashes.push(sha256(b))));
   });
   await page.goto(build.url+'?model='+variant.id,{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status')?.textContent===''&&window.qaFrame.calls>0,null,{timeout:60000});
   await Promise.all(pending);
   assert.ok(hashes.includes(variant.hash),'production build loads the exact tested GLB');
   const canvas=page.locator('#viewport canvas');
   // Pointer clicks change :focus-visible independently of the camera. Compare
   // WebGL pixels inside the 4 px inset focus outline at every tested viewport.
   const snapshot=async()=>{
    await canvas.scrollIntoViewIfNeeded();
    const b=await canvas.boundingBox();
    return page.screenshot({clip:{x:b.x+8,y:b.y+8,width:b.width-16,height:b.height-16}});
   };
   await canvas.focus();await page.waitForTimeout(300);
   const initial=await snapshot();
   await page.keyboard.press('ArrowLeft');await page.waitForTimeout(300);
   const rotated=await snapshot();
   assert.ok(!initial.equals(rotated),'keyboard rotation changes visible pixels');
   await page.keyboard.press('+');await page.waitForTimeout(300);
   assert.ok(!rotated.equals(await snapshot()),'zoom changes visible pixels');
   await page.getByRole('button',{name:/Reset view/}).click();await canvas.focus();await page.waitForTimeout(300);
   assert.ok(initial.equals(await snapshot()),'reset restores exact WebGL interior pixels');
   const render=await page.evaluate(()=>({...window.qaFrame,overflow:document.documentElement.scrollWidth>innerWidth,
    canvas_label:document.querySelector('#viewport canvas').getAttribute('aria-label'),
    context_lost:document.querySelector('#viewport canvas').getContext('webgl2').isContextLost()}));
   assert.equal(render.calls,2);assert.equal(render.triangles,6976);
   assert.equal(render.overflow,false);assert.equal(render.context_lost,false);assert.deepEqual(errors,[]);
   const screenshot=path.join(delivery,`stacked-can-pyramid${variant.suffix}${width===1440?'':'-390'}-page.png`);
   await page.screenshot({path:screenshot});
   results.push({kind:'production-gallery',id:variant.id,viewport:[width,900],loaded_sha256:variant.hash,render,
    controls:'rotation and zoom change WebGL interior pixels; reset restores exact interior pixels (focus outline excluded)',errors,screenshot});
   await page.close();
  }
  const qa=await context.newPage(),errors=[],hashes=[],pending=[];
  qa.on('pageerror',e=>errors.push(e.message));qa.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  qa.on('response',r=>{
   if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);
   if(new URL(r.url()).pathname.endsWith('.glb')&&r.ok())pending.push(r.body().then(b=>hashes.push(sha256(b))));
  });
  await qa.goto(source.url+'models/stacked-can-pyramid/reports/runtime-qa.html');
  await qa.waitForFunction(()=>window.qaResults?.ready);
  await Promise.all(pending);
  const record=await qa.evaluate(()=>window.qaResults);
  assert.equal(record.records.length,4);
  for(const r of record.records){assert.equal(r.draw_calls_model_only,2);assert.equal(r.rendered_triangles,6976);assert.equal(r.collider_visible,false);assert.equal(r.context_lost,false);}
  for(const v of variants)assert.ok(hashes.includes(v.hash));
  assert.deepEqual(errors,[]);
  const screenshot=here+`previews/contact-${width}.png`;
  await qa.screenshot({path:screenshot,fullPage:true});
  results.push({kind:'variant-contact-sheet',width,...record,hashes,errors,screenshot});
  await context.close();
 }
} catch(e){failures.push(e.stack);throw e;}
finally {
 await fs.writeFile(here+'reports/browser.json',JSON.stringify({result:failures.length?'FAIL':'PASS',browser_version:browser.version(),results,failures,
  scope:'Local production build and GLB contact sheets in desktop Chromium, including 390 px viewport emulation; physical devices and assembled mall unverified.'},null,2)+'\n');
 await browser.close();await source.close();await build.close();
}
console.log(JSON.stringify({result:'PASS',results},null,2));
