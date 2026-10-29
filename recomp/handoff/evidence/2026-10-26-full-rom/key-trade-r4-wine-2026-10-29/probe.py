from pathlib import Path
import argparse,sys,time,hashlib
sys.path.insert(0,'Z:/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07')
sys.path.insert(0,'Z:/workspace/DWM2t/recomp/tools')
import repeat_vs_probe as rp
from repeat_vs_probe import Probe
rp.SEED_SHA256='91b3690b8e7acee6a55118152497f0d57245236bce7c62d1b537ec0486180054'
args=argparse.Namespace(exe=Path('Z:/workspace/scratch/full-rom-2026-10-26/r4-audit/production/candidate/DWM2t-M8-UNTESTED/DWM2tRecomp.exe'),seed=Path('Z:/workspace/scratch/full-rom-2026-10-26/independent-postgame-r3-01/quietsea-clear/native/checkpoint.sav'),output=Path('Z:/workspace/scratch/full-rom-2026-10-26/key-trade-explore/run-01'),source='1351bcd058e491455a477045a2ff86bbc3bd7b1c',exe_sha256='63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95',environment='Wine on Linux')
p=Probe(args)
try:
 p.prepare()
 command=[str(p.exe),'--play',str(p.saves[1]),'--link-save',str(p.saves[2]),'--scale','1','--audio-volume','0']
 p.serial_process=p.start(command,'linked');p.windows=dict(zip((1,2),p.api.pair(p.serial_process),strict=True));p.active={1:p.serial_process,2:p.serial_process}
 for player in (1,2):p.saved_menu(player,f'linked-p{player}')
 for player in (1,2):
  for index,selected in enumerate(('menu_new','menu_breeding','menu_key'),1):
   p.pulse(player,0x28);p.wait(player,lambda pix,selected=selected:p.is_menu(pix,selected),f'p{player}-down{index}',15)
 print('READY FOR COMMANDS',flush=True)
 keys={'z':0x5a,'x':0x58,'up':0x26,'down':0x28,'left':0x25,'right':0x27,'start':0x0d}
 index=0
 while True:
  line=input('KEYTRADE> ').strip().split()
  if not line:continue
  if line[0]=='q':break
  if line[0]=='p':
   for player in (1,2):p.observe(player);p.preserve(player,f'manual-{index}')
  elif len(line)==2 and int(line[0]) in (1,2) and line[1] in keys:
   player=int(line[0]);p.pulse(player,keys[line[1]],1.5);index+=1
   for who in (1,2):p.observe(who);p.preserve(who,f'manual-{index}')
  else:print('Expected 1 z, 2 z, p, or q',flush=True)
 p.api.close(p.windows[2],p.serial_process);p.active.clear()
 p.report.update(status='exploratory',linked_exit_code=p.serial_process.returncode)
finally:p.finish()
