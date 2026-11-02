"""Observed original maps -> finite P1 walk commands. Never writes game state."""
from pathlib import Path
import time,sys,collections,json
sys.path.insert(0,'/workspace/DWM2t/recomp/tools')
from inspect_map import map_grid,byte,word,bank
root=Path('/workspace/scratch/arena-b-2026-11-02/session33')
log=root.with_suffix('.log')
def latest():
 for p in sorted(root.glob('m8_*.ram'),key=lambda p:int(p.stem.split('_')[1]),reverse=True):
  b=p.read_bytes()
  if len(b)==65536:return b
 raise ValueError('No complete original RAM observation')

def drive(cmds):
 for command in cmds:
  parts=command.split()
  if parts and parts[0]=='walk':
   if len(parts) not in (3,4) or parts[1] not in ('U','D','L','R') or not all(p.isdigit() for p in parts[2:]):
    raise ValueError('Invalid finite P1 walking syntax: '+command)
 n=len((root/'commands_executed.txt').read_text().splitlines());cs=cmds+['snapshot']
 with (root/'commands.txt').open('a') as f:f.write('\n'.join(cs)+'\n')
 end=time.monotonic()+25
 while time.monotonic()<end:
  if 'M8_SESSION_FAIL' in log.read_text(errors='replace'):raise RuntimeError('Native session failed')
  if len((root/'commands_executed.txt').read_text().splitlines())>=n+len(cs):time.sleep(.04);return
  time.sleep(.02)
 raise TimeoutError(cmds)

def loc(r):return (r[0xff90],r[0xff8f],r[0xff92],r[0xff8e],r[0xff91])
def flee():
 import battle_ui as b
 support=False
 for step in range(600):
  r=latest()
  if r[0xc5db]!=4:
   if tuple(r[0xc5db:0xc5dd])==(1,0):
    import field_care as f
    data=f.data()
    if any(i==12 and status==0 and hp>0 and mp>=7 for i,status,hp,mx,mp in data):
     drive(['D 6 90'])
     for i,(_,status,hp,mx,mp) in enumerate(f.data()):
      if status==0 and 0<hp<mx:f.heal(i)
   return
  if r[0xcfc8]==2 and r[0xcfc9]==5 and r[0xcfca]==3 and r[0xcfcc]==2:raise RuntimeError('Original recruitment requires deliberate input')
  if r[0xcfc8:0xcfcc]==bytes((1,1,0,3)):
   party=list(r[0xc6fe:0xc701]);hp=b.words(r,0xd8bf);mp=b.words(r,0xd8df)
   if not support and 10 in party and hp[party.index(10)]>0 and mp[party.index(10)]>=3:
    import garon_plan as gp
    target=min((i for i in range(3) if hp[i]),key=lambda i:hp[i]/max(1,b.words(r,0xd8cf)[i]))
    gi=party.index(12)
    skill='heal' if hp[gi] and hp[target]<b.words(r,0xd8cf)[target]*.7 and mp[gi]>=7 else 'increase' if hp[gi] and mp[gi]>=3 else 'attack'
    gp.plan(skill,target=target,derzo_skill='sleep',slash_guard=True);support=True
   else:b.choose_root(3)
  else:drive(['A 2 60'])
 raise RuntimeError('Finite original flee budget exhausted')

def run():
 world=int(sys.argv[1]);target=tuple(map(int,sys.argv[2:4]));last=None;stuck=0;blocked=set()
 cache_path=Path('/workspace/scratch/arena-b-2026-11-02/control/observed-ground-maps.json')
 cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
 external=set(); raw=bank(17); entry=word(17,0x67a6+world*2)-0x4000
 for _ in range(150):
  record=raw[entry:entry+9]
  if not record or record[0]==0x80:break
  if record[0] in (1,2,3,4,0xfd) and record[4]!=world:
   external.add((record[1]//16*10+record[2]//16,record[1]%16*9+record[3]//16))
  entry+=9
 else:raise RuntimeError('Original warp observation exceeds finite bound')
 for step in range(500):
  r=latest();l=loc(r);print(step,l,tuple(r[0xc5db:0xc5dd]),flush=True)
  if l[0]!=world:print('WORLD_CHANGED',l,flush=True);return
  if r[0xc5db]==4:
   if world==32:drive(['battle 12000'])
   elif world>=112:__import__('safe_battle').run()
   else:flee()
   if latest()[0xcfc8]==2 and latest()[0xcfc9]==5 and latest()[0xcfca]==3 and latest()[0xcfcc]==2:raise RuntimeError('Original recruitment requires input')
   continue
  if world==48 and r[0xc5db]==1 and r[0xc5dc]==1 and r[0xc916]==0x0f:
   drive(['A 6 180']);continue
  if r[0xc5db]==1 and r[0xc5dc] in (1,2):
   print('ORIGINAL_DIALOGUE',l,flush=True);return
  if r[0xc5db]!=1 or r[0xc5dc]!=0:
   drive(['- 1 180']);continue
  start=l[1]*10+l[3]//16,l[2]*9+l[4]//16
  if start==target:print('DESTINATION',l,flush=True);return
  w,h,m=map_grid(world,r);header=word(17,0x44b8+world*2);threshold=byte(17,header+8)
  mask=r[word(17,header+16)];key=f'{world}:{mask}:{l[1]}:{l[2]}'
  cache[key]=list(r[0xC198:0xC300]);cache_path.write_text(json.dumps(cache))
  for ry in range(h):
   for rx in range(w):
    k=f'{world}:{mask}:{rx}:{ry}'
    if k in cache:m[ry][rx]=bytes(cache[k])
  def allowed(x,y):
   if not (0<=x<w*10 and 0<=y<h*9) or (x,y) in blocked:return False
   if (x,y) in external and (x,y)!=target:return False
   data=m[y//9][x//10];o=(y%9)*40+(x%10)*2
   return all(data[o+k]>threshold for k in (0,1,20,21))
  seen={start:None};q=collections.deque([start])
  while q:
   p=q.popleft()
   if p==target:break
   for dx,dy,d in ((0,-1,'U'),(0,1,'D'),(-1,0,'L'),(1,0,'R')):
    n=p[0]+dx,p[1]+dy
    if n not in seen and allowed(*n):seen[n]=(p,d);q.append(n)
  if target not in seen:raise RuntimeError(f'No original passable route {start} -> {target}, threshold={threshold}')
  path=[];p=target
  while p!=start:p,d=seen[p];path.append(d)
  path.reverse();d=path[0];n=next((i for i,c in enumerate(path) if c!=d),len(path));n=min(n,7)
  # Single direction, followed by an original frame idle for map loading.
  drive([f'walk {d} {16*n} 120'])
  now=loc(latest())
  if now==l:
   stuck+=1
   if stuck>=2:
    dx,dy={'U':(0,-1),'D':(0,1),'L':(-1,0),'R':(1,0)}[d]
    blocked.add((start[0]+dx,start[1]+dy));print('OBSERVED_BLOCK',start,d,flush=True);stuck=0
  else:stuck=0
 raise RuntimeError('finite navigation budget exhausted')
if __name__=='__main__':run()
