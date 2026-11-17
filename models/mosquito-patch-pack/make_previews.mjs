// Convert rendered PNG previews to lightweight WebP using the installed Chromium codec.
import fs from 'node:fs/promises';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  for (const name of ['hero', 'front', 'side', '3q']) {
    const path = new URL(`previews/${name}.png`, import.meta.url);
    const bytes = await fs.readFile(path);
    const encoded = await page.evaluate(async base64 => {
      const image = new Image();
      image.src = 'data:image/png;base64,' + base64;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.width;
      canvas.height = image.height;
      canvas.getContext('2d').drawImage(image, 0, 0);
      return canvas.toDataURL('image/webp', .88).split(',')[1];
    }, bytes.toString('base64'));
    await fs.writeFile(new URL(`previews/${name}.webp`, import.meta.url), Buffer.from(encoded, 'base64'));
  }
} finally { await browser.close(); }
