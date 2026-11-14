// Additional negative/boundary coverage. Existing test-game-ux.mjs stays unchanged.
// CDP is used only to create gestures absent from Playwright's native tap API.
// All action buttons are activated through native Locator.tap()/keyboard input.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
import { serveBuild, launchOptions, gameReady, readGame } from './browser-test-utils.mjs';
const out = process.env.TEST_ARTIFACT_DIR || 'output/game-touch-cancellation';
await fs.mkdir(out, { recursive: true });
const server = await serveBuild(), browser = await chromium.launch(launchOptions), results = [];
const nextFrame = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
const digest = b => createHash('sha256').update(b).digest('hex');
async function stableCanvas(page, canvas, label) {
  let previous = null;
  for (let i=0;i<8;i++) { await nextFrame(page); const bytes = await canvas.screenshot(); const hash=digest(bytes); if(hash===previous) { await fs.writeFile(path.join(out,`${label}.png`),bytes); return hash; } previous=hash; }
  throw new Error('Canvas did not settle: '+label);
}
async function run(name, fn) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, serviceWorkers: 'block' });
  const page = await context.newPage(), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const result = { name, status: 'FAIL' };
  try { await gameReady(page, server.url); await fn(page, context); assert.deepEqual(errors, []); result.status = 'PASS'; console.log('PASS', name); }
  catch (error) { result.error = error.stack; console.error('FAIL', name, error.message); await page.screenshot({ path: path.join(out, `${name}-failure.png`), fullPage: true }).catch(() => {}); }
  finally { result.pageErrors = errors; results.push(result); await context.close(); await fs.writeFile(path.join(out, 'results.json'), JSON.stringify({ browser: browser.version(), scope: 'Desktop Chromium touch emulation, not physical-device verification', results }, null, 2)); }
}
async function startAiming(page) {
  await page.locator('[data-action="new"]').first().tap();
  await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'placing');
  await page.locator('[data-action="place"]').tap();
  await page.waitForFunction(() => !document.querySelector('#power-handle').disabled);
}
async function gesture(cdp, points, end = 'touchEnd') {
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: points[0] });
  for (const sample of points.slice(1)) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: sample });
  await cdp.send('Input.dispatchTouchEvent', { type: end, touchPoints: [] });
}
const point = (x, y, id = 1) => ({ x, y, id });
try {
  await run('cancel-charge-and-canvas-drag', async (page, context) => {
    await startAiming(page);
    const before = await readGame(page), cdp = await context.newCDPSession(page);
    const handle = page.locator('#power-handle'); await handle.scrollIntoViewIfNeeded();
    const b = await handle.boundingBox();
    const travel = await page.locator('#power-track').evaluate(el => el.clientHeight - document.querySelector('#power-handle').offsetHeight);
    await gesture(cdp, [[point(b.x+b.width/2,b.y+b.height/2)], [point(b.x+b.width/2,b.y+b.height/2+travel*.6)]], 'touchCancel');
    await nextFrame(page);
    assert.equal((await readGame(page)).phase, 'aiming');
    assert.equal((await readGame(page)).committedShots, before.committedShots, 'canceling charged pull never shoots');
    assert.equal(await handle.getAttribute('aria-valuenow'), '0', 'canceled charge resets power');
    const canvas = page.locator('#game-viewport canvas'); await canvas.scrollIntoViewIfNeeded(); const r = await canvas.boundingBox();
    await gesture(cdp, [[point(r.x+r.width*.45,r.y+r.height*.5)], [point(r.x+r.width*.6,r.y+r.height*.5)]], 'touchCancel');
    await nextFrame(page);
    assert.equal((await readGame(page)).committedShots, before.committedShots, 'canceling aim never shoots');
    assert.equal((await readGame(page)).phase, 'aiming');
    await cdp.detach();
    await page.locator('[data-action="pause"]').tap();
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'paused');
    await page.locator('[data-action="continue"]').tap();
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'aiming');
  });
  await run('inspection-pinch-and-orbit', async (page, context) => {
    await startAiming(page); const before = await readGame(page);
    await page.locator('[data-action="inspect"]').tap();
    const canvas = page.locator('#game-viewport canvas'); await canvas.scrollIntoViewIfNeeded(); await nextFrame(page);
    const initial = await stableCanvas(page,canvas,'inspection-initial'), beforeSpan=(await readGame(page)).cameraSpan, r = await canvas.boundingBox(), cx = r.x+r.width/2, cy = r.y+r.height/2;
    const cdp = await context.newCDPSession(page), pinch = [];
    for (let i=0;i<=6;i++) pinch.push([point(cx-30-i*4,cy,1),point(cx+30+i*4,cy,2)]);
    await gesture(cdp,pinch); await nextFrame(page);
    const pinched = await stableCanvas(page,canvas,'inspection-pinched'); assert.notDeepEqual((await readGame(page)).cameraSpan,beforeSpan,'inspection pinch changes actual camera span'); assert.notEqual(pinched,initial,'inspection two-finger pinch changes rendered camera view');
    const orbit = [];for(let i=0;i<=6;i++) orbit.push([point(cx-30+i*10,cy-10+i*4)]);
    await gesture(cdp,orbit); await nextFrame(page);
    assert.notEqual(await stableCanvas(page,canvas,'inspection-orbit'),pinched,'inspection one-finger orbit changes rendered camera view');
    assert.equal((await readGame(page)).committedShots,before.committedShots);
    await cdp.detach(); await page.locator('[data-action="inspect"]').tap();
    assert.equal((await readGame(page)).phase,'aiming');
  });
  await run('keyboard-and-native-button-once', async page => {
    await startAiming(page); const viewport=page.locator('#game-viewport'); await viewport.focus();
    const before=await readGame(page);await page.keyboard.press('ArrowLeft');
    assert.ok(Math.abs((await readGame(page)).aim-before.aim+2*Math.PI/180)<1e-7,'keyboard left remains exactly two degrees');
    await page.keyboard.press('ArrowRight');assert.ok(Math.abs((await readGame(page)).aim-before.aim)<1e-7);
    const left=page.locator('[data-action="aim-left"]'),right=page.locator('[data-action="aim-right"]');
    await left.tap();assert.ok(Math.abs((await readGame(page)).aim-before.aim+Math.PI/180)<1e-7,'native tap activates once, not twice');
    await right.tap();assert.ok(Math.abs((await readGame(page)).aim-before.aim)<1e-7);
    await left.focus();await page.keyboard.press('Enter');assert.ok(Math.abs((await readGame(page)).aim-before.aim+Math.PI/180)<1e-7,'native keyboard button activates once');
    assert.equal((await readGame(page)).committedShots,before.committedShots);
  });
  await run('noncanvas-scroll-and-prevention-scope', async (page,context) => {
    await page.setViewportSize({width:320,height:568});await startAiming(page);
    await page.evaluate(()=>{window.touchScope=[];document.addEventListener('touchstart',e=>window.touchScope.push({canvas:e.target.tagName==='CANVAS',prevented:e.defaultPrevented}),{passive:true});window.scrollTo({top:0,behavior:'instant'});});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollHeight>innerHeight),'fixture has scrollable page');
    const start=await page.evaluate(()=>scrollY),cdp=await context.newCDPSession(page);
    assert.notEqual(await page.evaluate(()=>document.elementFromPoint(innerWidth-3,innerHeight*.75)?.tagName),'CANVAS');
    const points=[];for(let i=0;i<=8;i++)points.push([point(317,426-i*15)]);
    await gesture(cdp,points);await page.waitForFunction(y=>scrollY>y+10,start);
    const observations=await page.evaluate(()=>window.touchScope);assert.ok(observations.some(e=>!e.canvas),'observed noncanvas real touch');assert.ok(observations.filter(e=>!e.canvas).every(e=>!e.prevented),'no global prevention of noncanvas touch');
    await cdp.detach();
  });
  await run('repeated-mount-disposes-canvas-listener', async page => {
    for(let cycle=0;cycle<3;cycle++) {
      await page.evaluate(()=>{window.oldGameViewport=document.querySelector('#game-viewport');window.oldGameCanvas=window.oldGameViewport.querySelector('canvas');});
      // This synthetic event checks only listener cleanup, never activates a UI control.
      assert.equal(await page.evaluate(()=>{const e=new Event('touchstart',{bubbles:true,cancelable:true});window.oldGameCanvas.dispatchEvent(e);return e.defaultPrevented;}),true,'current canvas listener is active');
      await page.locator('#demo-breadcrumb a[data-page="demos"]').click();
      await page.waitForFunction(()=>!document.querySelector('#demos-page').hidden);
      assert.equal(await page.evaluate(()=>{const v=window.oldGameViewport,c=window.oldGameCanvas;if(v.isConnected)throw new Error('old viewport still connected');v.append(c);const e=new Event('touchstart',{bubbles:true,cancelable:true});c.dispatchEvent(e);return e.defaultPrevented;}),false,'old detached viewport no longer handles canvas touch');
      await page.locator('.demo-card[data-demo-id="game"] a').first().click();
      await page.waitForFunction(()=>window.render_game_to_text&&JSON.parse(window.render_game_to_text()).ready);
    }
  });
} finally { await browser.close(); await server.close(); }
if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
