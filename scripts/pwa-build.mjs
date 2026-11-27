import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { GAME_ASSET_IDS } from "../src/game/assets.js";
import { RULES_VERSION } from "../src/game/rules.js";
import { TABLE } from "../src/game/table.js";
import { loadCatalog } from "./catalog.mjs";
const hash = (b) => crypto.createHash("sha256").update(b).digest("hex");
// Code, styles and install icons only. Content images under assets/ (posters, demo
// textures) are fetched on demand: precaching them delayed install and competed
// with the visible thumbnails.
export function isShellEntry(url) {
  if (url === "index.html" || /\.(js|css|webmanifest|svg)$/.test(url)) return true;
  return url.endsWith(".png") && !url.startsWith("assets/");
}
export function pwaBuildPlugin(version) {
  return {
    name: "gallery-pwa-build",
    apply: "build",
    closeBundle() {
      const root = path.resolve("dist");
      const walk = (dir) =>
        fs
          .readdirSync(dir, { withFileTypes: true })
          .flatMap((e) =>
            e.isDirectory()
              ? walk(path.join(dir, e.name))
              : [path.join(dir, e.name)],
          );
      const files = walk(root)
        .filter(
          (p) =>
            !["sw.js", "build-info.json", "game-pack.json"].includes(
              path.basename(p),
            ),
        )
        .map((p) => ({
          url: path.relative(root, p).split(path.sep).join("/"),
          sha256: hash(fs.readFileSync(p)),
          bytes: fs.statSync(p).size,
        }));
      const template = fs.readFileSync("src/pwa/sw-template.js", "utf8");
      const catalog = loadCatalog().collections.flatMap((c) => c.assets);
      const required = GAME_ASSET_IDS.map((id) => {
        const a = catalog.find((a) => a.id === id);
        if (!a) throw new Error("Missing game asset " + id);
        const digest = hash(fs.readFileSync(a.file));
        const file = files.find(
          (f) => f.sha256 === digest && f.url.endsWith(".glb"),
        );
        if (!file) throw new Error("Game asset not emitted: " + id);
        return { ...file, id };
      });
      if (!required.length) throw new Error("Game pack has no assets");
      const offlineGame = {
        version: [RULES_VERSION, TABLE.version].join("/"),
        files: required,
      };
      const shell = files.filter((f) => isShellEntry(f.url));
      // The selection is part of the identity: a rule change must not reuse a shell cache name.
      const build = hash(
        JSON.stringify({ files, shell: shell.map((f) => f.url), offlineGame }) +
          template + (process.env.B3G_TEST_BUILD || ""),
      ).slice(0, 16);
      const pack = { build, ...offlineGame };
      fs.writeFileSync(
        path.join(root, "build-info.json"),
        JSON.stringify({ build, version }),
      );
      fs.writeFileSync(path.join(root, "game-pack.json"), JSON.stringify(pack));
      fs.writeFileSync(
        path.join(root, "sw.js"),
        template
          .replace("__BUILD__", JSON.stringify(build))
          .replace("__SHELL__", JSON.stringify(shell))
          .replace("__PACK__", JSON.stringify(pack)),
      );
    },
  };
}
