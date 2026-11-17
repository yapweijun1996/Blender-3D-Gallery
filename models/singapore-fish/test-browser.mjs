import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {chromium} from 'playwright';
import {serveBuild,launchOptions,openModelFilters} from '../../scripts/browser-test-utils.mjs';
const collection=JSON.parse(await fs.readFile('models/catalog.json','utf8')).collections.find(c=>c.id==='singapore-fish');
const hash=b=>createHash('sha256').update(b).digest('hex');const builtHashes=new Set(await Promise.all((await fs.readdir('dist/assets')).filter(f=>f.endsWith('.glb')).map(async f=>hash(await fs.readFile('dist/assets/'+f)))));
for(const a of collection.assets)assert.ok(builtHashes.has(hash(await fs.readFile(a.file))),'Build must contain final GLBs');
const server=await serveBuild();const browser=await chromium.launch(launchOptions);const context=await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block'});const page=await context.newPage();const errors=[];const glbs=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().endsWith('.glb'))glbs.push(r.url())});page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
await page.addInitScript(()=>{window.fishDraws=0;for(const type of [WebGLRenderingContext,WebGL2RenderingContext])for(const name of ['drawElements','drawArrays']){const f=type.prototype[name];type.prototype[name]=function(...a){window.fishDraws++;return f.apply(this,a)}}});
try{
 await page.goto(server.url);
 await openModelFilters(page);
 await page.locator('#model-collection').selectOption('singapore-fish');
 assert.equal(await page.locator('#catalog .asset-card').count(),60);assert.equal(glbs.length,0);
 for(const width of [390,1440]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:`models/singapore-fish/library-${width}.png`});}
 await page.locator('#model-search').fill('金目鲈');assert.equal(await page.locator('#catalog .asset-card').count(),1);await page.locator('#model-search').fill('');
 for(const a of collection.assets){
  const before=await page.evaluate(()=>window.fishDraws);
  await page.locator(`a[data-asset-id="${a.id}"]`).first().click();
  await page.waitForFunction(n=>document.querySelector('#viewport canvas')&&document.querySelector('#viewer-status')?.textContent===''&&window.fishDraws>n,before,{timeout:30000});
  if(['fish-barramundi','fish-stingray','fish-reef-shark','fish-clownfish','fish-betta'].includes(a.id))await page.screenshot({path:`models/singapore-fish/${a.id}-browser.png`});
  console.log('RENDERED',a.id);
  await page.keyboard.press('Escape');assert.equal(await page.locator('#viewer').evaluate(e=>e.open),false);
 }
 assert.deepEqual(errors,[]);console.log('PASS: 60 model viewers rendered; 60 filtered cards, Chinese search, lazy loading, mobile/desktop overflow checks.');
}finally{await context.close();await browser.close();await server.close();}
