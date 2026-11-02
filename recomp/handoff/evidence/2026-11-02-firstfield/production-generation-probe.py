from pathlib import Path
import argparse,sys,time
sys.path.insert(0,'Z:/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07')
sys.path.insert(0,'Z:/workspace/DWM2t/recomp/tools')
import repeat_vs_probe as rp
from repeat_vs_probe import Probe
rp.SEED_SHA256='67f0ccce0a65951e8dbab96d24e9f753a5c9cf916ca89340afec84da7fe4c7cf'
args=argparse.Namespace(exe=Path('Z:/workspace/scratch/full-rom-2026-10-26/r4-audit/production/candidate/DWM2t-M8-UNTESTED/DWM2tRecomp.exe'),seed=Path('Z:/workspace/scratch/key-validation-2026-11-02/appraise-session/firstfield_appraised.sav'),output=Path('Z:/workspace/scratch/key-validation-2026-11-02/firstfield-production-generation-02'),source='1351bcd058e491455a477045a2ff86bbc3bd7b1c',exe_sha256='63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95',environment='Wine on Linux')
p=Probe(args)
try:
 p.prepare()
 for name,path in {'shop':'appraise-session/firstfield_appraised_continue/m8_0.bmp','door':'appraise-session/m8_47.bmp','choose':'appraise-session/m8_48.bmp','action':'appraise-session/m8_49.bmp','prompt':'firstfield-replay/m8_10.bmp','confirm':'firstfield-replay/m8_11.bmp','castle':'firstfield-fresh/m8_0.bmp'}.items():p.refs[name]=p.bitmap(Path('Z:/workspace/scratch/key-validation-2026-11-02')/path)
 save=p.saves[1];proc=p.start([str(p.exe),'--play',str(save),'--scale','1','--audio-volume','0'],'production');p.active[1]=proc;p.windows[1]=p.api.find(proc);p.saved_menu(1,'production')
 p.pulse(1,0x5a,1.2);p.observe(1);p.preserve(1,'original-save-card');p.pulse(1,0x5a,1)
 p.wait(1,lambda q:p.score('shop',q)>=.90,'continue-in-key-shop',60)
 def walk(key,frames):
  hwnd=p.windows[1];p.api.focus(hwnd)
  if not p.api.user.PostMessageW(hwnd,0x100,key,0):raise RuntimeError('keydown failed')
  time.sleep(frames/59.7)
  if not p.api.user.PostMessageW(hwnd,0x101,key,0):raise RuntimeError('keyup failed')
  time.sleep(2.1);p.event('original_p1_walk',key=key,hold_frames_requested=frames)
 for key,frames in [(0x28,65),(0x28,8),(0x28,16),(0x27,16),(0x28,16),(0x27,16),(0x28,112),(0x27,112),(0x27,64),(0x28,64),(0x25,112),(0x25,112),(0x25,80),(0x28,16),(0x25,32),(0x26,16)]:walk(key,frames)
 p.wait(1,lambda q:p.score('door',q)>=.90,'original-key-door',20)
 p.pulse(1,0x5a,1);p.wait(1,lambda q:p.score('choose',q)>=.96,'firstfield-selected',15)
 p.pulse(1,0x5a,1);p.wait(1,lambda q:p.score('action',q)>=.96,'firstfield-use-selected',15)
 p.pulse(1,0x5a,1.5);p.observe(1);p.preserve(1,'original-insert-key');p.pulse(1,0x5a,1)
 p.wait(1,lambda q:p.score('castle',q)>=.90,'newly-generated-firstfield-castle',90)
 p.pulse(1,0x28,.5);p.pulse(1,0x5a,.5);p.pulse(1,0x27,.3);p.pulse(1,0x28,.3);p.pulse(1,0x5a,.5)
 for _ in range(5):p.pulse(1,0x28,.3)
 p.pulse(1,0x5a,.5);p.pulse(1,0x5a,.5)
 p.wait(1,lambda q:p.score('prompt',q,(0,104,160,144))>=.98,'original-journal-prompt',20)
 p.pulse(1,0x5a,.7)
 p.wait(1,lambda q:p.score('confirm',q,(0,104,160,144))>=.98,'original-journal-confirmed',20)
 p.pulse(1,0x5a,.5);p.pulse(1,0x58,.5);p.pulse(1,0x58,.5);p.api.close(p.windows[1],proc);p.active.pop(1)
 b=save.read_bytes();expected=Path('Z:/workspace/scratch/key-validation-2026-11-02/firstfield-world-original-journal.sav').read_bytes()
 checks={'size':len(b)==32768,'original_key_records':b[0x3c0a:0x3c8a]==expected[0x3c0a:0x3c8a],'original_key_seeds':b[0x3c8a:0x3cca]==expected[0x3c8a:0x3cca],'original_quest_bytes':b[0x3da0:0x3e0b]==expected[0x3da0:0x3e0b],'generated_working_cache':b[0x4000:0x4000+405]==expected[0x4000:0x4000+405],'generated_backup_cache':b[0x6000:0x6000+405]==expected[0x6000:0x6000+405], 'original_input_seed_unchanged':p.digest(p.seed)==rp.SEED_SHA256,'executable_unchanged':p.digest(p.exe)==args.exe_sha256,'normal_exit':proc.returncode==0}
 p.event('original_saved_world_checks',checks=checks,output_save_sha256=p.digest(save))
 if not all(checks.values()):raise RuntimeError('Original generated save differs from replayed descriptor')
 p.report.update(kind='firstfield_production_generation',status='passed',checks=checks,output_save_sha256=p.digest(save),fresh_process_reload=False)
finally:p.finish()
