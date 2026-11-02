"""On a deadline, terminate only the explicitly identified isolated game."""
import os
import signal
import time
from pathlib import Path


def stop_game(session):
    marker=('Z:'+str(Path(session))).encode()
    matches=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args=(proc/'cmdline').read_bytes().split(b'\0')
        except (OSError, ProcessLookupError):
            continue
        if args and args[0].endswith(b'/DWM2tRecompFull.exe') and b'--m8-probe' in args and marker in args:
            matches.append(int(proc.name))
    if len(matches)!=1:
        raise RuntimeError('Cannot establish unique isolated game process: '+repr(matches))
    pid=matches[0]
    os.kill(pid,signal.SIGKILL)
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        try:
            state=Path(f'/proc/{pid}/stat').read_text().split()[2]
            if state=='Z':return pid
        except FileNotFoundError:
            return pid
        time.sleep(.01)
    raise RuntimeError('Isolated game did not terminate after timeout')
