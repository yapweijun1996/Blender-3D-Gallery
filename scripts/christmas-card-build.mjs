import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { cardVersion } from '../src/christmas-card/version.js';

// Capture the card's Rollup dependency closure, including assets emitted by Vite.
export function christmasCardBuild() {
  let dependencies = [];
  return {
    name: 'christmas-card-offline',
    apply: 'build',
    generateBundle(_options, bundle) {
      const entry = Object.values(bundle).find(item => item.type === 'chunk' && Object.keys(item.modules).some(id => id.endsWith('/src/christmas-card/main.js')));
      if (!entry) throw new Error('Christmas card entry missing');
      const found = new Set();
      function visit(name) {
        if (found.has(name)) return;
        found.add(name);
        const item = bundle[name];
        if (item?.type === 'chunk') {
          for (const child of [...item.imports, ...item.dynamicImports, ...(item.viteMetadata?.importedCss || []), ...(item.viteMetadata?.importedAssets || [])]) visit(child);
        }
      }
      visit(entry.fileName);
      dependencies = [...found];
    },
    closeBundle() {
      const root = path.resolve('dist');
      const htmlPath = path.join(root, 'christmas-card/index.html');
      if (!fs.existsSync(htmlPath)) return;
      const files = ['christmas-card/index.html', 'christmas-card/manifest.webmanifest', 'christmas-card/icons/icon.svg', 'christmas-card/icons/icon-192.png', 'christmas-card/icons/icon-512.png', ...dependencies].sort();
      const hash = crypto.createHash('sha256');
      for (const file of files) hash.update(file).update(fs.readFileSync(path.join(root, file)));
      const template = fs.readFileSync('src/christmas-card/sw-template.js', 'utf8');
      hash.update(template).update(cardVersion);
      const build = hash.digest('hex').slice(0, 12);
      // Fill the marker after hashing the shell so its build ID is available offline.
      const html = fs.readFileSync(htmlPath, 'utf8');
      if (!html.includes('data-build=""')) throw new Error('Christmas card build marker missing');
      fs.writeFileSync(htmlPath, html.replace('data-build=""', `data-build="${build}"`));
      fs.writeFileSync(path.join(root, 'christmas-card/version.json'), JSON.stringify({version: cardVersion, build}));
      fs.writeFileSync(path.join(root, 'christmas-card/sw.js'), template.replace('__BUILD__', JSON.stringify(build)).replace('__FILES__', JSON.stringify([...files, 'christmas-card/version.json'])));
    },
  };
}
