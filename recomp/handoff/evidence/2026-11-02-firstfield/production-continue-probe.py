from pathlib import Path
import argparse, sys
sys.path.insert(0, 'Z:/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07')
sys.path.insert(0, 'Z:/workspace/DWM2t/recomp/tools')
import repeat_vs_probe as rp
from repeat_vs_probe import Probe
rp.SEED_SHA256='55b117bab52296d990e904f3736474c7a7ccdf81e2ecfc10d31805c72ed59609'
args=argparse.Namespace(exe=Path('Z:/workspace/scratch/full-rom-2026-10-26/r4-audit/production/candidate/DWM2t-M8-UNTESTED/DWM2tRecomp.exe'),seed=Path('Z:/workspace/scratch/key-validation-2026-11-02/firstfield-world-original-journal.sav'),output=Path('Z:/workspace/scratch/key-validation-2026-11-02/firstfield-prod-01'),source='1351bcd058e491455a477045a2ff86bbc3bd7b1c',exe_sha256='63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95',environment='Wine on Linux')
p=Probe(args)
try:
 p.prepare()
 p.refs['firstfield_castle']=p.bitmap(Path('Z:/workspace/scratch/key-validation-2026-11-02/firstfield-fresh/m8_0.bmp'))
 save=p.saves[1]; process=p.start([str(p.exe),'--play',str(save),'--scale','1','--audio-volume','0'],'production')
 p.active[1]=process;p.windows[1]=p.api.find(process);p.saved_menu(1,'production')
 p.pulse(1,0x5a,1.5);p.observe(1);p.preserve(1,'original-save-card')
 p.pulse(1,0x5a,1)
 pix=p.wait(1,lambda q:p.score('firstfield_castle',q)>=.90,'firstfield-fresh-continue',60)
 score=p.score('firstfield_castle',pix)
 p.api.close(p.windows[1],process);p.active.pop(1)
 actual=save.read_bytes();seed=p.initial
 if len(actual)!=32768 or process.returncode != 0:raise RuntimeError('native shutdown or save size differs')
 checks={'source_journal_unchanged':p.digest(p.seed)==rp.SEED_SHA256,'game_exe_unchanged':p.digest(p.exe)==args.exe_sha256,'entire_journal_identical':actual==seed,'all_key_records_identical':actual[0x3c0a:0x3c8a]==seed[0x3c0a:0x3c8a],'all_key_seeds_identical':actual[0x3c8a:0x3cca]==seed[0x3c8a:0x3cca],'all_107_quest_bytes_identical':actual[0x3da0:0x3e0b]==seed[0x3da0:0x3e0b],'working_and_backup_cache_identical':actual[0x4000:0x6000]==seed[0x4000:0x6000] and actual[0x6000:0x8000]==seed[0x6000:0x8000]}
 if not all(checks.values()):raise RuntimeError('FirstField original Journal data changed')
 p.report.update(kind='firstfield_production_fresh_continue',status='passed',fresh_process_reload=True,normal_shutdowns=1,firstfield_screen_similarity=score,checks=checks,output_save_sha256=p.digest(save));p.event('passed',screen_similarity=score,checks=checks)
finally:p.finish()
