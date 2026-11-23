// Deterministic frame renderer: steps the three.js scene to exact times in headless Chrome and pipes frames to ffmpeg.
// Usage:
//   node render.mjs stills 0,5,10 outDir      -> outDir/t-<time>.png
//   node render.mjs video out.mp4 [fps=24] [start=0] [end=28]
// Needs: npm i playwright-core (in a folder on the module path), Google Chrome, and ffmpeg on PATH.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const dir = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(process.env.PW_FROM ? path.resolve(process.env.PW_FROM) + '/' : import.meta.url);
const { chromium } = require('playwright-core');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' };
const server = http.createServer((req, res) => {
  const f = path.join(dir, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!f.startsWith(dir) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(f)] ?? 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const port = server.address().port;

const [mode, ...rest] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', args: ['--use-angle=metal', '--enable-gpu-rasterization', '--ignore-gpu-blocklist'] });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${port}/index.html?render=1`);
  await page.waitForFunction(() => window.ready === true, null, { timeout: 30000 });
  const shot = async (t) => {
    await page.evaluate((x) => window.renderAt(x), t);
    return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1280, height: 720 } });
  };

  if (mode === 'stills') {
    const [times, out] = rest;
    fs.mkdirSync(out, { recursive: true });
    for (const t of times.split(',').map(Number)) fs.writeFileSync(`${out}/t-${t}.png`, await shot(t));
  } else if (mode === 'video') {
    const [out, fpsArg = '24', startArg = '0', endArg = '28'] = rest;
    const fps = Number(fpsArg), start = Number(startArg), end = Number(endArg);
    const n = Math.round((end - start) * fps);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise((r) => ff.on('close', r));
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      const png = await shot(start + i / fps);          // frame i samples time i / fps, like a video player
      if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
      if (i % 48 === 0) console.log(`frame ${i}/${n} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
    ff.stdin.end();
    const code = await done;
    console.log('frames', n, 'ffmpeg exit', code, 'seconds', ((Date.now() - t0) / 1000).toFixed(1));
  }
  if (errors.length) console.log('PAGE MESSAGES:\n' + [...new Set(errors)].join('\n'));
} finally { await browser.close(); server.close(); }
