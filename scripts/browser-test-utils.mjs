import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";

export async function serveBuild(initialRoot = "dist") {
  let root = path.resolve(initialRoot),
    fault = null;
  const base = "/Blender-3D-Gallery/";
  const types = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".glb": "model/gltf-binary",
  };
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    const relative =
      decodeURIComponent(url.pathname.slice(base.length)) || "index.html";
    const file = path.resolve(root, relative);
    if (!url.pathname.startsWith(base) || !file.startsWith(root + path.sep)) {
      res.writeHead(404);
      res.end();
      return;
    }
    try {
      let bytes = await fs.readFile(file);
      const result = fault?.({ relative, url, bytes });
      if (result?.status) {
        res.writeHead(result.status);
        res.end("Injected test failure");
        return;
      }
      if (result?.bytes) bytes = result.bytes;
      res.writeHead(200, {
        "Content-Type": types[path.extname(file)] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      res.end(bytes);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    url: `http://127.0.0.1:${server.address().port}${base}`,
    setRoot: (value) => {
      root = path.resolve(value);
    },
    setFault: (value) => {
      fault = value;
    },
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}
export const launchOptions = {
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
};
export async function gameReady(page, url) {
  await page.goto(url + "?page=game");
  await page.waitForFunction(
    () =>
      window.render_game_to_text &&
      JSON.parse(window.render_game_to_text()).ready,
    {},
    { timeout: 60000 },
  );
}
export const readGame = (page) =>
  page.evaluate(() => JSON.parse(window.render_game_to_text()));
export async function writeCheckpoint(page, checkpoint) {
  await page.evaluate(
    (checkpoint) =>
      new Promise((resolve, reject) => {
        const r = indexedDB.open("blender-gallery-game-v1", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("records");
        r.onerror = () => reject(r.error);
        r.onsuccess = () => {
          const db = r.result,
            tx = db.transaction("records", "readwrite");
          tx.objectStore("records").put(
            { checkpoint, pending: null, savedAt: Date.now() },
            "match",
          );
          tx.oncomplete = () => {
            db.close();
            resolve();
          };
          tx.onerror = () => reject(tx.error);
        };
      }),
    checkpoint,
  );
}

// Configure the next real test gesture; this never writes application state.
const pullRatios = new WeakMap();
export function setPullRatio(page, ratio) {
  pullRatios.set(page, ratio);
}
export async function chargePull(page, ratio = pullRatios.get(page) ?? 0.45) {
  const handle = page.locator("#power-handle");
  await handle.scrollIntoViewIfNeeded();
  const box = await handle.boundingBox();
  if (!box) throw new Error("Power handle is not visible");
  const distance = await page
    .locator("#power-track")
    .evaluate(
      (track) =>
        track.clientHeight -
        document.querySelector("#power-handle").offsetHeight,
    );
  if (!(distance > 0)) throw new Error("Power track has no travel");
  const x = box.x + box.width / 2,
    y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x, y + distance * ratio, { steps: 5 });
  return { x, y, distance };
}
export async function releasePull(page) {
  await page.mouse.up();
}
export async function pullShot(page, ratio = pullRatios.get(page) ?? 0.45) {
  await chargePull(page, ratio);
  await releasePull(page);
}
