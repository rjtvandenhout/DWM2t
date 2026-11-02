"""One finite S-Class trial from genuine level-41 Journal, original input only."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

import navigate as n

delay = int(sys.argv[1])
run = int(sys.argv[2])
if delay not in (73, 147, 221, 295, 369) or not 1 <= run <= 5:
    raise ValueError('unexpected finite trial identifier or delay')
base = Path('/workspace/scratch/arena-b-2026-11-02')
out = base / ('s-batch-' + str(run))
out.mkdir(exist_ok=False)
n.root = out
n.log = out.with_suffix('.log')
import control
import battle_ui as b
import safe_battle
from screen_text import read

seed = base / 'session28/trained_garon41.sav'
exe = Path('/workspace/scratch/full-rom-2026-10-26/r4-audit/audit-diagnostic/extracted/diagnostic-output/DWM2tRecompFull.exe')
assert hashlib.sha256(seed.read_bytes()).hexdigest() == 'a261d433e47f1ad62fbcdf43e6095d49afd170ad0ebe2aedf22f4964b572f797'
assert hashlib.sha256(exe.read_bytes()).hexdigest() == '61a0e6d3ff84b5322b101247fc93ff6889f123a1bcd94df663135757fb3b9855'
env = os.environ.copy()
env.update(DISPLAY=':146', WINEPREFIX=str(base/'wineprefix'),
           WINEDLLPATH='/workspace/.tools/wine-root/usr/lib/x86_64-linux-gnu/wine',
           WINESERVER='/workspace/.tools/wine-root/usr/lib/wine/wineserver64', WINEDEBUG='-all',
           LD_LIBRARY_PATH='/workspace/.tools/wine-root/usr/lib/x86_64-linux-gnu')
wine = '/workspace/.tools/wine-root/usr/lib/wine/wine64'
log = n.log.open('w')
proc = subprocess.Popen([wine, str(exe), '--m8-probe',
                         'Z:' + str(seed), 'Z:' + str(out)], env=env,
                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
for _ in range(400):
    if (out/'m8_0.ram').exists() and (out/'m8_0.ram').stat().st_size == 65536 and (out/'commands_executed.txt').exists():
        break
    if proc.poll() is not None: raise RuntimeError('original diagnostic stopped on Continue')
    time.sleep(.05)
else: raise TimeoutError('original Continue')

commands = (base/'session28/commands_executed.txt').read_text().splitlines()
assert commands[249] == 'journal trained_garon41'
control.drive(commands[251:280] + ['- 1 '+str(delay)] + commands[280:305])
r = n.latest()
if r[0xc5db] != 4 or not b.next_root(): raise RuntimeError('original S battle root not reached')
print('START',run,'idle_frames',delay,'party',b.words(n.latest(),0xd8bf)[:3],flush=True)
b.choose_root(2)
for name,choice in [('Garon',2),('Slash',0),('Derzo',0)]:
    print('ORIGINAL_TACTIC',name,choice,flush=True)
    b.choose_vertical(4,choice)
b.next_root()
for round_number in range(1,4):
    if n.latest()[0xc5db] == 4:
        safe_battle.run()
    r=n.latest()
    print('ROUND_END',run,round_number,'location',n.loc(r),'mode',tuple(r[0xc5db:0xc5dd]),
          'text',' '.join(read(r).split())[-150:],flush=True)
    if n.loc(r)[0] == 4:
        print('RESULT LOSS',run,'round',round_number,flush=True)
        control.drive(['quit']);proc.wait(timeout=15);log.close();sys.exit(0)
    if round_number == 3:
        title=' '.join(read(r).split())
        if 'S Class' in title and 'champion' in title.lower():
            print('RESULT POSSIBLE_S_WIN_REQUIRES_FINAL_CONFIRMATION',run,flush=True)
            log.flush();sys.exit(0)
        print('RESULT UNRESOLVED_AFTER_ROUND3',run,title,flush=True)
        log.flush();sys.exit(2)
    for step in range(50):
        r=n.latest()
        if r[0xc5db] == 4: break
        if n.loc(r)[0] == 4:
            print('RESULT LOSS',run,'between_rounds',round_number,flush=True)
            control.drive(['quit']);proc.wait(timeout=15);log.close();sys.exit(0)
        control.drive(['A 6 120'])
    else: raise RuntimeError('bounded original round transition did not finish')
print('UNEXPECTED_END',flush=True)
