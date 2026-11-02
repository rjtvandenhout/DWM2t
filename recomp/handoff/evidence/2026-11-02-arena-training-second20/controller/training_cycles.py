"""Finite original-P1 training cycles; preserve a checked Journal each cycle."""
import hashlib
import json
from pathlib import Path
import runpy
import signal
import sys
import time

import control
import navigate as n
import battle_ui as b

MAX_CYCLES=1
HERE=Path(__file__).resolve().parent
overall=time.monotonic()

def cycle_timeout(signum,frame):
    from timeout_stop import stop_game
    pid=stop_game(n.root)
    raise TimeoutError(f'isolated game {pid} terminated after 300-second cycle deadline')

signal.signal(signal.SIGALRM,cycle_timeout)

def tell(event, **values):
    print(json.dumps({'event':event,'elapsed_seconds':round(time.monotonic()-overall,3),**values}),flush=True)

def status():
    r=n.latest()
    return n.loc(r),tuple(r[0xc5db:0xc5dd]),tuple(r[0xcc42:0xcc46])

def require(test,message):
    if not test:raise RuntimeError(message+'; observed '+repr(status()))

def require_full_original_party():
    r=n.latest();ids=list(r[0xc6fe:0xc6fe+r[0xc6fd]])
    require(ids==[12,0,10],'original party identity/order changed')
    p=max(n.root.glob('m8_*.sram'),key=lambda f:int(f.stem[3:]));s=p.read_bytes()
    for monster in ids:
        q=monster*165
        hp=int.from_bytes(s[q+0x5b:q+0x5d],'little');mh=int.from_bytes(s[q+0x5d:q+0x5f],'little')
        mp=int.from_bytes(s[q+0x5f:q+0x61],'little');mm=int.from_bytes(s[q+0x61:q+0x63],'little')
        require(s[q+0x55]==0 and hp==mh and mp==mm,'party not fully restored')

def goto_field_warp():
    # This specific training corridor is x=48 in QuietCrag region (5,2).
    for step in range(24):
        r=n.latest();loc=n.loc(r);mode=tuple(r[0xc5db:0xc5dd]);context=tuple(r[0xcc42:0xcc46])
        if context[2]==135:return
        if r[0xc5db]==4:
            for flee in range(4):
                if not battle_advance():break
                hp=b.words(n.latest(),0xd8bf)[:3]
                require(all(v>=40 for v in hp),'low/unconscious party on original return encounter')
                b.choose_root(3)
            require(n.latest()[0xc5db]!=4,'original flee budget exhausted')
            continue
        if mode in ((1,3),(1,6)):
            control.drive(['- 1 180']);continue
        require(mode==(1,5) and context[:3]==(1,0,128),'unexpected original QuietCrag field')
        require(loc[1:3]==(5,2) and loc[3] in (48,64),'outside tested return corridor')
        if loc[3]==48 and loc[4]<96:direction='D'
        elif loc[3]==48 and loc[4]>96:direction='U'
        elif loc[3]==48:direction='R'
        else:direction='D' if loc[4]<96 else 'U' if loc[4]>96 else 'R'
        before=loc
        control.drive([direction+' 16 90'])
        require(n.loc(n.latest())!=before or tuple(n.latest()[0xcc42:0xcc46])[2]==135,
                'original return movement blocked')
    raise RuntimeError('original return step budget exhausted')

for cycle in range(1,MAX_CYCLES+1):
    signal.setitimer(signal.ITIMER_REAL,300)
    require(status()[0]==(5,1,0,80,64) and status()[1]==(1,0),'expected saved GreatLog grotto')
    require_full_original_party()
    t0=time.monotonic();tell('cycle_start',cycle=cycle)
    # Original movement to the key door, then the existing QuietCrag key.
    sys.argv=['navigate.py','5','7','5'];n.run()
    require(status()[0]==(5,0,0,112,80),'key-room approach failed')
    control.drive(['L 32 60','U 16 40','A 6 50','D 6 35','D 6 35',
                   'A 6 40','A 6 150','A 6 400','- 1 500','D 70 100','L 16 60'])
    require(status()[0]==(3,5,2,48,96) and status()[1]==(1,5) and status()[2][:3]==(1,0,128),
            'original QuietCrag launch differed')
    result=runpy.run_path(str(HERE/'bounded_training.py'))
    battle_advance=result['advance']
    won=result['won'];party=result['data']()
    tell('cycle_training_done',cycle=cycle,wins=won,party=party)
    require(won==2 and status()[1]==(1,5),'bounded training stopped early')
    require(all(p['status']==0 and p['hp']*2>=p['max_hp'] for p in party),'party requires manual care')
    goto_field_warp()
    require(status()==((3,0,0,64,128),(1,5),(1,0,135,1)),
            'original key shrine context/location differed')
    control.drive(['U 64 50','A 6 50','R 6 50','A 6 40','A 6 120',
                   'A 6 400','- 1 400','talk 2500 16','D 6 50'])
    require(status()[0]==(5,1,0,80,64) and status()[1]==(1,0),'original GreatLog restoration did not finish')
    restored=result['data']()
    require(all(p['status']==0 and p['hp']==p['max_hp'] and p['mp']==p['max_mp'] for p in restored),
            'original Warubou did not fully restore the party')
    name='training_supervised_14'
    control.drive(['journal '+name])
    save=n.root/(name+'.sav');fresh=n.root/(name+'_continue')/'m8_0.sram'
    require(save.stat().st_size==32768 and fresh.stat().st_size==32768,'bad original Journal size')
    sha=hashlib.sha256(save.read_bytes()).hexdigest()
    require(sha==hashlib.sha256(fresh.read_bytes()).hexdigest(),'fresh Continue not byte-identical')
    tell('cycle_checkpoint',cycle=cycle,wins=won,elapsed_cycle=round(time.monotonic()-t0,3),
         journal=str(save),sha256=sha,fresh_continue_identical=True,party=result['data']())
    signal.setitimer(signal.ITIMER_REAL,0)
tell('finite_cycles_complete',cycles=MAX_CYCLES)
