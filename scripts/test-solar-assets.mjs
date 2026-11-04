import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { createServer } from "vite";
import { chromium } from "playwright";
import validator from "gltf-validator";
import { launchOptions } from "./browser-test-utils.mjs";
const root = "models/solar-system",
  ids = process.argv.slice(2).length
    ? process.argv.slice(2)
    : fs
        .readdirSync(root + "/exports")
        .filter((x) => x.endsWith(".glb"))
        .map((x) => x.slice(0, -4));
const expected = [
  "sun",
  "mercury",
  "venus",
  "earth",
  "mars",
  "jupiter",
  "saturn",
  "uranus",
  "neptune",
  "moon",
  "pluto",
  "asteroid-01",
  "asteroid-02",
  "asteroid-03",
  "asteroid-04",
  "asteroid-05",
  "comet",
];
assert.ok(
  ids.length &&
    new Set(ids).size === ids.length &&
    ids.every((id) => expected.includes(id)),
);
if (!process.argv.slice(2).length)
  assert.deepEqual(new Set(ids), new Set(expected));
const visual = JSON.parse(
  fs.existsSync(root + "/reports/visual-review.json")
    ? fs.readFileSync(root + "/reports/visual-review.json", "utf8")
    : "{}",
);
const server = await createServer({
  server: { host: "127.0.0.1", port: 0 },
  logLevel: "error",
});
await server.listen();
const browser = await chromium.launch(launchOptions);
const page = await browser.newPage({ viewport: { width: 640, height: 640 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
const reports = [];
try {
  await page.goto(server.resolvedUrls.local[0] + "scripts/solar-review.html");
  await page.waitForFunction(() => window.solarReviewReady);
  for (const id of ids) {
    const file = `${root}/exports/${id}.glb`,
      b = fs.readFileSync(file);
    const header =
      b.toString("ascii", 0, 4) === "glTF" &&
      b.readUInt32LE(4) === 2 &&
      b.readUInt32LE(8) === b.length;
    const j = JSON.parse(b.subarray(20, 20 + b.readUInt32LE(12)));
    const embedded =
      !(j.images ?? []).some((i) => i.uri) &&
      !(j.buffers ?? []).some((i) => i.uri);
    const result = await validator.validateBytes(new Uint8Array(b), {
      uri: file,
      maxIssues: 100,
    });
    const metrics = await page.evaluate((id) => window.reviewAsset(id), id);
    await page.screenshot({ path: `${root}/previews/${id}-three.png` });
    await page.evaluate((id) => window.reviewAsset(id, 2.5), id);
    await page.screenshot({ path: `${root}/previews/${id}-reverse-three.png` });
    const statuses = {
      exists: "PASS",
      header: header ? "PASS" : "FAIL",
      khronos:
        result.issues.numErrors || result.issues.numWarnings ? "FAIL" : "PASS",
      embeddedTextures: embedded ? "PASS" : "FAIL",
      threeLoader: "PASS",
      geometry: metrics.allPass ? "PASS" : "FAIL",
      browserErrors: errors.length ? "FAIL" : "PASS",
      blenderPreview: fs.existsSync(`${root}/previews/${id}.png`)
        ? "PASS"
        : "FAIL",
      visualReview: "NOT TESTED",
      physicalMobileDevice: "NOT TESTED",
    };
    const report = {
      ...metrics,
      bytes: b.length,
      sha256: (await import("node:crypto"))
        .createHash("sha256")
        .update(b)
        .digest("hex"),
      statuses,
      khronos: result.issues,
      browserErrors: [...errors],
      testedAt: new Date().toISOString(),
      browser: await browser.version(),
    };
    reports.push(report);
    if (visual[id]?.sha256 === report.sha256)
      report.statuses.visualReview = "PASS";
    fs.writeFileSync(
      `${root}/reports/${id}.json`,
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(id, b.length, metrics.triangles, JSON.stringify(statuses));
    assert.ok(
      !Object.values(statuses).includes("FAIL"),
      id + " failed validation",
    );
  }
  fs.writeFileSync(
    `${root}/reports/validation.json`,
    JSON.stringify(reports, null, 2) + "\n",
  );
} finally {
  await browser.close();
  await server.close();
}
