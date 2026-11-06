import { pullShot, chargePull, releasePull, setPullRatio } from "./browser-test-utils.mjs";
import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';

const mode = process.argv[2] ?? 'baseline';
if (process.argv.length > 3 || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(mode)) {
  console.error('Usage: node scripts/audit-game-observations.mjs [mode]');
  console.error('Mode must be one directory name: 1–64 letters, digits, underscores or hyphens, starting with a letter or digit.');
  process.exit(2);
}
const parent = path.resolve(process.env.TEST_ARTIFACT_DIR || '/tmp/blender-gallery-game-audit');
const out = path.join(parent, mode);
try {
  await fs.mkdir(parent, { recursive: true });
  // No recursive flag: directory creation is exclusive even under concurrent runs.
  await fs.mkdir(out);
} catch (error) {
  console.error(error.code === 'EEXIST'
    ? `Output already exists: ${out}. Choose a new mode.`
    : `Cannot create output directory ${out}: ${error.message}`);
  process.exit(1);
}
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const report = { mode, browser: browser.version(), platform: process.platform, architecture: process.arch, launchOptions, viewports: [], faults: {}, performance: [] };
const read = page => page.evaluate(() => JSON.parse(window.render_game_to_text()));
const ready = async page => { await page.goto(server.url + '?page=game'); await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready, null, { timeout: 60000 }); await page.evaluate(() => document.fonts.ready); };
const phase = (page, value) => page.waitForFunction(value => JSON.parse(window.render_game_to_text()).phase === value, value);
const start = async page => { await page.locator('[data-action=new]:visible').click(); await phase(page, 'placing'); await page.locator('[data-action=place]').click(); await phase(page, 'aiming'); };
const errorsFor = page => { const errors = []; page.on('pageerror', e => errors.push('pageerror: ' + e.message)); page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); }); return errors; };
const screenshot = async (page, filename) => {
  const png = await page.screenshot({type:'png',fullPage:true});
  await fs.writeFile(path.join(out,filename),png,{flag:'wx'});
};
try {
  for (const [width, height] of [[360,800],[390,844],[768,1024],[1440,900]]) {
    const mobile = width < 600;
    const context = await browser.newContext({ viewport: {width,height}, isMobile:mobile, hasTouch:mobile, deviceScaleFactor:1 });
    const page = await context.newPage();
    const errors = errorsFor(page);
    await ready(page);
    await screenshot(page,`setup-${width}x${height}.png`);
    await start(page);
    await page.evaluate(() => scrollTo(0,0));
    await screenshot(page,`aiming-${width}x${height}.png`);
    const layout = await page.evaluate(() => {
      const rect = el => { const r=el.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom}; };
      const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length) && !el.closest('[hidden]');
      const buttons=[...document.querySelectorAll('.game-shell button')].filter(visible).map(el=>({text:el.innerText.trim(),disabled:el.disabled,...rect(el)}));
      return {innerWidth,innerHeight,scrollWidth:document.documentElement.scrollWidth,viewport:rect(document.querySelector('#game-viewport')),buttons};
    });
    const before=await read(page);
    const canvas=page.locator('#game-viewport canvas');
    const box=await canvas.boundingBox();
    if(mobile) await page.touchscreen.tap(box.x+box.width*0.75,box.y+box.height*0.65);
    else await page.mouse.click(box.x+box.width*0.75,box.y+box.height*0.65);
    const after=await read(page);
    await page.locator('[data-action=pause]').click();
    await screenshot(page,`paused-${width}x${height}.png`);
    const paused=await read(page);
    await page.locator('[data-action=continue]').click();
    await phase(page,'aiming');
    report.viewports.push({width,height,mobile,layout,pointerChangedAim:before.aim!==after.aim,pausePhase:paused.phase,resumed:(await read(page)).phase,errors});
    await context.close();
  }
  {
    const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();
    await ready(page); await start(page);
    await page.locator('#game-title').click();
    const before=await read(page);
    const active=await page.evaluate(() => document.activeElement.tagName);
    await page.keyboard.press('Space');
    await page.waitForTimeout(300);
    const after=await read(page);
    report.keyboardOutsideTable={activeElement:active,before:before.phase,after:after.phase};
    await context.close();
  }
  for(const fault of ['missing','invalid','webgl']) {
    const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
    const page=await context.newPage(); const errors=errorsFor(page);
    if(fault==='webgl') await page.addInitScript(() => { const original=HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext=function(type,...args){if(/^webgl2?$|^experimental-webgl$/.test(type)) return null; return original.call(this,type,...args);};});
    else await page.route('**/*.glb', route => fault==='missing' ? route.fulfill({status:404,body:'missing'}) : route.fulfill({status:200,contentType:'model/gltf-binary',body:'not a valid glb'}));
    await page.goto(server.url+'?page=game');
    await page.waitForFunction(() => document.querySelector('#game-loading')?.textContent.includes('could not load'), null, {timeout:60000});
    report.faults[fault]={loading:await page.locator('#game-loading').innerText(),saveStatus:await page.locator('#save-status').innerText(),visibleButtons:await page.locator('.game-shell button:visible').allTextContents(),errors};
    await screenshot(page,`fault-${fault}.png`);
    await context.close();
  }
  for (let sample=0;sample<3;sample++) {
    const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
    const page=await context.newPage();
    const startTime=Date.now(); await ready(page); const readyMs=Date.now()-startTime;
    await start(page);
    const gl=await page.evaluate(() => { const c=document.querySelector('canvas'); const gl=c.getContext('webgl2') || c.getContext('webgl'); const ext=gl?.getExtension('WEBGL_debug_renderer_info'); return {renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable',vendor:ext?gl.getParameter(ext.UNMASKED_VENDOR_WEBGL):'unavailable',canvas:[c.width,c.height],devicePixelRatio}; });
    await pullShot(page);
    const timing=await page.evaluate(() => new Promise(resolve => { let last, values=[], start=performance.now(); function tick(t){ if(last!==undefined)values.push(t-last); last=t; if(t-start < 5000) requestAnimationFrame(tick); else {values.sort((a,b)=>a-b); resolve({n:values.length,median:values[Math.floor(values.length*.5)],p95:values[Math.min(values.length-1,Math.floor(values.length*.95))],average:values.reduce((a,b)=>a+b,0)/values.length,phase:JSON.parse(window.render_game_to_text()).phase});}} requestAnimationFrame(tick); }));
    report.performance.push({sample:sample+1,readyMs,gl,timing});
    await context.close();
  }
  await fs.writeFile(path.join(out,'results.json'),JSON.stringify(report,null,2),{flag:'wx'});
  console.log(JSON.stringify(report,null,2));
} finally {await browser.close(); await server.close();}
