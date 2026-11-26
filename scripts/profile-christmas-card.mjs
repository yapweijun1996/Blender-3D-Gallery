import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { launchOptions, serveBuild } from './browser-test-utils.mjs';

const phases = ['entrance', 'idle', 'opening'];
const baselineUrl = process.argv[2];
const server = await serveBuild();
let browser;
try {
  browser = await chromium.launch(launchOptions);
  const baseline = baselineUrl && await profile(baselineUrl);
  const candidate = await profile(`${server.url}christmas-card/index.html`);
  if (baseline) console.log('Stage A', JSON.stringify(baseline, null, 2));
  console.log('Current build', JSON.stringify(candidate, null, 2));
  for (const phase of baseline ? phases : []) {
    const fps = candidate[phase].fps, minimum = baseline[phase].fps * .9;
    assert.ok(fps >= minimum, `${phase}: ${fps.toFixed(1)} fps, expected at least ${minimum.toFixed(1)} fps`);
  }
  assert.equal(candidate.completion.reason, 'timeline', JSON.stringify(candidate.completion));
  for (const phase of ['entrance', 'idle', 'tapThroughHandover']) {
    assert.equal(candidate[phase].programsAdded, 0, `Shader programs were added during ${phase}`);
  }
} finally {
  await browser?.close();
  await server.close();
}

async function profile(address) {
  const url = new URL(address);
  url.searchParams.set('card-test', '1');
  const context = await browser.newContext({viewport: {width: 1440, height: 900}, deviceScaleFactor: 1});
  try {
    const page = await context.newPage();
    await page.addInitScript(() => {
      const samples = window.cardProfile = {warmup: [], entrance: [], idle: [], opening: []};
      let tapped = false, presentedMessage = false;
      document.addEventListener('click', event => {
        if (event.target.id === 'open') tapped = true;
      }, true);
      function observe() {
        const renderer = window.__christmasCardTest?.renderer;
        if (!renderer) { requestAnimationFrame(observe); return; }
        const open = document.getElementById('open');
        const message = document.getElementById('message');
        const render = renderer.render;
        renderer.render = function (...args) {
          if (!message.hidden) {
            if (!tapped || presentedMessage) return render.apply(this, args);
            presentedMessage = true;
          }
          const phase = this.getScissorTest() ? 'warmup' : tapped ? 'opening' : open.hidden ? 'entrance' : 'idle';
          const start = performance.now();
          const compiled = this.info.programs.length;
          const result = render.apply(this, args);
          samples[phase].push({start, renderMs: performance.now() - start,
            calls: this.info.render.calls, programsAdded: this.info.programs.length - compiled});
          return result;
        };
      }
      requestAnimationFrame(observe);
    });
    await page.goto(url.href);
    await page.locator('#open:not([disabled]):visible').waitFor({timeout: 15000});
    await page.waitForFunction(() => {
      const frames = window.cardProfile.idle;
      return frames.length > 1 && frames.at(-1).start - frames[0].start >= 2000;
    }, undefined, {timeout: 8000});
    await page.locator('#open').click();
    await page.locator('#message:visible').waitFor({timeout: 15000});
    const {samples, completion, drawingBuffer, renderer} = await page.evaluate(() => {
      const canvas = document.getElementById('canvas');
      const gl = window.__christmasCardTest.renderer.getContext();
      const info = gl.getExtension('WEBGL_debug_renderer_info');
      return {samples: window.cardProfile, completion: window.__christmasCardTest.entranceCompletion,
        drawingBuffer: [canvas.width, canvas.height], renderer: info && gl.getParameter(info.UNMASKED_RENDERER_WEBGL)};
    });
    const warmup = {draws: samples.warmup.length, programsAdded: programsAdded(samples.warmup)};
    return {renderer, drawingBuffer, completion, warmup, entrance: stats(samples.entrance), idle: stats(samples.idle, 2000),
      opening: stats(samples.opening, 2000), tapThroughHandover: stats(samples.opening)};
  } finally {
    await context.close();
  }
}

function stats(samples, windowMs) {
  assert.ok(samples.length > 1, 'Too few rendered frames');
  const start = samples[0].start;
  let frames = samples;
  if (windowMs !== undefined) {
    const end = samples.findIndex(sample => sample.start >= start + windowMs);
    assert.ok(end > 0, `Expected at least ${windowMs} ms of frame samples`);
    frames = samples.slice(0, end + 1);
  }
  const intervals = frames.slice(1).map((sample, i) => sample.start - frames[i].start).sort((a, b) => a - b);
  return {
    sampleMs: frames.at(-1).start - start,
    fps: (frames.length - 1) * 1000 / (frames.at(-1).start - start),
    p95FrameMs: intervals[Math.ceil(intervals.length * .95) - 1], worstFrameMs: intervals.at(-1),
    worstRenderMs: Math.max(...frames.map(sample => sample.renderMs)),
    averageDrawCalls: frames.reduce((total, sample) => total + sample.calls, 0) / frames.length,
    programsAdded: programsAdded(frames),
  };
}

function programsAdded(frames) {
  return frames.reduce((total, sample) => total + Math.max(0, sample.programsAdded), 0);
}
