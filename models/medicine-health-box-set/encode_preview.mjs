// Encode the rendered hero as a lightweight gallery thumbnail; no image changes.
import fs from 'node:fs/promises';
import { chromium } from 'playwright';
import { launchOptions } from '../../scripts/browser-test-utils.mjs';

const preview = new URL('previews/', import.meta.url);
const png = await fs.readFile(new URL('hero.png', preview));
const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage();
  const encoded = await page.evaluate(async base64 => {
    const image = new Image();
    image.src = 'data:image/png;base64,' + base64;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.getContext('2d').drawImage(image, 0, 0);
    return canvas.toDataURL('image/webp', .92).split(',')[1];
  }, png.toString('base64'));
  await fs.writeFile(new URL('hero.webp', preview), Buffer.from(encoded, 'base64'));
} finally {
  await browser.close();
}
