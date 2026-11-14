"""Create the original, unbranded DEMO beverage artwork used by generate.py."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
HERE.joinpath("textures").mkdir(exist_ok=True)
image = Image.new("RGB", (1024, 512), "#0d4f59")
draw = ImageDraw.Draw(image)
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def centered(text, y, size, color):
    font = ImageFont.truetype(font_path, size)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((1024 - box[2] + box[0]) / 2, y), text, font=font, fill=color)

draw.rectangle((0, 22, 1024, 34), fill="#f4b544")
draw.rectangle((0, 478, 1024, 490), fill="#f4b544")
draw.ellipse((438, 55, 586, 203), outline="#f4b544", width=7)
draw.arc((465, 84, 559, 178), 200, 340, fill="#fff3cf", width=7)
centered("DEMO", 214, 72, "#fff3cf")
centered("CITRUS FIZZ", 302, 36, "#fff3cf")
centered("ORIGINAL CONCEPT", 365, 20, "#f4b544")
centered("NOT FOR SALE", 411, 18, "#fff3cf")
image.save(HERE / "textures" / "beverage-label.png")
