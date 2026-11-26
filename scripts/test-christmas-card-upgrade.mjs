import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';
import { launchOptions, serveBuild } from './browser-test-utils.mjs';
import { encodeGreeting } from '../src/christmas-card/greeting-link.js';

const [firstRoot, lastRoot, newRoot = 'dist'] = process.argv.slice(2);
assert.ok(firstRoot && lastRoot, 'Usage: node scripts/test-christmas-card-upgrade.mjs <acdd9590-dist> <6abd140a-dist> [new-dist]');
const releaseFiles = ['christmas-card/index.html', 'christmas-card/version.json', 'christmas-card/sw.js'];
const roots = await Promise.all([firstRoot, lastRoot, newRoot].map(async root => {
  const [, version, worker] = await Promise.all(releaseFiles.map(file => fs.readFile(path.join(root, file), 'utf8')));
  return {root, ...JSON.parse(version), worker};
}));
const [first, last, current] = roots;
for (const release of [first, last]) {
  assert.match(release.version, /^[a-f0-9]{12}$/);
  assert.match(release.worker, /allowUpdate/, 'each legacy fixture must contain the released worker');
}
assert.notEqual(first.version, last.version, 'use two distinct legacy builds');
assert.match(current.build, /^[a-f0-9]{12}$/);

const server = await serveBuild(first.root);
const cardUrl = server.url + 'christmas-card/index.html';
const url = cardUrl + '?card-test=1#to=Riley&msg=Happy+holidays&from=Alex&lang=en';
const scopePath = new URL('./', cardUrl).pathname;
const oldCache = release => 'christmas-card-' + scopePath.replace(/[^a-z0-9]/gi, '_') + release.version;
const newCache = build => 'christmas-card:' + encodeURIComponent(scopePath) + ':' + build;
const galleryCache = 'b3g-_Blender_3D_Gallery_-shell-upgrade-test';
const waitForControl = page => page.waitForFunction(() => navigator.serviceWorker.controller?.state === 'activated');
const waitForBuild = (page, build) => page.locator(`#update[data-build="${build}"]`).waitFor();
const status = page => page.locator('#update-status');
const loads = page => page.evaluate(() => Number(sessionStorage.getItem('upgrade-test-loads')));

