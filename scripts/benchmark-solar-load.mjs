import { chromium } from 'playwright';
import { serveBuild, launchOptions } from './browser-test-utils.mjs';

const server = await serveBuild(process.env.TEST_BUILD_DIR || 'dist');
const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 40, downloadThroughput: 2_500_000, uploadThroughput: 750_000 });
  const requests = new Set();
  cdp.on('Network.requestWillBeSent', event => { if (new URL(event.request.url).pathname.endsWith('.glb')) requests.add(event.requestId); });
  const start = performance.now();
  await page.goto(server.url + '?page=solar');
  await page.waitForFunction(() => document.querySelector('#solar-status')?.textContent === '', null, { timeout: 150000 });
  console.log(JSON.stringify({ sceneReadyMs: Math.round(performance.now() - start), modelRequests: requests.size, network: '20 Mbps down, 40 ms latency; Chromium mobile emulation' }, null, 2));
} finally { await browser.close(); await server.close(); }
