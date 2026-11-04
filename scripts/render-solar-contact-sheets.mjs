import fs from "node:fs";
import { createServer } from "vite";
import { chromium } from "playwright";
import { loadCatalog } from "./catalog.mjs";
const ids = loadCatalog()
  .collections.find((c) => c.id === "solar-system")
  .assets.map((a) => a.solarId);
const server = await createServer({
  server: { host: "127.0.0.1", port: 0 },
  logLevel: "error",
});
await server.listen();
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: 1280, height: Math.ceil(ids.length / 5) * 280 },
  });
  const base = server.resolvedUrls.local[0];
  for (const [name, suffix] of [
    ["blender", ""],
    ["three", "-three"],
    ["reverse", "-reverse-three"],
  ]) {
    await page.setContent(
      `<body style="margin:0;background:#20252a;display:grid;grid-template-columns:repeat(5,1fr);color:white;font:16px system-ui">${ids.map((id) => `<div><img style="width:256px" alt="${id}" src="${base}models/solar-system/previews/${id}${suffix}.png"><div style="text-align:center">${id}</div></div>`).join("")}</body>`,
    );
    await page
      .locator("img")
      .evaluateAll((images) =>
        Promise.all(images.map((image) => image.decode())),
      );
    await page.screenshot({
      path: `models/solar-system/reports/${name}-contact-sheet.png`,
      fullPage: true,
    });
  }
} finally {
  await browser.close();
  await server.close();
}
