"""Read rendered original glyphs from observed Game Boy tile maps; no writes."""
import navigate as n
from dialogue_text import glyph

def read(r):
 lcd=r[0xff40];lines=[]
 for y in range(0,144,8):
  line=''
  for x in range(0,160,8):
   if lcd&32 and y>=r[0xff4a] and x>=r[0xff4b]-7:
    px=x-r[0xff4b]+7;py=y-r[0xff4a];base=0x9c00 if lcd&64 else 0x9800
   else:px=(x+r[0xff43])%256;py=(y+r[0xff42])%256;base=0x9c00 if lcd&8 else 0x9800
   tile=r[base+py//8*32+px//8];offset=0x8000+tile*16 if lcd&16 else 0x9000+(tile if tile<128 else tile-256)*16
   line+=glyph.get(r[offset:offset+16],' ')
  lines.append(line)
 return '\n'.join(lines)
if __name__=='__main__':print(read(n.latest()))
