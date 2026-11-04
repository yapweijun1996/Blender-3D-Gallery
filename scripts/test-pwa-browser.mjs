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
async function variant(label) {
  const root = path.join(temp, label);
  await fs.cp("dist", root, { recursive: true });
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
    template
      .replace("__BUILD__", JSON.stringify(build))
      .replace("__SHELL__", JSON.stringify(shell))
      .replace("__PACK__", JSON.stringify(pack)),
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
        timer = setTimeout(
          () => reject(new Error("SW request timeout")),
          45000,
        );
      ch.port1.onmessage = (e) => {
        if (e.data.progress) return;
        clearTimeout(timer);
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
