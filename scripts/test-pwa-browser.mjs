import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { chromium } from "playwright";
import {
  serveBuild,
  launchOptions,
  gameReady,
  readGame,
} from "./browser-test-utils.mjs";

const artifacts =
  process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-pwa-qa";
await fs.mkdir(artifacts, { recursive: true });
const temp = await fs.mkdtemp(path.join(os.tmpdir(), "b3g-pwa-builds-"));
const template = await fs.readFile("src/pwa/sw-template.js", "utf8");
async function variant(
  label,
  changeWorker = (source) => source,
  sourceRoot = "dist",
) {
  const root = path.join(temp, label);
  await fs.cp(sourceRoot, root, { recursive: true });
  const html = path.join(root, "index.html");
  await fs.writeFile(
    html,
    (await fs.readFile(html, "utf8")).replace(
      "</head>",
      `<meta name="test-build" content="${label}"></head>`,
    ),
  );
  const walk = async (dir) =>
    (
      await Promise.all(
        (await fs.readdir(dir, { withFileTypes: true })).map((e) =>
          e.isDirectory()
            ? walk(path.join(dir, e.name))
            : path.join(dir, e.name),
        ),
      )
    ).flat();
  const files = await Promise.all(
    (await walk(root))
      .filter(
        (p) =>
          !["sw.js", "build-info.json", "game-pack.json"].includes(
            path.basename(p),
          ),
      )
      .map(async (p) => {
        const b = await fs.readFile(p);
        return {
          url: path.relative(root, p).split(path.sep).join("/"),
          bytes: b.length,
          sha256: crypto.createHash("sha256").update(b).digest("hex"),
        };
      }),
  );
  const build = crypto
    .createHash("sha256")
    .update(label + JSON.stringify(files))
    .digest("hex")
    .slice(0, 16);
  const pack = JSON.parse(
    await fs.readFile(path.join(root, "game-pack.json"), "utf8"),
  );
  pack.build = build;
  const shell = files.filter(
    (f) =>
      f.url === "index.html" || /\.(js|css|webmanifest|png|svg)$/.test(f.url),
  );
  await fs.writeFile(
    path.join(root, "build-info.json"),
    JSON.stringify({ build }),
  );
  await fs.writeFile(path.join(root, "game-pack.json"), JSON.stringify(pack));
  await fs.writeFile(
    path.join(root, "sw.js"),
    changeWorker(
      template
        .replace("__BUILD__", JSON.stringify(build))
        .replace("__SHELL__", JSON.stringify(shell))
        .replace("__PACK__", JSON.stringify(pack)),
    ),
  );
  return { root, build, pack };
}
const a = await variant("A"),
  b = await variant("B-missing-file"),
  c = await variant("C-wrong-identity"),
  d = await variant("D");
