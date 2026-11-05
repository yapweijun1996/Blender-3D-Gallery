import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const artifacts = process.env.TEST_ARTIFACT_DIR || '/tmp/blender-gallery-library-qa';
await fs.mkdir(artifacts, { recursive: true });
const results = [];
const errors = [];
const viewports = [[320,720], [390,844], [430,932], [768,1024], [1024,768], [1440,900], [1920,1080]];
async function run(name, test, options = {}) {
  const context = await browser.newContext({ viewport: {width:1440,height:900}, serviceWorkers:'block', ...options });
  await context.addInitScript(()=>{
    window.qaDrawCalls=0;
    for(const type of [WebGLRenderingContext,WebGL2RenderingContext])for(const name of ['drawArrays','drawElements','drawArraysInstanced','drawElementsInstanced']){
      const original=type.prototype[name];
      if(original)type.prototype[name]=function(...args){window.qaDrawCalls++;return original.apply(this,args);};
    }
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  try {
    await test(page, context);
    results.push({name, passed:true});
    console.log('PASS', name);
  } catch (error) {
    await page.screenshot({path:path.join(artifacts,'failure.png')}).catch(()=>{});
    throw error;
  } finally { await context.close(); }
}
async function noOverflow(page) {
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth > innerWidth), false, `document overflow at ${page.viewportSize().width}`);
}
async function viewerReady(page) {
  await page.waitForFunction(()=>document.querySelector('#viewport canvas') && document.querySelector('#viewer-status')?.textContent === '' && window.qaDrawCalls > (window.qaReadyDraws ?? 0), null, {timeout:60000});
  await page.evaluate(()=>window.qaReadyDraws=window.qaDrawCalls);
}
async function demoReady(page, kind) {
  if (kind === 'game') await page.waitForFunction(()=>window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready,null,{timeout:60000});
  else await page.waitForFunction(()=>document.querySelector('#solar-status')?.textContent === '',null,{timeout:60000});
}
try {
  await run('static indexes preserve all assets and never download GLBs or create WebGL', async page => {
    const glbs = [];
    const failures = [];
    page.on('request', r => { if(new URL(r.url()).pathname.endsWith('.glb')) glbs.push(r.url()); });
    page.on('response', r => { if(r.status()>=400) failures.push(`${r.status()} ${r.url()}`); });
    page.on('console', m => { if(m.type()==='error') failures.push(m.text()); });
    for(const [width,height] of viewports) {
      await page.setViewportSize({width,height});
      await page.goto(server.url);
      assert.equal(await page.locator('#catalog .asset-card').count(),39);
      await noOverflow(page);
      await page.screenshot({path:path.join(artifacts,`models-${width}.png`)});
      await page.goto(server.url+'?page=demos');
      await page.getByRole('heading',{name:/^Interactive Demos/}).waitFor();
      assert.equal(await page.locator('.demo-card').count(),2);
      assert.equal(await page.locator('canvas').count(),0);
      await noOverflow(page);
      await page.screenshot({path:path.join(artifacts,`demos-${width}.png`)});
    }
    assert.deepEqual(glbs,[]);
    assert.deepEqual(failures,[]);
  });
  await run('model search, combined filters, empty state and clear preserve URL state', async page => {
    await page.goto(server.url);
    await page.locator('#model-search').fill('  eArTh  ');
    assert.equal(await page.locator('#catalog .asset-card').count(),1);
    assert.match(await page.locator('#catalog').innerText(), /Earth/);
    await page.locator('#model-category').selectOption('Planets');
    await page.locator('#model-collection').selectOption('billiards');
    assert.equal(await page.locator('#catalog .asset-card').count(),0);
    await page.getByRole('button',{name:/clear filters/i}).first().click();
    await page.waitForFunction(()=>document.querySelectorAll('#catalog .asset-card').length===39);
    assert.equal(await page.locator('#catalog .asset-card').count(),39);
    await page.locator('#model-search').fill('  cue   stick ');
    assert.equal(await page.locator('#catalog .asset-card').count(),2);
    const searchUrl=page.url();
    await page.reload();
    assert.equal(await page.locator('#catalog .asset-card').count(),2);
    assert.equal(page.url(),searchUrl);
    await page.locator('[data-asset-id="cue-stick-01"]').first().click();
    await viewerReady(page);
    assert.equal(new URL(page.url()).searchParams.get('model'),'cue-stick-01');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#catalog .asset-card').count(),2);
    assert.equal(await page.locator('#viewer').evaluate(el=>el.open),false);
    assert.equal(await page.locator('#viewport canvas').count(),0);
    assert.equal(await page.locator('[data-asset-id="cue-stick-01"]').first().evaluate(el=>el===document.activeElement),true);
  });
  await run('demo search/category combine and clear', async page => {
    await page.goto(server.url+'?page=demos');
    await page.locator('#demo-search').fill('  sOlAr   sYstEm ');
    assert.equal(await page.locator('.demo-card').count(),1);
    await page.locator('#demo-category').selectOption('Game');
    assert.equal(await page.locator('.demo-card').count(),0);
    await page.getByRole('button',{name:/clear filters/i}).last().click();
    await page.waitForFunction(()=>document.querySelectorAll('.demo-card').length===2);
    assert.equal(await page.locator('.demo-card').count(),2);
    await page.locator('#demo-category').selectOption('Simulation');
    assert.equal(await page.locator('.demo-card').count(),1);
    await page.reload();
    assert.equal(await page.locator('.demo-card').count(),1);
  });
  await run('legacy model detail direct link, refresh, metadata, related and history', async page => {
    await page.goto(server.url+'?model=pool-table');
    await viewerReady(page);
    assert.match(await page.locator('#viewer-title').innerText(),/Pool Table/);
    assert.match(await page.locator('#viewer').innerText(),/triangles/i);
    assert.match(await page.locator('#viewer-download').getAttribute('href'),/\.glb$/);
    assert.equal(await page.locator('#viewer-download').getAttribute('download'),'pool-table.glb');
    await page.waitForTimeout(1200);
    const idleDraws=await page.evaluate(()=>window.qaDrawCalls);
    await page.waitForTimeout(250);
    assert.equal(await page.evaluate(()=>window.qaDrawCalls),idleDraws,'viewer stops drawing when idle');
    await page.locator('#reset-view').click();
    await page.waitForFunction(previous=>window.qaDrawCalls>previous,idleDraws);
    await page.reload();
    await viewerReady(page);
    await page.locator('#close-viewer').click();
    assert.equal(new URL(page.url()).searchParams.has('model'),false);
    await page.locator('[data-asset-id="cue-ball"]').first().click();
    await viewerReady(page);
    await page.goBack();
    await page.waitForFunction(()=>!document.querySelector('#viewer').open);
    await page.goForward();
    await viewerReady(page);
    assert.match(await page.locator('#viewer-title').innerText(),/Cue Ball/);
    const related=page.locator('#viewer-related a').first();
    assert.ok(await related.count(),'related model link exists');
    await related.click();
    await viewerReady(page);
    assert.notEqual(new URL(page.url()).searchParams.get('model'),'cue-ball');
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(()=>document.activeElement!==document.body && document.activeElement.isConnected),true,'closing related model restores a useful focus target');
  });
  await run('failed model load retains fallback and can retry', async page => {
    let fail=true;
    await page.route('**/*.glb',route=>fail?route.fulfill({status:503,body:'Unavailable'}):route.continue());
    await page.goto(server.url+'?model=pool-table');
    await page.getByRole('button',{name:/retry/i}).waitFor();
    assert.equal(await page.locator('#viewer').evaluate(el=>el.open),true);
    assert.equal(await page.locator('#viewport canvas').count(),0);
    fail=false;
    await page.getByRole('button',{name:/retry/i}).click();
    await viewerReady(page);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#viewport canvas').count(),0);
  });
  await run('unknown model and unavailable WebGL provide useful recovery', async (page, context) => {
    await page.goto(server.url+'?model=missing-model');
    assert.equal(await page.locator('#viewer').evaluate(el=>el.open),false);
    assert.match(await page.locator('#route-notice').innerText(),/not.*found|unknown|unavailable/i);
    await context.addInitScript(()=>{
      const original=HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/.test(type)?null:original.call(this,type,...args);};
    });
    await page.goto(server.url+'?model=pool-table');
    await page.getByRole('button',{name:/retry/i}).waitFor();
    assert.equal(await page.locator('#viewport canvas').count(),0);
    assert.equal(await page.locator('#viewer-poster').isVisible(),true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#viewer').evaluate(el=>el.open),false);
  });
  await run('mobile menu supports keyboard dismissal, focus return and navigation', async page => {
    await page.goto(server.url);
    const trigger=page.getByRole('button',{name:/open.*menu|menu/i}).first();
    await trigger.click();
    const menu=page.locator('#mobile-menu');
    await menu.waitFor({state:'visible'});
    await page.screenshot({path:path.join(artifacts,'mobile-menu-open.png')});
    assert.equal(await trigger.getAttribute('aria-expanded'),'true');
    assert.equal(await menu.evaluate(el=>el.contains(document.activeElement)),true);
    assert.equal(await page.evaluate(()=>getComputedStyle(document.body).overflow),'hidden');
    await page.keyboard.press('Escape');
    await page.waitForFunction(()=>document.querySelector('#menu-trigger').getAttribute('aria-expanded')==='false');
    assert.equal(await trigger.getAttribute('aria-expanded'),'false');
    assert.equal(await trigger.evaluate(el=>el===document.activeElement),true);
    await trigger.click();
    const rect=await menu.boundingBox();
    await page.mouse.click(2,Math.max(2,rect.y-2));
    await page.waitForFunction(()=>!document.querySelector('#mobile-menu').open);
    assert.equal(await trigger.evaluate(el=>el===document.activeElement),true);
    await trigger.click();
    await menu.getByRole('link',{name:/^Interactive Demos/}).click();
    await page.getByRole('heading',{name:/^Interactive Demos/}).waitFor();
    assert.equal(await menu.evaluate(el=>el.open),false);
    await page.waitForFunction(()=>getComputedStyle(document.body).overflow!=='hidden');
    assert.notEqual(await page.evaluate(()=>getComputedStyle(document.body).overflow),'hidden');
    await noOverflow(page);
  },{viewport:{width:390,height:844},hasTouch:true});
  await run('legacy demos launch, refresh, return to index and release canvas', async page => {
    for(const kind of ['game','solar']) {
      await page.goto(server.url+'?page='+kind);
      await demoReady(page,kind);
      assert.equal(await page.locator('canvas').count(),1);
      await page.reload();
      await demoReady(page,kind);
      await page.getByRole('link',{name:/back to.*demos/i}).click();
      await page.getByRole('heading',{name:/^Interactive Demos/}).waitFor();
      assert.equal(await page.locator('canvas').count(),0);
      const draws=await page.evaluate(()=>window.qaDrawCalls);
      await page.waitForTimeout(250);
      assert.equal(await page.evaluate(()=>window.qaDrawCalls),draws,'demo draw calls stop after leaving');
      await page.goBack();
      await demoReady(page,kind);
      assert.equal(await page.locator('canvas').count(),1);
    }
  });
  await run('reduced motion and equivalent 200 percent reflow remain usable',async page=>{
    await page.goto(server.url+'?page=demos');
    await noOverflow(page);
    assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior),'auto');
    await page.screenshot({path:path.join(artifacts,'reflow-200-percent-equivalent.png')});
  },{viewport:{width:512,height:768},reducedMotion:'reduce'});
  assert.deepEqual(errors,[],'uncaught page errors');
} finally {
  await fs.writeFile(path.join(artifacts,'results.json'),JSON.stringify({results,errors,environment:{browser:'Chromium',device:'macOS headless / SwiftShader',network:'localhost, unthrottled',cache:'fresh context, service worker blocked'},limits:['Viewport reflow is not real browser zoom','Physical mobile GPU, real installation and production Core Web Vitals not measured']},null,2));
  await browser.close();
  await server.close();
}
