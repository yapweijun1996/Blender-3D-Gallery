// Source-gallery delivery checks; animation playback is tested by the consuming mall.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {serveBuild,launchOptions} from './browser-test-utils.mjs';
const id='gjh-mall-visitor';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const catalog=JSON.parse(await fs.readFile('models/catalog.json','utf8'));
const collection=catalog.collections.find(item=>item.id===id);
assert.equal(collection.assets.length,1);
const asset=collection.assets[0];assert.equal(asset.downloadable,false);
const source=await fs.readFile(asset.file),expected=hash(source);
// Vite emits imported models under assets with content-hashed filenames.
const builtNames=(await fs.readdir('dist/assets')).filter(name=>/^gjh-mall-visitor-[A-Za-z0-9_-]+\.glb$/.test(name));
assert.equal(builtNames.length,1,'one visitor export must be emitted by the production build');
assert.equal(hash(await fs.readFile(`dist/assets/${builtNames[0]}`)),expected,'built bytes match the registered export');
const metadata=JSON.parse(await fs.readFile(asset.metadata,'utf8'));
assert.equal(expected,metadata.metrics.sha256);
assert.deepEqual(metadata.metrics.clips.map(c=>c.name).sort(),['idle','sprint','walk']);
const out='/tmp/blender-gjh-visitor-qa';await fs.mkdir(out,{recursive:true});
const server=await serveBuild();let browser;
const results=[];
try{
 browser=await chromium.launch(launchOptions);
 for(const [width,height] of [[1440,900],[768,1024],[390,844]]){
  const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',serviceWorkers:'block'});
  const page=await context.newPage(),errors=[],responses=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);if(r.url().endsWith('.glb'))responses.push(r.body().then(bytes=>({url:r.url(),hash:hash(bytes)})));});
  try{
   await page.goto(server.url,{waitUntil:'networkidle'});
   await page.locator('#model-collection').selectOption(id);
   assert.equal(await page.locator('#catalog .asset-card').count(),1);
   assert.equal(await page.locator('#catalog .asset-download').count(),0);
   await page.locator('#catalog img').evaluate(img=>img.decode());
   assert.equal(responses.length,0,'discovery stays lightweight');
   await page.locator('#model-search').fill('mascot');
   assert.equal(await page.locator('#catalog .asset-card').count(),1);
   await page.goto(server.url+'?model='+id,{waitUntil:'networkidle'});
   await page.waitForFunction(()=>document.querySelector('#viewer')?.open&&document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status')?.textContent==='',null,{timeout:60000});
   assert.equal(await page.locator('#viewer-title').innerText(),asset.name);
   assert.equal(await page.locator('#viewer-download').isVisible(),false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const canvas=page.locator('#viewport canvas');await canvas.scrollIntoViewIfNeeded();await canvas.focus();
   const initial=hash(await canvas.screenshot({path:`${out}/front-${width}.png`}));
   await canvas.press('ArrowRight');await canvas.press('ArrowRight');
   // OrbitControls damping is asynchronous, so sample after the requested orbit settles.
   await page.waitForTimeout(500);
   assert.notEqual(hash(await canvas.screenshot({path:`${out}/orbit-${width}.png`})),initial);
   await page.locator('#reset-view').click();
   await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('#viewer').open);
   assert.equal(await page.locator('#viewport canvas').count(),0);
   const loaded=await Promise.all(responses);assert.ok(loaded.length);
   for(const item of loaded){assert.equal(item.url,new URL(`assets/${builtNames[0]}`,server.url).href,'viewer requests the production visitor URL');assert.equal(item.hash,expected);}
   assert.deepEqual(errors,[]);
   results.push({width,status:'PASS',glbSha256:expected,glbResponses:loaded.length});
   console.log('PASS visitor gallery',width);
  }finally{await context.close();}
 }
}finally{await browser?.close();await server.close();await fs.writeFile(`${out}/results.json`,JSON.stringify(results,null,2)+'\n');}
