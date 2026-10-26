"""Generate sparse synthetic CPU fixtures with the production AOT emitters.

Only the selected native case bodies and unmodified production master dispatch
are compiled. This never reads the original ROM or a game save, and it is not
an assertion that every entry in either complete original bank was exercised.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[2]/'tools'
sys.path.insert(0, str(TOOLS))
import recompile_bank0 as bank0_aot
import recompile_romx_bank as romx_aot


def fixture_banks() -> tuple[bytes, bytes, list[int], list[int]]:
    fixed = bytearray(0x4000)
    switchable = bytearray(0x4000)
    instructions = {
        0: bytes.fromhex('86'),             # CB boundary payload: RES0,(HL).
        0x100: bytes.fromhex('18 02'),       # JR +2.
        0x104: bytes.fromhex('CD 40 41'),    # CALL4140; return address must stay4107.
        0x107: bytes.fromhex('3E 5A'),       # LD A,5A.
        0x110: bytes.fromhex('01 34 12'),    # LD BC,1234.
        0x120: bytes.fromhex('20 02'),       # JR NZ,+2.
        0x140: bytes.fromhex('C9'),          # RET.
        0x1000: bytes.fromhex('3E 77'),
        0x2000: bytes.fromhex('3E 88'),
        0x3000: bytes.fromhex('3E 99'),
        0x3FFE: bytes.fromhex('01 CB'),      # LD BC reads high byte from next mapped window.
    }
    for offset, data in instructions.items():
        fixed[offset:offset+len(data)] = data
    switchable[0] = 0x46                    # CB boundary payload: BIT0,(HL).
    switchable[0x3FFF] = 0xCB               # CB operand comes from mapped VRAM.
    return bytes(fixed), bytes(switchable), sorted([*instructions, 0x3FFF]), [0, 0x3FFF]


def sparse_chunks(bank: bytes, offsets: list[int], fixed: bool) -> str:
    parts = ['// Synthetic unit fixture. Selected cases use actual production emitters.',
             '#include "recomp/bank0.hpp"', '#include "recomp/romx.hpp"',
             '#include "recomp/lr35902_exec.hpp"', 'namespace dwm2t {']
    for chunk in range(4):
        selected = [offset for offset in offsets if offset//0x1000 == chunk]
        for alias in ([False, True] if fixed else [False]):
            if fixed:
                function = f'execute_bank0_{"romx_" if alias else ""}chunk_{chunk}'
                body = '\n'.join(bank0_aot.emit_case(bank, offset, 0x4000 if alias else 0)
                                 for offset in selected)
            else:
                function = f'execute_romx_bank_1_chunk_{chunk}'
                body = '\n'.join(romx_aot.emit_case(bank, offset) for offset in selected)
            parts.append(f'StepResult {function}(Cpu& cpu, Memory& memory) {{\n'
                         f'    switch (cpu.pc) {{\n{body}\n'
                         '        default: cpu.trap(cpu.pc, memory.read8(cpu.pc));\n'
                         '                 return StepResult::Trapped;\n    }\n}')
    parts.append('}\n')
    return '\n'.join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    fixed, switchable, offsets0, offsets1 = fixture_banks()
    files = {'fixture_bank0_master.cpp': bank0_aot.emit_master(fixed),
             'fixture_bank0_chunks.cpp': sparse_chunks(fixed, offsets0, True),
             'fixture_bank1_master.cpp': romx_aot.emit_master(1),
             'fixture_bank1_chunks.cpp': sparse_chunks(switchable, offsets1, False)}
    stores = '\n'.join(f'    memory.set_rom_byte(0x{0x4000+i:X}u, 0x{value:02X}u);'
                       for i, value in enumerate(switchable) if value)
    files['fixture_rom_image.cpp'] = (
        '// Synthetic unit ROM only; never original game/save evidence.\n'
        '#include "recomp/memory.hpp"\n#include "recomp/bank0.hpp"\n'
        'namespace dwm2t {\nvoid load_full_rom_image(Memory& memory) {\n'
        f'    load_bank0_image(memory);\n{stores}\n}}\n}}\n')
    manifest = dict(schema=1, original_rom_read=False, original_game_executed=False,
                    synthetic_fixture=True, sparse_generated_cases=True,
                    bank0_offsets=offsets0, bank0_alias_cpu_base=0x4000,
                    bank1_offsets=offsets1,
                    emitted_case_bodies=2*len(offsets0)+len(offsets1),
                    fixture_bank0_sha256=hashlib.sha256(fixed).hexdigest(),
                    fixture_bank1_sha256=hashlib.sha256(switchable).hexdigest(),
                    production_generators=['recompile_bank0.py', 'recompile_romx_bank.py',
                                           'generate_romx_dispatch.py', 'lr35902.py'])
    files['fixture-source.json'] = json.dumps(manifest, indent=2)+'\n'
    for name, text in files.items():
        bank0_aot.write_text_if_changed(args.output/name, text)
    print('GENERATED_AOT_UNIT_FIXTURES sparse_cases='+str(manifest['emitted_case_bodies'])+
          ' original_ROM=false')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
