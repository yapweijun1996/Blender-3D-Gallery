import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { serveBuild, launchOptions, gameReady, readGame } from "./browser-test-utils.mjs";
import { TABLE } from "../src/game/table.js";
const server = process.env.B3G_GAME_TEST_URL
  ? { url: process.env.B3G_GAME_TEST_URL, close: async () => {} }
  : await serveBuild();
const browser = await chromium.launch(launchOptions);
const artifacts = process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-game-responsive";
await fs.mkdir(artifacts, { recursive: true });
const insets = { top:24, right:18, bottom:28, left:14 }, results = [], errors = [];
const sizes = [[320,568],[360,640],[390,844],[430,932],[568,320],[640,360],[844,390],[768,1024],[1024,768],[1440,900]];
const requested = process.env.B3G_GAME_VIEWPORT;
const selected = requested ? sizes.filter(([width,height]) => `${width}x${height}` === requested) : sizes;
assert.ok(selected.length, `Unknown viewport: ${requested}`);
async function reveal(page, phase) {
  await page.evaluate(({ phase, insets }) => {
    window.scrollTo({ top:0, behavior:"instant" });
    const selectors = ["#game-viewport", ".game-table-caption", "#game-pause", phase === "placing" ? '[data-action="place"]' : '[data-action="shoot"]'];
    const bottom = Math.max(...selectors.map((selector) => document.querySelector(selector).getBoundingClientRect().bottom));
    window.scrollBy({ top:Math.max(0, bottom-innerHeight+insets.bottom+4), behavior:"instant" });
  }, { phase, insets });
}
async function snapshot(page, phase) {
  return page.evaluate((phase) => {
    const rect = (selector) => {
      const r = document.querySelector(selector).getBoundingClientRect();
      return { x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom };
    };
    return { scrollY, scrollWidth:document.documentElement.scrollWidth,
      canvas:rect("#game-viewport"), caption:rect(".game-table-caption"),
      action:rect(phase === "placing" ? '[data-action="place"]' : '[data-action="shoot"]'),
      pause:rect("#game-pause"), inspect:rect('[data-action="inspect"]'), options:rect('[data-action="options"]'),
      status:rect("#game-status"), input1:rect(phase === "placing" ? "#place-x" : "#aim-angle"),
      input2:rect(phase === "placing" ? "#place-z" : "#shot-power"),
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
  // Scene framing uses a 2.82 x 1.62 m envelope. This estimates projected
  // physical ball diameter, not individual texture detail.
  const scale = data.canvas.width >= data.canvas.height
    ? Math.min(data.canvas.width / 2.82, data.canvas.height / 1.62)
    : Math.min(data.canvas.width / 1.62, data.canvas.height / 2.82);
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
          await page.waitForFunction(() => !document.querySelector('[data-action="shoot"]').disabled);
        }
        await reveal(page, phase);
        const data = await snapshot(page, phase), projectedBall = verifyLayout(data,width,height,phase);
        const status = await page.locator('#game-status').evaluate((el) => ({ font: parseFloat(getComputedStyle(el).fontSize), scroll: el.scrollHeight, client: el.clientHeight }));
        assert.ok(status.font >= 12, `${width}x${height}: status text is too small`);
        assert.ok(status.scroll <= status.client + 1, `${width}x${height}: status is clipped`);
        await page.screenshot({ path:path.join(artifacts,`${width}x${height}-${phase}.png`) });
        results.push({ width,height,phase,projectedBall, ...data });
        if (phase === "placing") {
          const input = page.locator('#place-x');
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
          await page.touchscreen.tap(r.x + r.width * 0.78, r.y + r.height * 0.35);
          assert.notEqual((await readGame(page)).aim, adjusted.aim, `${width}x${height}: touch aiming did not change`);
          await page.locator('[data-action="shoot"]').tap();
          await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'moving');
          const shot = await readGame(page);
          await page.waitForFunction((cue) => {
            const next = JSON.parse(window.render_game_to_text()).balls[0];
            return Math.hypot(next.x-cue.x,next.z-cue.z) > 0.002;
          }, shot.balls[0], { timeout:10000 });
          await page.locator('[data-action="pause"]').tap();
          await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'paused');
          await page.locator('[data-action="continue"]').tap();
          await page.waitForFunction(() => JSON.parse(window.render_game_to_text()).phase === 'moving');
          await page.evaluate(() => window.advanceTime(26000));
          await page.waitForFunction(() => !['moving','adjudicating'].includes(JSON.parse(window.render_game_to_text()).phase), null, { timeout:30000 });
          await page.locator('#demo-breadcrumb a[data-page="demos"]').tap();
          await page.waitForFunction(() => !document.querySelector('#demos-page').hidden);
          assert.equal(await page.locator('#game-page canvas').count(), 0);
        }
      }
      assert.deepEqual(pageErrors, [], `${width}x${height}: page errors`);
      console.log(`PASS responsive touch journey ${width}x${height}`);
    } catch (error) {
      errors.push(`${width}x${height}: ${error.message}`);
      await page.screenshot({ path:path.join(artifacts,`failure-${width}x${height}.png`) }).catch(() => {});
      throw error;
    } finally { await context.close(); }
  }
} finally {
  await fs.writeFile(path.join(artifacts,'results.json'), JSON.stringify({ results,errors,insets,scope:'Headless Chromium viewport and CSS safe-area simulation. Real installed mode, iOS and Android devices are unverified.' },null,2));
  await browser.close();
  await server.close();
}
