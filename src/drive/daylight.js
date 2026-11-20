import { Color } from "three";

// A day in the neighbourhood: sky, ground, sun and lamps by the hour (one hour passes in 40 seconds).
export const DAY = [
  { hour: 0, sky: 0x0b1530, ground: 0x26332a, sun: 0.25, lamp: 1 }, { hour: 5.5, sky: 0x2e3566, ground: 0x34402f, sun: 0.4, lamp: 1 },
  { hour: 6.5, sky: 0xe8a77a, ground: 0x60734a, sun: 1.6, lamp: 0.3 }, { hour: 9, sky: 0x9fd0f2, ground: 0x6f8a4f, sun: 2.6, lamp: 0 },
  { hour: 15, sky: 0xa9d6f5, ground: 0x6f8a4f, sun: 2.6, lamp: 0 }, { hour: 17.5, sky: 0xf2b27c, ground: 0x6f7a55, sun: 2.2, lamp: 0 },
  { hour: 18.8, sky: 0x7a5a87, ground: 0x4b5545, sun: 1.0, lamp: 0.7 }, { hour: 19.8, sky: 0x1c2250, ground: 0x2a3030, sun: 0.4, lamp: 1 },
  { hour: 24, sky: 0x0b1530, ground: 0x26332a, sun: 0.25, lamp: 1 },
];
export function dayAt(hour) {
  let i = 0;
  while (i < DAY.length - 2 && hour > DAY[i + 1].hour) i++;
  const a = DAY[i], b = DAY[i + 1], k = Math.max(0, Math.min(1, (hour - a.hour) / (b.hour - a.hour)));
  return { sky: new Color(a.sky).lerp(new Color(b.sky), k), ground: new Color(a.ground).lerp(new Color(b.ground), k), sun: a.sun + (b.sun - a.sun) * k, lamp: a.lamp + (b.lamp - a.lamp) * k };
}
