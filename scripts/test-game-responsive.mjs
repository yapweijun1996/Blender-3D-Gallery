import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { serveBuild, launchOptions, gameReady, readGame } from "./browser-test-utils.mjs";
import { TABLE, POCKETS } from "../src/game/table.js";
const server = process.env.B3G_GAME_TEST_URL
  ? { url: process.env.B3G_GAME_TEST_URL, close: async () => {} }
  : await serveBuild();
const browser = await chromium.launch(launchOptions);
const artifacts = process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-game-responsive";
await fs.mkdir(artifacts, { recursive: true });
const insets = { top:24, right:18, bottom:28, left:14 }, results = [], fontChecks = [], errors = [];
const sizes = [[320,568],[360,640],[360,651],[360,800],[390,844],[430,932],[568,320],[640,360],[844,390],[768,1024],[1024,768],[1440,900]];
const requested = process.env.B3G_GAME_VIEWPORT;
const selected = requested ? sizes.filter(([width,height]) => `${width}x${height}` === requested) : sizes;
assert.ok(selected.length, `Unknown viewport: ${requested}`);
async function reveal(page, phase) {
  await page.evaluate(({ phase, insets }) => {
    window.scrollTo({ top:0, behavior:"instant" });
    const selectors = ["#game-viewport", ".game-table-caption", "#game-pause", phase === "placing" ? '[data-action="place"]' : '#power-handle'];
    const bottom = Math.max(...selectors.map((selector) => document.querySelector(selector).getBoundingClientRect().bottom));
    window.scrollBy({ top:Math.max(0, bottom-innerHeight+insets.bottom+4), behavior:"instant" });
  }, { phase, insets });
}
async function snapshot(page, phase) {
  // Phase changes alter the layout before ResizeObserver updates the renderer.
  // Measure projection only once its backing canvas uses the current bounds.
  await page.waitForFunction(() => {
    const viewport = document.querySelector("#game-viewport");
    const canvas = viewport?.querySelector("canvas");
    // Every context in this viewport matrix uses deviceScaleFactor: 1.
    return canvas && canvas.width === viewport.clientWidth &&
      canvas.height === viewport.clientHeight;
  });
  return page.evaluate((phase) => {
    const rect = (selector) => {
      const r = document.querySelector(selector).getBoundingClientRect();
      return { x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom };
    };
    return { scrollY, scrollWidth:document.documentElement.scrollWidth,
      cameraSpan: JSON.parse(window.render_game_to_text()).cameraSpan,
      canvas:rect("#game-viewport"), caption:rect(".game-table-caption"),
      action:rect(phase === "placing" ? '[data-action="place"]' : '#power-handle'),
      pause:rect("#game-pause"), inspect:rect('[data-action="inspect"]'), options:rect('[data-action="options"]'),
      status:rect("#game-status"), input1:rect(phase === "placing" ? "#place-x" : "#aim-angle"),
      input2:rect(phase === "placing" ? "#place-z" : "#power-handle"),
      fineLeft:phase === "aiming" ? rect('[data-action="aim-left"]') : null,
      fineRight:phase === "aiming" ? rect('[data-action="aim-right"]') : null,
      pointerCoarse:matchMedia("(pointer: coarse)").matches,
      displayMode:matchMedia("(display-mode: standalone)").matches ? "standalone" : "browser" };
  }, phase);
}
function inside(rect, width, height) {
  return rect.x >= insets.left-1 && rect.right <= width-insets.right+1 &&
    rect.y >= insets.top-1 && rect.bottom <= height-insets.bottom+1;
}
function verifyLayout(data, width, height, phase) {
  assert.ok(data.scrollWidth <= width, `${width}x${height} ${phase}: horizontal overflow`);
  assert.ok(data.scrollY <= height/2, `${width}x${height} ${phase}: excessive scrolling ${data.scrollY}`);
  for (const key of ["canvas","caption","action","pause","inspect","options","status","input1","input2"])
    assert.ok(inside(data[key],width,height),`${width}x${height} ${phase} ${key}: ${JSON.stringify(data[key])}`);
  for (const key of ["action","pause","inspect","options"])
    assert.ok(data[key].width >= 44 && data[key].height >= 44, `${width}x${height} ${phase} ${key}: touch target`);
  if (phase === "aiming") {
    for (const key of ["fineLeft","fineRight"]) {
      assert.ok(inside(data[key],width,height), `${width}x${height} ${key}: outside safe viewport`);
      assert.ok(data[key].width >= 44 && data[key].height >= 44, `${width}x${height} ${key}: touch target`);
    }
  }
  if (width <= 900 || height <= 500 || data.pointerCoarse)
    assert.ok(data.input1.height >= 44 && data.input2.height >= 44, `${width}x${height} ${phase}: range touch targets`);
  if (width === 320 && height === 568) assert.ok(data.canvas.height >= 190, "small portrait table must remain playable");
  if (width === 844 && height === 390) assert.ok(data.canvas.height >= 180, "short landscape table must remain playable with insets");
  // Read the actual orthographic camera projection rather than assume a
  // fixed envelope after responsive framing changes. Preserve cabinet fit
  // and the existing minimum projected ball diameter independently.
  const span = data.cameraSpan;
  assert.ok(span && Number.isFinite(span.width) && Number.isFinite(span.height));
  const portrait = data.canvas.width < data.canvas.height;
  assert.ok(span.width >= (portrait ? 1.4 : 2.54), "full cabinet width stays in frame");
  assert.ok(span.height >= (portrait ? 2.54 : 1.4), "full cabinet height stays in frame");
  for (const pocket of POCKETS) {
    const horizontal = portrait ? pocket.z : pocket.x;
    const vertical = portrait ? pocket.x : pocket.z;
    assert.ok(Math.abs(horizontal) + TABLE.pocketRadius < span.width / 2, `pocket ${pocket.id} horizontally clipped`);
    assert.ok(Math.abs(vertical) + TABLE.pocketRadius < span.height / 2, `pocket ${pocket.id} vertically clipped`);
  }
  const scale = Math.min(data.canvas.width / span.width, data.canvas.height / span.height);
  const projectedBall = 2 * TABLE.radius * scale;
  if (width <= 900) assert.ok(projectedBall >= 4.9, `${width}x${height} ${phase}: projected ball ${projectedBall}px`);
  return projectedBall;
}
try {
  for (const [width,height] of selected) {
    const context = await browser.newContext({ viewport:{width,height}, deviceScaleFactor:1, hasTouch:true, isMobile:width < 1024, serviceWorkers:"block" });
    const page = await context.newPage(), pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => { if (message.type() === "error") pageErrors.push(message.text()); });
    try {
      await gameReady(page, server.url);
      await page.evaluate((insets) => {
        for (const [edge,value] of Object.entries(insets)) document.documentElement.style.setProperty(`--safe-${edge}`, `${value}px`);
      }, insets);
      assert.equal(await page.locator('#demo-breadcrumb a[data-page="demos"]').isVisible(), true);
      await page.locator('[data-action="new"]').first().tap();
      await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'placing');
      for (const phase of ["placing", "aiming"]) {
        if (phase === "aiming") {
          await page.locator('[data-action="place"]').tap();
          await page.waitForFunction(() => !document.querySelector('#power-handle').disabled);
        }
        await reveal(page, phase);
        const data = await snapshot(page, phase), projectedBall = verifyLayout(data,width,height,phase);
        if (width <= 650 && height <= 500) {
          for (const family of ["Arial, sans-serif", "Verdana, sans-serif", "system-ui, sans-serif"]) {
            await page.locator(".game-controls").evaluate((controls, family) => {
              for (const element of [controls, ...controls.querySelectorAll("button, input")])
                element.style.fontFamily = family;
            }, family);
            await reveal(page, phase);
            const fontLayout = await snapshot(page, phase);
            let fontBall;
            try {
              fontBall = verifyLayout(fontLayout, width, height, phase);
            } catch (error) {
              error.message = `${family}: ${error.message}`;
              throw error;
            }
            fontChecks.push({ width, height, phase, family, projectedBall: fontBall, ...fontLayout });
            await page.screenshot({ path: path.join(artifacts, `${width}x${height}-${phase}-${family.split(",")[0]}.png`) });
          }
          await page.locator(".game-controls").evaluate((controls) => {
            for (const element of [controls, ...controls.querySelectorAll("button, input")])
              element.style.fontFamily = "";
          });
          await reveal(page, phase);
        }
        const status = await page.locator('#game-status').evaluate((el) => ({ font: parseFloat(getComputedStyle(el).fontSize), scroll: el.scrollHeight, client: el.clientHeight }));
        assert.ok(status.font >= 12, `${width}x${height}: status text is too small`);
        assert.ok(status.scroll <= status.client + 1, `${width}x${height}: status is clipped`);
        await page.screenshot({ path:path.join(artifacts,`${width}x${height}-${phase}.png`) });
        results.push({ width,height,phase,projectedBall, ...data });
        if (phase === "placing") {
          const input = page.locator('#place-x');
          await page.locator('[data-action="pause"]').tap();
          await page.waitForFunction(()=>JSON.parse(window.render_game_to_text()).phase==='paused');
          await page.locator('[data-action="continue"]').tap();
          assert.equal((await readGame(page)).phase,'placing','placement pause resumes placement');
          const before = await input.inputValue(), r = await input.boundingBox();
          await page.touchscreen.tap(r.x + r.width * 0.1, r.y + r.height / 2);
          assert.notEqual(await input.inputValue(), before, `${width}x${height}: touch placement did not change`);
          assert.equal(await page.locator('[data-action="place"]').isEnabled(), true);
        } else {
          const before = await readGame(page), r = await page.locator('#game-viewport').boundingBox();
          await page.locator('[data-action="aim-right"]').tap();
          const adjusted = await readGame(page);
          const delta = Math.atan2(Math.sin(adjusted.aim-before.aim), Math.cos(adjusted.aim-before.aim));
          assert.ok(Math.abs(delta-Math.PI/180) < 1e-6, `${width}x${height}: fine aim did not move one degree`);
          const aimTarget = {x:r.x + r.width * 0.78, y:r.y + r.height * 0.35};
          const aimStart = {x:r.x + r.width * 0.73, y:r.y + r.height * 0.40};
          await page.touchscreen.tap(aimTarget.x, aimTarget.y);
          assert.equal((await readGame(page)).aim, adjusted.aim, `${width}x${height}: a tap must not change aim`);
          assert.equal(await page.evaluate(({x,y}) => document.elementFromPoint(x,y)?.tagName, aimStart), 'CANVAS', `${width}x${height}: drag must start on the canvas`);
          const cdp = await context.newCDPSession(page);
          await cdp.send('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[{...aimStart,id:1}]});
          await cdp.send('Input.dispatchTouchEvent', {type:'touchMove',touchPoints:[{...aimTarget,id:1}]});
          await cdp.send('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
          await cdp.detach();
          assert.notEqual((await readGame(page)).aim, adjusted.aim, `${width}x${height}: touch aiming did not change`);
          // This is a touch journey: do not mix a synthetic mouse pull with touch taps.
          const handle=page.locator('#power-handle');await handle.scrollIntoViewIfNeeded();
          const hb=await handle.boundingBox(),travel=await page.locator('#power-track').evaluate(t=>t.clientHeight-document.querySelector('#power-handle').offsetHeight);
          const touch=await context.newCDPSession(page),tx=hb.x+hb.width/2,ty=hb.y+hb.height/2;
          await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:tx,y:ty,id:1}]});
          for(let step=1;step<=5;step++)await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:tx,y:ty+travel*.45*step/5,id:1}]});
          await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await touch.detach();
          await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'moving');
          const shot = await readGame(page);
          await page.waitForFunction((cue) => {
            const state = JSON.parse(window.render_game_to_text()), next=state.balls[0];
            if(state.phase==='moving' && Math.hypot(next.x-cue.x,next.z-cue.z)>0.002) {
              // Existing deterministic QA clock prevents a real-time settle during the subsequent tap.
              window.advanceTime(0);window.qaMotionClock=setInterval(()=>window.advanceTime(0),50);return true;
            }
            return false;
          }, shot.balls[0], { timeout:10000 });
          // Capture event-time phases: a low-power shot may settle before the tap arrives.
          // Continue must restore the phase actually paused, not an earlier polled phase.
          await page.evaluate(() => {
            window.qaEvents=[];for(const type of ['touchstart','touchend','pointerdown','pointerup','click'])document.addEventListener(type,e=>window.qaEvents.push([type,e.target.tagName,e.target.dataset?.action]),{capture:true});
            document.addEventListener('click', e => {
              if(e.target.closest('[data-action="pause"]')) window.qaPausedFrom=JSON.parse(window.render_game_to_text()).phase;
            },{capture:true});
            document.addEventListener('click', e => {
              if(e.target.closest('[data-action="continue"]')) window.qaResumedTo=JSON.parse(window.render_game_to_text()).phase;
            });
          });
          await page.waitForTimeout(500);
          await page.locator('[data-action="pause"]').tap();
          await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'paused');
          const pausedBalls=(await readGame(page)).balls;
          await page.waitForTimeout(180);
          assert.deepEqual((await readGame(page)).balls,pausedBalls,'paused physics must remain frozen');
          await page.locator('[data-action="continue"]').tap();
          const phases=await page.evaluate(()=>({from:window.qaPausedFrom,to:window.qaResumedTo}));
          assert.equal(phases.from,'moving','pause is exercised during verified real ball motion');
          assert.equal(phases.to,phases.from,'Continue restores the exact event-time paused phase');
          await page.evaluate(() => {clearInterval(window.qaMotionClock);window.advanceTime(26000);});
          await page.waitForFunction(() => !['moving','adjudicating'].includes(JSON.parse(window.render_game_to_text()).phase), null, { timeout:30000 });
          await page.locator('#demo-breadcrumb a[data-page="demos"]').tap();
          await page.waitForFunction(() => !document.querySelector('#demos-page').hidden);
          assert.equal(await page.locator('#game-page canvas').count(), 0);
        }
      }
      assert.deepEqual(pageErrors, [], `${width}x${height}: page errors`);
      console.log(`PASS responsive touch journey ${width}x${height}`);
    } catch (error) {
      console.log('DIAGNOSTIC',JSON.stringify(await page.evaluate(()=>({state:JSON.parse(window.render_game_to_text()),from:window.qaPausedFrom,to:window.qaResumedTo,menu:document.querySelector('#game-menu')?.open,focus:document.activeElement?.tagName,events:window.qaEvents,clock:window.qaMotionClock})).catch(()=>({}))));
      errors.push(`${width}x${height}: ${error.message}`);
      await page.screenshot({ path:path.join(artifacts,`failure-${width}x${height}.png`) }).catch(() => {});
      throw error;
    } finally { await context.close(); }
  }
} finally {
  await fs.writeFile(path.join(artifacts,'results.json'), JSON.stringify({ results,fontChecks,errors,insets,scope:'Headless Chromium viewport and CSS safe-area simulation. Real installed mode, iOS and Android devices are unverified.' },null,2));
  await browser.close();
  await server.close();
}
