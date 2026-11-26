import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium, devices, webkit } from 'playwright';
import { mutePreference } from '../src/christmas-card/audio.js';

const origin = 'http://localhost/Blender-3D-Gallery/';
const root = path.resolve('dist');
const audioSource = await fs.readFile('src/christmas-card/audio.js', 'utf8');
const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.glb':'model/gltf-binary'};
const selected = process.argv.find(arg => arg.startsWith('--browser='))?.slice('--browser='.length);
const engines = {chromium, webkit};
assert.ok(!selected || selected in engines, 'Choose chromium or webkit');

async function assertMix(page) {
  const levels = await page.evaluate(async source => {
    const {createCardMix, measureLevel} = await import(URL.createObjectURL(new Blob([source], {type:'text/javascript'})));
    const renders = {
      music:23, entrance:1, seal:.22, flap:.35, sparkle:.65, arrival:.9, test:1.1, overlap:1.1,
    };
    const results = [];
    for (const sampleRate of [44100, 48000]) {
      for (const [name, duration] of Object.entries(renders)) {
        const context = new OfflineAudioContext(1, Math.ceil(sampleRate * duration), sampleRate);
        const mix = createCardMix(context);
        if (name === 'music' || name === 'overlap') mix.fillMusic(.025, duration);
        if (name === 'test' || name === 'overlap') mix.testSound(.015);
        if (name === 'overlap') {
          for (let i = 0; i < 30; i++) mix.play('arrival', .015);
        } else if (name !== 'music' && name !== 'test') mix.play(name, .015);
        const buffer = await context.startRendering();
        results.push({sampleRate, name, ...measureLevel(buffer.getChannelData(0))});
      }
    }
    return results;
  }, audioSource);

  // Each pair is an inclusive dBFS range. RMS is over the full render.
  const ranges = {
    music: [[-14, -10], [-28, -21]],
    entrance: [[-14, -7], [-28, -20]],
    seal: [[-13, -6], [-31, -22]],
    flap: [[-13, -7], [-31, -22]],
    sparkle: [[-13, -6], [-27, -19]],
    arrival: [[-11, -5], [-26, -18]],
    test: [[-6, -4], [-11, -7]],
    overlap: [[-5, -1], [-16, -5]],
  };
  for (const {sampleRate, name, peak, rms} of levels) {
    console.log(`${sampleRate} Hz ${name.padEnd(8)} peak ${peak.toFixed(1)} dBFS, RMS ${rms.toFixed(1)} dBFS`);
    const [[minPeak, maxPeak], [minRms, maxRms]] = ranges[name];
    assert.ok(peak >= minPeak && peak <= maxPeak, `${name} peak ${peak} dBFS at ${sampleRate} Hz`);
    assert.ok(rms >= minRms && rms <= maxRms, `${name} RMS ${rms} dBFS at ${sampleRate} Hz`);
  }
}

