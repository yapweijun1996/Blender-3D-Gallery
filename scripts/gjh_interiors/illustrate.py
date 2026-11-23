"""Bake the common 256px print and display sheet from the registered shop marks."""
import argparse
import json
from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

from palette import SWATCHES


def draw_atlas(brands, output):
    sheet = Image.new("RGB", (256, 256), "#f9f3df")
    draw = ImageDraw.Draw(sheet)
    sources = json.loads((brands / "logo-sources.json").read_text())
    for index, (slot, record) in enumerate(sorted(sources.items())):
        assert slot == f"S{index + 1:02}"
        image = Image.open(brands / record["file"]).convert("RGBA")
        white = Image.new("RGB", image.size, "white")
        white.paste(image, mask=image.getchannel("A"))
        mask = ImageChops.difference(white, Image.new("RGB", image.size, "white")).convert("L")
        mark = white.crop(mask.point(lambda value: 255 if value > 24 else 0).getbbox())
        if slot == "S09":
            # The registered artwork is yellow lettering inside a navy square.
            # Crop to the actual ink and extend its background to the whole fascia.
            red,green,blue = white.split()
            yellow = ImageChops.multiply(red.point(lambda v: 255 if v>135 else 0),
                                         green.point(lambda v: 255 if v>105 else 0))
            yellow = ImageChops.multiply(yellow,ImageChops.darker(red,green).point(lambda v: .75*v))
            yellow = ImageChops.subtract(yellow,blue)
            mark = white.crop(yellow.getbbox())
        mark = ImageOps.contain(mark, (58, 25), Image.Resampling.LANCZOS)
        x, y = index % 4 * 64, index // 4 * 32
        draw.rectangle((x, y, x+63, y+31), fill="#1d214e" if slot=="S09" else "white")
        sheet.paste(mark, (x+(64-mark.width)//2, y+(32-mark.height)//2))
    for index, colour in enumerate(SWATCHES):
        x,y = 64+16*(index%4),128+10*(index//4)
        draw.rectangle((x,y,x+15,y+9),fill="#"+colour)
    # A breakfast advert for the jar display, illustrated at its final texel size.
    draw.rectangle((128,128,191,159),fill="#f3d7a0")
    draw.polygon([(128,128),(151,128),(138,159),(128,159)],fill="#345780")
    for cx,cy in ((132,138),(136,151)):
        draw.ellipse((cx-3,cy-4,cx+1,cy+1),fill="#d9a055",outline="#ae733f")
        draw.ellipse((cx-1,cy-1,cx+4,cy+4),fill="#d9a055",outline="#ae733f")
    skippy = sheet.crop((194,33,254,63))
    sheet.paste(ImageOps.contain(skippy,(36,18)),(144,130))
    draw.rounded_rectangle((174,147,188,157),radius=3,fill="#ae6b3c")
    draw.rounded_rectangle((176,148,186,155),radius=2,fill="#edbd7f")
    draw.arc((177,150,185,154),0,305,fill="#b87a49")
    # Two seamless full-width programmes. Each display unwraps only its own band.
    for x in range(256):
        t = x / 256 * 2 * pi
        for y in range(40):
            f = y / 39
            wave = .5 + .5 * cos(t + 3.2*f + .8*sin(t-f))
            glow = (1-abs(2*wave-1))**4
            sheet.putpixel((x, 161+y), (int(52+168*wave+30*glow),
                int(35+109*(1-wave)+71*glow), int(108+97*(1-wave)+41*glow)))
        crest = int(4+14*(.5+.5*sin(t*2+sin(3*t))))
        draw.line((x, 204, x, 229), fill="#122944")
        if x%5<3:
            draw.line((x,226-crest,x,226),fill="#72deff" if x%20<10 else "#b3edff")
    # Shelf-edge catalogue tickets, with blank price fields for the showroom.
    for i,c in enumerate(("#ab562c","#267e72","#5b5c98")):
        x=i*64
        draw.rectangle((x,234,x+63,255),fill="#fff5d9")
        draw.rectangle((x+2,236,x+8,253),fill=c)
        draw.text((x+11,236),f"{chr(65+i)}0{i+1}", fill="#253944")
        draw.text((x+11,245),'$ --',fill='#42504e')
        for j in (0,2,5,6,10,12,16):
            draw.line((x+41+j,239,x+41+j,250),fill="#42504e")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brands", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    draw_atlas(args.brands, args.output)
