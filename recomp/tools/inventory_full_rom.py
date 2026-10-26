#!/usr/bin/env python3
"""Inventory every original cartridge bank without executing the game.

This verifies byte preservation, not reachability or dynamic test coverage.
Native translation/build evidence remains separate from this source receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from generate_rom_image import BANK_COUNT, BANK_SIZE, EXPECTED_SHA256, parse_bank


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(root: Path) -> dict:
    bank_dir = root / 'src/banks'
    expected = {f'bank_{bank:03d}.asm' for bank in range(BANK_COUNT)}
    if {path.name for path in bank_dir.glob('bank_*.asm')} != expected:
        raise ValueError('Expected exactly the original 256 cartridge banks')
    records, chunks = [], []
    for bank in range(BANK_COUNT):
        relative = f'src/banks/bank_{bank:03d}.asm'
        path = root / relative
        data = parse_bank(path)
        chunks.append(data)
        records.append(dict(bank=bank, source=relative, bytes=len(data),
                            source_sha256=digest(path.read_bytes()),
                            original_bytes_sha256=digest(data),
                            rom_offset=bank * BANK_SIZE,
                            cpu_window=['0000', '3FFF'] if bank == 0 else ['4000', '7FFF']))
    rom = b''.join(chunks)
    if len(rom) != BANK_COUNT * BANK_SIZE or digest(rom) != EXPECTED_SHA256:
        raise ValueError('Reconstructed cartridge differs from the original Cobi ROM')
    cmake = (root / 'recomp/CMakeLists.txt').read_text(encoding='utf-8')
    default_full = bool(re.search(r'option\(DWM2T_ALL_ROMX\s+"[^"\n]*"\s+ON\)', cmake))
    inputs = ['src/banks', 'recomp/CMakeLists.txt',
              'recomp/tools/generate_rom_image.py', 'recomp/tools/recompile_bank0.py',
              'recomp/tools/recompile_romx_bank.py', 'recomp/tools/generate_romx_dispatch.py',
              'recomp/tools/lr35902.py', 'recomp/tools/inventory_full_rom.py']
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit):
        raise ValueError('Expected a complete Git source identity')
    status = subprocess.check_output(
        ['git', 'status', '--porcelain', '--untracked-files=normal', '--', *inputs],
        cwd=root, text=True).splitlines()
    return dict(schema=1, kind='original_cartridge_source_inventory',
                source_commit=source_commit, source_inputs_match_commit=not status,
                source_input_changes=status, runtime_execution_performed=False,
                dynamic_coverage_claimed=False, native_build_verified_by_this_receipt=False,
                target='Original Cobi USA cartridge in the native CGB target',
                rom_bytes=len(rom), rom_sha256=digest(rom), bank_count=len(records),
                bytes_per_bank=BANK_SIZE, default_all_romx=default_full,
                intended_aot_entries_per_bank=BANK_SIZE,
                original_byte_entry_addresses=BANK_COUNT * BANK_SIZE,
                bank_zero_alias='The switchable window may mirror physical bank 0; this adds no cartridge bytes',
                source_tool_sha256=digest(Path(__file__).read_bytes()),
                translation_inputs={relative: digest((root / relative).read_bytes())
                                    for relative in inputs[1:]}, banks=records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inventory(args.root.resolve(strict=True))
    if not report['default_all_romx']:
        raise SystemExit('The normal product configuration does not default to all ROMX banks')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(f"FULL_ROM_SOURCE_INVENTORY banks={report['bank_count']} "
          f"bytes={report['rom_bytes']} sha256={report['rom_sha256']} "
          f"source_inputs_match_commit={report['source_inputs_match_commit']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
