import { pullShot, chargePull, releasePull, setPullRatio } from "./browser-test-utils.mjs";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { serveBuild, launchOptions, gameReady, readGame, writeCheckpoint } from "./browser-test-utils.mjs";
import { makeRack, TABLE, groupOf } from "../src/game/table.js";
import { RULES_VERSION } from "../src/game/rules.js";

const artifactRoot = "/tmp/game-pr1-followup/mobile-a11y";
await fs.mkdir(artifactRoot, { recursive: true });
const artifacts = await fs.mkdtemp(path.join(artifactRoot, "run-"));
const server = await serveBuild();
const browser = await chromium.launch(launchOptions);
const browserVersion = browser.version();
const results = [];
const buildInfo = await fs.readFile("dist/build-info.json", "utf8");
const indexSha256 = crypto.createHash("sha256").update(await fs.readFile("dist/index.html")).digest("hex");

const waitPhase = (page, phase) => page.waitForFunction(
  phase => window.render_game_to_text && JSON.parse(window.render_game_to_text()).phase === phase,
  phase,
  { timeout: 20000 },
);
const waitReadyToShoot = page => page.waitForFunction(() => {
  const button = document.querySelector('#power-handle');
  return button && !button.disabled && button.getClientRects().length;
});
const tap = async (page, selector) => {
  const locator = page.locator(selector).first();
  await locator.waitFor({ state: "visible" });
  await locator.scrollIntoViewIfNeeded();
  assert.equal(await locator.isEnabled(), true, `${selector} must be enabled`);
  const rect = await locator.boundingBox();
  assert.ok(rect && rect.width && rect.height, `${selector} has no hit area`);
  await page.touchscreen.tap(rect.x + rect.width / 2, rect.y + rect.height / 2);
};
const start = async page => {
  await page.locator('[data-action="new"]').first().click();
  await waitPhase(page, "placing");
  await page.locator('[data-action="place"]').click();
  await waitPhase(page, "aiming");
  await waitReadyToShoot(page);
};
const run = async (name, options, check) => {
  const context = await browser.newContext(options);
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  const record = { name, passed: false, pageErrors: [], consoleErrors: [] };
  page.on("pageerror", error => record.pageErrors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error") record.consoleErrors.push(message.text());
  });
  try {
    await check(page, context, record);
    assert.deepEqual(record.pageErrors, [], "uncaught page errors");
    assert.deepEqual(record.consoleErrors, [], "unexpected console errors");
    record.passed = true;
    console.log("PASS", name);
  } catch (error) {
    record.error = error.message;
    record.failureScreenshot = path.join(artifacts, `${name.replace(/[^a-z0-9]+/gi, "-")}-failure.png`);
    await page.screenshot({ path: record.failureScreenshot, fullPage: true }).catch(() => {});
    console.error("FAIL", name, error.message);
  } finally {
    results.push(record);
    await context.close();
  }
};
const inspectLayout = page => page.evaluate(() => {
  const modal = [...document.querySelectorAll('dialog[open]')].at(-1);
  const visible = el => {
    const r = el.getBoundingClientRect(), style = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && !el.closest('[hidden]');
  };
  const rect = el => {
    const r = el.getBoundingClientRect(), range = document.createRange();
    range.selectNodeContents(el);
    const text = range.getBoundingClientRect();
    return {name:el.dataset.action || el.id || el.tagName, tag:el.tagName, id:el.id,
      type:el instanceof HTMLInputElement ? el.type : null,
      labelFor:el instanceof HTMLLabelElement ? el.htmlFor : null,
      labelControlId:el instanceof HTMLLabelElement ? el.control?.id || null : null,
      pointerEvents:getComputedStyle(el).pointerEvents,
      paddingTop:parseFloat(getComputedStyle(el).paddingTop) || 0,
      left:r.left, right:r.right, top:r.top, bottom:r.bottom,
      width:r.width, height:r.height, textTop:text.top, textBottom:text.bottom, textLeft:text.left, textRight:text.right,
      hasText:el.tagName === 'BUTTON' && !!el.textContent.trim()};
  };
  const scope = modal || document;
  const controls = [...scope.querySelectorAll(modal ? 'button, input, select' : '.game-shell button, .game-shell input, .header button')]
    .filter(visible).filter(el => modal || !el.closest('dialog')).map(rect);
  const messages = [...scope.querySelectorAll(modal ? 'h2, p' : '#game-status, #placement-hint, .control-note, #aim-contact, .game-controls label')]
    .filter(visible).filter(el => !!el.textContent.trim()).map(rect);
  const viewport = window.visualViewport;
  return {innerWidth, scrollWidth:document.documentElement.scrollWidth,
    visual:viewport ? {width:viewport.width, height:viewport.height, scale:viewport.scale, offsetLeft:viewport.offsetLeft} : null,
    controls, messages};
});
const assertLayout = layout => {
  const viewportLeft = layout.visual?.offsetLeft || 0;
  const viewportRight = viewportLeft + (layout.visual?.width || layout.innerWidth);
  assert.ok(layout.scrollWidth <= viewportRight + 1, `horizontal overflow: ${JSON.stringify(layout)}`);
  const overlap = (a, b) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
    Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
  const associatedRangeLabel = (control, message) => control.tag === 'INPUT' && control.type === 'range' &&
    ['aim-angle'].includes(control.id) && message.tag === 'LABEL' &&
    message.labelFor === control.id && message.labelControlId === control.id && message.pointerEvents === 'none' &&
    control.paddingTop >= 16 && message.textLeft >= control.left - 1 && message.textRight <= control.right + 1 &&
    message.textTop >= control.top - 1 && message.textBottom <= control.top + control.paddingTop + 3;
  for (const [index, item] of layout.controls.entries()) {
    assert.ok(item.width >= 44 && item.height >= 44, `small control: ${JSON.stringify(item)}`);
    assert.ok(item.left >= viewportLeft - 1 && item.right <= viewportRight + 1, `outside visual viewport: ${JSON.stringify(item)}`);
    if (item.hasText) assert.ok(item.textTop >= item.top - 1 && item.textBottom <= item.bottom + 1 &&
      item.textLeft >= item.left - 1 && item.textRight <= item.right + 1, `clipped control text: ${JSON.stringify(item)}`);
    for (const other of layout.controls.slice(index + 1))
      assert.ok(!overlap(item, other), `overlapping controls: ${JSON.stringify({item,other})}`);
    for (const message of layout.messages) {
      const text = {left:message.textLeft,right:message.textRight,top:message.textTop,bottom:message.textBottom};
      assert.ok(!overlap(item, text) || associatedRangeLabel(item, message),
        `control overlaps text: ${JSON.stringify({item,message})}`);
    }
  }
};
const assertHit = async (page, selector) => {
  const locator = page.locator(selector).first();
  await locator.scrollIntoViewIfNeeded();
  assert.equal(await locator.evaluate(el => {
    const r = el.getBoundingClientRect(), hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return hit === el || el.contains(hit);
  }), true, `${selector} center must receive the pointer`);
};
const touchRange = async (page, id) => {
  const locator = page.locator(`#${id}`);
  await locator.scrollIntoViewIfNeeded();
  const result = await locator.evaluate(el => {
    const label = el.labels?.[0], r = el.getBoundingClientRect();
    const textRange = document.createRange();
    if (label) textRange.selectNodeContents(label);
    const text = label ? textRange.getBoundingClientRect() : null;
    const hit = (x, y) => document.elementFromPoint(x, y)?.id || null;
    const paddingTop = parseFloat(getComputedStyle(el).paddingTop) || 0;
    const x = r.left + r.width * .8, y = r.top + paddingTop + (r.height - paddingTop) / 2;
    const labelOverlaps = text && Math.min(r.right, text.right) - Math.max(r.left, text.left) > 1 &&
      Math.min(r.bottom, text.bottom) - Math.max(r.top, text.top) > 1;
    return {id:el.id, type:el.type, valueBefore:el.value, labelFor:label?.htmlFor || null,
      labelControlId:label?.control?.id || null, labelPointerEvents:label ? getComputedStyle(label).pointerEvents : null,
      paddingTop, labelOverlaps:!!labelOverlaps, trackPoint:{x,y,hit:hit(x,y)},
      labelHit:labelOverlaps ? hit((text.left + text.right) / 2, (text.top + text.bottom) / 2) : null};
  });
  assert.equal(result.type, 'range');
  assert.equal(result.labelFor, id);
  assert.equal(result.labelControlId, id);
  assert.equal(result.trackPoint.hit, id, `${id} track must receive the pointer`);
  if (result.labelOverlaps) {
    assert.equal(result.labelPointerEvents, 'none');
    assert.equal(result.labelHit, id, `${id} label must not intercept the pointer`);
  }
  await page.touchscreen.tap(result.trackPoint.x, result.trackPoint.y);
  result.valueAfter = await locator.inputValue();
  assert.notEqual(result.valueAfter, result.valueBefore, `${id} touch must change the value`);
  return result;
};

