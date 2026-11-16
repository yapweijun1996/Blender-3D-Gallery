// Convert Blender PNGs to lightweight card images with the installed Chromium.
import fs from 'node:fs/promises';
import {chromium} from 'playwright';
const browser = await chromium.launch({headless: true});
try {
  const page = await browser.newPage();
  for (const name of ['hero', 'front', 'side', '3q']) {
    const file = new URL(`previews/${name}.png`, import.meta.url);
    const input = await fs.readFile(file);
    const data = await page.evaluate(async base64 => {
      const image = new Image();
      image.src = 'data:image/png;base64,' + base64;
      await image.decode();
      if (image.width !== 768 || image.height !== 768) throw new Error('Unexpected preview dimensions');
      const canvas = document.createElement('canvas');
      canvas.width = image.width;
      canvas.height = image.height;
      canvas.getContext('2d').drawImage(image, 0, 0);
      return canvas.toDataURL('image/webp', .92).split(',')[1];
    }, input.toString('base64'));
    await fs.writeFile(new URL(`previews/${name}.webp`, import.meta.url), Buffer.from(data, 'base64'));
  }
} finally {
  await browser.close();
}
