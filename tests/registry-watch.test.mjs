import test from 'node:test';
import assert from 'node:assert/strict';
import { copyFile, mkdir, mkdtemp, readFile, rename, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { createServer } from 'vite';
import config from '../vite.config.js';

const source = relative => new URL('../' + relative, import.meta.url);
const floor = 'models/mall-floor-tile/exports/mall-floor-tile-module.glb';
const corner = 'models/mall-floor-corner-tile/exports/mall-floor-corner-tile.glb';
const thumbnail = 'models/mall-floor-tile/previews/mall-floor-tile-module.webp';

test('development registries refresh after atomic edits to their inputs', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'gallery-registry-'));
  const file = relative => path.join(root, relative);
  let server;
  try {
    await Promise.all(['models', 'data'].map(dir => mkdir(file(dir))));
    const asset = { id: 'sample', name: 'Test floor', category: 'Architecture', metadata: 'models/sample.json',
      file: 'models/floor.glb', thumbnail: 'models/one.webp' };
    const catalog = { collections: [{ id: 'fixtures', name: 'Fixtures', assets: [asset] }] };
    const details = { id: asset.id, display: { previewRotationY: 0 }, accuracy_notes: 'Original notes', attribution: [] };
    const demos = JSON.parse(await readFile(source('data/demos.json'), 'utf8'));
    for (const demo of demos) demo.thumbnailAssetId = asset.id;
    const write = (name, data) => writeFile(file(name), JSON.stringify(data));
    await Promise.all([
      write('models/catalog.json', catalog), write(asset.metadata, details), write('data/demos.json', demos),
      copyFile(source(floor), file(asset.file)), copyFile(source(thumbnail), file(asset.thumbnail)),
      copyFile(source(thumbnail), file('models/two.webp')),
      writeFile(file('index.html'), '<script type="module" src="/consumer.js"></script>'),
      writeFile(file('consumer.js'), 'import catalog from "virtual:gallery-catalog"; import demos from "virtual:gallery-demos"; export default {catalog,demos};'),
    ]);
    server = await createServer({ configFile: false, root, logLevel: 'silent',
      plugins: [config.plugins.find(plugin => plugin.name === 'gallery-registries')],
      optimizeDeps: { noDiscovery: true }, server: { host: '127.0.0.1', port: 0 },
    });
    await server.listen();
    const base = 'http://127.0.0.1:' + server.httpServer.address().port;
    const consumer = await (await fetch(base + '/consumer.js')).text();
    const endpoint = name => {
      const match = consumer.match(new RegExp('"([^"]*virtual:gallery-' + name + ')"'));
      assert.ok(match, 'consumer resolves ' + name);
      return base + match[1];
    };
    const catalogUrl = endpoint('catalog'), demosUrl = endpoint('demos');
    async function snapshot(url) {
      const response = await fetch(url);
      assert.equal(response.status, 200);
      return response.text();
    }
    async function waitFor(url, needle) {
      const deadline = Date.now() + 8000;
      do {
        if ((await snapshot(url)).includes(needle)) return;
        await delay(50);
      } while (Date.now() < deadline);
      assert.fail('Live registry did not update ' + needle);
    }
    await Promise.all([waitFor(catalogUrl, 'Original notes'), waitFor(demosUrl, '/models/one.webp')]);
    // Model authoring tools and editors replace files with atomic renames.
    async function replace(name, data) {
      const next = file(name + '.tmp');
      await writeFile(next, data);
      await rename(next, file(name));
    }
    details.accuracy_notes = 'Updated notes';
    await replace(asset.metadata, JSON.stringify(details));
    await waitFor(catalogUrl, 'Updated notes');

    asset.thumbnail = 'models/two.webp';
    asset.metadata = 'models/replacement.json';
    await write(asset.metadata, details);
    await replace('models/catalog.json', JSON.stringify(catalog));
    await Promise.all([waitFor(catalogUrl, asset.thumbnail), waitFor(demosUrl, asset.thumbnail)]);

    details.accuracy_notes = 'Replacement metadata is watched';
    await replace(asset.metadata, JSON.stringify(details));
    await waitFor(catalogUrl, details.accuracy_notes);

    demos[0].description = 'Revised demo description';
    await replace('data/demos.json', JSON.stringify(demos));
    await waitFor(demosUrl, 'Revised demo description');

    const changedModel = await readFile(source(corner));
    await replace(asset.file, changedModel);
    await waitFor(catalogUrl, '"bytes":' + changedModel.length);
  } finally {
    await server?.close();
    await rm(root, { recursive: true, force: true });
  }
});
