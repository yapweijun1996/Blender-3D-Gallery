import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from 'playwright';
import { serveBuild, launchOptions, gameReady, readGame } from './browser-test-utils.mjs';
const server = await serveBuild(), browser = await chromium.launch(launchOptions);
const artifacts = process.env.TEST_ARTIFACT_DIR || '/tmp/blender-gallery-game-experience';
await fs.mkdir(artifacts, {recursive:true});
const errors = [], results = [];
try {
  for (const [width,height] of [[390,844],[617,827],[1440,900]]) {
    const context = await browser.newContext({viewport:{width,height},hasTouch:true,serviceWorkers:'block'});
    const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message));
    await gameReady(page,server.url);
    await page.screenshot({path:`${artifacts}/${width}-entry.png`});
    await page.locator('[data-action=new]').first().click();
    await page.waitForFunction(() => !document.querySelector('[data-action=place]').disabled);
    await page.locator('[data-action=place]').click();
    await page.waitForFunction(() => !document.querySelector('[data-action=shoot]').disabled);
    const before = await readGame(page);
    assert.equal(before.guide.kind,'ball'); assert.ok(before.guide.distance > 0.65);
    await page.evaluate(() => window.scrollTo(0,0));
    await page.screenshot({path:`${artifacts}/${width}-aiming-top.png`});
    await page.locator('[data-action=shoot]').scrollIntoViewIfNeeded();
    const rectangles = await page.evaluate(() => {
      const box = s => {const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom};};
      return {canvas:box('#game-viewport'), controls:box('.game-controls'), action:box('[data-action=shoot]'), overflow:document.documentElement.scrollWidth>innerWidth};
    });
    assert.equal(rectangles.overflow,false);
    const r = rectangles.canvas;
    assert.ok(Math.abs(r.width/r.height - (width===390 ? 1.62/2.82 : 2.82/1.62)) < 0.02);
    if(width===390) assert.ok(r.height >= 484-1,'phone table size preserves previous projected ball diameter');
    await page.screenshot({path:`${artifacts}/${width}-aiming.png`});
    // Hold a real IndexedDB completion to reproduce pause while shot startup is pending.
    await page.evaluate(() => {
      const descriptor = Object.getOwnPropertyDescriptor(IDBTransaction.prototype,'oncomplete');
      Object.defineProperty(IDBTransaction.prototype,'oncomplete',{...descriptor,set(callback) {
        descriptor.set.call(this,function(event) {
          if(window.delayStorage) {window.delayStorage=false; window.releaseStorage=()=>callback.call(this,event);}
          else callback.call(this,event);
        });
      }});
      window.delayStorage=true;
    });
    await page.locator('[data-action=shoot]').click();
    await page.waitForFunction(() => !!window.releaseStorage);
    await page.locator('[data-action=pause]').click();
    await page.evaluate(() => window.releaseStorage());
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase==='paused');
    assert.deepEqual((await readGame(page)).balls,before.balls,'pause before delivery cannot apply impulse');
    await page.locator('[data-action=continue]').click();
    // Freeze frame progression via the existing stepping hook, then inspect delivery.
    await page.evaluate(() => window.advanceTime(0));
    await page.locator('[data-action=shoot]').click();
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).delivery);
    assert.deepEqual((await readGame(page)).balls,before.balls,'delivery is presentation only');
    await page.locator('#game-viewport').focus();
    await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowUp');
    const locked=await readGame(page);
    assert.equal(locked.aim,before.aim); assert.equal(locked.power,before.power,'startup locks keyboard aim and power');
    await page.locator('[data-action=shoot]').evaluate(el=>el.click());
    await page.evaluate(() => window.advanceTime(150));
    await page.screenshot({path:`${artifacts}/${width}-delivery.png`});
    await page.evaluate(() => window.advanceTime(150));
    await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase==='moving');
    const moving = await readGame(page);
    assert.ok(Math.abs(Math.hypot(moving.balls[0].vx,moving.balls[0].vz)-(0.18+0.45*2.8))<1e-6,'exactly one unchanged impulse');
    const movingBox = await page.locator('.game-controls').boundingBox();
    assert.ok(Math.abs(movingBox.height-rectangles.controls.height)<1,'controls do not jump during motion');
    await page.evaluate(()=>window.advanceTime(26000));
    await page.waitForFunction(()=>!['moving','adjudicating'].includes(JSON.parse(window.render_game_to_text()).phase));
    assert.match((await readGame(page)).lastResult,/Player [12]/);
    await page.screenshot({path:`${artifacts}/${width}-result.png`});
    results.push({width,height,...rectangles});
    console.log(`PASS experience ${width}x${height}: framing, pending-pause, cue delivery, single impulse, stable HUD, factual result`);
    await context.close();
  }
  for (const reducedMotion of ['reduce','no-preference']) {
    const context=await browser.newContext({viewport:{width:617,height:827}, reducedMotion, serviceWorkers:'block'});
    const page=await context.newPage(); page.on('pageerror',e=>errors.push(e.message));
    await gameReady(page,server.url);
    await page.locator('[data-action=new]').first().click();
    await page.waitForFunction(()=>!document.querySelector('[data-action=place]').disabled);
    await page.locator('[data-action=place]').click();
    await page.waitForFunction(()=>!document.querySelector('[data-action=shoot]').disabled);
    const initial=await readGame(page);
    await page.evaluate(()=> {
      const descriptor=Object.getOwnPropertyDescriptor(IDBTransaction.prototype,'oncomplete');
      window.pendingCompletions=0;
      Object.defineProperty(IDBTransaction.prototype,'oncomplete',{...descriptor,set(callback){
        descriptor.set.call(this,function(event){
          if(++window.pendingCompletions===2) window.releaseCheckpoint=()=>callback.call(this,event);
          else callback.call(this,event);
        });
      }});
    });
    await page.locator('[data-action=shoot]').click();
    await page.waitForFunction(()=>!!window.releaseCheckpoint);
    await page.locator('[data-action=pause]').click();
    await page.evaluate(()=>window.releaseCheckpoint());
    await page.waitForFunction(()=>JSON.parse(window.render_game_to_text()).phase==='paused');
    assert.deepEqual((await readGame(page)).balls,initial.balls,'pause at delayed pending-checkpoint prevents impulse');
    await page.locator('[data-action=continue]').click();
    if(reducedMotion==='reduce') {
      await page.locator('[data-action=shoot]').click();
      await page.waitForFunction(()=>JSON.parse(window.render_game_to_text()).phase==='moving');
      assert.equal((await readGame(page)).delivery,false,'reduced motion skips cue travel');
    } else {
      await page.evaluate(()=>window.advanceTime(0));
      await page.locator('[data-action=shoot]').click();
      await page.waitForFunction(()=>JSON.parse(window.render_game_to_text()).delivery);
      await page.locator('[data-action=pause]').click();
      await page.waitForFunction(()=>JSON.parse(window.render_game_to_text()).phase==='paused');
      assert.deepEqual((await readGame(page)).balls,initial.balls,'pause during delivery prevents impulse');
      await page.locator('[data-action=continue]').click();
      await page.locator('[data-action=shoot]').click();
      await page.waitForFunction(()=>JSON.parse(window.render_game_to_text()).delivery);
      await page.locator('#demo-breadcrumb a[data-page=demos]').click();
      await page.waitForFunction(()=>!window.render_game_to_text);
      assert.equal(await page.locator('#game-page canvas').count(),0,'navigation cancels delivery and disposes renderer');
      await page.waitForTimeout(400);
    }
    console.log(`PASS ${reducedMotion}: delayed checkpoint pause, cancellation / immediate impulse`);
    await context.close();
  }
  assert.deepEqual(errors,[]);
} finally {await fs.writeFile(`${artifacts}/results.json`,JSON.stringify({results,errors},null,2)); await browser.close();await server.close();}
