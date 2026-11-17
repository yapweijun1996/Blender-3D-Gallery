// Lossy preview derivatives only; original rendered PNGs are preserved.
import fs from 'node:fs/promises';
import {chromium} from 'playwright';
const browser = await chromium.launch({headless: true});
try {
  const page = await browser.newPage();
  for (const name of ['hero', 'front', 'side', '3q']) {
    const png = await fs.readFile(new URL(`previews/${name}.png`, import.meta.url));
    const encoded = await page.evaluate(async data => {
      const image = new Image();
      image.src = 'data:image/png;base64,' + data;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.width; canvas.height = image.height;
      canvas.getContext('2d').drawImage(image, 0, 0);
      return canvas.toDataURL('image/webp', .88).split(',')[1];
    }, png.toString('base64'));
    const bytes = Buffer.from(encoded, 'base64');
    await fs.writeFile(new URL(`previews/${name}.webp`, import.meta.url), bytes);
    console.log(`${name}.webp: ${bytes.length} bytes`);
  }
} finally {
  await browser.close();
}
