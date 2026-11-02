"""Observe native HUD/menu pixels; issue only finite original P1 commands."""
import sys,struct
from pathlib import Path
sys.path.insert(0,'/workspace/scratch/m8-postgame/quest3-control')
from navigate import latest,drive,loc,root

def words(r,base,count=8):return [int.from_bytes(r[base+i*2:base+i*2+2],'little') for i in range(count)]
def arrows():
 p=max(root.glob('m8_*.bmp'),key=lambda p:int(p.stem[3:]));b=p.read_bytes();off=struct.unpack_from('<I',b,10)[0];w,h=struct.unpack_from('<ii',b,18);stride=w*4
 def dark(x,y):
  i=off+(y if h<0 else h-1-y)*stride+x*4;return max(b[i:i+3])<100
 found=[]
 for y in (65,81,97,113,129):
  for x in (9,17,25,65,73,81):
   if all(dark(x+xx,y+yy)==(xx<3+min(yy,6-yy)) for yy in range(7) for xx in range(6)):found.append((x,y))
 return found

def cursor(positions):
 for n in range(16):
  found=arrows();matches=[i for i,ps in enumerate(positions) if any(p in found for p in ps)]
  if len(matches)==1:return matches[0]
  drive(['- 1 8'])
 raise RuntimeError(f'Original menu arrow not observed: {positions}; {arrows()}')

ROOT_POS=[[(9,113)],[(65,113),(73,113),(81,113)],[(9,129)],[(65,129),(73,129),(81,129)]]
def choose_root(target):
 current=cursor(ROOT_POS);moves=[]
 if current%2!=target%2:moves.append(('R' if target%2 else 'L')+' 6 24')
 if current//2!=target//2:moves.append(('D' if target//2 else 'U')+' 6 24')
 if moves:drive(moves)
 if cursor(ROOT_POS)!=target:raise RuntimeError('Original root cursor did not reach target')
 drive(['A 6 120'])

def choose_vertical(count,target):
 pos=[[(x,129-16*(count-1)+i*16) for x in (9,17,25)] for i in range(count)]
 current=cursor(pos)
 if current!=target:drive([('D' if target>current else 'U')+' 6 24']*abs(target-current))
 if cursor(pos)!=target:raise RuntimeError('Original vertical cursor did not reach target')
 drive(['A 6 120'])

def next_root():
 for step in range(400):
  r=latest()
  if r[0xc5db]!=4:return False
  from screen_text import read
  if any(s in read(r).lower() for s in ('which skill','forget')):
   raise RuntimeError('Original skill choice requires review')
  if any(s in read(r) for s in ('Enter Name','Please name','Take along')):
   print('ORIGINAL_RECRUITMENT_REQUIRES_INSPECTION',flush=True);return False
  if r[0xcfc8:0xcfcc]==bytes((1,1,0,3)):
   for _ in range(12):
    if any(p in arrows() for ps in ROOT_POS for p in ps):return True
    drive(['- 1 8'])
  drive(['A 2 30'])
 raise RuntimeError('Original action-message budget exhausted')

def inventory(r):
 items=[]
 for item in r[0xc61d:0xc635]:
  if item in (0,255):break
  items.append(item)
 return items

def herb(target):
 r=latest();hp=words(r,0xd8bf);items=inventory(r);types=list(dict.fromkeys(items))
 if 1 not in types:raise RuntimeError('No original Herb remains')
 choose_root(1);choose_vertical(min(4,len(items)),items.index(1));choose_vertical(2,0);choose_vertical(3,target)
 now=words(latest(),0xd8bf)
 if now[target]<=hp[target]:raise RuntimeError('Original Herb did not restore observed combat HP')
 print('ORIGINAL_HERB',target,hp,'->',now,flush=True)
 if not next_root():raise RuntimeError('Unexpected field during item menu')

def plan(increase=False,guard=True):
 choose_root(2)
 choose_vertical(4,0)
 choose_vertical(4,2 if guard else 0)
 choose_vertical(4,3 if increase else 0)
 if increase:choose_vertical(3,1);choose_vertical(4,0)

def start_boss():
 drive(['U 6 24','A 6 120'])
 for _ in range(80):
  r=latest()
  if r[0xc5db]==4:return
  if r[0xc5db]==1 and r[0xc5dc]==3:drive(['- 1 180']);continue
  if r[0xc5db]!=1 or r[0xc5dc]!=1:raise RuntimeError('Unexpected original NPC stage')
  drive(['A 6 120'])
 raise RuntimeError('Original NPC did not start combat')

def boss():
 if latest()[0xc5db]!=4:start_boss()
 capped=False
 for turn in range(40):
  if not next_root():print('ORIGINAL_FIELD',loc(latest()),tuple(latest()[0xc5db:0xc5dd]),flush=True);return
  r=latest();hp=words(r,0xd8bf);mh=words(r,0xd8cf);mp=words(r,0xd8df);de=words(r,0xd90f);inv=inventory(r)
  print('TURN',turn,'HP',hp,'MAX',mh,'MP',mp,'DEF',de,'Herbs',inv.count(1),flush=True)
  for _ in range(3):
   r=latest();hp=words(r,0xd8bf);mh=words(r,0xd8cf)
   candidates=[i for i in range(3) if hp[i]>0 and mh[i]-hp[i]>=28 and (hp[i]<mh[i]*.7 or hp[i]<40)]
   if not candidates or 1 not in inventory(r):break
   herb(min(candidates,key=lambda i:hp[i]/mh[i]))
  r=latest();hp=words(r,0xd8bf);mp=words(r,0xd8df);de=words(r,0xd90f)
  increase=not capped and de[0]<100 and hp[2]>0 and mp[2]>=3
  before_def,before_mp=de[0],mp[2]
  guard=hp[1]<40 or hp[4]>120
  plan(increase,guard)
  if not next_root():print('ORIGINAL_FIELD',loc(latest()),tuple(latest()[0xc5db:0xc5dd]),flush=True);return
  now=latest()
  if increase and words(now,0xd8df)[2]<before_mp and words(now,0xd90f)[0]==before_def:capped=True
 raise RuntimeError('Finite original boss-turn budget exhausted')
if __name__=='__main__':boss()
