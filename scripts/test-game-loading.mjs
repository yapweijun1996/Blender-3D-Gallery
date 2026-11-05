import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";
import { launchOptions, serveBuild } from "./browser-test-utils.mjs";

const tablePattern = /\/table-[^/]+\.glb(?:\?.*)?$/;
const waitReady = (page) =>
  page.waitForFunction(
    () =>
      window.render_game_to_text &&
      JSON.parse(window.render_game_to_text()).ready,
    null,
    { timeout: 60000 },
  );
const waitRecovery = (page) =>
  page.waitForSelector("#game-load-error:visible", { timeout: 15000 });

export async function abortedAssetRecovers(page, _context, url) {
  await page.route(tablePattern, (route) => route.abort("failed"));
  await page.goto(`${url}?page=game`);
  await waitRecovery(page);
  assert.equal(
    await page.locator('[data-action="retry-load"]').isEnabled(),
    true,
  );
  assert.equal(
    await page.locator('[data-action="new"]').first().isDisabled(),
    true,
  );
  await page.unroute(tablePattern);
  await page.locator('[data-action="retry-load"]').click();
  await waitReady(page);
  assert.equal(await page.locator("#game-page canvas").count(), 1);
}

export async function truncatedAssetRecovers(page, _context, url) {
  await page.route(tablePattern, async (route) => {
    const response = await route.fetch();
    const bytes = await response.body();
    assert.ok(bytes.length > 100);
    await route.fulfill({
      status: 200,
      contentType: "model/gltf-binary",
      body: bytes.subarray(0, Math.floor(bytes.length / 2)),
    });
  });
  await page.goto(`${url}?page=game`);
  await waitRecovery(page);
  assert.equal(
    await page.locator('[data-action="retry-load"]').isEnabled(),
    true,
  );
  await page.unroute(tablePattern);
  await page.locator('[data-action="retry-load"]').click();
  await waitReady(page);
  assert.equal(await page.locator("#game-page canvas").count(), 1);
}

// glTF permits arbitrary JSON extras. Add valid metadata without touching the
// binary chunk so a stricter loader cannot reject an otherwise valid GLB.
function addGlbExtras(original) {
  assert.equal(original.toString("ascii", 0, 4), "glTF");
  const oldJsonLength = original.readUInt32LE(12);
  assert.equal(original.toString("ascii", 16, 20), "JSON");
  const json = JSON.parse(
    original.subarray(20, 20 + oldJsonLength).toString("utf8"),
  );
  json.asset.extras = { audit: { note: "Valid extra metadata", version: 1 } };
  const content = Buffer.from(JSON.stringify(json), "utf8");
  const paddedLength = Math.ceil(content.length / 4) * 4;
  const padded = Buffer.alloc(paddedLength, 0x20);
  content.copy(padded);
  const rest = original.subarray(20 + oldJsonLength);
  const header = Buffer.from(original.subarray(0, 20));
  header.writeUInt32LE(20 + padded.length + rest.length, 8);
  header.writeUInt32LE(padded.length, 12);
  return Buffer.concat([header, padded, rest]);
}

export async function validExtraMetadataLoads(page, _context, url) {
  let served = 0;
  await page.route(tablePattern, async (route) => {
    const response = await route.fetch();
    const bytes = addGlbExtras(await response.body());
    served++;
    await route.fulfill({
      status: 200,
      contentType: "model/gltf-binary",
      body: bytes,
    });
  });
  await page.goto(`${url}?page=game`);
  await waitReady(page);
  assert.equal(served, 1);
  assert.equal(
    await page.locator('[data-action="new"]').first().isEnabled(),
    true,
  );
  assert.equal(await page.locator("#game-page canvas").count(), 1);
}

