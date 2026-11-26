import { resolve } from "node:path";
import { defineConfig } from "vite";
import { loadCatalog } from "./scripts/catalog.mjs";
import { loadDemos } from "./scripts/demo-registry.mjs";
import { pwaBuildPlugin } from "./scripts/pwa-build.mjs";
import { i18nBuildPlugin } from "./scripts/i18n-build.mjs";
import { paletteBuildPlugin } from "./scripts/palette-build.mjs";
import { christmasCardBuild } from "./scripts/christmas-card-build.mjs";
import packageInfo from "./package.json" with { type: "json" };

const { version } = packageInfo;
const virtualId = "virtual:gallery-catalog";
const demosId = "virtual:gallery-demos";
export default defineConfig({
  base: "./",
  define: { __APP_VERSION__: JSON.stringify(version) },
  build: { assetsInlineLimit: 0, rollupOptions: { input: { gallery: resolve("index.html"), christmasCard: resolve("christmas-card/index.html") } } },
  plugins: [
    pwaBuildPlugin(version),
    christmasCardBuild(),
    paletteBuildPlugin(),
    i18nBuildPlugin(),
    {
      name: "development-csp-exception",
      apply: "serve",
      transformIndexHtml(html, context) {
        // Vite's development CSS/HMR transport is not the production resource graph.
        return context.server
          ? html.replace(/<meta\b(?=[^>]*\bdata-production-csp\b)[^>]*>/g, "")
          : html;
      },
    },
    {
      name: "gallery-registries",
      resolveId(id) {
        return [virtualId, demosId].includes(id) ? "\0" + id : null;
      },
      load(id) {
        if (![virtualId, demosId].some((value) => id === "\0" + value))
          return null;
        const root = this.environment.config.root;
        const watch = file => this.addWatchFile(resolve(root, file));
        watch("models/catalog.json");
        const catalog = loadCatalog(root);
        const imports = [];
        let index = 0;
        const assetUrl = (file) => {
          const name = `asset${index++}`;
          imports.push(
            `import ${name} from ${JSON.stringify("/" + file + "?url")};`,
          );
          return `__GALLERY_URL_${name}__`;
        };
        let content;
        if (id === "\0" + demosId) {
          watch("data/demos.json");
          content = loadDemos(root, catalog);
          for (const demo of content) demo.thumbnail = assetUrl(demo.thumbnail);
        } else {
          content = catalog;
          for (const collection of catalog.collections)
            for (const asset of collection.assets) {
              // These details are embedded directly, so Vite cannot infer the JSON dependency.
              if (asset.metadata) watch(asset.metadata);
              asset.file = assetUrl(asset.file);
              asset.thumbnail = assetUrl(asset.thumbnail);
            }
        }
        const body = JSON.stringify(content).replace(
          /"__GALLERY_URL_(asset\d+)__"/g,
          "$1",
        );
        return `${imports.join("\n")}\nexport default ${body};`;
      },
    },
  ],
});
