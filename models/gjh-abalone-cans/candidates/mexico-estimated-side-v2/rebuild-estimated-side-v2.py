from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import struct,json,io,math,hashlib,sys
src=Path(sys.argv[1]).read_bytes()
n=struct.unpack_from('<I',src,12)[0]; doc=json.loads(src[20:20+n]); pos=20+n; bn=struct.unpack_from('<I',src,pos)[0]; b=src[pos+8:pos+8+bn]; view=doc['bufferViews'][7]; start=view['byteOffset']; end=start+view['byteLength']; im=Image.open(io.BytesIO(b[start:end])).convert('RGB'); assert im.size==(640,312)
original = im.copy()
d=ImageDraw.Draw(im)
# Decorative continuation restricted to the disclosed, unsupported side sector.
for x0,x1 in [(0,198),(620,639)]:
 for x in range(x0,x1+1):
  gold=212; blue=179
  d.line((x,0,x,228),fill=(239,gold,123))
  d.line((x,236,x,311),fill=(71,98,blue))
  y=229+round(5*math.cos((x-4)*2*math.pi/35))
  d.line((x,229,x,235),fill=(255,255,255))
  d.line((x,y,x,235),fill=(71,98,blue))
# High-contrast disclosure on the estimated sector only.
d.rounded_rectangle((4, 78, 100, 143), radius=6, fill=(24, 58, 46), outline=(248, 231, 174), width=2)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 13)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 13)
d.text((9, 82), 'ESTIMATED', font=font, fill=(255, 250, 226))
d.text((34, 101), 'SIDE', font=small, fill=(255, 250, 226))
d.text((13, 120), 'DEMO ONLY', font=small, fill=(255, 250, 226))
# Feather only inside the unknown sector; original photo panels stay intact.
for x in range(183, 199):
    alpha = (x - 183) / 15
    edge = original.crop((199, 0, 200, 312))
    col = im.crop((x, 0, x+1, 312))
    im.paste(Image.blend(col, edge, alpha), (x, 0))
for x in range(620, 640):
    alpha = 1 - (x - 620) / 19
    edge = original.crop((619, 0, 620, 312))
    col = im.crop((x, 0, x+1, 312))
    im.paste(Image.blend(col, edge, alpha), (x, 0))
out=io.BytesIO();im.save(out,format='PNG',optimize=True); pic=out.getvalue(); old_end=(end+3)&~3; chunk=pic+b'\0'*((-len(pic))%4); delta=len(chunk)-(old_end-start); binary=b[:start]+chunk+b[old_end:]
view['byteLength']=len(pic)
for j,v in enumerate(doc['bufferViews']):
 if j!=7 and v.get('byteOffset',0)>=old_end:v['byteOffset']+=delta
doc['images'][0]['mimeType']='image/png';doc['images'][0]['name']='mexico-estimated-side-demo';doc['buffers'][0]['byteLength']=len(binary)
j=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode();j+=b' '*((-len(j))%4); binary+=b'\0'*((-len(binary))%4)
result=struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\0')+binary
outpath=Path(sys.argv[2]);outpath.write_bytes(result)
print('source_sha256',hashlib.sha256(src).hexdigest());print('candidate_sha256',hashlib.sha256(result).hexdigest());print('bytes',len(src),len(result)); print('texture_pixels',im.size)

