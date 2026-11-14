"""Original geometric DEMO graphic; DejaVu Sans font from system, see font copyright."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
P=Path(__file__).resolve().parent; (P/'textures').mkdir(exist_ok=True)
im=Image.new('RGB',(1024,512),'#163f42');d=ImageDraw.Draw(im)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def text(t,y,size,fill):
 f=ImageFont.truetype(font,size);b=d.textbbox((0,0),t,font=f);d.text(((1024-(b[2]-b[0]))/2,y),t,font=f,fill=fill)
d.rectangle((0,24,1024,34),fill='#dfba70');d.rectangle((0,478,1024,488),fill='#dfba70')
d.ellipse((450,68,574,192),outline='#dfba70',width=5);d.line((476,155,512,105,548,155),fill='#dfba70',width=6)
text('DEMO',218,64,'#fff4dc');text('FOOD TIN',297,34,'#fff4dc');text('ORIGINAL CONCEPT',367,20,'#dfba70');text('NOT FOR SALE',413,18,'#fff4dc')
im.save(P/'textures'/'concept-label.png')