let browser;
try {
  browser = await chromium.launch(launchOptions);
  const legacyOptions = {reducedMotion:'reduce', viewport:{width:420, height:740}};
  for (const release of [first, last]) {
    server.setRoot(release.root);
    const context = await browser.newContext(legacyOptions);
    try {
      const page = await context.newPage();
      await page.goto(url);
      await waitForControl(page);
      await page.locator('#version').filter({hasText:'v' + release.version}).waitFor();
      await page.evaluate(name => caches.open(name).then(() => {}), galleryCache);
      server.setRoot(current.root);
      if (release === first) {
        server.setFault(({relative}) => relative === 'christmas-card/version.json' ? {status:503} : null);
        const failure = context.waitForEvent('response', {
          predicate: response => response.url().endsWith('/christmas-card/version.json') && response.status() === 503,
        });
        await Promise.all([failure, page.reload()]);
        await page.waitForFunction(async name => {
          const registration = await navigator.serviceWorker.getRegistration();
          return registration?.active && !registration.installing && !(await caches.has(name));
        }, newCache(current.build));
        await context.setOffline(true);
        await page.reload();
        await page.locator('#version').filter({hasText:'v' + release.version}).waitFor();
        await page.locator('#open').waitFor();
        await context.setOffline(false);
        server.setFault(null);
      }
      await page.reload();
      await waitForBuild(page, current.build);
      assert.equal(page.url(), url, 'the upgrade preserves the URL, including the fragment');
      assert.deepEqual((await page.evaluate(() => caches.keys())).sort(), [galleryCache, newCache(current.build)].sort());
      await context.setOffline(true);
      await page.reload();
      await waitForBuild(page, current.build);
      await page.locator('#open').click();
      await page.locator('#message:not([hidden])').waitFor();
      assert.equal(await page.locator('#recipient').textContent(), 'Riley');
      assert.equal(await page.locator('#lines').textContent(), 'Happy holidays');
      await page.locator('#update').click();
      await status(page).filter({hasText:'You’re offline'}).waitFor();
      await page.locator('#language').click();
      assert.equal(await page.locator('#update').textContent(), `v${current.version} · 检查更新`);
      await status(page).filter({hasText:'当前处于离线状态'}).waitFor();
      await page.getByRole('button', {name:'写贺卡'}).click();
      await page.getByRole('dialog', {name:'写一张圣诞贺卡'}).waitFor();
      assert.equal(await page.locator('#compose-msg').inputValue(), 'Happy holidays');
      console.log(`PASS legacy ${release.version}: automatic upgrade, cache cleanup and offline greeting`);
    } finally {
      server.setFault(null);
      await context.close();
    }
  }

  const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'christmas-card-upgrade-'));
  let persistentContext;
  try {
    const openProfile = () => chromium.launchPersistentContext(profile, {...launchOptions, ...legacyOptions});
    server.setRoot(first.root);
    persistentContext = await openProfile();
    let page = persistentContext.pages()[0];
    await page.goto(cardUrl);
    await waitForControl(page);
    await page.locator('#version').filter({hasText:'v' + first.version}).waitFor();

    server.setRoot(last.root);
    await page.reload();
    await page.waitForFunction(async name => {
      const registration = await navigator.serviceWorker.getRegistration();
      return registration?.installing?.state === 'installing' &&
        !registration.waiting && !!(await caches.match('./version.json', {cacheName:name}));
    }, oldCache(last));

    server.setRoot(current.root);
    await persistentContext.close();
    persistentContext = await openProfile();
    page = persistentContext.pages()[0];
    await page.goto(cardUrl);
    await waitForBuild(page, current.build);
    assert.equal(page.url(), cardUrl);
    assert.deepEqual(await page.evaluate(() => caches.keys()), [newCache(current.build)]);
    console.log(`PASS legacy ${first.version} with pending install: browser restart recovers the card and removes old card caches`);
  } finally {
    try {
      await persistentContext?.close();
    } finally {
      await fs.rm(profile, {recursive:true, force:true});
    }
  }

  function serveRebuild(label) {
    const build = createHash('sha256').update(current.build + label).digest('hex').slice(0, 12);
    server.setFault(({relative, bytes}) => releaseFiles.includes(relative)
      ? {bytes:Buffer.from(bytes.toString().replaceAll(current.build, build))}
      : null);
    return build;
  }

  const context = await browser.newContext({viewport:{width:720, height:800}});
  await context.addInitScript(() => {
    const count = Number(sessionStorage.getItem('upgrade-test-loads')) + 1;
    sessionStorage.setItem('upgrade-test-loads', String(count));
    if (count !== 1) return;
    const register = navigator.serviceWorker.register.bind(navigator.serviceWorker);
    const gate = new Promise(resolve => { window.releaseRegistration = resolve; });
    navigator.serviceWorker.register = async (...args) => {
      await gate;
      return register(...args);
    };
  });
  const page = await context.newPage();
  await page.goto(url);
  await page.locator('#update').filter({hasText:'Checking…'}).waitFor();
  await page.locator('#update').click();
  assert.equal(await status(page).textContent(), '', 'a click during a pending registration reports no error');
  await status(page).filter({hasText:'taking longer than expected'}).waitFor({timeout:25000});
  await page.locator('#update').click();
  await page.locator('#update').filter({hasText:'Checking…'}).waitFor();
  await page.evaluate(() => window.releaseRegistration());
  await waitForControl(page);
  await status(page).filter({hasText:`v${current.version} is up to date`}).waitFor();
  assert.equal(await loads(page), 1, 'first install does not reload');
  assert.equal(await page.locator('#update').getAttribute('title'), 'Build ' + current.build);
  assert.equal(await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).updateViaCache), 'none');

  // Freeze real rendered frames to hold the animation guards until the worker takes over.
  await page.reload({waitUntil:'domcontentloaded'});
  await page.evaluate(() => window.__christmasCardTest.captureAt(.3, 'entrance'));
  await page.waitForFunction(() => window.__christmasCardTest.snapshot?.phase === 'entrance');
  await status(page).filter({hasText:'is up to date'}).waitFor();
  const secondBuild = serveRebuild('entrance');
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await status(page).filter({hasText:'Update ready'}).waitFor();
  assert.match(await page.locator('#update').textContent(), /Updating…/);
  assert.equal(await loads(page), 2, 'an update waits during the entrance');
  await page.evaluate(() => window.__christmasCardTest.release());
  await waitForBuild(page, secondBuild);
  assert.equal(await loads(page), 3);

  await page.locator('#open').waitFor();
  await status(page).filter({hasText:'is up to date'}).waitFor();
  await page.evaluate(() => window.__christmasCardTest.captureAt(.3, 'opening'));
  await page.locator('#open').click();
  await page.waitForFunction(() => window.__christmasCardTest.snapshot?.phase === 'opening');
  const thirdBuild = serveRebuild('opening');
  await page.locator('#update').click();
  await status(page).filter({hasText:'Update ready'}).waitFor();
  assert.equal(await loads(page), 3, 'an update waits during opening');
  await page.locator('#write-card').click();
  await page.locator('#composer[open]').waitFor();
  await page.waitForFunction(() => document.activeElement?.id === 'compose-close');
  await page.evaluate(() => window.__christmasCardTest.release());
  await page.locator('#message:not([hidden]) #replay:not([data-pending])').waitFor();
  await page.waitForTimeout(500);
  assert.equal(await loads(page), 3, 'an open dialog defers reload after the animation');
  await page.evaluate(() => {
    const editor = document.createElement('textarea');
    editor.id = 'upgrade-test-editor';
    document.body.append(editor);
    const dialog = document.getElementById('composer');
    dialog.addEventListener('close', () => editor.focus(), {once:true});
    dialog.close();
    editor.focus();
  });
  const editor = page.locator('#upgrade-test-editor');
  await editor.fill('Unsaved greeting');
  await page.waitForTimeout(500);
  assert.equal(await loads(page), 3, 'a focused editor defers reload');
  await editor.blur();
  await waitForBuild(page, thirdBuild);
  await page.locator('#open').waitFor();
  assert.equal(await loads(page), 4, 'each takeover reloads exactly once');
  assert.equal(page.url(), url);
  assert.deepEqual(await page.evaluate(() => caches.keys()), [newCache(thirdBuild)]);

  const password = 'separate password 🌟';
  const protectedFragment = await encodeGreeting({to:'Riley', msg:'Happy holidays', lang:'en'}, password);
  await page.evaluate(hash => { location.hash = hash; }, protectedFragment);
  const unlock = page.locator('#unlock-dialog');
  const passwordField = unlock.locator('#unlock-password');
  await unlock.waitFor();
  await passwordField.fill(password);
  const fourthBuild = serveRebuild('unlock');
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.waitForFunction(() => document.getElementById('update-status').textContent.includes('Update ready'));
  await page.waitForTimeout(500);
  assert.equal(await loads(page), 4, 'the password dialog defers the reload');
  assert.equal(await passwordField.inputValue(), password);
  await passwordField.press('Enter');
  await page.waitForFunction(build => document.getElementById('update').dataset.build === build, fourthBuild);
  await unlock.waitFor();
  assert.equal(await loads(page), 5);
  assert.equal(new URL(page.url()).hash, protectedFragment, 'the upgrade preserves the encrypted fragment');
  assert.equal(await passwordField.inputValue(), '', 'the reloaded card asks for the password again');
  console.log('PASS first install, slow registration, localized update states, safe reload and no reload loop');
} finally {
  await browser?.close();
  await server.close();
}
