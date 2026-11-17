// Encode the rendered PNG with Chromium's built-in WebP encoder, no new packages.
import fs from 'node:fs/promises';
import { chromium } from 'playwright';

const here = new URL('./previews/', import.meta.url);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const png = await fs.readFile(new URL('hero.png', here));
  const data = await page.evaluate(async data => {
    const image = new Image();
    image.src = 'data:image/png;base64,' + data;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.getContext('2d').drawImage(image, 0, 0);
    return canvas.toDataURL('image/webp', .88).split(',')[1];
  }, png.toString('base64'));
  await fs.writeFile(new URL('hero.webp', here), Buffer.from(data, 'base64'));
} finally {
  await browser.close();
}
