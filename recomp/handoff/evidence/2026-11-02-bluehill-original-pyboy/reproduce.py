"""Replay only original P1 input on PyBoy with the genuine Cobi ROM and Journal.

Usage: PYTHONPATH=/path/to/pyboy python reproduce.py --rom <cobi.gbc>
       --save <genuine-prechallenge.sav> --output <new-directory>
No emulator memory writes, cheats, save states, or save output are used.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from importlib.metadata import version
from pathlib import Path
from pyboy import PyBoy

ROM_SHA = '8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e'
SAVE_SHA = '5afe17c1e9817cf9229af195690ba0834fccbe8155bf9992e6415f6a45d4ee00'
HERE = Path(__file__).resolve().parent
KEYS = {'A':'a','B':'b','Start':'start','Select':'select','R':'right','L':'left','U':'up','D':'down'}

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def commands(path):
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.partition('#')[0].strip()
        if not line:
            continue
        name, duration, idle = line.split()
        if name not in (*KEYS, '-') or not duration.isdigit() or not idle.isdigit():
            raise ValueError('Invalid original-input command')
        yield name, int(duration), int(idle)

def main():
    arg = argparse.ArgumentParser(description=__doc__)
    for option in ('rom','save','output'):
        arg.add_argument('--'+option, type=Path, required=True)
    a = arg.parse_args()
    rom, save = a.rom.resolve(strict=True), a.save.resolve(strict=True)
    out = a.output.resolve()
    if digest(rom) != ROM_SHA or digest(save) != SAVE_SHA or save.stat().st_size != 32768:
        raise ValueError('The original Cobi ROM and genuine pre-challenge Journal must match')
    if version('pyboy') != '2.6.1':
        raise ValueError('Use PyBoy 2.6.1 for this recorded comparison')
    out.mkdir(parents=True, exist_ok=False)
    emu = PyBoy(str(rom), ram_file=io.BytesIO(save.read_bytes()), window='null',
                cgb=True, sound_emulated=True)
    emu.set_emulation_speed(0)
    def pulse(name, duration, idle):
        if name != '-': emu.button_press(KEYS[name])
        emu.tick(duration, render=True, sound=False)
        if name != '-': emu.button_release(KEYS[name])
        if idle: emu.tick(idle, render=True, sound=False)
    events=[]
    try:
        for event in commands(HERE/'prefix-p1.txt'): pulse(*event)
        for index, event in enumerate(commands(HERE/'followup-p1.txt'),1):
            pulse(*event)
            if index in (15,42,44,46,47,52,61,62,63):
                image=out/f'original-rom-{index:03}.png'
                emu.screen.image.save(str(image))
                inventory=bytes(emu.memory[0xc61d:0xc635])
                events.append({'step':index, 'frame':emu.frame_count,
                               'inventory_hex':inventory.hex(),
                               'occupied_slots':sum(value != 0 for value in inventory),
                               'image_sha256':digest(image),
                               'reference_image_matches':digest(image)==digest(HERE/image.name)})
        if (len(events)!=9 or events[0]['occupied_slots']!=8 or events[3]['occupied_slots']!=9
                or events[6]['occupied_slots']!=24 or events[-1]['occupied_slots']!=24
                or any(not event['reference_image_matches'] for event in events)):
            raise ValueError('Observed inventory or screenshots did not match this original-ROM run')
    finally:
        emu.stop(save=False)
    if digest(rom)!=ROM_SHA or digest(save)!=SAVE_SHA:
        raise ValueError('Original input ROM or Journal changed')
    result={'status':'passed','emulator':'PyBoy 2.6.1','hardware':'CGB',
            'rom_sha256':ROM_SHA,'journal_sha256':SAVE_SHA,'original_input_only':True,
            'memory_edits':False,'original_inputs_unchanged':True,'events':events}
    (out/'reproduction.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('BLUEHILL_ORIGINAL_ROM_PASS 8 initial slots, 16 prizes, 24 final slots')
if __name__=='__main__': main()
