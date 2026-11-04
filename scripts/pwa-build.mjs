import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { loadCatalog } from "./catalog.mjs";
const hash = (b) => crypto.createHash("sha256").update(b).digest("hex");
export function pwaBuildPlugin() {
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
      const build = hash(
        JSON.stringify(files) + template + (process.env.B3G_TEST_BUILD || ""),
      ).slice(0, 16);
      const ids = [
        "pool-table",
        "cue-stick-01",
        "cue-ball",
        ...Array.from(
          { length: 15 },
          (_, i) => `ball-${String(i + 1).padStart(2, "0")}`,
        ),
      ];
      const catalog = loadCatalog().collections.flatMap((c) => c.assets);
      const required = ids.map((id) => {
        const a = catalog.find((a) => a.id === id);
        if (!a) throw new Error("Missing game asset " + id);
        const digest = hash(fs.readFileSync(a.file));
        const file = files.find(
          (f) => f.sha256 === digest && f.url.endsWith(".glb"),
        );
        if (!file) throw new Error("Game asset not emitted: " + id);
        return { ...file, id };
      });
      const shell = files.filter(
        (f) =>
          f.url === "index.html" ||
          /\.(js|css|webmanifest|png|svg)$/.test(f.url),
      );
      const pack = {
        build,
        version: "casual-8ball-v1/billiards-2026-11-v1",
        files: required,
      };
      fs.writeFileSync(
        path.join(root, "build-info.json"),
        JSON.stringify({ build }),
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