try {
  for (const [width,height] of [[195,422],[195,800],[260,422],[261,422],[320,450],[320,568],[360,800],[390,844],[768,1024],[1440,900],[844,390],[568,320]]) {
    await run(`narrow action layout ${width}x${height}`, {
      viewport:{width,height}, hasTouch:true, isMobile:width < 1024, deviceScaleFactor:1,
    }, async (page, context, record) => {
      record.stages = [];
      const checkStage = async phase => {
        await page.evaluate(() => scrollTo({top:0, behavior:'instant'}));
        const layout = await inspectLayout(page);
        record.stages.push({phase,layout});
        await page.screenshot({path:path.join(artifacts, `actions-${width}x${height}-${phase}.png`), fullPage:true});
        assertLayout(layout);
      };
      await gameReady(page, server.url);
      await checkStage('setup');
      for (const selector of ['[data-action="new"]','[data-action="options"]','[data-action="rules"]']) await assertHit(page, selector);
      await tap(page, '[data-action="new"]');
      await waitPhase(page, 'placing');
      await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'placing');
      await checkStage('placing');
      for (const selector of ['[data-action="place"]','[data-action="pause"]']) await assertHit(page, selector);
      await tap(page, '[data-action="place"]');
      await waitPhase(page, 'aiming');
      await waitReadyToShoot(page);
      await checkStage('aiming');
      for (const selector of ['[data-action="aim-left"]','[data-action="aim-right"]','#power-handle','[data-action="pause"]']) await assertHit(page, selector);
      record.ranges = [];
      for (const id of ['aim-angle']) record.ranges.push(await touchRange(page, id));
      await tap(page, '[data-action="pause"]');
      await waitPhase(page, 'paused');
      await checkStage('paused');
      for (const selector of ['[data-action="continue"]','[data-action="restart"]','[data-action="leave"]']) await assertHit(page, selector);
      await tap(page, '[data-action="continue"]');
      await waitPhase(page, 'aiming');
      if (width === 320 && height === 450) {
        await pullShot(page);
        await waitPhase(page, 'moving');
        await tap(page, '[data-action="pause"]');
        await waitPhase(page, 'paused');
        await tap(page, '[data-action="continue"]');
        await waitPhase(page, 'moving');
        await page.evaluate(() => window.advanceTime(26000));
        await page.waitForFunction(() => !['moving','adjudicating'].includes(JSON.parse(window.render_game_to_text()).phase));
        assert.notEqual((await readGame(page)).phase, 'recovery');
      }
      record.outcome = 'setup, placement, aiming and pause checked after scrolling as needed';
    });
  }
  await run('narrow recovery actions remain usable', {
    viewport:{width:195,height:422}, hasTouch:true, isMobile:true, deviceScaleFactor:1,
  }, async (page, context, record) => {
    await page.route('**/*.glb', route => route.fulfill({status:200,contentType:'model/gltf-binary',body:'invalid glb'}));
    await page.goto(server.url + '?page=game');
    await page.waitForSelector('#game-load-error:visible');
    record.layout = await inspectLayout(page);
    await page.screenshot({path:path.join(artifacts,'actions-195x422-recovery.png'),fullPage:true});
    assertLayout(record.layout);
    for (const selector of ['[data-action="retry-load"]','[data-action="back-to-gallery"]']) await assertHit(page, selector);
    await page.unroute('**/*.glb');
    await tap(page, '[data-action="retry-load"]');
    await page.waitForFunction(() => window.render_game_to_text && JSON.parse(window.render_game_to_text()).ready, null, {timeout:60000});
    assert.equal(await page.locator('[data-action="new"]').first().isEnabled(), true);
  });
  for (const [width, height] of [[320,450], [195,422]]) {
    await run(`narrow viewport reflow ${width}x${height}`, {
      viewport: {width, height}, hasTouch: true, isMobile: true, deviceScaleFactor: 1,
    }, async (page, context, record) => {
      await gameReady(page, server.url);
      await start(page);
      await page.evaluate(() => scrollTo(0, 0));
      record.requestedViewport = {width, height};
      record.layout = await page.evaluate(() => {
        const rect = el => {
          const r = el.getBoundingClientRect();
          const text = document.createRange();
          text.selectNodeContents(el);
          const t = text.getBoundingClientRect();
          return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width, height:r.height,
            textTop:t.top, textBottom:t.bottom};
        };
        const selectors = ['.header', '#game-title', '.players', '#game-viewport', '.control-note', '#power-handle', '[data-action="pause"]'];
        return {width:innerWidth, height:innerHeight, scrollWidth:document.documentElement.scrollWidth,
          visualViewport:visualViewport ? {width:visualViewport.width, height:visualViewport.height, scale:visualViewport.scale} : null,
          elements:Object.fromEntries(selectors.map(selector => [selector, rect(document.querySelector(selector))]))};
      });
      record.screenshot = path.join(artifacts, `reflow-${width}x${height}.png`);
      await page.screenshot({path:record.screenshot, fullPage:true});
      assert.equal(record.layout.scrollWidth, record.layout.width, `document horizontal overflow: ${JSON.stringify(record.layout)}`);
      for (const selector of ['#power-handle', '[data-action="pause"]']) {
        const r = record.layout.elements[selector];
        assert.ok(r.left >= 0 && r.right <= record.layout.width && r.width >= 44 && r.height >= 44,
          `clipped or undersized ${selector}: ${JSON.stringify(r)}`);
        assert.ok(r.textTop >= r.top - 1 && r.textBottom <= r.bottom + 1,
          `button label extends outside ${selector}: ${JSON.stringify(r)}`);
      }
    });
  }

  for (const [width, height, dpr] of [[360,800,2], [390,844,3], [768,1024,2]]) {
    await run(`touch journey ${width}x${height}`, {
      viewport: {width, height}, hasTouch:true, isMobile:true, deviceScaleFactor:dpr,
    }, async (page, context, record) => {
      await gameReady(page, server.url);
      await tap(page, '[data-action="new"]');
      await waitPhase(page, "placing");
      await tap(page, '[data-action="place"]');
      await waitPhase(page, "aiming");
      await waitReadyToShoot(page);
      const before = await readGame(page);
      const canvas = page.locator('#game-viewport canvas');
      await canvas.scrollIntoViewIfNeeded();
      const rect = await canvas.boundingBox();
      assert.ok(rect);
      await page.touchscreen.tap(rect.x + rect.width * 0.74, rect.y + rect.height * 0.62);
      assert.notEqual((await readGame(page)).aim, before.aim, "touch changes aim");
      await page.evaluate(() => scrollTo(0, 0));
      record.layout = await page.evaluate(() => {
        const rect = selector => {
          const r = document.querySelector(selector).getBoundingClientRect();
          return {left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height};
        };
        return {width:innerWidth, height:innerHeight, scrollWidth:document.documentElement.scrollWidth,
          controls:Object.fromEntries(['rules','inspect','options','shoot','pause'].map(action => [action, rect(action === "shoot" ? "#power-handle" : `[data-action="${action}"]`)]))};
      });
      record.aimingScreenshot = path.join(artifacts, `touch-${width}x${height}-aiming.png`);
      await page.screenshot({path:record.aimingScreenshot, fullPage:true});
      assert.equal(record.layout.scrollWidth, width, "no horizontal overflow");
      for (const [action, r] of Object.entries(record.layout.controls))
        assert.ok(r.width >= 44 && r.height >= 44, `${action} target ${r.width}x${r.height}`);
      await tap(page, '[data-action="pause"]');
      await waitPhase(page, "paused");
      record.pausedScreenshot = path.join(artifacts, `touch-${width}x${height}-paused.png`);
      await page.screenshot({path:record.pausedScreenshot});
      await tap(page, '[data-action="continue"]');
      await waitPhase(page, "aiming");
      await tap(page, '[data-action="pause"]');
      await tap(page, '[data-action="restart"]');
      await tap(page, '[data-action="confirm-new"]');
      await page.waitForFunction(() => document.querySelector('.game-shell').dataset.phase === 'placing');
      const restarted = await readGame(page);
      assert.equal(restarted.revision, 0);
      assert.equal(restarted.player, 0);
      await tap(page, '[data-action="pause"]');
      await tap(page, '[data-action="leave"]');
      await page.waitForSelector('#catalog .asset-card');
      assert.equal(await page.locator('#game-page canvas').count(), 0);
      assert.equal(await page.evaluate(() => typeof window.render_game_to_text), 'undefined');
      record.outcome = { touchAimChanged:true, paused:true, resumed:true, restartPhase:restarted.phase, exited:true };
    });
  }

  await run("keyboard modal focus and restoration", {
    viewport:{width:1280,height:900}, deviceScaleFactor:1,
  }, async (page, context, record) => {
    await gameReady(page, server.url);
    await start(page);
    record.focus = [];
    const active = () => page.evaluate(() => {
      const el = document.activeElement;
      return {tag:el?.tagName, id:el?.id, action:el?.dataset?.action || null,
        dialog:el?.closest('dialog')?.id || null};
    });
    const inspectTabOrder = async (dialogId, steps) => {
      const sequence = [];
      for (let i = 0; i < steps; i++) {
        await page.keyboard.press('Tab');
        const current = await active();
        sequence.push(current);
        assert.ok(current.dialog === dialogId || current.tag === 'BODY',
          `Tab entered outside application control: ${JSON.stringify(current)}`);
      }
      record.focus.push({dialog:dialogId, sequence});
    };
    await page.locator('[data-action="rules"]').focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('#game-rules[open]');
    assert.equal((await active()).action, 'close-rules');
    await inspectTabOrder('game-rules', 4);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#game-rules').isVisible(), false);
    assert.equal((await active()).action, 'rules', 'Rules focus restored');
    await page.locator('[data-action="options"]').focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('#game-options[open]');
    assert.equal((await active()).id, 'graphics-quality');
    await inspectTabOrder('game-options', 8);
    await page.keyboard.press('Escape');
    assert.equal((await active()).action, 'options', 'Options focus restored');
    await page.locator('[data-action="pause"]').focus();
    await page.keyboard.press('Enter');
    await waitPhase(page, 'paused');
    assert.equal((await active()).action, 'continue');
    await inspectTabOrder('game-menu', 6);
    await page.locator('[data-action="restart"]').focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('#game-confirm[open]');
    assert.equal((await active()).action, 'cancel-new');
    await inspectTabOrder('game-confirm', 4);
    await page.keyboard.press('Escape');
    assert.equal((await active()).action, 'restart', 'nested dialog focus restored');
    await page.keyboard.press('Escape');
    await waitPhase(page, 'aiming');
    assert.equal((await active()).action, 'pause', 'Pause focus restored');
    record.outcome = 'Rules, Options and nested Pause/Restart focus paths exercised';
  });

  await run("accessibility tree names, status and actual progress", {
    viewport:{width:390,height:844}, hasTouch:true, isMobile:true, deviceScaleFactor:1,
  }, async (page, context, record) => {
    await page.goto(server.url);
    const match = {schema:1, rulesVersion:RULES_VERSION, tableVersion:TABLE.version, matchId:'a11y-review',
      revision:8, phase:'aiming', player:0, groups:['solids','stripes'], break:false, ballInHand:false,
      winner:null, balls:makeRack(42)};
    for (const ball of match.balls) if (groupOf(ball.id) === 'solids') ball.pocketed = true;
    await writeCheckpoint(page, match);
    await gameReady(page, server.url);
    await page.locator('[data-action="resume"]').click();
    await page.waitForFunction(() => document.querySelector('#player-0 .remaining-accessible').textContent.includes('8 ball next'));
    const cdp = await context.newCDPSession(page);
    await cdp.send('Accessibility.enable');
    const tree = await cdp.send('Accessibility.getFullAXTree');
    const nodes = tree.nodes.filter(node => !node.ignored).map(node => ({role:node.role?.value, name:node.name?.value || ''}));
    const staticText = nodes.filter(node => node.role === 'StaticText').map(node => node.name);
    record.accessibility = {
      focusable: nodes.filter(node => ['button','slider'].includes(node.role)).map(node => ({role:node.role,name:node.name})),
      progress: staticText.filter(text => /solids cleared|stripes remaining/i.test(text)),
    };
    const names = record.accessibility.focusable.map(node => node.name);
    for (const label of ['Pause / menu']) assert.ok(names.includes(label), `missing accessible button ${label}`);
    assert.ok(names.some(name => /^Aim\b/.test(name)), 'Aim slider accessible name');
    assert.ok(names.some(name => /^Pull to shoot\b/.test(name)), 'Power handle accessible name');
    assert.equal(staticText.filter(text => text === 'solids cleared; 8 ball next.').length, 1);
    assert.equal(staticText.filter(text => text === 'stripes remaining: balls 9, 10, 11, 12, 13, 14, 15.').length, 1);
    assert.equal(staticText.includes('7 left'), false, 'visual summary is not announced twice');
    const doc = await cdp.send('DOM.getDocument');
    const status = await cdp.send('DOM.querySelector', {nodeId:doc.root.nodeId, selector:'#game-status'});
    const statusTree = await cdp.send('Accessibility.getPartialAXTree', {nodeId:status.nodeId, fetchRelatives:false});
    record.accessibility.status = statusTree.nodes.map(node => ({role:node.role?.value, name:node.name?.value || ''}));
    assert.equal(statusTree.nodes[0]?.role?.value, 'status');
    assert.equal(await page.locator('#game-status').getAttribute('aria-live'), 'polite');
    record.screenshot = path.join(artifacts, 'accessibility-progress-390.png');
    await page.screenshot({path:record.screenshot, fullPage:true});
  });
} finally {
  await browser.close();
  await server.close();
  const summary = {date:'2026-11-05', node:process.version, browser:browserVersion, platform:process.platform,
    architecture:process.arch, webgl:'SwiftShader (Playwright launch flags)', buildInfo:JSON.parse(buildInfo),
    indexSha256, artifacts, results};
  await fs.writeFile(path.join(artifacts, 'results.json'), JSON.stringify(summary, null, 2));
  console.log(`ARTIFACTS ${artifacts}`);
  console.log(`RESULT ${results.filter(result => result.passed).length}/${results.length} passed`);
  if (results.some(result => !result.passed)) process.exitCode = 1;
}
