import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { serveBuild, launchOptions, gameReady } from "./browser-test-utils.mjs";
const catalog = JSON.parse(await fs.readFile(new URL("../models/catalog.json", import.meta.url), "utf8"));
const expectedDemoCount = JSON.parse(await fs.readFile(new URL("../data/demos.json", import.meta.url), "utf8")).length;
const expectedAssetCount = catalog.collections.reduce((total, collection) => total + collection.assets.length, 0);
const artifacts =
  process.env.TEST_ARTIFACT_DIR || "/tmp/blender-gallery-pwa-standard";
await fs.mkdir(artifacts, { recursive: true });
const buildRoot = process.env.TEST_BUILD_DIR || "dist";
const server = await serveBuild(buildRoot),
  browser = await chromium.launch(launchOptions),
  results = [],
  pageErrors = [];
const sizes = [
    [320, 720],
    [390, 844],
    [430, 932],
    [768, 1024],
    [1024, 768],
    [1440, 900],
    [1920, 1080],
  ],
  insets = { top: 24, right: 18, bottom: 28, left: 14 };
async function run(name, fn, options = {}) {
  const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      serviceWorkers: "block",
      ...options,
    }),
    page = await context.newPage();
  page.on("pageerror", (e) => pageErrors.push(`${name}: ${e.message}`));
  try {
    await fn(page, context);
    results.push({ name, passed: true });
    console.log("PASS", name);
  } catch (error) {
    await page
      .screenshot({ path: path.join(artifacts, "failure.png") })
      .catch(() => {});
    throw error;
  } finally {
    await context.close();
  }
}
async function safeInsets(page) {
  await page.evaluate((insets) => {
    for (const [edge, value] of Object.entries(insets))
      document.documentElement.style.setProperty(
        `--safe-${edge}`,
        `${value}px`,
      );
  }, insets);
}
async function noOverflow(page) {
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
}
async function safeRect(locator, viewport, description) {
  const r = await locator.boundingBox();
  assert.ok(r, `${description} visible`);
  assert.ok(
    r.x >= insets.left - 1 &&
      r.y >= insets.top - 1 &&
      r.x + r.width <= viewport.width - insets.right + 1 &&
      r.y + r.height <= viewport.height - insets.bottom + 1,
    `${description}: ${JSON.stringify(r)}`,
  );
}
function contrastRatio(foreground, background) {
  const luminance = (color) => {
    const rgb = color.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
    assert.ok(rgb, `opaque RGB color required: ${color}`);
    const linear = rgb
      .slice(1)
      .map(Number)
      .map((value) => {
        const channel = value / 255;
        return channel <= 0.04045
          ? channel / 12.92
          : ((channel + 0.055) / 1.055) ** 2.4;
      });
    return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
  };
  const a = luminance(foreground),
    b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
async function viewerReady(page) {
  await page.waitForFunction(
    () =>
      document.querySelector("#viewport canvas") &&
      document.querySelector("#viewer-status")?.textContent === "",
    null,
    { timeout: 60000 },
  );
}
async function menu(page) {
  await page.locator("#menu-trigger").click();
  await page.locator("#mobile-menu").waitFor({ state: "visible" });
}
async function closeDialogAtPositions(page, selector, closeSelector, open) {
  for (const fraction of [0, 0.5, 1]) {
    await open();
    const dialog = page.locator(selector),
      before = await page.locator("#gallery-page").boundingBox();
    await dialog.evaluate((el, fraction) => {
      el.scrollTop = (el.scrollHeight - el.clientHeight) * fraction;
    }, fraction);
    const close = page.locator(closeSelector);
    const closeBounds = await close.boundingBox(),
      dialogBounds = await dialog.boundingBox();
    assert.ok(
      closeBounds.y >= dialogBounds.y &&
        closeBounds.y + closeBounds.height <=
          dialogBounds.y + dialogBounds.height,
      `close remains inside ${selector} at scroll fraction ${fraction}`,
    );
    assert.equal(await close.isVisible(), true);
    await close.click();
    await page.waitForFunction(
      (selector) => !document.querySelector(selector).open,
      selector,
    );
    const after = await page.locator("#gallery-page").boundingBox();
    if (before && after)
      assert.ok(
        Math.abs(before.width - after.width) < 1,
        "modal must not resize background",
      );
  }
}
async function buildVariant(label, root) {
  await fs.cp(buildRoot, root, { recursive: true });
  const html = path.join(root, "index.html");
  await fs.writeFile(
    html,
    (await fs.readFile(html, "utf8")).replace(
      "</head>",
      `<meta name="standard-test-build" content="${label}"></head>`,
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
      .slice(0, 16),
    pack = JSON.parse(
      await fs.readFile(path.join(root, "game-pack.json"), "utf8"),
    );
  pack.build = build;
  const shell = files.filter(
      (f) =>
        f.url === "index.html" || /\.(js|css|webmanifest|png|svg)$/.test(f.url),
    ),
    template = await fs.readFile(
      process.env.TEST_SW_TEMPLATE || "src/pwa/sw-template.js",
      "utf8",
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
  return { root, build };
}
try {
  await run(
    "seven viewports keep readable text entry, safe chrome and lightweight indexes",
    async (page) => {
      const glbs = [],
        violations = [];
      page.on("request", (r) => {
        if (new URL(r.url()).pathname.endsWith(".glb")) glbs.push(r.url());
      });
      await page.addInitScript(() => {
        window.standardCsp = [];
        document.addEventListener("securitypolicyviolation", (e) =>
          window.standardCsp.push({
            directive: e.violatedDirective,
            blocked: e.blockedURI,
          }),
        );
      });
      for (const [width, height] of sizes) {
        await page.setViewportSize({ width, height });
        for (const [route, input, count] of [
          ["", "#model-search", expectedAssetCount],
          ["?page=demos", "#demo-search", expectedDemoCount],
        ]) {
          await page.goto(server.url + route);
          await safeInsets(page);
          await noOverflow(page);
          assert.ok(
            parseFloat(
              await page
                .locator(input)
                .evaluate((el) => getComputedStyle(el).fontSize),
            ) >= (width <= 900 ? 16 : 14),
            "mobile text entry at least16px",
          );
          assert.equal(
            await page.locator(route ? ".demo-card" : ".asset-card").count(),
            count,
          );
          if (route) {
            const expected = [["game", "?page=game"], ["solar-system", "?page=solar"], ["product-studio", "?page=product-studio"]];
            assert.deepEqual((await page.locator(".demo-card").evaluateAll(cards => cards.map(c => c.dataset.demoId))).sort(), expected.map(([id]) => id).sort());
            for (const [id, target] of expected) {
              const card = page.locator(`.demo-card[data-demo-id="${id}"]`);
              assert.equal(await card.count(), 1);
              assert.equal(await card.locator("h2 a").getAttribute("href"), target);
            }
          }
          assert.equal(await page.locator("canvas").count(), 0);
          const h = await page.locator(".header").boundingBox();
          assert.ok(h.y >= insets.top - 1, "header below top inset");
          assert.ok(
            h.x >= insets.left - 1 && h.x + h.width <= width - insets.right + 1,
            "header within side insets",
          );
          assert.equal(
            await page
              .locator("meta[name=theme-color]")
              .getAttribute("content"),
            "#111513",
          );
          assert.notEqual(
            await page
              .locator(".header")
              .evaluate((el) => getComputedStyle(el).backgroundColor),
            "rgba(0, 0, 0, 0)",
          );
          await page.screenshot({
            path: path.join(
              artifacts,
              `${route ? "demos" : "models"}-${width}-safe.png`,
            ),
          });
          violations.push(...(await page.evaluate(() => window.standardCsp)));
        }
      }
      assert.deepEqual(glbs, []);
      assert.deepEqual(violations, [], "normal index requests satisfy CSP");
    },
  );
  await run(
    "menu and model dialogs respect four-edge insets and reliable close paths",
    async (page) => {
      await page.goto(server.url);
      await safeInsets(page);
      const viewport = page.viewportSize();
      await menu(page);
      await safeRect(page.locator("#mobile-menu"), viewport, "mobile menu");
      await page.keyboard.press("Escape");
      await page.waitForFunction(
        () => !document.querySelector("#mobile-menu").open,
      );
      assert.equal(
        await page
          .locator("#menu-trigger")
          .evaluate((el) => el === document.activeElement),
        true,
      );
      await closeDialogAtPositions(page, "#mobile-menu", "#close-menu", () =>
        menu(page),
      );
      await menu(page);
      await page.mouse.click(1, 1);
      await page.waitForFunction(
        () => !document.querySelector("#mobile-menu").open,
      );
      const open = async () => {
        await page.locator("[data-asset-id=pool-table]").first().click();
        await viewerReady(page);
      };
      await open();
      await safeRect(page.locator("#viewer"), viewport, "model dialog");
      if (await page.locator("#fullscreen-view").isVisible()) {
        await page.locator("#fullscreen-view").click();
        await page.waitForFunction(() => !!document.fullscreenElement);
        await safeRect(
          page.locator("#viewport canvas"),
          viewport,
          "fullscreen canvas",
        );
        await page.evaluate(() => document.exitFullscreen());
      }
      await page.keyboard.press("Escape");
      await page.waitForFunction(() => !document.querySelector("#viewer").open);
      assert.equal(
        await page
          .locator("[data-asset-id=pool-table]")
          .first()
          .evaluate((el) => el === document.activeElement),
        true,
      );
      await closeDialogAtPositions(page, "#viewer", "#close-viewer", open);
      await open();
      await page.mouse.click(1, 1);
      await page.waitForFunction(() => !document.querySelector("#viewer").open);
      await noOverflow(page);
    },
  );
  await run(
    "contextual scroll-to-top is safe, keyboard accessible and hidden on interactive or modal pages",
    async (page) => {
      await page.goto(server.url);
      await safeInsets(page);
      const top = page.locator("#scroll-to-top");
      assert.equal(await top.isVisible(), false);
      await page.evaluate(() =>
        window.scrollTo({ top: innerHeight * 2, behavior: "instant" }),
      );
      await top.waitFor({ state: "visible" });
      await safeRect(top, page.viewportSize(), "scroll-to-top");
      await top.focus();
      await page.keyboard.press("Enter");
      await page.waitForFunction(() => scrollY < 2);
      await top.waitFor({ state: "hidden" });
      assert.equal(await top.isVisible(), false);
      assert.ok(
        await page.evaluate(() => document.activeElement !== document.body),
        "keyboard top leaves useful focus",
      );
      await page.evaluate(() =>
        window.scrollTo({ top: innerHeight * 2, behavior: "instant" }),
      );
      await top.waitFor({ state: "visible" });
      await menu(page);
      await top.waitFor({ state: "hidden" });
      assert.equal(await top.isVisible(), false);
      await page.keyboard.press("Escape");
      await page.goto(server.url + "?model=pool-table");
      await viewerReady(page);
      assert.equal(await top.isVisible(), false);
      for (const route of ["game", "solar"]) {
        await page.goto(server.url + "?page=" + route);
        await page.evaluate(() =>
          window.scrollTo({ top: 10000, behavior: "instant" }),
        );
        assert.equal(await top.isVisible(), false);
      }
    },
    { reducedMotion: "reduce" },
  );
  await run(
    "manifest identity and declared PNG dimensions remain intact",
    async (page) => {
      const manifest = JSON.parse(
        await fs.readFile("public/manifest.webmanifest", "utf8"),
      );
      assert.equal(manifest.id, "./");
      assert.equal(manifest.scope, "./");
      assert.equal(manifest.start_url, "./?page=game");
      assert.equal(manifest.display, "standalone");
      assert.equal(manifest.theme_color, "#111513");
      assert.equal(manifest.background_color, "#111513");
      assert.ok(
        manifest.icons.some((icon) =>
          icon.purpose?.split(" ").includes("maskable"),
        ),
      );
      for (const icon of manifest.icons) {
        const bytes = await fs.readFile(path.join("public", icon.src));
        assert.equal(bytes.subarray(1, 4).toString(), "PNG");
        assert.equal(
          `${bytes.readUInt32BE(16)}x${bytes.readUInt32BE(20)}`,
          icon.sizes,
        );
      }
      await page.goto(server.url);
      assert.match(
        await page.locator("meta[name=viewport]").getAttribute("content"),
        /viewport-fit=cover/,
      );
      assert.equal(
        await page
          .locator("meta[name=apple-mobile-web-app-capable]")
          .getAttribute("content"),
        "yes",
      );
    },
  );
  await run(
    "production CSP permits actual GLB textures and rejects an untrusted resource",
    async (page) => {
      await page.addInitScript(() => {
        window.standardCsp = [];
        document.addEventListener("securitypolicyviolation", (e) =>
          window.standardCsp.push({
            directive: e.violatedDirective,
            blocked: e.blockedURI,
          }),
        );
      });
      await page.goto(server.url + "?model=solar-earth");
      await viewerReady(page);
      const policy = await page
        .locator('meta[http-equiv="Content-Security-Policy"]')
        .getAttribute("content");
      assert.ok(policy);
      assert.doesNotMatch(policy, /unsafe-inline|unsafe-eval|\*/);
      assert.deepEqual(
        await page.evaluate(() => window.standardCsp),
        [],
        "normal embedded textures satisfy CSP",
      );
      await page.evaluate(() => {
        const img = document.createElement("img");
        img.src = "https://blocked-resource.invalid/pwa-standard.png";
        document.body.append(img);
      });
      await page.waitForFunction(() =>
        window.standardCsp.some((e) =>
          e.blocked.startsWith("https://blocked-resource.invalid"),
        ),
      );
      assert.ok(
        (await page.evaluate(() => window.standardCsp)).every((e) =>
          e.blocked.startsWith("https://blocked-resource.invalid"),
        ),
        "only deliberate CSP probe blocked",
      );
    },
  );
  await run(
    "offline Demo status follows a genuinely prepared Game pack",
    async (page, context) => {
      await page.addInitScript(() => {
        window.standardPwaStates = [];
        window.addEventListener("pwa-state-change", (event) =>
          window.standardPwaStates.push({
            state: event.detail,
            frozen: Object.isFrozen(event.detail),
          }),
        );
      });
      await page.goto(server.url + "?page=demos");
      await page.evaluate(() => navigator.serviceWorker.ready);
      await page.reload();
      await page.waitForFunction(() => navigator.serviceWorker.controller);
      const game = page.locator(".demo-card[data-demo-id=game]"),
        solar = page.locator(".demo-card[data-demo-id=solar-system]");
      await page.waitForFunction(() =>
        document
          .querySelector(".demo-card[data-demo-id=game] .demo-offline-status")
          ?.textContent.match(
            /not.*saved|not.*prepared|not ready|prepare.*offline/i,
          ),
      );
      assert.match(
        await solar.locator(".demo-offline-status").innerText(),
        /online/i,
      );
      await gameReady(page, server.url);
      await page.locator("[data-action=options]").click();
      await page.locator("[data-action=offline]").click();
      await page.waitForFunction(
        () =>
          document
            .querySelector("#game-offline-status")
            ?.textContent.includes("Offline ready"),
        null,
        { timeout: 120000 },
      );
      await page.locator("[data-action=close-options]").click();
      await page.locator("#demo-breadcrumb a").click();
      await page.waitForFunction(() =>
        document
          .querySelector(".demo-card[data-demo-id=game] .demo-offline-status")
          ?.textContent.match(/offline ready|available offline/i),
      );
      await context.setOffline(true);
      await page.waitForFunction(() =>
        window.standardPwaStates.some(
          (item) => item.state.connectivity === "offline",
        ),
      );
      assert.ok(
        await page.evaluate(() =>
          window.standardPwaStates.every((item) => item.frozen),
        ),
        "runtime publishes immutable status snapshots",
      );
      await page.reload();
      await page.waitForFunction(() =>
        document
          .querySelector(".demo-card[data-demo-id=game] .demo-offline-status")
          ?.textContent.match(/offline ready|available offline/i),
      );
      assert.match(
        await game.locator(".demo-offline-status").innerText(),
        /offline ready|available offline/i,
      );
      assert.match(
        await solar.locator(".demo-offline-status").innerText(),
        /online|required|unavailable/i,
      );
    },
    { serviceWorkers: "allow" },
  );
  await run(
    "install help has safe bounds and restores actual trigger focus",
    async (page) => {
      await gameReady(page, server.url);
      await safeInsets(page);
      await page.locator("[data-action=options]").click();
      await page.locator("[data-action=install]").click();
      const help = page.locator(".pwa-help");
      await help.waitFor({ state: "visible" });
      await safeRect(help, page.viewportSize(), "install help");
      const helpButtonColors = await help.getByRole("button").evaluate((el) => {
        const style = getComputedStyle(el);
        return { foreground: style.color, background: style.backgroundColor };
      });
      assert.ok(
        contrastRatio(
          helpButtonColors.foreground,
          helpButtonColors.background,
        ) >= 4.5,
        `install-help action contrast: ${JSON.stringify(helpButtonColors)}`,
      );
      await page.screenshot({
        path: path.join(artifacts, "install-help-safe.png"),
      });
      await help.getByRole("button").click();
      await page.waitForFunction(
        () => !document.querySelector(".pwa-help").open,
      );
      assert.equal(
        await page
          .locator("[data-action=install]")
          .evaluate((el) => el === document.activeElement),
        true,
      );
      await page.locator("[data-action=install]").click();
      await page.keyboard.press("Escape");
      await page.waitForFunction(
        () => !document.querySelector(".pwa-help").open,
      );
      await page.locator("[data-action=install]").click();
      await page.mouse.click(1, 1);
      await page.waitForFunction(
        () => !document.querySelector(".pwa-help").open,
      );
    },
  );
  await run(
    "real waiting worker displays safe modal loader only after explicit Update",
    async (page) => {
      const temp = await fs.mkdtemp(
          path.join(os.tmpdir(), "b3g-standard-update-"),
        ),
        a = await buildVariant("standard-A", path.join(temp, "A")),
        b = await buildVariant("standard-B", path.join(temp, "B")),
        updates = await serveBuild(a.root);
      try {
        await page.goto(updates.url);
        await page.evaluate(() => navigator.serviceWorker.ready);
        await page.reload();
        await page.waitForFunction(() => navigator.serviceWorker.controller);
        await safeInsets(page);
        updates.setRoot(b.root);
        await page.evaluate(async () => {
          const r = await navigator.serviceWorker.getRegistration();
          await r.update();
        });
        const notice = page.locator(".pwa-notice");
        await notice.waitFor({ state: "visible" });
        assert.equal(
          await page
            .locator("meta[name=standard-test-build]")
            .getAttribute("content"),
          "standard-A",
          "update discovery must not reload",
        );
        await safeRect(notice, page.viewportSize(), "update notice");
        await notice.getByRole("button", { name: /update now/i }).click();
        const loader = page.locator("#pwa-update-dialog");
        await loader.waitFor({ state: "visible" });
        await safeRect(loader, page.viewportSize(), "update loader");
        await page.screenshot({
          path: path.join(artifacts, "update-loader-safe.png"),
        });
        await page.waitForFunction(
          () =>
            document.querySelector("meta[name=standard-test-build]")
              ?.content === "standard-B",
          null,
          { timeout: 30000 },
        );
        assert.equal(
          await page.locator("#pwa-update-dialog").evaluate((el) => el.open),
          false,
        );
      } finally {
        await updates.close();
        await fs.rm(temp, { recursive: true, force: true });
      }
    },
    { serviceWorkers: "allow" },
  );
  await run(
    "Vite development serves real styles and its HMR client without production CSP",
    async (page) => {
      const { createServer } = await import("vite"),
        dev = await createServer({ server: { host: "127.0.0.1", port: 0 } });
      await dev.listen();
      try {
        const port = dev.httpServer.address().port,
          errors = [],
          clients = [];
        page.on("console", (m) => {
          if (m.type() === "error") errors.push(m.text());
        });
        page.on("response", (r) => {
          if (r.url().includes("/@vite/client")) clients.push(r.status());
        });
        await page.goto(`http://127.0.0.1:${port}/`);
        await page.waitForFunction(() =>
          [...document.querySelectorAll("style")].some((s) =>
            s.textContent.includes(".header"),
          ),
        );
        assert.equal(
          await page.locator("meta[data-production-csp]").count(),
          0,
        );
        assert.equal(
          await page
            .locator("body")
            .evaluate((el) => getComputedStyle(el).backgroundColor),
          "rgb(17, 21, 19)",
        );
        assert.ok(clients.includes(200), "actual Vite HMR client delivered");
        assert.deepEqual(errors, []);
      } finally {
        await dev.close();
      }
    },
  );
  assert.deepEqual(pageErrors, []);
} finally {
  await fs.writeFile(
    path.join(artifacts, "results.json"),
    JSON.stringify(
      {
        results,
        pageErrors,
        environment: {
          node: process.version,
          browser: "Chromium",
          surface: "macOS headless SwiftShader",
          network: "localhost unthrottled",
          safeInsets: insets,
        },
        limits: {
          physicalIosInstall: "UNVERIFIED",
          physicalAndroidInstall: "UNVERIFIED",
          physicalStatusBar: "UNVERIFIED",
          physicalKeyboardZoom: "UNVERIFIED",
          realBrowserZoom: "UNVERIFIED",
          maskable:
            "Central logo visually inside safe zone; PNG dimensions and purpose checked; platform masking UNVERIFIED",
        },
      },
      null,
      2,
    ),
  );
  await browser.close();
  await server.close();
}
