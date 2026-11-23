// Usage (repo root): node models/chibi-mall-guide-v5/trellis-trial/shoot-glb.mjs GLB_FILE OUT_PNG
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright';
const [glb, outPng] = process.argv.slice(2); const root = process.cwd();
const types = { '.js': 'text/javascript', '.html': 'text/html', '.glb': 'model/gltf-binary', '.mjs': 'text/javascript' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]); const f = u === '/model.glb' ? glb : path.join(root, u);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(f)] ?? 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
}).listen(0, '127.0.0.1');
await new Promise(resolve => server.once('listening', resolve));
const port = server.address().port;
let browser;
try {
  browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 2240, height: 560 } });
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}/models/chibi-mall-guide-v5/trellis-trial/view-glb.html?glb=/model.glb`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  const { info, png } = await page.evaluate(() => ({ info: window.__info, png: window.captureTurnaround() }));
  if (!png.startsWith('data:image/png;base64,')) throw Error('Unable to encode the turnaround');
  fs.writeFileSync(outPng, Buffer.from(png.slice('data:image/png;base64,'.length), 'base64'));
  console.log(JSON.stringify({ info, errors }));
} finally {
  await browser?.close();
  server.close();
}