export async function leavingLoadingCancelsRequests(page, context, url) {
  await context.addInitScript(() => {
    const originalFetch = window.fetch;
    window.__gameGlbSignals = { started: [], aborted: [] };
    window.fetch = function (input, init) {
      const target = input instanceof Request ? input.url : String(input);
      const resolved = new URL(target, location.href);
      const signal =
        init?.signal || (input instanceof Request ? input.signal : null);
      if (resolved.pathname.endsWith(".glb")) {
        window.__gameGlbSignals.started.push(resolved.pathname);
        signal?.addEventListener(
          "abort",
          () => window.__gameGlbSignals.aborted.push(resolved.pathname),
          { once: true },
        );
      }
      return originalFetch.call(this, input, init);
    };
  });
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  const handler = async (route) => {
    await gate;
    await route.continue().catch(() => {});
  };
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("**/*.glb", handler);
  try {
    await page.goto(`${url}?page=game`);
    await page.waitForFunction(
      () => window.__gameGlbSignals.started.length >= 4,
      null,
      { timeout: 15000 },
    );
    const initial = await page.evaluate(() =>
      structuredClone(window.__gameGlbSignals),
    );
    assert.equal(
      initial.started.length,
      4,
      "Four initial workers are the existing concurrency limit",
    );
    await page.locator('.desktop-nav [data-page="gallery"]').click();
    await page.waitForFunction(
      () =>
        document.querySelector("#game-page").hidden &&
        !window.render_game_to_text,
    );
    const afterLeave = await page.evaluate(() =>
      structuredClone(window.__gameGlbSignals),
    );
    assert.deepEqual(
      [...afterLeave.aborted].sort(),
      [...initial.started].sort(),
      "Leaving must abort each in-flight game GLB request",
    );
    release();
    await page.waitForTimeout(500);
    const afterRelease = await page.evaluate(() =>
      structuredClone(window.__gameGlbSignals),
    );
    assert.equal(
      afterRelease.started.length,
      initial.started.length,
      "Disposed workers must not start queued GLBs",
    );
    assert.equal(await page.locator("#game-page canvas").count(), 0);
    assert.equal(
      await page.evaluate(() => typeof window.advanceTime),
      "undefined",
    );
    assert.deepEqual(pageErrors, []);
    await page.unroute("**/*.glb", handler);
    await page.locator('.desktop-nav [data-page="demos"]').click();
    await page
      .locator('#demos-page .demo-card a[data-page="game"]')
      .first()
      .click();
    await waitReady(page);
    assert.equal(await page.locator("#game-page canvas").count(), 1);
    assert.deepEqual(pageErrors, []);
  } finally {
    release();
    await page.unroute("**/*.glb", handler).catch(() => {});
  }
}

