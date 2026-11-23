import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { chromium } from 'playwright';
import { captureCanvas, launchOptions, recordConsumedGlbHashes, waitForRenderedFrames } from './browser-test-utils.mjs';
import { escalatorTerminalPaths } from '../mall-modules-preview/escalator-terminal.js';

const url = new URL('mall-modules-preview/?view=escalator-terminals', process.env.MALL_PREVIEW_SITE || 'http://127.0.0.1:5173/');
const output = process.env.MALL_PREVIEW_OUTPUT;
if (output) await mkdir(output, {recursive:true});
const avatar = 'models/gjh-mall-visitor/exports/gjh-mall-visitor.glb';
const digest = async path => createHash('sha256').update(await readFile(path)).digest('hex');
const staticHashes = await Promise.all(Object.values(escalatorTerminalPaths).map(digest));
const avatarHash = await digest(avatar);
const end = 17.8;
const browser = await chromium.launch(launchOptions);

async function checkViewport(width, height, reduced) {
  const context = await browser.newContext({
    viewport:{width,height}, hasTouch:reduced, isMobile:reduced,
    deviceScaleFactor:1, reducedMotion:reduced?'reduce':'no-preference',
  });
  // The request pending during reset/navigation resolves to the original bytes.
  const pending = Promise.withResolvers();
  const release = Promise.withResolvers();
  const trace = stage => console.log(width + 'px ' + stage);
  let requests = 0;
  try {
    await context.addInitScript(recordConsumedGlbHashes);
    await context.route('**/' + avatar, async route => {
      requests++;
      if (reduced && requests === 1) {
        await route.fulfill({status:503,contentType:'text/plain',body:'Injected passenger loading failure'});
        return;
      }
      if (requests === (reduced ? 2 : 1)) {
        pending.resolve();
        await release.promise;
      }
      await route.continue();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(45000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const ready = view => page.locator('#canvas-wrap[data-view="'+view+'"] #canvas-status[data-state="ready"]').waitFor({state:'attached'});
    const panel = page.locator('#ride-controls');
    const start = page.locator('#ride-start');
    const travelUp = page.getByRole('button', { name: 'Travel up', exact: true });
    const travelDown = page.getByRole('button', { name: 'Travel down', exact: true });
    const toggle = page.locator('#ride-toggle');
    const time = page.locator('#ride-time');
    const message = page.locator('#ride-message');
    const canvas = page.locator('#canvas-wrap canvas');
    const reset = page.getByRole('button',{name:'Reset camera view'});
    const switchView = async view => {
      await page.locator('#grid-layout').selectOption(view);
      await ready(view);
    };
    const waitForHash = hash => page.waitForFunction(expected => window.consumedModelHashes.includes(expected),hash);
    const waitForLabel = label => page.getByRole('button',{name:label,exact:true}).waitFor();
    const frames = () => waitForRenderedFrames(page);
    const position = async () => Number(await time.inputValue());
    const visibleImage = name => captureCanvas(page, canvas, output && join(output, width + '-' + name + '.png'));
    await page.goto(url.href,{waitUntil:'domcontentloaded'});
    await ready('escalator-terminals');
    trace('real terminal assembly loaded');
    await Promise.all(staticHashes.map(waitForHash));
    assert.equal(requests,0,'terminal overview loads without the visitor');
    assert.equal(await page.evaluate(hash=>window.consumedModelHashes.includes(hash),avatarHash),false);
    assert.equal(await start.textContent(),'Ride a step');
    assert.ok(await travelUp.isEnabled() && await travelDown.isEnabled());
    const targets = await page.locator('#terminal-tools > .walk-buttons button').evaluateAll(buttons =>
      buttons.map(button => {
        const rect = button.getBoundingClientRect();
        return rect.height >= 44 && rect.left >= 0 && rect.right <= document.documentElement.clientWidth;
      }));
    assert.ok(targets.every(Boolean), 'all five actions fit the viewport and retain touch-sized targets');
    assert.equal(await panel.isHidden(),true);
    assert.equal(await message.innerText(),'');
    const live = await message.evaluate(el=>el.getAttribute('aria-live') || (el.getAttribute('role')==='status'?'polite':null));
    assert.equal(live,'polite');
    await page.evaluate(()=>document.fonts.ready);
    const overview = await visibleImage('overview');
    trace('native machine ready, passenger still lazy');

    if (reduced) {
      await travelDown.tap();
      await page.waitForFunction(()=>document.getElementById('ride-message').textContent.includes('Select Travel down to retry.'));
      assert.ok(await travelDown.isEnabled());
      assert.equal(await panel.isHidden(),true);
      assert.ok(await start.isEnabled());
      assert.equal(await start.innerText(),'Ride a step');
    }
    const pendingStart = reduced ? travelDown : travelUp;
    await pendingStart.focus();
    const requested = page.waitForRequest(req => new URL(req.url()).pathname.endsWith('/'+avatar));
    await pendingStart.press('Enter');
    await requested;
    await pending.promise;
    trace('avatar request held for cancellation');
    assert.equal(await page.locator('#terminal-tools button[aria-controls="ride-controls"]:disabled').count(),3,
      'loading one action disables all three passenger starts');
    assert.equal(await message.textContent(),'','normal pending download leaves the live error region empty');
    if (reduced) await switchView('floor-transition');
    else await reset.click();
    assert.equal(await panel.isHidden(),true);
    release.resolve();
    await waitForHash(avatarHash);
    await frames();
    assert.equal(await panel.isHidden(),true,'late GLB response cannot reopen a cancelled ride');
    assert.equal(await message.textContent(),'');
    if (reduced) {
      assert.equal(await start.isVisible(),false);
      await switchView('escalator-terminals');
    }
    assert.equal(await start.innerText(),'Ride a step');
    assert.ok(await start.isEnabled());
    assert.ok((await visibleImage('cancelled')).equals(overview),'cancelled request leaves native machine overview');
    trace('cancelled request restored native state');
    await start.click();
    await panel.waitFor();
    assert.equal(await start.isHidden(),true);
    assert.equal(Number(await time.getAttribute('min')),0);
    assert.equal(Number(await time.getAttribute('max')),end);
    assert.equal(await message.textContent(),'');
    if (reduced) {
      await waitForLabel('Play ride');
      await frames();
      assert.equal(await position(),0,'reduced motion starts at rest');
      await toggle.tap();
    } else {
      await waitForLabel('Pause ride');
    }
    await page.waitForFunction(()=>document.getElementById('ride-time').valueAsNumber >= .1);
    await toggle.click();
    await waitForLabel('Play ride');
    const paused = await position();
    await frames();
    assert.equal(await position(),paused,'pause holds the scrubber and model clock');
    await time.focus();
    await time.press('Home');
    await time.press('ArrowRight');
    assert.ok((await position())>0 && (await position())<.5,'range responds to keyboard');
    if (output) await visibleImage('lower-ride');
    const track = await time.boundingBox();
    await time.click({position:{x:track.width*.5,y:track.height*.5}});
    const middle = await position();
    assert.ok(middle>7 && middle<11,'pointer seeks into the travelled interval');
    await waitForLabel('Play ride');
    assert.ok(!(await visibleImage('midride')).equals(overview),'midride rendering differs from initial native overview');

    trace('pause, keyboard and seek verified');
    await time.press('End');
    await waitForLabel('Replay ride');
    assert.equal(await position(),end);
    await time.press('ArrowLeft');
    assert.ok((await position())<end);
    await toggle.click();
    await waitForLabel('Replay ride');
    assert.equal(await position(),end,'playback settles at the true endpoint');
    if (output) await visibleImage('upper-ride');
    await toggle.click();
    await waitForLabel('Pause ride');
    assert.ok((await position())<end/2,'replay restarts at the lower end');

    const upper = page.getByRole('button',{name:'Inspect upper terminal'});
    await upper.click();
    await panel.waitFor({state:'hidden'});
    assert.equal(await upper.getAttribute('aria-pressed'),'true');
    assert.equal(await start.isEnabled(),true);
    await reset.click();
    assert.ok((await visibleImage('native-reset')).equals(overview),'reset restores native pose and removes passenger');
    await start.click();
    await panel.waitFor();
    await switchView('floor-transition');
    assert.equal(await panel.isHidden(),true);
    assert.equal(await start.isVisible(),false);
    await switchView('escalator-terminals');
    assert.equal(await panel.isHidden(),true);
    assert.equal(await start.innerText(),'Ride a step');
    assert.equal(await message.textContent(),'');
    assert.ok((await visibleImage('returned')).equals(overview),'leaving an active ride restores native overview on return');
    const phase = page.locator('#ride-phase');
    let lowerFloorAtStart;
    for (const journey of [
      { button: travelUp, from: 'lower', to: 'upper', board: 3.73, alight: 21.80, prefix: '' },
      { button: travelDown, from: 'upper', to: 'lower', board: 4.28, alight: 22.34, prefix: 'down-' },
    ]) {
      if (reduced) await journey.button.tap();
      else await journey.button.press('Enter');
      await panel.waitFor();
      await waitForLabel(reduced ? 'Play journey' : 'Pause journey');
      assert.ok(await toggle.evaluate(el => el === document.activeElement), 'keyboard focus moves to playback');
      if (!reduced) await toggle.click();
      assert.equal(await time.getAttribute('max'), '26.24');
      assert.equal(Number(await time.getAttribute('step')), .01);
      await time.press('Home');
      assert.equal(await phase.innerText(), 'Walking from the ' + journey.from + ' floor to the escalator');
      const atStart = await visibleImage(journey.prefix + 'start-floor');
      if (journey.from === 'lower') lowerFloorAtStart = atStart;
      else assert.ok(!atStart.equals(lowerFloorAtStart), 'the downward route starts at a different rendered floor');

      const track = await time.boundingBox();
      for (const [seconds, text, image] of [
        [journey.board, 'Stepping from the ' + journey.from + ' landing onto the moving tread', 'boarding'],
        [12, 'Riding the tread to the ' + journey.to + ' floor', 'between-floors'],
        [journey.alight, 'Stepping onto the ' + journey.to + ' landing', 'alighting'],
        [24.5, 'Walking across the ' + journey.to + ' floor joint', journey.to + '-floor'],
      ]) {
        const x = 8 + seconds / 26.24 * (track.width - 16);
        await time.click({ position: { x, y: track.height / 2 } });
        const ticks = Math.round((seconds - await position()) * 100);
        for (let tick = 0; tick < Math.abs(ticks); tick++) await time.press(ticks > 0 ? 'ArrowRight' : 'ArrowLeft');
        assert.equal(await position(), seconds, 'the slider reaches the selected transfer to the hundredth');
        assert.equal(await phase.innerText(), text);
        if (output) await visibleImage(journey.prefix + image);
      }
      await time.press('End');
      await waitForLabel('Replay journey');
      assert.equal(await phase.innerText(), 'Arrived on the ' + journey.to + ' floor');
      await toggle.click();
      await waitForLabel('Pause journey');
      assert.ok(await position() < 13, 'replay starts a new trip');
      await reset.click();
      assert.equal(await panel.isHidden(), true);
      assert.ok(await travelUp.isEnabled() && await travelDown.isEnabled() && await start.isEnabled());
      assert.ok((await visibleImage(journey.prefix + 'journey-reset')).equals(overview), 'reset restores the native escalator');
    }
    if (!reduced) {
      // Navigating a real document out of the foreground delivers Chromium's
      // trusted hidden event even in headless builds which keep both tabs visible.
      // Observe the application's state after its registered visibility listener.
      await start.click();
      await waitForLabel('Pause ride');
      await page.evaluate(() => document.addEventListener('visibilitychange', event => {
        if (document.hidden) sessionStorage.setItem('ride-background-check',JSON.stringify({
          trusted:event.isTrusted, state:document.visibilityState, label:document.getElementById('ride-toggle').textContent,
        }));
      }));
      const checkpoint = new URL('passenger-visibility-check',url).href;
      await page.route(checkpoint,route => route.fulfill({contentType:'text/html',body:'<title>Background check</title>'}));
      await page.goto(checkpoint,{waitUntil:'domcontentloaded'});
      assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('ride-background-check'))),
        {trusted:true,state:'hidden',label:'Play ride'},'browser hidden event pauses the active ride before unloading');
    }
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({width,height,reducedMotion:reduced,avatarRequests:requests,consumedStaticGlbs:staticHashes.length,avatarHash,
      pausedSeconds:paused,seekSeconds:middle,endSeconds:end,journeys:['up','down'],background:reduced?'desktop coverage':'native hidden event',result:'passed'}));
  } finally {
    release.resolve();
    await context.close();
  }
}

try {
  await checkViewport(1440,900,false);
  await checkViewport(390,844,true);
} finally {
  await browser.close();
}
