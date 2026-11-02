"""Disposable local Wine probe; original no-button wait input only."""
import signal,time,hashlib
from pathlib import Path
from timeout_stop import stop_game
root=Path('/workspace/scratch/arena-b-2026-11-02/session34')
deadline=time.monotonic()+25
while not (root/'commands_executed.txt').exists() and time.monotonic()<deadline:time.sleep(.05)
assert (root/'commands_executed.txt').exists()
def stop(signum,frame):
    print('SIGALRM: stopped isolated game PID',stop_game(root),flush=True)
signal.signal(signal.SIGALRM,stop)
(root/'commands.txt').write_text('- 1 30000\n'*100)
signal.setitimer(signal.ITIMER_REAL,.25)
time.sleep(.5)
def count():return len((root/'commands_executed.txt').read_text().splitlines())
a=count();time.sleep(2);b=count()
print('Enqueued 100 waits; executed immediately and after 2 seconds:',a,b)
print('Stopped with pending commands:',a<100,'count remained unchanged:',a==b)
p=Path('/workspace/scratch/arena-b-2026-11-02/session29/training_cycle11.sav')
print('Seed Journal SHA256:',hashlib.sha256(p.read_bytes()).hexdigest())
