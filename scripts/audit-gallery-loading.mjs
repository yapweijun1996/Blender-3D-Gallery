import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

// One fixed pass, with every request failure preserved. The original build is
// expected to fail; output directories are exclusive so its evidence survives.
const [build, out] = process.argv.slice(2);
assert.ok(build && out, 'Usage: node scripts/audit-gallery-loading.mjs <build> <new-output-dir>');
await fs.mkdir(out);
const catalog = JSON.parse(await fs.readFile(new URL('../models/catalog.json', import.meta.url), 'utf8'));
const assets = catalog.collections.flatMap(c => c.assets);
const ids = ['mall-glass-railing-1m', 'mall-glass-railing-2m', 'mall-waste-sorting-station', 'pool-table'];
const server = await serveBuild(build), browser = await chromium.launch(launchOptions), results = [];
try {
  for (const observed of [false, true]) for (const id of ids) {
    const asset = assets.find(a => a.id === id);
    const bytes = await fs.readFile(new URL('../' + asset.file, import.meta.url));
    const expected = { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
    const context = await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block'});
    const page = await context.newPage(), cdp = await context.newCDPSession(page);
    const requests = [], finished = [], failed = [], errors = [], responses = [], received = {};
    const result = {id,observed,expected,requests,finished,failed,errors,responses,received,passed:false};
    try {
      // Only the observed half wraps the byte-returning API. The unobserved half
      // uses CDP/Playwright alone, excluding observation as a necessary cause.
      if (observed) await page.addInitScript(() => {
        window.consumed = [];
        const original = Response.prototype.arrayBuffer;
        Response.prototype.arrayBuffer = async function(...args) {
          const bytes = await original.apply(this,args);
          if(bytes.byteLength >= 4 && new DataView(bytes).getUint32(0,true) === 0x46546c67) {
            const digest = await crypto.subtle.digest('SHA-256',bytes);
            window.consumed.push({bytes:bytes.byteLength,sha256:[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('')});
          }
          return bytes;
        };
      });
      page.on('requestfailed', r => errors.push({type:'requestfailed',url:r.url(),message:r.failure()?.errorText}));
      page.on('console', m => {if(m.type()==='error') errors.push({type:'console',message:m.text()});});
      page.on('pageerror', e => errors.push({type:'pageerror',message:e.message}));
      await cdp.send('Network.enable');
      await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
      await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:100,downloadThroughput:500000,uploadThroughput:125000,connectionType:'cellular4g'});
      cdp.on('Network.requestWillBeSent',e=>{if(new URL(e.request.url).pathname.endsWith('.glb'))requests.push({id:e.requestId,url:e.request.url,timestamp:e.timestamp});});
      const known = id => requests.some(r=>r.id===id);
      cdp.on('Network.responseReceived',e=>{if(known(e.requestId))responses.push({id:e.requestId,status:e.response.status,url:e.response.url});});
      cdp.on('Network.dataReceived',e=>{if(known(e.requestId))received[e.requestId]=(received[e.requestId]||0)+e.dataLength;});
      cdp.on('Network.loadingFinished',e=>{if(known(e.requestId))finished.push(e);});
      cdp.on('Network.loadingFailed',e=>{if(known(e.requestId))failed.push(e);});
      await page.goto(server.url+'?model='+id,{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>document.querySelector('#viewer')?.open && document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent==='' && !document.querySelector('#reset-view').disabled,null,{timeout:60000});
      await page.locator('#viewport canvas').screenshot({path:path.join(out,id+'-'+observed+'.png')});
      await page.waitForTimeout(250);
      result.viewerStillOpen = await page.locator('#viewer').evaluate(e=>e.open);
      if(observed) {result.consumed = await page.evaluate(()=>window.consumed); assert.deepEqual(result.consumed,[expected]);}
      assert.equal(requests.length,1,'exactly one model request, no duplicate');
      assert.equal(responses[0].status,200);
      assert.deepEqual(errors,[],'no ignored console/page/request failures');
      assert.deepEqual(failed,[],'no CDP loading failure before teardown');
      assert.equal(finished.length,1,'completed model request');
      result.passed=true;
    } catch(e) {result.failure=e.message;}
    finally {results.push(result);console.log(result.passed?'PASS':'FAIL',id,observed,result.failure||'');await context.close();}
  }
} finally {
  await browser.close();await server.close();
  await fs.writeFile(path.join(out,'results.json'),JSON.stringify({browser:browser.version(),build,environment:'Ubuntu headless Chromium / SwiftShader; 390x844 viewport, CDP 100 ms / 4 Mbps, no service worker/cache; not physical mobile',results},null,2)+'\n');
}
if(results.some(r=>!r.passed))process.exitCode=1;
