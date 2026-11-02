"""Control one isolated original-game P1 session; observations never become seeds."""
from pathlib import Path
import json
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
OLD = Path('/workspace/scratch/arena-b-2026-11-02/control')
sys.path.insert(0, str(HERE))
import navigate as n

def drive(commands):
    if not commands:
        return
    allowed = {'A', 'B', 'U', 'D', 'L', 'R', '-', 'Start', 'Select',
               'walk', 'snapshot', 'talk', 'battle', 'flee', 'journal', 'quit'}
    for command in commands:
        parts = command.split()
        if not parts or parts[0] not in allowed:
            raise ValueError('Only original finite P1/Journal/observation commands are allowed')
    if 'M8_SESSION_FAIL' in n.log.read_text(errors='replace'):
        raise RuntimeError('Original native session has failed')
    images = [int(p.stem.split('_')[1]) for p in n.root.glob('m8_*.bmp')]
    before = max(images, default=-1)
    pending = list(commands) + ([] if commands[-1] == 'quit' else ['snapshot'])
    count = len((n.root/'commands_executed.txt').read_text().splitlines())
    with (n.root/'commands.txt').open('a') as stream:
        stream.write('\n'.join(pending)+'\n')
    deadline = time.monotonic()+55
    while time.monotonic() < deadline:
        text = n.log.read_text(errors='replace')
        if 'M8_SESSION_FAIL' in text or 'M8_RUNTIME_FAIL' in text:
            raise RuntimeError(text.splitlines()[-5:])
        done = len((n.root/'commands_executed.txt').read_text().splitlines())
        captures = sorted(n.root.glob('m8_*.ram'), key=lambda p:int(p.stem.split('_')[1]))
        if done >= count+len(pending):
            if pending[-1] == 'quit':
                return
            if captures and int(captures[-1].stem.split('_')[1]) >= before+len(pending):
                if captures[-1].stat().st_size == 65536 and captures[-1].with_suffix('.sram').stat().st_size == 32768:
                    return
        time.sleep(.03)
    from timeout_stop import stop_game
    pid=stop_game(n.root)
    raise TimeoutError(f'isolated game {pid} terminated after controller deadline: {commands}')

n.drive = drive
sys.path.insert(1, str(OLD))

def status():
    from screen_text import read
    r=n.latest()
    p=max(n.root.glob('m8_*.bmp'),key=lambda p:int(p.stem.split('_')[1]))
    print('STATE', n.loc(r), 'mode', tuple(r[0xc5db:0xc5dd]), 'image', p)
    print(read(r))
    print('\n'.join(n.log.read_text(errors='replace').splitlines()[-3:]))

if __name__ == '__main__':
    mode=sys.argv[1]
    if mode == 'input':
        drive([line for line in sys.argv[2].splitlines() if line.strip()])
        status()
    elif mode == 'status':
        status()
    elif mode == 'navigate':
        sys.argv=['navigate.py',*sys.argv[2:]]
        n.run()
        status()
    elif mode == 'interact':
        world,x,y=map(int,sys.argv[2:5])
        direction=sys.argv[5]
        sys.argv=['navigate.py',str(world),str(x),str(y)]
        n.run()
        r=n.latest();where=n.loc(r)
        if (where[0],where[1]*10+where[3]//16,where[2]*9+where[4]//16)!=(world,x,y) or tuple(r[0xc5db:0xc5dd])!=(1,0):
            raise RuntimeError('Original interaction target not reached')
        drive([direction+' 1 120','A 6 180'])
        runpy.run_path(str(OLD/'read_talk.py'),run_name='__main__')
        status()
    elif mode == 'helper':
        script=OLD/(sys.argv[2]+'.py')
        if not script.is_file():
            raise ValueError('Unknown original controller helper')
        sys.argv=[str(script),*sys.argv[3:]]
        runpy.run_path(str(script),run_name='__main__')
        status()
    else:
        raise ValueError('Expected status, input, navigate or helper')