const server = await serveBuild(a.root),
  browser = await chromium.launch(launchOptions),
  context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  }),
  page = await context.newPage(),
  results = [],
  errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const pass = (name) => {
  results.push(name);
  console.log("PASS", name);
};
async function request(page, type) {
  return page.evaluate(async (type) => {
    const r = await navigator.serviceWorker.ready;
    return new Promise((resolve, reject) => {
      const ch = new MessageChannel(),
        timer = setTimeout(() => {
          ch.port1.close();
          ch.port2.close();
          reject(new Error("SW request timeout"));
        }, 45000);
      ch.port1.onmessage = (e) => {
        if (e.data.progress) return;
        clearTimeout(timer);
        ch.port1.close();
        ch.port2.close();
        resolve(e.data);
      };
      r.active.postMessage({ type }, [ch.port2]);
    });
  }, type);
}
async function update(page) {
  return page.evaluate(async () => {
    const r = await navigator.serviceWorker.getRegistration();
    const settled = new Promise((resolve) => {
      const observe = () => {
        const w = r.installing;
        if (!w) {
          resolve(r.waiting ? "installed" : "none");
          return;
        }
        if (["installed", "redundant"].includes(w.state)) {
          resolve(w.state);
          return;
        }
        w.addEventListener("statechange", () => {
          if (["installed", "redundant"].includes(w.state)) resolve(w.state);
        });
      };
      r.addEventListener("updatefound", observe, { once: true });
      if (r.installing) observe();
      setTimeout(() => resolve(r.waiting ? "installed" : "timeout"), 20000);
    });
    await r.update();
    return settled;
  });
}
try {
  await gameReady(page, server.url);
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await page.waitForFunction(
    () =>
      navigator.serviceWorker.controller &&
      window.render_game_to_text &&
      JSON.parse(window.render_game_to_text()).ready,
  );
  assert.equal((await request(page, "PACK_STATUS")).build, a.build);
  assert.equal((await request(page, "PACK_STATUS")).ready, false);
  assert.equal((await request(page, "CACHE_GAME")).ready, true);
  pass("initial shell and all 18 verified game assets cached");
  await page.click("[data-action=new]");
  await page.click("[data-action=place]");
  await page.waitForFunction(
    () => !document.querySelector("[data-action=shoot]").disabled,
  );
  const checkpoint = await readGame(page);
  await page.evaluate(() => caches.open("sibling-app-keep-me"));
  await context.setOffline(true);
  assert.equal((await request(page, "CACHE_GAME")).ready, true);
  await gameReady(page, server.url);
  await page.click("[data-action=resume]");
  assert.deepEqual((await readGame(page)).balls, checkpoint.balls);
  const missing = await page.evaluate(async () => {
    const r = await fetch("./assets/not-cached.glb");
    return {
      status: r.status,
      type: r.headers.get("Content-Type"),
      body: await r.text(),
    };
  });
  assert.equal(missing.status, 503);
  assert.equal(missing.type, "text/plain");
  assert.doesNotMatch(missing.body, /<html/i);
  pass(
    "offline cold start, checkpoint resume, repeated preparation and non-HTML GLB failure",
  );
  await context.setOffline(false);
  server.setRoot(b.root);
  server.setFault(({ relative }) =>
    relative.startsWith("assets/") && relative.endsWith(".js")
      ? { status: 404 }
      : null,
  );
  assert.equal(await update(page), "redundant");
  assert.equal((await request(page, "PACK_STATUS")).build, a.build);
  assert.equal((await request(page, "PACK_STATUS")).ready, true);
  pass(
    "missing required shell resource rejects candidate and preserves active build",
  );
  server.setRoot(c.root);
  server.setFault(({ relative }) =>
    relative === "build-info.json"
      ? { bytes: Buffer.from('{"build":"wrong"}') }
      : null,
  );
  assert.equal(await update(page), "redundant");
  assert.equal((await request(page, "PACK_STATUS")).build, a.build);
  pass("HTML/worker build identity mismatch rejects installation");
  server.setRoot(d.root);
  server.setFault(null);
  assert.equal(await update(page), "installed");
  assert.equal((await request(page, "PACK_STATUS")).build, a.build);
  assert.equal(
    await page.locator("meta[name=test-build]").getAttribute("content"),
    "A",
  );
  pass("new worker waits without replacing an active game");
  const other = await context.newPage();
  await other.goto(server.url);
  await other.waitForSelector(".pwa-notice:not([hidden])");
  await other.locator(".pwa-notice button").first().click();
  await other.waitForFunction(() =>
    document.querySelector(".pwa-notice").textContent.includes("Another tab"),
  );
  assert.equal((await request(page, "PACK_STATUS")).build, a.build);
  assert.equal((await readGame(page)).phase, "aiming");
  pass("another playing tab blocks explicit update");
  await other.close();
  await page.waitForSelector(".pwa-notice:not([hidden])");
  await page.locator(".pwa-notice button").first().click();
  await page.waitForFunction(
    () => document.querySelector("meta[name=test-build]")?.content === "D",
    {},
    { timeout: 30000 },
  );
  await page.waitForFunction(
    () =>
      window.render_game_to_text &&
      JSON.parse(window.render_game_to_text()).ready,
  );
  assert.equal((await request(page, "PACK_STATUS")).build, d.build);
  await page.click("[data-action=resume]");
  assert.deepEqual((await readGame(page)).balls, checkpoint.balls);
  pass("explicit N to N+1 update reloads once and restores the saved turn");
  server.setFault(({ relative }) =>
    relative.endsWith(".glb") ? { status: 404 } : null,
  );
  assert.equal((await request(page, "CACHE_GAME")).ok, false);
  assert.equal((await request(page, "PACK_STATUS")).ready, false);
  let names = await page.evaluate(() => caches.keys());
  assert.ok(names.some((n) => n.endsWith(a.build) && n.includes("-game-")));
  assert.ok(names.includes("sibling-app-keep-me"));
  assert.ok(!names.some((n) => n.includes("-candidate-")));
  pass(
    "failed new pack keeps the previous good pack and unrelated project caches",
  );
  server.setFault(null);
  assert.equal((await request(page, "CACHE_GAME")).ready, true);
  await context.setOffline(true);
  await gameReady(page, server.url);
  await page.click("[data-action=resume]");
  assert.deepEqual((await readGame(page)).balls, checkpoint.balls);
  await page.screenshot({
    path: path.join(artifacts, "offline-updated-game.png"),
  });
  pass("updated version also starts and resumes offline");
  // Each scenario starts with an actual installed A worker and a real waiting
  // candidate. Faults stay inside the test server/IndexedDB/worker environment.
  async function scenario(label, changeWorker, verify) {
    const candidate = await variant(label, changeWorker);
    const isolated = await browser.newContext({
      viewport: { width: 1280, height: 900 },
    });
    const tab = await isolated.newPage();
    tab.on("pageerror", (error) => errors.push(error.message));
    try {
      server.setRoot(a.root);
      server.setFault(null);
      await gameReady(tab, server.url);
      await tab.evaluate(() => navigator.serviceWorker.ready);
      await tab.reload();
      await tab.waitForFunction(
        () =>
          navigator.serviceWorker.controller &&
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready,
      );
      server.setRoot(candidate.root);
      assert.equal(await update(tab), "installed");
      await tab.locator(".pwa-notice:not([hidden])").waitFor();
      await verify(tab, isolated, candidate);
    } finally {
      await isolated.close();
    }
  }
  const clickUpdate = (tab) =>
    tab.locator(".pwa-notice button").first().click();
  const updateError = (tab) =>
    tab.waitForFunction(
      () =>
        document.querySelector("#pwa-update-dialog")?.dataset.phase === "error",
    );
  const loadedBuild = async (tab, build) => {
    await tab.waitForFunction(
      (build) =>
        document.querySelector("meta[name=test-build]")?.content === build,
      build,
      { timeout: 30000 },
    );
    await tab.waitForFunction(
      () =>
        window.render_game_to_text &&
        JSON.parse(window.render_game_to_text()).ready,
    );
  };
  await scenario(
    "E-save-and-input-guards",
    (source) => source,
    async (tab, isolated) => {
      await tab.locator("[data-action=new]").first().click();
      await tab.locator("[data-action=place]").click();
      await tab.waitForFunction(
        () => !document.querySelector("[data-action=shoot]").disabled,
      );
      const before = await readGame(tab);
      await tab.evaluate(() => {
        window.originalPwaTransaction = IDBDatabase.prototype.transaction;
        IDBDatabase.prototype.transaction = function (...args) {
          if (
            this.name === "blender-gallery-game-v1" &&
            args[1] === "readwrite"
          )
            throw new DOMException(
              "Injected storage unavailable",
              "QuotaExceededError",
            );
          return window.originalPwaTransaction.apply(this, args);
        };
      });
      await clickUpdate(tab);
      await updateError(tab);
      assert.match(
        await tab.locator("#pwa-update-status").innerText(),
        /save your turn/i,
      );
      assert.equal((await request(tab, "PACK_STATUS")).build, a.build);
      assert.deepEqual((await readGame(tab)).balls, before.balls);
      await tab.evaluate(() => {
        IDBDatabase.prototype.transaction = window.originalPwaTransaction;
        delete window.originalPwaTransaction;
      });
      let reloads = 0;
      // Same-document history replacements are not reloads.
      tab.on("request", (request) => {
        if (
          request.isNavigationRequest() &&
          request.frame() === tab.mainFrame()
        )
          reloads++;
      });
      await tab.locator("[data-update-action=retry]").click();
      await tab.waitForFunction(
        () =>
          document.querySelector("#pwa-update-dialog")?.dataset.phase ===
          "checking-tabs",
      );
      assert.equal(
        await tab
          .locator("#pwa-update-dialog")
          .evaluate(
            (dialog) => dialog.open && dialog.contains(document.activeElement),
          ),
        true,
      );
      await tab.keyboard.press("Escape");
      assert.equal(
        await tab
          .locator("#pwa-update-dialog")
          .evaluate((dialog) => dialog.open),
        true,
      );
      assert.equal(
        await tab.locator("#game-menu").evaluate((dialog) => dialog.open),
        false,
      );
      await assert.rejects(
        tab.locator("[data-action=shoot]").click({ timeout: 200 }),
        /Timeout/,
      );
      assert.notEqual((await readGame(tab)).phase, "moving");
      await tab.evaluate(() => {
        Object.defineProperty(document, "hidden", {
          configurable: true,
          get: () => true,
        });
        document.dispatchEvent(new Event("visibilitychange"));
      });
      assert.equal((await readGame(tab)).phase, "paused");
      assert.equal(
        await tab.locator("#game-menu").evaluate((dialog) => dialog.open),
        false,
      );
      assert.equal(
        await tab
          .locator("#pwa-update-dialog")
          .evaluate((dialog) => dialog.open),
        true,
      );
      await tab.evaluate(() => {
        delete document.hidden;
        document.dispatchEvent(new Event("visibilitychange"));
      });
      await loadedBuild(tab, "E-save-and-input-guards");
      assert.equal(reloads, 1);
      pass(
        "failed stable save refuses activation; retry locks shots, Escape and background menus, then reloads once",
      );
    },
  );
  await scenario(
    "F-activation-rejection",
    (source) =>
      source.replace(
        "await self.skipWaiting();",
        'if (!self.testRejectedOnce) { self.testRejectedOnce = true; throw new Error("Injected activation unavailable"); } await self.skipWaiting();',
      ),
    async (tab) => {
      await clickUpdate(tab);
      await updateError(tab);
      assert.match(
        await tab.locator("#pwa-update-status").innerText(),
        /activation unavailable/i,
      );
      assert.equal((await request(tab, "PACK_STATUS")).build, a.build);
      await tab.locator("[data-update-action=close]").click();
      assert.equal(
        await tab
          .locator("#pwa-update-dialog")
          .evaluate((dialog) => dialog.open),
        false,
      );
      assert.equal(
        await tab.locator(".pwa-notice button").first().isEnabled(),
        true,
      );
      await clickUpdate(tab);
      await loadedBuild(tab, "F-activation-rejection");
      pass(
        "worker activation rejection unlocks loader and permits an explicit successful retry",
      );
    },
  );
  await scenario(
    "G-request-timeout",
    (source) =>
      source.replace(
        "await new Promise((resolve) => setTimeout(resolve, 1200));",
        "self.testAttempt=(self.testAttempt||0)+1; await new Promise(resolve=>setTimeout(resolve,self.testAttempt===1?16000:1200));",
      ),
    async (tab) => {
      let reloads = 0;
      // Same-document history replacements are not reloads.
      tab.on("request", (request) => {
        if (
          request.isNavigationRequest() &&
          request.frame() === tab.mainFrame()
        )
          reloads++;
      });
      await clickUpdate(tab);
      await updateError(tab);
      assert.match(
        await tab.locator("#pwa-update-status").innerText(),
        /timed out/i,
      );
      assert.equal((await request(tab, "PACK_STATUS")).build, a.build);
      await tab.waitForTimeout(4500);
      assert.equal(
        reloads,
        0,
        "late expired worker reply cannot activate or reload",
      );
      assert.equal((await request(tab, "PACK_STATUS")).build, a.build);
      await tab.locator("[data-update-action=retry]").click();
      await loadedBuild(tab, "G-request-timeout");
      assert.equal(reloads, 1);
      pass(
        "request timeout cancels activation; late callbacks cannot reload; retry reloads once",
      );
    },
  );
  await scenario(
    "H-controller-timeout",
    (source) =>
      source.replace(
        "await self.skipWaiting();",
        "if (!self.testSkippedOnce) self.testSkippedOnce=true; else await self.skipWaiting();",
      ),
    async (tab) => {
      let reloads = 0;
      // Same-document history replacements are not reloads.
      tab.on("request", (request) => {
        if (
          request.isNavigationRequest() &&
          request.frame() === tab.mainFrame()
        )
          reloads++;
      });
      await clickUpdate(tab);
      await tab.waitForFunction(
        () =>
          document.querySelector("#pwa-update-dialog")?.dataset.phase ===
          "activating",
      );
      await updateError(tab);
      assert.match(
        await tab.locator("#pwa-update-status").innerText(),
        /did not finish/i,
      );
      assert.equal(reloads, 0);
      await tab.locator("[data-update-action=retry]").click();
      await loadedBuild(tab, "H-controller-timeout");
      assert.equal(reloads, 1);
      pass(
        "activation without controllerchange times out recoverably and retries without a duplicate reload",
      );
    },
  );
  await scenario(
    "I-multi-tab-retention",
    (source) => source,
    async (tab, isolated, candidate) => {
      // No active match in either tab: the non-initiator must block new gameplay
      // during the readiness window, then keep its current document on activation.
      const old = await isolated.newPage();
      await old.goto(server.url);
      await old.waitForSelector(".pwa-notice:not([hidden])");
      await request(tab, "CACHE_GAME");
      let reloads = 0;
      // Same-document history replacements are not reloads.
      tab.on("request", (request) => {
        if (
          request.isNavigationRequest() &&
          request.frame() === tab.mainFrame()
        )
          reloads++;
      });
      const button = tab.locator(".pwa-notice button").first();
      const rect = await button.boundingBox();
      await tab.mouse.dblclick(
        rect.x + rect.width / 2,
        rect.y + rect.height / 2,
      );
      await old.locator("#pwa-update-dialog[open]").waitFor();
      await assert.rejects(
        old
          .getByRole("link", { name: "Interactive Demos", exact: true })
          .first()
          .click({ timeout: 200 }),
        /Timeout/,
      );
      await loadedBuild(tab, "I-multi-tab-retention");
      assert.equal(reloads, 1);
      await old.waitForFunction(
        () => !document.querySelector("#pwa-update-dialog").open,
      );
      assert.equal(
        await old.locator("meta[name=test-build]").getAttribute("content"),
        "A",
        "other tabs are not force-reloaded",
      );
      const next = await variant("J-third-build");
      server.setRoot(next.root);
      assert.equal(await update(tab), "installed");
      await clickUpdate(tab);
      await loadedBuild(tab, "J-third-build");
      let names = await tab.evaluate(() => caches.keys());
      for (const build of [a.build, candidate.build, next.build])
        assert.ok(
          names.some(
            (name) => name.includes("-shell-") && name.endsWith(build),
          ),
          `retained shell ${build}`,
        );
      assert.ok(
        names.some((name) => name.includes("-game-") && name.endsWith(a.build)),
        "previous complete pack retained",
      );
      await clickUpdate(old);
      await old.waitForFunction(
        () =>
          document.querySelector("meta[name=test-build]")?.content ===
          "J-third-build",
      );
      await old.close();
      names = await tab.evaluate(() => caches.keys());
      assert.ok(
        names.some((name) => name.endsWith(a.build)),
        "documented conservative retention exception persists after old tab closes",
      );
      assert.ok(!names.some((name) => name.includes("-candidate-")));
      pass(
        "idle tabs block new demo input during update; duplicate clicks reload once; three-build caches and last good pack retained safely",
      );
    },
  );
  await scenario(
    "L-active-shot-refusal",
    (source) => source,
    async (tab) => {
      await tab.locator("[data-action=new]").first().click();
      await tab.locator("[data-action=place]").click();
      await tab.locator("#shot-power").focus();
      await tab.keyboard.press("Home");
      await tab.locator("[data-action=shoot]").click();
      await tab.waitForFunction(
        () => JSON.parse(window.render_game_to_text()).phase === "moving",
      );
      assert.equal((await readGame(tab)).phase, "moving");
      await clickUpdate(tab);
      await updateError(tab);
      assert.match(
        await tab.locator("#pwa-update-status").innerText(),
        /finish or restore the current shot/i,
      );
      assert.equal((await request(tab, "PACK_STATUS")).build, a.build);
      await tab.locator("[data-update-action=close]").click();
      await tab.waitForFunction(
        () =>
          !["moving", "adjudicating"].includes(
            JSON.parse(window.render_game_to_text()).phase,
          ),
      );
      const stable = await readGame(tab);
      await clickUpdate(tab);
      await loadedBuild(tab, "L-active-shot-refusal");
      await tab.locator("[data-action=resume]").click();
      assert.deepEqual((await readGame(tab)).balls, stable.balls);
      pass(
        "a real active shot refuses update; completed-shot retry saves and restores actual stable balls",
      );
    },
  );
  await scenario(
    "M-blocked-save-timeout",
    (source) => source,
    async (tab) => {
      await tab.locator("[data-action=new]").first().click();
      await tab.locator("[data-action=place]").click();
      await tab.waitForFunction(
        () => !document.querySelector("[data-action=shoot]").disabled,
      );
      const before = await readGame(tab);
      await tab.evaluate(
        () =>
          new Promise((resolve, reject) => {
            const opened = indexedDB.open("blender-gallery-game-v1", 1);
            opened.onerror = () => reject(opened.error);
            opened.onsuccess = () => {
              const db = opened.result,
                tx = db.transaction("records", "readwrite"),
                store = tx.objectStore("records");
              window.releasePwaSaveBlock = false;
              const hold = () => {
                const request = store.get("owner");
                request.onsuccess = () => {
                  if (!window.releasePwaSaveBlock) hold();
                };
              };
              hold();
              tx.oncomplete = () => db.close();
              resolve();
            };
          }),
      );
      await clickUpdate(tab);
      await updateError(tab);
      assert.match(
        await tab.locator("#pwa-update-status").innerText(),
        /did not finish/i,
      );
      assert.equal((await request(tab, "PACK_STATUS")).build, a.build);
      await tab.evaluate(() => {
        window.releasePwaSaveBlock = true;
      });
      await tab.waitForTimeout(250);
      assert.equal(
        await tab.locator("#pwa-update-dialog").getAttribute("data-phase"),
        "error",
      );
      assert.equal(
        (await request(tab, "PACK_STATUS")).build,
        a.build,
        "late IndexedDB completion cannot start activation",
      );
      await tab.locator("[data-update-action=retry]").click();
      await loadedBuild(tab, "M-blocked-save-timeout");
      await tab.locator("[data-action=resume]").click();
      assert.deepEqual((await readGame(tab)).balls, before.balls);
      pass(
        "blocked IndexedDB save times out visibly; late completion cannot activate; explicit retry preserves checkpoint",
      );
    },
  );
  if (process.env.PWA_LEGACY_DIST) {
    const legacy = await variant(
      "Legacy-runtime",
      (source) => source,
      process.env.PWA_LEGACY_DIST,
    );
    const latest = await variant("K-legacy-migration");
    const isolated = await browser.newContext({
      viewport: { width: 1280, height: 900 },
    });
    let old = await isolated.newPage();
    try {
      server.setRoot(legacy.root);
      server.setFault(null);
      await gameReady(old, server.url);
      await old.evaluate(() => navigator.serviceWorker.ready);
      await old.reload();
      await old.waitForFunction(
        () =>
          navigator.serviceWorker.controller &&
          window.render_game_to_text &&
          JSON.parse(window.render_game_to_text()).ready,
      );
      await old.locator("[data-action=new]").first().click();
      await old.locator("[data-action=place]").click();
      await old.waitForFunction(
        () => !document.querySelector("[data-action=shoot]").disabled,
      );
      const saved = await readGame(old);
      server.setRoot(latest.root);
      assert.equal(await update(old), "installed");
      await clickUpdate(old);
      await old.waitForFunction(() =>
        document
          .querySelector(".pwa-notice")
          .textContent.includes("older update interface"),
      );
      assert.match(
        await old.locator(".pwa-notice").innerText(),
        /save your turn.*close all gallery tabs/i,
      );
      assert.equal((await request(old, "PACK_STATUS")).build, legacy.build);
      assert.deepEqual((await readGame(old)).balls, saved.balls);
      const oldWorker = isolated.serviceWorkers()[0];
      const waitingWorker = isolated
        .serviceWorkers()
        .find((worker) => worker !== oldWorker);
      await old.close();
      if (waitingWorker)
        await waitingWorker.evaluate(async () => {
          if (self.registration.waiting)
            await new Promise((resolve) =>
              self.addEventListener("activate", resolve, { once: true }),
            );
        });
      old = await isolated.newPage();
      await gameReady(old, server.url);
      await loadedBuild(old, "K-legacy-migration");
      await old.locator("[data-action=resume]").click();
      assert.deepEqual((await readGame(old)).balls, saved.balls);
      pass(
        "actual legacy runtime refuses unlocked activation, preserves checkpoint and migrates safely after closing all old tabs",
      );
    } finally {
      await isolated.close();
    }
  }
  assert.deepEqual(errors, []);
  await fs.writeFile(
    path.join(artifacts, "results.json"),
    JSON.stringify(
      { results, errors, builds: { a: a.build, d: d.build } },
      null,
      2,
    ),
  );
} catch (e) {
  await page
    .screenshot({ path: path.join(artifacts, "failure.png") })
    .catch(() => {});
  throw e;
} finally {
  await context.close();
  await browser.close();
  await server.close();
  await fs.rm(temp, { recursive: true, force: true });
}
