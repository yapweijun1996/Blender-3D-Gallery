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
    assert.equal(await panel.isHidden(),true);
    assert.equal(await message.innerText(),'');
    const live = await message.evaluate(el=>el.getAttribute('aria-live') || (el.getAttribute('role')==='status'?'polite':null));
    assert.equal(live,'polite');
    await page.evaluate(()=>document.fonts.ready);
    const overview = await visibleImage('overview');
    trace('native machine ready, passenger still lazy');

    if (reduced) {
      await start.tap();
      await page.waitForFunction(()=>/retry/i.test(document.getElementById('ride-message').textContent));
      assert.equal(await panel.isHidden(),true);
      assert.ok(await start.isEnabled());
      assert.equal(await start.innerText(),'Ride a step');
    }
    await start.focus();
    const requested = page.waitForRequest(req => new URL(req.url()).pathname.endsWith('/'+avatar));
    await start.press('Enter');
    await requested;
    await pending.promise;
    trace('avatar request held for cancellation');
    assert.ok(await start.isDisabled(),'duplicate activation blocked during pending load');
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
      pausedSeconds:paused,seekSeconds:middle,endSeconds:end,background:reduced?'desktop coverage':'native hidden event',result:'passed'}));
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
