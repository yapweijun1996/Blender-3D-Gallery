from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import struct,json,io,math,hashlib,sys
src=Path(sys.argv[1]).read_bytes()
n=struct.unpack_from('<I',src,12)[0]; doc=json.loads(src[20:20+n]); pos=20+n; bn=struct.unpack_from('<I',src,pos)[0]; b=src[pos+8:pos+8+bn]; view=doc['bufferViews'][7]; start=view['byteOffset']; end=start+view['byteLength']; im=Image.open(io.BytesIO(b[start:end])).convert('RGB'); assert im.size==(640,312)
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
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',12)
d.text((47,111),'ESTIMATED SIDE',font=font,fill=(95,76,34),stroke_width=0)
d.text((48,129),'DEMO ONLY',font=font,fill=(95,76,34))
out=io.BytesIO();im.save(out,format='PNG',optimize=True); pic=out.getvalue(); old_end=(end+3)&~3; chunk=pic+b'\0'*((-len(pic))%4); delta=len(chunk)-(old_end-start); binary=b[:start]+chunk+b[old_end:]
view['byteLength']=len(pic)
for j,v in enumerate(doc['bufferViews']):
 if j!=7 and v.get('byteOffset',0)>=old_end:v['byteOffset']+=delta
doc['images'][0]['mimeType']='image/png';doc['images'][0]['name']='mexico-estimated-side-demo';doc['buffers'][0]['byteLength']=len(binary)
j=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode();j+=b' '*((-len(j))%4); binary+=b'\0'*((-len(binary))%4)
result=struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\0')+binary
outpath=Path(sys.argv[2]);outpath.write_bytes(result)
print('source_sha256',hashlib.sha256(src).hexdigest());print('candidate_sha256',hashlib.sha256(result).hexdigest());print('bytes',len(src),len(result)); print('texture_pixels',im.size)

