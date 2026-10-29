from pathlib import Path
import argparse,sys,shutil
sys.path.insert(0,'Z:/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07')
sys.path.insert(0,'Z:/workspace/DWM2t/recomp/tools')
import repeat_vs_probe as rp
from repeat_vs_probe import Probe
rp.SEED_SHA256='91b3690b8e7acee6a55118152497f0d57245236bce7c62d1b537ec0486180054'
args=argparse.Namespace(exe=Path('Z:/workspace/scratch/full-rom-2026-10-26/r4-audit/production/candidate/DWM2t-M8-UNTESTED/DWM2tRecomp.exe'),seed=Path('Z:/workspace/scratch/full-rom-2026-10-26/independent-postgame-r3-01/quietsea-clear/native/checkpoint.sav'),output=Path('Z:/workspace/scratch/full-rom-2026-10-26/key-trade-explore/fresh-01'),source='1351bcd058e491455a477045a2ff86bbc3bd7b1c',exe_sha256='63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95',environment='Wine on Linux')
p=Probe(args)
try:
 p.prepare();p.refs['cave']=p.bitmap(Path('Z:/workspace/scratch/full-rom-2026-10-26/independent-postgame-r3-01/quietsea-clear/native/fresh_continue/m8_0.bmp'))
 root=Path('Z:/workspace/scratch/full-rom-2026-10-26/key-trade-explore/run-01/profiles')
 results=[]
 for player in (1,2):
  source=root/f'player{player}.sav';save=p.saves[player];before=p.digest(source);shutil.copyfile(source,save)
  if p.digest(save)!=before:raise ValueError('actual post-trade journal copy differs')
  process=p.start([str(p.exe),'--play',str(save),'--scale','1','--audio-volume','0'],f'fresh-p{player}')
  p.active[player]=process;p.windows[player]=p.api.find(process);p.saved_menu(player,f'fresh-p{player}');p.pulse(player,0x5a,1)
  p.wait(player,lambda pix:p.score('save_card',pix,omit=((7,2,15,24),))>=.99,'save-card',30);p.pulse(player,0x5a,1)
  p.wait(player,lambda pix:p.score('cave',pix)>=.92,'fresh-original-quietsea',30);p.api.close(p.windows[player],process);p.active.pop(player)
  b=save.read_bytes();result={'player':player,'pre_continue_sha256':before,'post_continue_sha256':p.digest(save),'bytes':len(b),'quest107_same':b[0x3da0:0x3e0b]==p.initial[0x3da0:0x3e0b],'full_equal_seed':b==p.initial,'exit_code':process.returncode};results.append(result);p.event('fresh_continue',**result)
  if len(b)!=32768 or not result['quest107_same'] or process.returncode:raise ValueError('Fresh Continue failed')
 p.report.update(status='passed',original_p1_only=True,players=results)
finally:p.finish()
