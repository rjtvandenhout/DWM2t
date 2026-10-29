from pathlib import Path
import argparse,hashlib,json,sys,time
sys.path.insert(0,'Z:/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07')
sys.path.insert(0,'Z:/workspace/DWM2t/recomp/tools')
from repeat_vs_probe import Probe
args=argparse.Namespace(exe=Path('Z:/workspace/scratch/full-rom-2026-10-26/r4-audit/production/candidate/DWM2t-M8-UNTESTED/DWM2tRecomp.exe'),seed=Path('Z:/workspace/DWM2t/outputs/M8-ending-3d573873ae81/ending_complete.sav'),output=Path('Z:/workspace/scratch/full-rom-2026-10-26/link-breeding-r4/run-03'),source='1351bcd058e491455a477045a2ff86bbc3bd7b1c',exe_sha256='63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95',environment='Wine on Linux')
p=Probe(args);p.report.update(kind='original_link_breeding_fresh_continue',completed_breeding=False,selected_squiz=False)
try:
 p.prepare()
 src=Path('Z:/workspace/scratch/full-rom-2026-10-26/link-breeding-explore/run-02')
 for name in ('after1','after2','after3','after5','farm-choices','page2','parents-after-wait','proceed','confirm','after-confirm','animation','offspring-full','after-egg','after-care'):
  for player in (1,2):
   f=src/f'{name}-player{player}.bmp'
   if f.exists():p.refs[f'breed-{name}-{player}']=p.bitmap(f)
 def waitref(player,name,rect=(0,0,160,144),omit=(),timeout=45,threshold=.995):
  key=f'breed-{name}-{player}'
  p.wait(player,lambda pix:p.score(key,pix,rect,omit)>=threshold,f'{name}',timeout)
 command=[str(p.exe),'--play',str(p.saves[1]),'--link-save',str(p.saves[2]),'--scale','1','--audio-volume','0']
 p.serial_process=p.start(command,'linked');p.windows=dict(zip((1,2),p.api.pair(p.serial_process),strict=True));p.active={1:p.serial_process,2:p.serial_process}
 for player in (1,2):p.saved_menu(player,f'linked-p{player}')
 for player in (1,2):
  for index,selected in enumerate(('menu_new','menu_breeding'),1):p.pulse(player,0x28);p.wait(player,lambda pix,selected=selected:p.is_menu(pix,selected),f'p{player}-down{index}',15)
 p.pulse(1,0x5a,3)
 rect=(0,104,160,144);omit=((144,128,160,144),)
 initial=p.wait(1,lambda pix:p.score('breed-after1-1',pix,rect,omit)>=.995 or p.score('breed-after3-1',pix,rect,omit)>=.995,'initial-link-response',45)
 if p.score('breed-after1-1',initial,rect,omit)>=.995:
  p.pulse(1,0x5a,.6);waitref(1,'after2',rect=rect,omit=omit)
  p.pulse(1,0x5a,.5);p.pulse(2,0x5a,2)
 for player in (1,2):waitref(player,'after3',rect=(0,104,160,144),omit=((144,128,160,144),))
 for player in (1,2):p.pulse(player,0x5a,.6)
 for player in (1,2):waitref(player,'after5',rect=(0,0,160,104),omit=((0,0,12,102),),threshold=.99)
 for _ in range(3):p.pulse(1,0x28,.3)
 p.pulse(2,0x27,.5)
 waitref(1,'farm-choices',rect=(0,0,160,104),omit=((0,0,12,102),),threshold=.99)
 waitref(2,'page2',rect=(0,0,160,104),omit=((0,0,12,102),),threshold=.99)
 for player in (1,2):p.pulse(player,0x5a,.5);p.pulse(player,0x28,.4);p.pulse(player,0x5a,1)
 waitref(1,'parents-after-wait',rect=(0,104,160,144),omit=((144,128,160,144),))
 p.pulse(1,0x5a,1);waitref(2,'proceed',rect=(0,104,160,144),omit=((144,128,160,144),))
 p.pulse(2,0x5a,1)
 for player in (1,2):waitref(player,'confirm',rect=(0,104,160,144),omit=((144,128,160,144),))
 for player in (1,2):p.pulse(player,0x5a,1)
 for player in (1,2):waitref(player,'after-confirm',rect=(0,104,160,144),omit=((144,128,160,144),))
 for player in (1,2):p.pulse(player,0x5a,1)
 for player in (1,2):waitref(player,'animation',rect=(0,104,160,144),omit=((144,128,160,144),),timeout=60)
 for player in (1,2):p.pulse(player,0x5a,1)
 for player in (1,2):waitref(player,'offspring-full',rect=(0,104,160,144),omit=((144,128,160,144),),timeout=60)
 for player in (1,2):p.pulse(player,0x5a,1)
 for player in (1,2):waitref(player,'after-egg',rect=(0,104,160,144),omit=((144,128,160,144),))
 for player in (1,2):p.pulse(player,0x5a,1)
 for player in (1,2):waitref(player,'after-care',rect=(0,0,96,120),omit=((7,2,15,114),),timeout=40)
 p.api.close(p.windows[2],p.serial_process);p.report['linked_exit_code']=p.serial_process.returncode;p.active.clear()
 original=[p.initial[i*165:(i+1)*165] for i in range(40) if p.initial[i*165] in (1,2)];results=[]
 for player in (1,2):
  save=p.saves[player];process=p.start([str(p.exe),'--play',str(save),'--scale','1','--audio-volume','0'],f'fresh-p{player}')
  p.active[player]=process;p.windows[player]=p.api.find(process);p.saved_menu(player,f'fresh-p{player}');p.pulse(player,0x5a,1)
  p.wait(player,lambda pix:p.score('save_card',pix,omit=((7,2,15,24),))>=.99,'save-card',30);p.pulse(player,0x5a,1)
  p.wait(player,lambda pix:p.score('field',pix)>=.95,'fresh-original-home',30);p.api.close(p.windows[player],process);p.active.pop(player)
  b=save.read_bytes();after=[b[i*165:(i+1)*165] for i in range(40) if b[i*165] in (1,2)];old=[r for r in original if r not in after];new=[r for r in after if r not in original]
  if len(b)!=32768 or len(original)!=17 or len(after)!=17 or len(old)!=1 or len(new)!=1 or p.initial[0x3da0:0x3e0b]!=b[0x3da0:0x3e0b]:raise ValueError('Original roster or quest continuity differs')
  parent=int.from_bytes(old[0][11:13],'little');child=int.from_bytes(new[0][11:13],'little')
  if parent!=[2,246][player-1] or child!=[7,246][player-1] or new[0][109]!=2:raise ValueError('Unexpected parent or original offspring')
  results.append(dict(player=player,sha256=p.digest(save),original_owned_records=17,resulting_owned_records=17,other_records_identical=16,quest107_identical=True,parent_species=parent,child_species=child,child_plus=2,exit_code=process.returncode))
 p.report.update(status='passed',completed_breeding=True,original_p1_only=True,squiz_selected=False,fresh_process_reload=True,players=results)
 p.event('passed',players=results)
except Exception as e:
 p.report.update(status='failed',error=str(e));p.event('failed',error=str(e));raise
finally:p.finish()
