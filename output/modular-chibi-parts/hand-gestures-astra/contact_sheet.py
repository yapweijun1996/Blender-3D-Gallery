"""Compose the 54 unretouched Cycles PNGs into a labelled visual index."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
OUT = Path(__file__).resolve().parent
GESTURES = ('fist', 'open_relaxed', 'point', 'thumbs_up', 'peace', 'ok', 'grip_small', 'pinch', 'open_wide')
FONT = '/System/Library/Fonts/HelveticaNeue.ttc'
def font(size, weight=0): return ImageFont.truetype(FONT, size, index=weight)


def main():
    metrics = json.loads((OUT/'hand_check.json').read_text())['gestures']
    cell = (240, 210)
    x0 = 177
    y0 = 121
    gap = 4
    gutter = 15
    width = x0+6*(cell[0]+gap)+gutter+17
    sheet = Image.new('RGB', (width, y0+9*(cell[1]+gap)+19), '#eeece7')
    p = ImageDraw.Draw(sheet)
    dark = '#263641'
    muted = '#536773'
    p.text((18, 13), 'Chibi hand gestures', font=font(36, 1), fill=dark)
    for i, hand in enumerate(('Left hand', 'Right hand')):
        x = x0+i*(3*(cell[0]+gap)+gutter)
        p.text((x, 61), hand, font=font(21, 1), fill=dark)
        for j, v in enumerate(('Palmar', 'Dorsal', 'Thumb side')):
            p.text((x+j*(cell[0]+gap), 91), v, font=font(16), fill=muted)
    for i, g in enumerate(GESTURES):
        y = y0+i*(cell[1]+gap)
        p.text((18, y+cell[1]//2-12), ('OK' if g == 'ok' else g.replace('_',
               ' ').capitalize()), font=font(20, 1), fill=dark)
        if g == 'grip_small':
            p.text((18, y+cell[1]//2+19), 'Ø 40 mm guide', font=font(15), fill=muted)
        for j, tag in enumerate(('L', 'R')):
            for k, view in enumerate(('palm', 'back', 'thumb-side')):
                path = OUT/'renders'/f'hand_{g}_{tag}_{view}.png'
                im = Image.open(path).convert('RGB')
                if g == 'grip_small' and view == 'thumb-side':
                    gauge = metrics[f'hand_{g}_{tag}'].get('gauge_projection_pixels')
                    if gauge:
                        cx, cy = gauge['center']
                        rad = gauge['radius']
                        box = (cx-rad, cy-rad, cx+rad, cy+rad)
                        layer = ImageDraw.Draw(im)
                        for angle in range(0, 360, 15):
                            layer.arc(box, angle, angle+9, fill='#8cbdc8', width=3)
                sheet.paste(im.resize(cell, Image.Resampling.LANCZOS),
                            (x0+(3*j+k)*(cell[0]+gap)+gutter*j, y))
    sheet.save(OUT/'contact_sheet.png', optimize=True)


if __name__ == '__main__':
    main()
