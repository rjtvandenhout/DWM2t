from pathlib import Path
import argparse,sys,shutil,hashlib
sys.path.insert(0,'Z:/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07')
sys.path.insert(0,'Z:/workspace/DWM2t/recomp/tools')
import repeat_vs_probe as rp
from repeat_vs_probe import Probe
rp.SEED_SHA256='61510b4446b038f4034f90bfc5656b1861eb0f4abc6ae65ba65a44564c9ece3e'
a=argparse.Namespace(exe=Path('Z:/workspace/scratch/full-rom-2026-10-26/r4-audit/production/candidate/DWM2t-M8-UNTESTED/DWM2tRecomp.exe'),seed=Path('Z:/workspace/scratch/dreamegg-validation-2026-11-02/greatlog-386g-original-journal.sav'),output=Path('Z:/workspace/scratch/full-rom-2026-11-02/link-distinct/fresh-arena-b-prize-01'),source='1351bcd058e491455a477045a2ff86bbc3bd7b1c',exe_sha256='63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95',environment='Wine on Linux')
p=Probe(a)
try:
 p.prepare()
 root=Path('Z:/workspace/scratch/full-rom-2026-11-02/link-distinct/trade-arena-b-prize-01/profiles')
 original={1:p.seed,2:Path('Z:/workspace/scratch/arena-b-2026-11-02/session16/arena_b_champion.sav')}
 references={1:Path('Z:/workspace/scratch/dreamegg-validation-2026-11-02/fresh-clear/m8_183.bmp'),2:Path('Z:/workspace/scratch/arena-b-2026-11-02/session16/arena_b_champion_continue/m8_0.bmp')}
 expect={1:('fe03171b','b723'),2:('82041408','2719')}
 results=[]
 for player in (1,2):
  ref='expected_field_'+str(player);p.refs[ref]=p.bitmap(references[player]); source=root/f'player{player}.sav'; save=p.saves[player]
  before=p.digest(source);shutil.copyfile(source,save)
  if p.digest(save)!=before:raise ValueError('actual post-trade journal copy differs')
  process=p.start([str(p.exe),'--play',str(save),'--scale','1','--audio-volume','0'],f'fresh-p{player}')
  p.active[player]=process;p.windows[player]=p.api.find(process);p.saved_menu(player,f'fresh-p{player}');p.pulse(player,0x5a,1);p.pulse(player,0x5a,1)
  p.wait(player,lambda pix:p.score(ref,pix)>=.92,'fresh-original-location',30);p.api.close(p.windows[player],process);p.active.pop(player)
  b=save.read_bytes(); orig=original[player].read_bytes(); key,seed=expect[player]
  matches=[i for i in range(32) if b[0x3c0a+4*i:0x3c0e+4*i].hex()==key and b[0x3c8a+2*i:0x3c8c+2*i].hex()==seed]
  owned=[i for i in range(40) if orig[i*165] in (1,2)]
  roster=all(b[i*165:(i+1)*165]==orig[i*165:(i+1)*165] for i in owned)
  entry={'player':player,'input_original_sha256':p.digest(original[player]),'before_continue_sha256':before,'after_continue_sha256':p.digest(save),'bytes':len(b),'expected_received_key':key,'expected_received_seed':seed,'received_slots':matches,'owned_record_count':len(owned),'all_owned_records_unchanged':roster,'quest107_same':b[0x3da0:0x3e0b]==orig[0x3da0:0x3e0b],'exit_code':process.returncode};p.event('fresh_continue',**entry);results.append(entry)
  if len(b)!=32768 or not matches or not entry['quest107_same'] or not roster or process.returncode:raise ValueError('Fresh Continue or save identity failed')
 p.report.update(status='passed',players=results,original_p1_only=True,scope='original B-class prize Magic Key traded for FirstField, linked process exited normally; fresh Continue checks on both actual resulting saves')
finally:p.finish()
