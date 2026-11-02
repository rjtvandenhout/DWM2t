"""Bounded original-input QuietCrag training; stop on danger or unknown choice."""
import json
import signal
import time
from pathlib import Path

import control
import navigate as n
import battle_ui as b
from screen_text import read

def timed_out(signum, frame):
    from timeout_stop import stop_game
    pid=stop_game(n.root)
    raise TimeoutError(f'isolated game {pid} terminated after 180-second batch deadline')

prior_timer=signal.getitimer(signal.ITIMER_REAL)
prior_timer_start=time.monotonic()
previous_handler=signal.signal(signal.SIGALRM,timed_out)
signal.setitimer(signal.ITIMER_REAL,180)

def data():
    r=n.latest()
    p=max(n.root.glob('m8_*.sram'),key=lambda f:int(f.stem[3:]))
    s=p.read_bytes()
    party=list(r[0xc6fe:0xc6fe+r[0xc6fd]])
    if party != [12,0,10]:
        raise RuntimeError('Unexpected party identity/order; no further input: '+repr(party))
    records=[]
    for index in party:
        q=index*165
        records.append({'index':index,'status':s[q+0x55],'level':s[q+0x56],
                        'exp':int.from_bytes(s[q+0x58:q+0x5b],'little'),
                        'hp':int.from_bytes(s[q+0x5b:q+0x5d],'little'),
                        'max_hp':int.from_bytes(s[q+0x5d:q+0x5f],'little'),
                        'mp':int.from_bytes(s[q+0x5f:q+0x61],'little'),
                        'max_mp':int.from_bytes(s[q+0x61:q+0x63],'little')})
    return records

def emit(label,**fields):
    print(json.dumps({'event':label,'elapsed_seconds':round(time.monotonic()-started,3),
                      'party':data(),**fields}),flush=True)

def advance():
    """Advance only recognized action/experience text to FIGHT or field."""
    deadline=time.monotonic()+45
    known_notice=False
    for _ in range(120):
        if time.monotonic()>=deadline:
            from timeout_stop import stop_game
            pid=stop_game(n.root)
            raise TimeoutError(f'isolated game {pid} terminated after battle message deadline')
        r=n.latest()
        if r[0xc5db]!=4:
            if known_notice:raise RuntimeError('known recruitment notice ended unexpectedly; manual inspection required')
            return False
        phase=tuple(r[0xcfc8:0xcfcc]);text=read(r).lower()
        normalized=' '.join(text.split())
        if not known_notice and phase==(2,5,1,1) and any(normalized.endswith(name+' got up looking hopeful') for name in ('goopi','ironturt')):
            known_notice=True
            control.drive(['A 2 90']);continue
        if known_notice and phase==(2,5,1,1) and normalized.endswith('but it sadly went away'):
            known_notice=False
            control.drive(['A 2 180']);continue
        if known_notice:
            raise RuntimeError('Unexpected response to known recruitment notice; manual inspection required')
        if any(x in text for x in ('which skill','forget','learn a new','wants to join',
                                    'looking hopeful','enter name','please name','take along')):
            raise RuntimeError('Original recruitment/skill/name choice requires inspection')
        if phase[:2]==(2,5):
            raise RuntimeError('Original post-battle recruitment phase requires inspection')
        if phase==(1,1,0,3):
            data()  # Exact party identity/order must still match.
            if any(p in b.arrows() for positions in b.ROOT_POS for p in positions):return True
            control.drive(['- 1 8']);continue
        if phase[:2]==(1,1):
            # Wait out a known transitional state; never choose a menu blindly.
            control.drive(['- 1 8']);continue
        if phase[:2] in ((0,0),(1,3),(2,0),(2,2),(2,4),(2,6)):
            control.drive(['A 2 30']);continue
        raise RuntimeError('Unrecognized original battle phase '+repr(phase))
    raise RuntimeError('Bounded battle message step budget exceeded')

started=time.monotonic();won=0;movement=0;transition_waits=0
emit('start',scope='original P1 only; four encounters maximum')
while won<4 and movement<200:
    r=n.latest();mode=tuple(r[0xc5db:0xc5dd])
    if r[0xc5db]==4:
        before_exp={p['index']:p['exp'] for p in data()}
        if not advance():emit('battle_ended_before_menu');break
        before=b.words(n.latest(),0xd8bf)[:3]
        if any(hp<40 for hp in before):emit('stop_low_hp_before_plan',hp=before);break
        b.choose_root(2)
        for actor,choice in [('Garon',2),('Slash',0),('Derzo',0)]:
            b.choose_vertical(4,choice)
        for turn in range(30):
            if not advance():break
            hp=b.words(n.latest(),0xd8bf)[:3]
            if any(v==0 for v in hp):
                emit('stop_unconscious_in_battle',hp=hp,turn=turn);raise SystemExit(2)
            if min(hp)<40:
                emit('stop_low_hp_in_battle',hp=hp,turn=turn);raise SystemExit(2)
            b.choose_root(0)
        else:emit('stop_turn_budget');break
        r=n.latest();mode=tuple(r[0xc5db:0xc5dd])
        if mode==(1,0) and tuple(r[0xcc42:0xcc45])==(1,0,128):
            # Original battle transitions can briefly report field mode over a
            # white fade. Wait without input and require the actual field.
            control.drive(['- 1 180']);r=n.latest();mode=tuple(r[0xc5db:0xc5dd])
        if mode!=(1,5) or tuple(r[0xcc42:0xcc45])!=(1,0,128):
            emit('stop_postbattle_choice',mode=mode);break
        after=data()
        if any(p['hp']==0 or p['exp']<=before_exp.get(p['index'],p['exp']) for p in after):
            emit('stop_victory_not_confirmed',mode=mode);break
        won+=1
        emit('victory',number=won)
        if any(x['status']!=0 or x['hp']==0 or x['hp']*2<x['max_hp'] for x in data()):
            emit('stop_field_care_needed');break
        continue
    if mode in ((1,3),(1,6)):
        transition_waits+=1
        if transition_waits>8:emit('stop_transition_budget',mode=mode);break
        control.drive(['- 1 180']);continue
    if mode not in ((1,0),(1,5)):
        emit('stop_unexpected_mode',mode=mode);break
    # One tile at a time; no A inputs until the original battle menu exists.
    control.drive([('U' if movement%2==0 else 'D')+' 16 60'])
    movement+=1
    transition_waits=0
else:
    emit('bounded_batch_complete',victories=won,movements=movement)
signal.setitimer(signal.ITIMER_REAL,0)
signal.signal(signal.SIGALRM,previous_handler)
if prior_timer[0]>0:
    signal.setitimer(signal.ITIMER_REAL,max(0.001,prior_timer[0]-(time.monotonic()-prior_timer_start)),prior_timer[1])
