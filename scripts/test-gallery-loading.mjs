import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

const out = process.env.TEST_ARTIFACT_DIR || '/tmp/blender-gallery-loading-qa';
await fs.mkdir(out, { recursive:true });
const server = await serveBuild(process.env.TEST_BUILD_DIR || 'dist');
const browser = await chromium.launch(launchOptions), results = [];
const ready = page => page.waitForFunction(() => document.querySelector('#viewer')?.open && document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && !document.querySelector('#reset-view').disabled, null, {timeout:60000});
async function until(condition, label) {
  const deadline = Date.now() + 10000;
  while (!condition()) {assert.ok(Date.now() < deadline, label); await new Promise(r=>setTimeout(r,25));}
}
async function run(name, test) {
  const context = await browser.newContext({serviceWorkers:'block'}), page = await context.newPage();
  const failures = [], consoleErrors = [], pageErrors = [];
  const result = {name,passed:false,failures,consoleErrors,pageErrors};
  page.on('requestfailed',r=>failures.push({url:r.url(),error:r.failure()?.errorText}));
  page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});
  page.on('pageerror',e=>pageErrors.push(e.message));
  try {await test({context,page,failures,consoleErrors,result});assert.deepEqual(pageErrors,[]);result.passed=true;console.log('PASS',name);}
  catch(e) {result.failure=e.message;console.error('FAIL',name,e.message);await page.screenshot({path:path.join(out,name+'.png')}).catch(()=>{});}
  finally {results.push(result);await context.close();}
}
try {
  await run('cancel-partial-transfer-and-reopen', async ({context,page,failures,consoleErrors,result}) => {
    await page.goto(server.url+'?model=pool-table');await ready(page);
    await page.locator('#close-viewer').click();
    assert.deepEqual(failures,[]);assert.deepEqual(consoleErrors,[]);
    const cdp = await context.newCDPSession(page), requests = [], failed = [], finished = [], received = {};
    await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:100,downloadThroughput:50000,uploadThroughput:125000,connectionType:'cellular3g'});
    cdp.on('Network.requestWillBeSent',e=>{if(new URL(e.request.url).pathname.endsWith('.glb'))requests.push({id:e.requestId,url:e.request.url});});
    const known = id => requests.some(r=>r.id===id);
    cdp.on('Network.dataReceived',e=>{if(known(e.requestId))received[e.requestId]=(received[e.requestId]||0)+e.dataLength;});
    cdp.on('Network.loadingFailed',e=>{if(known(e.requestId))failed.push(e);});
    cdp.on('Network.loadingFinished',e=>{if(known(e.requestId))finished.push(e);});
    await page.locator('[data-asset-id="pool-table"]').first().click();
    await until(()=>requests.length===1 && received[requests[0].id]>0,'request starts receiving');
    const catalog = JSON.parse(await fs.readFile('models/catalog.json','utf8'));
    const asset = catalog.collections.flatMap(c=>c.assets).find(a=>a.id==='pool-table');
    const first = requests[0], expected = (await fs.stat(asset.file)).size;
    await page.locator('#close-viewer').click();
    await until(()=>failed.some(e=>e.requestId===first.id),'close cancels actual partial transfer');
    assert.equal(failed.length,1);assert.equal(failed[0].errorText,'net::ERR_ABORTED');assert.equal(failed[0].canceled,true);
    assert.ok(received[first.id]>0 && received[first.id]<expected,'canceled before full model, not after complete read');
    assert.deepEqual(failures,[{url:first.url,error:'net::ERR_ABORTED'}],'only the deliberately canceled request may fail');
    assert.equal(await page.locator('#viewport canvas').count(),0);assert.equal(await page.locator('#viewer').evaluate(e=>e.open),false);
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
    await page.locator('[data-asset-id="cue-ball"]').first().click();await ready(page);
    await until(()=>finished.length===1,'replacement finishes');
    assert.equal(await page.locator('#viewer-title').textContent(),'Cue Ball');
    assert.equal(await page.locator('#viewport canvas').count(),1);
    await page.waitForTimeout(250);
    assert.equal(requests.length,2);assert.equal(failed.length,1);assert.equal(failures.length,1);assert.deepEqual(consoleErrors,[]);
    result.network={requests,failed,finished,received,expectedBytes:expected};
  });
  for(const mode of ['http-503','truncated-glb','transport-abort']) await run(mode+'-retry',async ({page,failures,consoleErrors,result})=>{
    let inject = true, target;
    await page.route('**/*.glb',route=>{
      target=route.request().url();
      if(!inject)return route.continue();
      if(mode==='http-503')return route.fulfill({status:503,body:'Unavailable'});
      if(mode==='truncated-glb')return route.fulfill({status:200,body:Buffer.from('glTF'),contentType:'model/gltf-binary'});
      return route.abort('failed');
    });
    await page.goto(server.url+'?model=pool-table');
    await page.locator('#retry-view').waitFor({state:'visible'});
    assert.equal(await page.locator('#viewport canvas').count(),0);assert.equal(await page.locator('#viewer-poster').isVisible(),true);
    assert.match(await page.locator('#viewer-status').textContent(),/unavailable/);
    if(mode==='transport-abort')assert.deepEqual(failures,[{url:target,error:'net::ERR_FAILED'}]);else assert.deepEqual(failures,[]);
    if(mode==='http-503') {assert.equal(consoleErrors.length,1);assert.match(consoleErrors[0],/status of 503/);}
    else if(mode==='transport-abort')assert.deepEqual(consoleErrors,['Failed to load resource: net::ERR_FAILED']);
    else assert.deepEqual(consoleErrors,[]);
    result.injectedErrors={failures:[...failures],consoleErrors:[...consoleErrors]};
    const failureCount=failures.length, consoleCount=consoleErrors.length;
    inject=false;await page.locator('#retry-view').click();await ready(page);
    assert.equal(failures.length,failureCount,'retry adds no request failure');assert.equal(consoleErrors.length,consoleCount,'retry adds no console error');
    await page.locator('#close-viewer').click();assert.equal(await page.locator('#viewport canvas').count(),0);
  });
} finally {await browser.close();await server.close();await fs.writeFile(path.join(out,'results.json'),JSON.stringify({results},null,2)+'\n');}
if(results.some(r=>!r.passed))process.exitCode=1;