export async function leavingLoadingCancelsNetwork(page, context, url) {
  await page.goto(url);
  await page.locator('.desktop-nav [data-page="demos"]').click();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 300,
    downloadThroughput: 500000,
    uploadThroughput: 125000,
    connectionType: "cellular4g",
  });
  const pack = JSON.parse(
    await fs.readFile(
      path.join(process.env.TEST_BUILD_DIR || "dist", "game-pack.json"),
      "utf8",
    ),
  );
  const expectedSizes = new Map(
    pack.files.map((entry) => [new URL(entry.url, url).pathname, entry.bytes]),
  );
  const network = new Map(),
    partialAborts = [];
  const pending = new Set(),
    started = [],
    failures = [];
  let resolveFour,
    resolveFailure,
    leaving = false,
    inFlight,
    inFlightPaths;
  const fourStarted = new Promise((resolve) => {
    resolveFour = resolve;
  });
  const aborted = new Promise((resolve) => {
    resolveFailure = resolve;
  });
  const maybeResolve = () => {
    if (
      failures.some(
        (failure) =>
          failure.error.includes("ERR_ABORTED") &&
          partialAborts.some((entry) => entry.path === failure.path),
      )
    )
      resolveFailure();
  };
  cdp.on("Network.requestWillBeSent", (event) => {
    const pathname = new URL(event.request.url).pathname;
    if (expectedSizes.has(pathname))
      network.set(event.requestId, {
        path: pathname,
        received: 0,
        expected: expectedSizes.get(pathname),
      });
  });
  cdp.on("Network.dataReceived", (event) => {
    const entry = network.get(event.requestId);
    if (entry) entry.received += event.dataLength;
  });
  cdp.on("Network.loadingFailed", (event) => {
    const entry = network.get(event.requestId);
    if (
      leaving &&
      entry &&
      inFlightPaths?.has(entry.path) &&
      event.errorText === "net::ERR_ABORTED" &&
      entry.received < entry.expected
    ) {
      partialAborts.push({ ...entry, requestId: event.requestId });
      maybeResolve();
    }
  });
  const isGlb = (request) => new URL(request.url()).pathname.endsWith(".glb");
  page.on("request", (request) => {
    if (!isGlb(request)) return;
    started.push(request);
    pending.add(request);
    if (started.length === 4) resolveFour();
  });
  page.on("requestfinished", (request) => pending.delete(request));
  page.on("requestfailed", (request) => {
    pending.delete(request);
    if (leaving && inFlight?.has(request)) {
      const error = request.failure()?.errorText || "";
      failures.push({ path: new URL(request.url()).pathname, error });
      maybeResolve();
    }
  });
  const deadline = async (promise, name) => {
    let timer;
    try {
      return await Promise.race([
        promise,
        new Promise((_, reject) => {
          timer = setTimeout(
            () => reject(new Error(`Timed out: ${name}`)),
            15000,
          );
        }),
      ]);
    } finally {
      clearTimeout(timer);
    }
  };
  await page
    .locator('#demos-page .demo-card a[data-page="game"]')
    .first()
    .click();
  await deadline(fourStarted, "initial GLB requests");
  inFlight = new Set(pending);
  inFlightPaths = new Set(
    [...inFlight].map((request) => new URL(request.url()).pathname),
  );
  assert.ok(
    inFlight.size > 0,
    "At least one passthrough GLB request must still be in flight",
  );
  leaving = true;
  await page.locator('.desktop-nav [data-page="gallery"]').click();
  await page.waitForFunction(
    () =>
      document.querySelector("#game-page").hidden &&
      !window.render_game_to_text,
  );
  const countAfterLeave = started.length;
  try {
    await deadline(
      aborted,
      "a partially received in-flight GLB to report ERR_ABORTED",
    );
  } finally {
    console.log(
      "NETWORK_EVIDENCE",
      JSON.stringify({
        profile: "300 ms latency, 4 Mbps down, 1 Mbps up; cache disabled",
        inFlightPaths: [...inFlightPaths],
        countAfterLeave,
        countAtEvidence: started.length,
        requests: [...network.entries()].map(([requestId, entry]) => ({
          requestId,
          ...entry,
        })),
        partialAborts,
        failures,
      }),
    );
  }
  await page.waitForTimeout(250);
  assert.ok(
    failures.some(
      (failure) =>
        failure.error.includes("ERR_ABORTED") &&
        partialAborts.some((entry) => entry.path === failure.path),
    ),
  );
  assert.equal(
    started.length,
    countAfterLeave,
    "No queued GLB may start after leaving",
  );
  assert.equal(await page.locator("#game-page canvas").count(), 0);
  console.log(
    `PASS observed passthrough network cancellation (${partialAborts.length} incomplete GLB responses)`,
  );
}

const cases = [
  ["aborted GLB offers retry", abortedAssetRecovers],
  ["truncated GLB offers retry", truncatedAssetRecovers],
  ["valid extra GLB metadata loads", validExtraMetadataLoads],
  [
    "leaving a loading game aborts in-flight GLBs",
    leavingLoadingCancelsRequests,
  ],
  [
    "leaving a loading game cancels passthrough network",
    leavingLoadingCancelsNetwork,
  ],
];

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  const selectedCases = cases.filter(
    ([name]) =>
      !process.env.GAME_LOADING_TEST ||
      name.includes(process.env.GAME_LOADING_TEST),
  );
  if (!selectedCases.length)
    throw new Error("GAME_LOADING_TEST did not match a loading test");
  const server = await serveBuild(process.env.TEST_BUILD_DIR || "dist");
  const browser = await chromium.launch(launchOptions);
  try {
    for (const [name, test] of selectedCases) {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 900 },
        serviceWorkers: "block",
      });
      const page = await context.newPage();
      try {
        await test(page, context, server.url);
        console.log(`PASS ${name}`);
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
    await server.close();
  }
}
