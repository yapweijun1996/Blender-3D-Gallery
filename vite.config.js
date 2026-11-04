import { defineConfig } from 'vite';
import { loadCatalog } from './scripts/catalog.mjs';
import { pwaBuildPlugin } from './scripts/pwa-build.mjs';

const virtualId = 'virtual:gallery-catalog';
const resolvedId = '\0' + virtualId;
export default defineConfig({
  base: './',
  build: { assetsInlineLimit: 0 },
  plugins: [pwaBuildPlugin(), {
    name: 'gallery-catalog',
    resolveId(id) { return id === virtualId ? resolvedId : null; },
    load(id) {
      if (id !== resolvedId) return null;
      const catalog = loadCatalog();
      const imports = [];
      let index = 0;
      for (const collection of catalog.collections) {
        for (const asset of collection.assets) {
          const n = index++;
          imports.push(`import file${n} from ${JSON.stringify('/' + asset.file + '?url')};`);
          imports.push(`import image${n} from ${JSON.stringify('/' + asset.thumbnail + '?url')};`);
          asset.file = `__FILE_${n}__`;
          asset.thumbnail = `__IMAGE_${n}__`;
        }
      }
      const body = JSON.stringify(catalog).replace(/"__FILE_(\d+)__"/g, 'file$1').replace(/"__IMAGE_(\d+)__"/g, 'image$1');
      return `${imports.join('\n')}\nexport default ${body};`;
    },
  }],
});
