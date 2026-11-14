import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { loadCatalog } from "./catalog.mjs";
import assert from "node:assert/strict";
import { chromium } from "playwright";
import { serveBuild, launchOptions } from "./browser-test-utils.mjs";
const assets=loadCatalog().collections.flatMap(c=>c.assets);
const realAsset=assets.find(a=>a.id==="demo-food-tin"), beverage=assets.find(a=>a.id==="demo-beverage-can");
assert.ok(beverage,"Beverage asset must be registered");
const foodURL=/\/demo-food-tin(?:-[\w-]+)?\.glb(?:\?|$)/, beverageURL=/\/demo-beverage-can(?:-[\w-]+)?\.glb(?:\?|$)/;
const beverageBytes=await fs.readFile(beverage.file),beverageSha=createHash("sha256").update(beverageBytes).digest("hex");
assert.ok(realAsset,"Real demo tin must be registered before this gate");
const expectedBytes=await fs.readFile(realAsset.file),expectedSha=createHash("sha256").update(expectedBytes).digest("hex");
const out=process.env.TEST_ARTIFACT_DIR||"output/product-studio-browser";
await fs.mkdir(out,{recursive:true});
const server=await serveBuild(),browser=await chromium.launch(launchOptions),results=[];
async function run(name,fn,options={}) {
 const context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:"block",...options});
 await context.addInitScript(()=>{
  window.qaDrawCalls=0;
  const gpu=Object.fromEntries(['Buffer','Texture','Program','Framebuffer','Renderbuffer','VertexArray'].map(k=>[k,new Set()]));
  window.qaGpu=()=>Object.fromEntries(Object.entries(gpu).map(([k,set])=>[k,set.size]));
  for(const C of [window.WebGLRenderingContext,window.WebGL2RenderingContext])if(C)for(const key of Object.keys(gpu))for(const operation of ['create','delete']) {
    const name=operation+key;if(!Object.hasOwn(C.prototype,name))continue;const f=C.prototype[name];
    C.prototype[name]=function(...args){const result=f.apply(this,args);if(operation==='create'&&result)gpu[key].add(result);if(operation==='delete')gpu[key].delete(args[0]);return result;};
  }
  window.qaBitmapClosed=0;window.qaBitmapHeld=0;window.qaReleaseBitmaps=()=>{for(const release of window.qaBitmapReleases.splice(0))release();};window.qaBitmapReleases=[];
  const close=ImageBitmap.prototype.close;ImageBitmap.prototype.close=function(){window.qaBitmapClosed++;return close.call(this);};
  const bitmap=window.createImageBitmap;window.createImageBitmap=async function(...args){const image=await bitmap.apply(this,args);if(window.qaDelayBitmapNext){window.qaDelayBitmapNext=false;window.qaBitmapHeld++;await new Promise(resolve=>window.qaBitmapReleases.push(resolve));}return image;};
  for(const C of [window.WebGLRenderingContext,window.WebGL2RenderingContext])if(C)for(const k of ["drawArrays","drawElements"]){const f=C.prototype[k];C.prototype[k]=function(...a){window.qaDrawCalls++;return f.apply(this,a);};}
 });
 context.setDefaultTimeout(15000);context.setDefaultNavigationTimeout(30000);
 const page=await context.newPage(),errors=[];console.log("START",name);
 page.on("pageerror",e=>errors.push(e.message));page.on("console",m=>{if(m.type()==="error")errors.push(m.text());});
 const result={name,status:"FAIL"};
 try{Object.assign(result,await fn(page,context,errors));result.status="PASS";console.log("PASS",name);}
 catch(e){result.error=e.stack;console.error("FAIL",name,e.message);await page.screenshot({path:path.join(out,name+"-failure.png"),fullPage:true}).catch(()=>{});}
 finally{result.errors=errors;results.push(result);server.setFault(null);await context.close();await fs.writeFile(path.join(out,"results.json"),JSON.stringify({browser:browser.version(),deviceScope:"Desktop Chromium with viewport/touch emulation; not physical iOS/Android",results},null,2));}
}
const hash=b=>createHash("sha256").update(b).digest("hex");
// Locator screenshots round fractional CSS edges differently after touch scrolling.
// Compare every interior pixel exactly; exclude only the 2px DOM border, never model geometry.
async function pixelHash(page, png) {
 const pixels=await page.evaluate(async data=>{
  const image=new Image();image.src="data:image/png;base64,"+data;await image.decode();
  const c=document.createElement("canvas");c.width=image.width;c.height=image.height;
  const ctx=c.getContext("2d");ctx.drawImage(image,0,0);
  const bytes=ctx.getImageData(2,2,c.width-4,c.height-4).data;
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))).map(n=>n.toString(16).padStart(2,"0")).join("");
 },png.toString("base64"));return pixels;
}
const studio="?page=product-studio";
async function ready(page,modelId="demo-food-tin"){await page.locator(`.ps-stage[data-pose=closed][data-model-id="${modelId}"]`).waitFor();assert.equal(await page.locator("#product-studio-page canvas").count(),1);assert.equal(await page.locator(".ps-stage").getAttribute("data-model-id"),modelId);assert.equal(await page.locator(".ps-stage").getAttribute("data-model-root"),assets.find(a=>a.id===modelId).root);assert.equal(await page.locator(".ps-stage").getAttribute("aria-busy"),"false");}
async function pose(page,state){await page.waitForFunction(s=>document.querySelector(".ps-stage")?.dataset.pose===s,state);}
const action=(page,a)=>page.locator('[data-action="'+a+'"]');
async function framed(page) {
 // Pixel-analysis capture removes only the ancestor cosmetic corner mask. Normal evidence retains it.
 const mask=page.locator(".ps-layout");
 const oldStyle=await mask.getAttribute("style");
 let png;
 try { await mask.evaluate(el=>el.style.setProperty("border-radius","0","important")); png=await page.locator(".ps-stage canvas").screenshot(); }
 finally { await mask.evaluate((el,old)=>{if(old===null)el.removeAttribute("style");else el.setAttribute("style",old);},oldStyle); }
 const bounds=await page.evaluate(async encoded=>{
  const im=new Image();im.src="data:image/png;base64,"+encoded;await im.decode();const c=document.createElement("canvas");c.width=im.width;c.height=im.height;const x=c.getContext("2d");x.drawImage(im,0,0);const d=x.getImageData(0,0,c.width,c.height).data;let minX=c.width,minY=c.height,maxX=-1,maxY=-1,count=0;
  const bg=(10*c.width+10)*4;
  // Screenshot clips can include a one-pixel fractional CSS border. Scan beyond it, still require >4px model margin.
  for(let y=2;y<c.height-2;y++)for(let xx=2;xx<c.width-2;xx++){const k=(y*c.width+xx)*4;if(Math.max(Math.abs(d[k]-d[bg]),Math.abs(d[k+1]-d[bg+1]),Math.abs(d[k+2]-d[bg+2]))>15){minX=Math.min(minX,xx);minY=Math.min(minY,y);maxX=Math.max(maxX,xx);maxY=Math.max(maxY,y);count++;}}
  return {minX,minY,maxX,maxY,count,width:c.width,height:c.height};
 },png.toString("base64"));
 assert.ok(bounds.count>100&&bounds.minX>4&&bounds.minY>4&&bounds.maxX<bounds.width-5&&bounds.maxY<bounds.height-5,"actual rendered model stays inside canvas: "+JSON.stringify(bounds));
}
async function noOverflow(page){assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);}
try {
 await run("skip-link-keyboard-access",async(page)=>{
  await page.goto(server.url+studio);await ready(page);
  const skip=page.locator('.skip-link');assert.equal(await skip.evaluate(el=>getComputedStyle(el).opacity),'0');
  await page.keyboard.press('Tab');assert.equal(await skip.evaluate(el=>el===document.activeElement),true);
  assert.equal(await skip.evaluate(el=>getComputedStyle(el).opacity),'1');
  assert.ok((await skip.boundingBox()).y>=0);await page.screenshot({path:path.join(out,'skip-keyboard.png')});
  await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>location.hash),'#main-content');
 });
 for(const width of [1440,768,390,320])await run("controls-"+width,async(page,context,errors)=>{
  const consumed=[],pending=[];page.on("response",r=>{if(r.url().endsWith(".glb")&&r.ok())pending.push(r.body().then(b=>consumed.push({url:r.url(),bytes:b.length,sha256:createHash("sha256").update(b).digest("hex")})));});
  await page.goto(server.url+studio,{waitUntil:"domcontentloaded"});await ready(page);
  await noOverflow(page);await framed(page);assert.equal(await page.locator(".ps-demo").innerText(),"FICTIONAL DEMO");
  const canvas=page.locator(".ps-stage canvas"),first=await canvas.screenshot({path:path.join(out,width+"-closed.png")});
  await action(page,"open").click();await pose(page,"open");const open=await canvas.screenshot({path:path.join(out,width+"-open.png")});assert.notDeepEqual(open,first);await framed(page);
  await action(page,"explode").click();await pose(page,"exploded");const exploded=await canvas.screenshot({path:path.join(out,width+"-exploded.png")});assert.notDeepEqual(exploded,open);await framed(page);console.log("STEP",width,"exploded-frame");
  assert.equal(await action(page,"open").getAttribute("aria-pressed"),"false");
  console.log("STEP",width,"reset");await action(page,"reset").click();await pose(page,"closed");const resetPixels=await canvas.screenshot({path:path.join(out,width+"-reset.png")});assert.equal(await pixelHash(page,resetPixels),await pixelHash(page,first),"reset restores exact product/camera pixels");
  for(const view of ["back","left","right","top","bottom","front"]){await page.locator('[data-view="'+view+'"]').click();await framed(page);await canvas.screenshot({path:path.join(out,width+"-"+view+".png")});}
  await canvas.focus();await page.keyboard.press("ArrowRight");assert.notDeepEqual(await canvas.screenshot(),first);
  await page.keyboard.press("Home");await canvas.evaluate(el=>el.blur());assert.equal(await pixelHash(page,await canvas.screenshot()),await pixelHash(page,first));
  await page.screenshot({path:path.join(out,width+"-page.png"),fullPage:true});await Promise.all(pending);assert.ok(consumed.length>=1);assert.ok(consumed.every(r=>r.sha256===expectedSha&&r.bytes===expectedBytes.length));assert.deepEqual(errors,[]);return {consumed,expectedSha};
 },{viewport:{width,height:width<=390?844:1000},hasTouch:width<=390});
 await run("orientation-resize",async(page,context,errors)=>{
  await page.goto(server.url+studio);await ready(page);
  for(const viewport of [{width:320,height:844},{width:844,height:390},{width:390,height:844}]){
   await page.setViewportSize(viewport);await action(page,"explode").click();await pose(page,"exploded");await noOverflow(page);await framed(page);
   await page.locator(".ps-stage canvas").screenshot({path:path.join(out,"orientation-"+viewport.width+"-exploded.png")});
   await action(page,"reset").click();await pose(page,"closed");
  }
  assert.deepEqual(errors,[]);
 },{viewport:{width:320,height:844},hasTouch:true});
 await run("rapid-switch-reset",async(page,context,errors)=>{
  await page.goto(server.url+studio);await ready(page);const c=page.locator(".ps-stage canvas"),first=await c.screenshot();
  for(let i=0;i<8;i++){await action(page,"open").click();await action(page,"explode").click();await action(page,"open").click();await action(page,"reset").click();}
  await pose(page,"closed");assert.equal(await pixelHash(page,await c.screenshot()),await pixelHash(page,first));assert.deepEqual(errors,[]);
 });
 await run("reduced-motion-keyboard",async(page,context,errors)=>{
  await page.goto(server.url+studio);await ready(page);
  await action(page,"open").focus();await page.keyboard.press("Enter");assert.equal(await page.locator(".ps-stage").getAttribute("data-pose"),"open");
  await action(page,"explode").focus();await page.keyboard.press("Space");assert.equal(await page.locator(".ps-stage").getAttribute("data-pose"),"exploded");
  await action(page,"reset").focus();await page.keyboard.press("Enter");await pose(page,"closed");assert.deepEqual(errors,[]);
 },{reducedMotion:"reduce"});
 await run("repeated-navigation-disposal",async(page,context,errors)=>{
  await page.goto(server.url+studio);await ready(page);
  for(let i=0;i<5;i++){
   await action(page,"explode").click();await pose(page,"exploded");
   await page.getByRole("link",{name:/Back to Interactive Demos/}).click();
   await page.getByRole("heading",{name:"Interactive Demos"}).waitFor();assert.equal(await page.locator("canvas").count(),0);
   const before=await page.evaluate(()=>qaDrawCalls);await page.waitForTimeout(180);assert.equal(await page.evaluate(()=>qaDrawCalls),before,"draw loop stops after leave");
   await page.locator('.demo-card[data-demo-id="product-studio"] .outline-button').click();await ready(page);
  }
  await page.reload({waitUntil:"domcontentloaded"});await ready(page);assert.deepEqual(errors,[]);
 });
 for(const fault of ["503","truncated"])await run("load-"+fault+"-retry",async(page)=>{
  let fail=false, intercepted=0;page.on("request",r=>{if(foodURL.test(r.url()))intercepted++;});
  await page.goto(server.url+studio);await ready(page);
  fail=true;server.setFault(({relative,bytes})=>foodURL.test("/"+relative)&&fail?(fault==="503"?{status:503}:{bytes:bytes.subarray(0,36)}):null);
  await page.reload();await page.getByRole("button",{name:"Retry experience"}).waitFor();
  assert.equal(await page.locator(".ps-stage").getAttribute("data-pose"),"error");assert.equal(await page.locator("canvas").count(),1);fail=false;await page.getByRole("button",{name:"Retry experience"}).click();await ready(page);assert.ok(intercepted>=3,"fault test intercepted actual asset URL");
 });
 await run("abort-delayed-load-newer-navigation",async(page,context,errors)=>{
  let release,arrived;const gate=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);
  await page.route("**/*.glb",async route=>{arrived();await gate;await route.continue().catch(()=>{});});
  await page.goto(server.url+studio,{waitUntil:"domcontentloaded"});await seen;
  await page.getByRole("link",{name:/Back to Interactive Demos/}).click();
  await page.getByRole("heading",{name:"Interactive Demos"}).waitFor();release();await page.waitForTimeout(300);
  assert.equal(await page.locator("canvas").count(),0);assert.equal(await page.locator("#product-studio-page").isHidden(),true);await page.unroute("**/*.glb");
  await page.locator('.demo-card[data-demo-id="product-studio"] .outline-button').click();await ready(page);
  assert.deepEqual(errors,[]);
 });
 await run("context-loss-during-load",async(page)=>{
  let release,arrived;const gate=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);
  await page.route("**/*.glb",async route=>{arrived();await gate;await route.continue().catch(()=>{});});
  await page.goto(server.url+studio,{waitUntil:"domcontentloaded"});await seen;
  await page.locator('.ps-stage canvas').evaluate(c=>c.dispatchEvent(new Event('webglcontextlost',{cancelable:true})));
  await page.getByRole('button',{name:'Retry experience'}).waitFor();
  assert.equal(await page.locator('canvas').count(),0);
  release();await page.unroute('**/*.glb');await page.getByRole('button',{name:'Retry experience'}).click();await ready(page);
 });
 await run("no-webgl-recovery",async(page,context)=>{
  await context.addInitScript(()=>{const f=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,...a){return /webgl/.test(t)?null:f.call(this,t,...a);};});
  await page.goto(server.url+studio);await page.getByRole("button",{name:"Retry experience"}).waitFor();assert.equal(await page.locator("canvas").count(),0);
  await page.getByRole("link",{name:/Back to Interactive Demos/}).click();await page.getByRole("heading",{name:"Interactive Demos"}).waitFor();
 });
 await run("context-loss-disposal",async(page)=>{
  await page.goto(server.url+studio);await ready(page);
  await page.locator(".ps-stage canvas").evaluate(c=>c.dispatchEvent(new Event("webglcontextlost",{cancelable:true})));
  await page.locator('.ps-loading').filter({hasText:'3D view interrupted'}).waitFor();assert.equal(await page.locator('.product-studio button:enabled:not([data-retry])').count(),0);assert.equal(await page.getByRole('button',{name:'Retry experience'}).isEnabled(),true);assert.equal(await page.locator("canvas").count(),0);
  const before=await page.evaluate(()=>qaDrawCalls);await page.waitForTimeout(200);assert.equal(await page.evaluate(()=>qaDrawCalls),before);
 });
 await run('delayedA-fastB-and-A-B-A-newest-wins',async page=>{
  let releaseA,arrivedA,hitsA=0;const gateA=new Promise(r=>releaseA=r),seenA=new Promise(r=>arrivedA=r);
  await page.route(foodURL,async route=>{hitsA++;const response=await route.fetch();arrivedA();await gateA;await route.fulfill({response}).catch(()=>{});});
  await page.goto(server.url+studio,{waitUntil:'domcontentloaded'});await seenA;
  await page.getByRole('button',{name:'Demo Beverage Can',exact:true}).click();await ready(page,'demo-beverage-can');releaseA();await page.waitForTimeout(150);await ready(page,'demo-beverage-can');assert.equal(hitsA,1);await page.unroute(foodURL);
  await page.getByRole('button',{name:'Demo Food Tin',exact:true}).click();await ready(page);
  let releaseB,arrivedB,hitsB=0;const gateB=new Promise(r=>releaseB=r),seenB=new Promise(r=>arrivedB=r);
  await page.route(beverageURL,async route=>{hitsB++;const response=await route.fetch();arrivedB();await gateB;await route.fulfill({response}).catch(()=>{});});
  await page.getByRole('button',{name:'Demo Beverage Can',exact:true}).click();await seenB;
  await page.getByRole('button',{name:'Demo Food Tin',exact:true}).click();await ready(page);releaseB();await page.waitForTimeout(150);await ready(page);assert.equal(hitsB,1);
 });
 await run('late-error-no-overwrite-and-switch-while-animating',async page=>{
  await page.goto(server.url+studio);await ready(page);await action(page,'open').click();await pose(page,'moving');
  await page.getByRole('button',{name:'Demo Beverage Can',exact:true}).click();await ready(page,'demo-beverage-can');assert.equal(await action(page,'open').getAttribute('aria-pressed'),'false');
  let release,arrived,hits=0;const gate=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);
  await page.route(foodURL,async route=>{hits++;arrived();await gate;await route.fulfill({status:503,body:'late A'}).catch(()=>{});});
  await page.getByRole('button',{name:'Demo Food Tin',exact:true}).click();await seen;
  await page.getByRole('button',{name:'Demo Beverage Can',exact:true}).click();await ready(page,'demo-beverage-can');release();await page.waitForTimeout(150);await ready(page,'demo-beverage-can');assert.equal(await page.locator('[data-retry]').count(),0);assert.equal(hits,1);
 });
 await run('twenty-switch-five-route-cycles-resource-stability',async page=>{
  let requests=0;page.on('request',r=>{if(foodURL.test(r.url())||beverageURL.test(r.url()))requests++;});
  await page.goto(server.url+studio);await ready(page);
  const choose=async id=>{await page.locator(`[data-product="${id}"]`).click();await ready(page,id);await page.locator('.ps-stage canvas').screenshot();};
  await choose('demo-beverage-can');await choose('demo-food-tin');await choose('demo-beverage-can');
  const baseline=await page.evaluate(()=>qaGpu()),startRequests=requests;
  for(let i=0;i<20;i++)await choose(i%2?'demo-beverage-can':'demo-food-tin');
  assert.equal(requests-startRequests,20,'one actual GLB request per changed selection');assert.deepEqual(await page.evaluate(()=>qaGpu()),baseline,'live WebGL resources return to same warmed model baseline');
  const sameRequests=requests;await page.locator('[data-product="demo-beverage-can"]').click();await page.waitForTimeout(100);assert.equal(requests,sameRequests,'same selection does not reload');
  for(let i=0;i<5;i++){await page.getByRole('link',{name:/Back to Interactive Demos/}).click();await page.getByRole('heading',{name:'Interactive Demos'}).waitFor();assert.equal(await page.locator('canvas').count(),0);const draws=await page.evaluate(()=>qaDrawCalls);await page.waitForTimeout(120);assert.equal(await page.evaluate(()=>qaDrawCalls),draws);await page.locator('.demo-card[data-demo-id="product-studio"] .outline-button').click();await ready(page);}
 });
 for(const fault of ['503','truncated'])await run('switch-current-'+fault+'-retry',async page=>{
  await page.goto(server.url+studio);await ready(page);let hits=0,fail=true;
  await page.route(beverageURL,async route=>{hits++;if(fail){if(fault==='503')await route.fulfill({status:503,body:'failure'});else await route.fulfill({body:beverageBytes.subarray(0,36),contentType:'model/gltf-binary'});}else await route.continue();});
  await page.locator('[data-product="demo-beverage-can"]').click();const retry=page.getByRole('button',{name:'Retry experience'});await retry.waitFor();assert.equal(await retry.isVisible(),true);assert.equal(await page.locator('.ps-stage').getAttribute('data-pose'),'error');assert.equal(await page.locator('.ps-loading').isVisible(),true);fail=false;await retry.click();await ready(page,'demo-beverage-can');assert.equal(hits,2);assert.equal(await page.locator('.ps-loading').isVisible(),false);
 });
 await run('stale-real-glb-parse-disposes-image',async(page,context)=>{
  await context.addInitScript(()=>{window.qaDelayBitmapNext=true;});
  await page.goto(server.url+studio,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>qaBitmapHeld===1);
  const closed=await page.evaluate(()=>qaBitmapClosed);
  await page.locator('[data-product="demo-beverage-can"]').click();await ready(page,'demo-beverage-can');
  await page.evaluate(()=>qaReleaseBitmaps());await page.waitForFunction(n=>qaBitmapClosed>n,closed);await ready(page,'demo-beverage-can');assert.equal(await page.locator('canvas').count(),1);
 });
 await run('beverage-touch-labels-reset-motion-change-history',async(page,context,errors)=>{
  const consumed=[];page.on('response',r=>{if(beverageURL.test(r.url())&&r.ok())consumed.push(r.body().then(b=>hash(b)));});
  await page.goto(server.url+studio);await ready(page);await page.locator('[data-product="demo-beverage-can"]').tap();await ready(page,'demo-beverage-can');
  assert.equal(await action(page,'open').innerText(),'Lift tab');await noOverflow(page);await framed(page);
  const canvas=page.locator('.ps-stage canvas'),initial=await canvas.screenshot({path:path.join(out,'beverage-touch-closed.png')});
  await action(page,'open').tap();await pose(page,'moving');await page.emulateMedia({reducedMotion:'reduce'});await pose(page,'open');assert.equal(await action(page,'open').innerText(),'Reset tab');await framed(page);
  await action(page,'explode').tap();await pose(page,'exploded');await framed(page);await canvas.screenshot({path:path.join(out,'beverage-touch-exploded.png')});
  for(const view of ['top','bottom','left','back','front']){await page.locator(`[data-view="${view}"]`).tap();await framed(page);}
  await action(page,'reset').tap();await ready(page,'demo-beverage-can');assert.equal(await pixelHash(page,await canvas.screenshot()),await pixelHash(page,initial));
  await canvas.focus();await page.keyboard.press('ArrowRight');assert.notEqual(await pixelHash(page,await canvas.screenshot()),await pixelHash(page,initial));await page.keyboard.press('Home');await canvas.evaluate(c=>c.blur());assert.equal(await pixelHash(page,await canvas.screenshot()),await pixelHash(page,initial));
  await page.getByRole('link',{name:/Back to Interactive Demos/}).click();await page.getByRole('heading',{name:'Interactive Demos'}).waitFor();await page.goBack();await ready(page);await page.goForward();await page.getByRole('heading',{name:'Interactive Demos'}).waitFor();assert.equal(await page.locator('canvas').count(),0);
  const hashes=await Promise.all(consumed);assert.ok(hashes.length);assert.ok(hashes.every(h=>h===beverageSha),'actual beverage GLB bytes match authored export');assert.deepEqual(errors,[]);
 },{viewport:{width:390,height:844},hasTouch:true});
} finally {await browser.close();await server.close();}
if(results.some(r=>r.status!=="PASS"))process.exitCode=1;