async function assertControls(page) {
  // Route locally built files through Playwright so the test needs no listening socket.
  await page.route(`${origin}**`, async route => {
    const relative = new URL(route.request().url()).pathname.slice(new URL(origin).pathname.length);
    const file = path.resolve(root, relative.endsWith('/') ? relative + 'index.html' : relative);
    assert.ok(file.startsWith(root + path.sep));
    try {
      await route.fulfill({body:await fs.readFile(file), contentType:types[path.extname(file)] ?? 'application/octet-stream'});
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      await route.abort('filenotfound');
    }
  });
  await page.addInitScript(() => {
    const Native = window.AudioContext ?? window.webkitAudioContext;
    const probe = window.audioProbe = {created:0, hidden:false, sessionAtCreation:[], silentStarts:0};
    Object.defineProperty(document, 'hidden', {get:() => probe.hidden});
    const schedule = window.setInterval;
    window.setInterval = (run, delay, ...args) => schedule(delay === 95 ? (...params) => {
      // Hold the transport's first clock check without changing Web Audio itself.
      if (!probe.holdProgress) run(...params);
    } : run, delay, ...args);
    window.AudioContext = class extends Native {
      constructor() {
        const sessionType = navigator.audioSession?.type;
        super();
        probe.created++;
        probe.sessionAtCreation.push(sessionType);
        probe.context = this;
      }
      createBufferSource() {
        const source = super.createBufferSource();
        const start = source.start.bind(source);
        source.start = (...args) => {
          if (source.buffer?.length === 1) probe.silentStarts++;
          start(...args);
        };
        return source;
      }
    };
  });

  const url = origin + 'christmas-card/';
  const mute = page.locator('#mute');
  const panel = page.locator('#audio-debug');
  await page.goto(url);
  assert.equal(await panel.isVisible(), false);
  await page.goto(url + '?audio-debug');
  await panel.waitFor();
  assert.equal(await mute.textContent(), 'Tap for sound');
  const reading = panel.locator('pre');
  assert.match(await reading.textContent(), /Context: Not created/);
  await mute.evaluate(node => node.click());
  await page.evaluate(() => document.body.dispatchEvent(new Event('touchend', {bubbles:true})));
  assert.equal(await page.evaluate(() => window.audioProbe.created), 0);

  await panel.getByRole('button', {name:'Test sound'}).tap();
  await page.waitForFunction(() => document.getElementById('mute').textContent === 'Sound on', null, {timeout:8000});
  await page.waitForFunction(() => {
    const peak = document.getElementById('audio-reading').textContent.match(/Peak held: (-?[\d.]+) dBFS/);
    return peak && Number(peak[1]) >= -8;
  }, null, {timeout:5000});
  assert.match(await reading.textContent(), /Context: running\nSample rate: \d+ Hz\nClock: [\d.]+ s \(advancing\)/);
  assert.match(await reading.textContent(), /Last resume error: —\nOutput: -[\d.]+ dBFS RMS/);
  assert.deepEqual(await page.evaluate(() => ({
    created: window.audioProbe.created,
    silentStarts: window.audioProbe.silentStarts,
    session: window.audioProbe.sessionAtCreation[0],
  })), {created:1, silentStarts:1, session:await page.evaluate(() => navigator.audioSession ? 'playback' : undefined)});

  const visibility = hidden => page.evaluate(hidden => {
    window.audioProbe.hidden = hidden;
    document.dispatchEvent(new Event('visibilitychange'));
  }, hidden);
  await visibility(true);
  await page.waitForFunction(() => window.audioProbe.context.state === 'suspended', null, {timeout:5000});
  assert.equal(await mute.textContent(), 'Tap for sound');
  assert.equal(await page.evaluate(() => navigator.audioSession?.type ?? 'auto'), 'auto');
  await visibility(false);
  await page.waitForFunction(() => document.getElementById('mute').textContent === 'Sound on', null, {timeout:5000});

  await mute.tap();
  await page.waitForFunction(() => window.audioProbe.context.state === 'suspended', null, {timeout:5000});
  assert.equal(await mute.textContent(), 'Muted');
  assert.equal(await panel.getByRole('button', {name:'Test sound'}).isDisabled(), true);
  assert.equal(await page.evaluate(key => localStorage.getItem(key), mutePreference), '1');
  assert.equal(await page.evaluate(() => navigator.audioSession?.type ?? 'auto'), 'auto');
  await page.reload();
  await panel.waitFor();
  assert.equal(await mute.textContent(), 'Muted');
  assert.equal(await page.evaluate(() => window.audioProbe.created), 0);
  await mute.tap();
  await page.waitForFunction(() => document.getElementById('mute').textContent === 'Sound on', null, {timeout:8000});
  await page.reload();
  await panel.waitFor();
  await page.evaluate(() => { window.audioProbe.holdProgress = true; });
  await page.locator('#subtitle').tap();
  await page.waitForFunction(() => window.audioProbe.context?.state === 'running', null, {timeout:8000});
  const startLabel = await mute.textContent();
  assert.equal(await mute.getAttribute('aria-pressed'), 'false');
  await mute.tap();
  assert.equal(await mute.getAttribute('aria-pressed'), 'true', 'mute works before the first audio clock check');
  assert.match(startLabel, /^(Sound on|Starting sound…)$/);
  assert.equal(await mute.textContent(), 'Muted');
  await page.waitForFunction(() => window.audioProbe.context.state === 'suspended', null, {timeout:5000});
}

for (const [name, engine] of Object.entries(engines)) {
  if (selected && name !== selected) continue;
  const args = name === 'chromium' && process.argv.includes('--single-process') ? ['--single-process', '--disable-gpu'] : [];
  const browser = await engine.launch({args});
  try {
    const page = await browser.newPage({...devices['iPhone 13'], serviceWorkers:'block', reducedMotion:'reduce'});
    await assertMix(page);
    await assertControls(page);
    console.log(`PASS ${name}: offline mix, touch activation, diagnostics, visibility, immediate and remembered mute`);
  } finally {
    await browser.close();
  }
}
