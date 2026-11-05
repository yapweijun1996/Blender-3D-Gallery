import { defineConfig } from 'vite';
import { loadCatalog } from './scripts/catalog.mjs';
import { loadDemos } from './scripts/demo-registry.mjs';
import { pwaBuildPlugin } from './scripts/pwa-build.mjs';

const virtualId = 'virtual:gallery-catalog';
const demosId = 'virtual:gallery-demos';
export default defineConfig({
  base: './',
  build: { assetsInlineLimit: 0 },
  plugins: [pwaBuildPlugin(), {
    name: 'gallery-registries',
    resolveId(id) { return [virtualId, demosId].includes(id) ? '\0' + id : null; },
    load(id) {
      if (![virtualId, demosId].some(value => id === '\0' + value)) return null;
      const catalog = loadCatalog();
      const imports = [];
      let index = 0;
      const assetUrl = (file) => {
        const name = `asset${index++}`;
        imports.push(`import ${name} from ${JSON.stringify('/' + file + '?url')};`);
        return `__GALLERY_URL_${name}__`;
      };
      let content;
      if (id === '\0' + demosId) {
        content = loadDemos(process.cwd(), catalog);
        for (const demo of content) demo.thumbnail = assetUrl(demo.thumbnail);
      } else {
        content = catalog;
        for (const collection of catalog.collections) for (const asset of collection.assets) {
          asset.file = assetUrl(asset.file);
          asset.thumbnail = assetUrl(asset.thumbnail);
        }
      }
      const body = JSON.stringify(content).replace(/"__GALLERY_URL_(asset\d+)__"/g, '$1');
      return `${imports.join('\n')}\nexport default ${body};`;
    },
  }],
});
