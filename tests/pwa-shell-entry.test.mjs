import test from "node:test";
import assert from "node:assert/strict";
import { isShellEntry } from "../scripts/pwa-build.mjs";

test("the shell keeps code, styles and install icons", () => {
  for (const url of ["index.html", "assets/gallery-a.js", "assets/gallery-a.css", "manifest.webmanifest",
    "icons/icon.svg", "icons/icon-192.png", "christmas-card/icons/icon-512.png"])
    assert.equal(isShellEntry(url), true, url);
});

test("content images and models are fetched on demand", () => {
  for (const url of ["assets/hero-a.png", "assets/happy-a.png", "assets/hero-a.webp", "assets/hero-a.jpg", "assets/model-a.glb"])
    assert.equal(isShellEntry(url), false, url);
});
