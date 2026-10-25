"""Replay original Sea World battle/recruitment/inn/Journal on a pinned Windows EXE.

This is a later field checkpoint, not Sea World completion or M8 acceptance.
No input save, cartridge state or executable is modified by this driver.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from m8_build_identity import load_identity

EXE_SHA = '4a12bd3197b414c888f50c606ccf3cb2ede030543f8058df83e0fcd67359e95d'
SEED_SHA = '6e05f52f2ead8b2ab7fa9f16d757668c39db924acd2b9295196740ca4ab8addd'
ROUTE_SHA = 'faee6b94a0896c23ac055b90ea2b65a9a18a661df77c9f78324b995cc8860cee'
FINAL_SHA = 'acf128eeeb75c5cb130c58bf692f39eb20c2129306bcb647bde784e7a14a770a'


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--route', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build-identity', type=Path,
                        help='Fresh diagnostic build identity; default preserves the historical pin')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'executable_source': '697647033b4ce6b00dd8e11759cb85e1ae469a65',
              'baseline_windows_run': 39836316030, 'seed_windows_run': 39846303155,
              'scope': 'Sea World village, recruitment/farm, inn and original Journal',
              'controller_frames': 8299, 'full_game_verified': False, 'sea_world_completed': False,
              'expected_executable_sha256': EXE_SHA, 'expected_seed_sha256': SEED_SHA,
              'expected_route_sha256': ROUTE_SHA, 'expected_final_sha256': FINAL_SHA}
    try:
        if os.name != 'nt':
            raise ValueError('This acceptance driver requires an actual Windows host')
        exe, original, route = [p.resolve(strict=True) for p in (args.exe, args.seed, args.route)]
        identity = load_identity(args.build_identity)
        identity.verify(exe)
        report.update(identity.report(), expected_executable_sha256=identity.sha256)
        if args.build_identity:
            report.update(historical_seed_windows_run=report.pop('seed_windows_run'),
                          historical_baseline_windows_run=report.pop('baseline_windows_run'))
        if original.stat().st_size != 32768 or digest(original) != SEED_SHA:
            raise ValueError('Original Sea World seed mismatch')
        if digest(route) != ROUTE_SHA:
            raise ValueError('P1 transcript mismatch')
        seed = out / 'seed-copy.sav'
        shutil.copyfile(original, seed)
        shutil.copyfile(route, out / route.name)
        command = [str(exe), '--m8-checkpoint-test', str(seed), str(route), str(out / 'native')]
        report['command'] = command
        with (out / 'native.log').open('xb') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=600, check=False)
        report['native_returncode'] = result.returncode
        if result.returncode != 0:
            raise RuntimeError(f'Native replay failed: {result.returncode}')
        final = out / 'native/checkpoint.sav'
        if final.stat().st_size != 32768 or digest(final) != FINAL_SHA:
            raise ValueError('Original village Journal differs from independently replayed discovery')
        log = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
        for marker in ('M8_TRACE_REPLAY_PASS', 'M8_FRESH_CONTINUE_PASS', 'M8_CHECKPOINT_PASS',
                       'frame=8299 mode=1:0 world=61 region=0,0 pos=112,48 party=3'):
            if marker not in log:
                raise ValueError(f'Missing native evidence: {marker}')
        saved = final.read_bytes()
        fresh = (out / 'native/fresh_continue/m8_0.sram').read_bytes()
        if len(fresh) != 32768:
            raise ValueError('Fresh Continue capture is not exact SRAM size')
        # Include the farm, not only the active party. The new ArmyAnt occupies
        # record 6; original Continue may change name-cache padding at 15..18,
        # but not these persistent status/level/experience/HP/MP/stat fields.
        for record in range(7):
            base = record * 0xA5
            if saved[base] == 0 or saved[base+0x55:base+0x6B] != fresh[base+0x55:base+0x6B]:
                raise ValueError(f'Persistent creature fields did not survive Continue: {record}')
        for record, hp in ((0, 60), (1, 44), (3, 32)):
            base = record * 0xA5
            actual = int.from_bytes(saved[base+0x5B:base+0x5D], 'little')
            maximum = int.from_bytes(saved[base+0x5D:base+0x5F], 'little')
            if actual != hp or actual != maximum:
                raise ValueError(f'Original inn healing is not preserved: {record}')
        for path, expected in ((exe, identity.sha256), (original, SEED_SHA), (seed, SEED_SHA), (route, ROUTE_SHA)):
            if digest(path) != expected:
                raise ValueError('An immutable input changed during native execution')
        identity.verify(exe)
        report.update(status='passed', final_sha256=digest(final), persistent_creature_bytes=154,
                      active_party_hp=[60, 44, 32], platform='Windows')
        print('M8_PIRATE_VILLAGE_WINDOWS_PASS original_battle_farm_inn_Journal_fresh_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_PIRATE_VILLAGE_WINDOWS_FAIL', error)
        return 1
    finally:
        (out / 'village-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
