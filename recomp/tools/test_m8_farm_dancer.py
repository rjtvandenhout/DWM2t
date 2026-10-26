"""Pin the original farm exchange and living Sea World dancer on the tested EXE.

--wine permits a clearly labelled Linux compatibility run with Wine's Z: mapping.
This does not certify the Sea World boss, ending, or final M8 acceptance.
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
SEED_SHA = 'acf128eeeb75c5cb130c58bf692f39eb20c2129306bcb647bde784e7a14a770a'
# stage, argument, fixture SHA, original Journal SHA, frames, party, HP, location
STAGES = (
    ('farm', 'route', 'bf0d4f4294bea732b06cd80e6c27c3faeca3dcb258a5d0b37b5c09f0f602a080',
     'cef352a25c2322aaea4f1848302ba0e9c80a5326bdd1da2160c36184cd13531e',
     31476, (0, 3, 5), (60, 33, 30), 'world=0 region=1,2 pos=112,48'),
    ('ready', 'ready_route', '0d015ee3d7c81775a545cc0551e831a0b469c74e00c8ea1cb25ac042cf7f20e8',
     'ba22e38f13668d4d0c6cde9c1b4c8d4290a410d2a72f91f6e3235002e3bf3059',
     7275, (0, 5, 1), (60, 30, 44), 'world=0 region=1,2 pos=112,48'),
    ('village', 'village_route', '2afb1dfd2697a92b60f0763c9359833959122464e6988dda51fcc63880841a24',
     '5632ab2d6c200ca3c93f768d8d56843f2a9c32fe4f437f9572b4ea843a86e333',
     12966, (0, 5, 1), (47, 30, 42), 'world=60 region=0,0 pos=96,48'),
)


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_file(path: Path, expected: str, size: int | None = None) -> None:
    if (size is not None and path.stat().st_size != size) or digest(path) != expected:
        raise ValueError(f'Pinned input/output mismatch: {path.name}')


def validate_creatures(native: Path, party: tuple[int, ...], hp: tuple[int, ...]) -> None:
    saved = (native / 'checkpoint.sav').read_bytes()
    fresh = (native / 'fresh_continue/m8_0.sram').read_bytes()
    ram = (native / 'fresh_continue/m8_0.ram').read_bytes()
    if len(saved) != 32768 or len(fresh) != 32768 or len(ram) != 65536:
        raise ValueError('Incomplete cartridge output capture')
    if ram[0xC6FD:0xC701] != bytes((3, *party)):
        raise ValueError('Original Continue did not restore the dancer party')
    for record in range(7):
        base = record * 0xA5
        if saved[base] != (2 if record in party else 1):
            raise ValueError(f'Original farm/active status differs: {record}')
        if saved[base+0x55:base+0x6B] != fresh[base+0x55:base+0x6B]:
            raise ValueError(f'Persistent creature fields differ after Continue: {record}')
    if saved[5*0xA5+0x34:5*0xA5+0x3C] != bytes((0x61, 0x76, 255, 255, 255, 255, 255, 255)):
        raise ValueError('Picked-up creature lacks the original dance skill')
    for record, expected_hp in zip(party, hp, strict=True):
        base = record * 0xA5
        if saved[base+0x55] & 0x80 or int.from_bytes(saved[base+0x5B:base+0x5D], 'little') != expected_hp:
            raise ValueError(f'Original living creature HP differs: {record}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'route', 'ready-route', 'village-route', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--wine', type=Path, help='Explicit Linux Wine launcher; never labelled Windows')
    parser.add_argument('--build-identity', type=Path,
                        help='Fresh diagnostic build identity; default preserves the historical pin')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'executable_source': '697647033b4ce6b00dd8e11759cb85e1ae469a65',
              'baseline_windows_run': 39836316030, 'seed_windows_run': 39876912500,
              'platform': 'Wine on Linux' if args.wine else 'Windows',
              'full_game_verified': False, 'sea_world_completed': False, 'stages': []}
    try:
        if os.name != 'nt' and args.wine is None:
            raise ValueError('A Windows host or explicit --wine launcher is required')
        if os.name == 'nt' and args.wine is not None:
            raise ValueError('--wine is reserved for Linux compatibility runs')
        launcher = [str(args.wine.resolve(strict=True))] if args.wine else []
        exe, seed = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
        identity = load_identity(args.build_identity)
        identity.verify(exe)
        report.update(identity.report())
        if args.build_identity:
            for key in ('baseline_windows_run', 'seed_windows_run'):
                if key in report:report['historical_'+key] = report.pop(key)
        check_file(seed, SEED_SHA, 32768)
        inputs = [(exe, identity.sha256), (seed, SEED_SHA)]
        for _, attr, route_sha, *_ in STAGES:
            route = getattr(args, attr).resolve(strict=True)
            check_file(route, route_sha)
            inputs.append((route, route_sha))

        def runtime_path(path: Path) -> str:
            return 'Z:'+path.as_posix() if args.wine else str(path)

        for name, attr, route_sha, save_sha, frames, party, hp, location in STAGES:
            stage = out / name
            stage.mkdir()
            route = getattr(args, attr).resolve(strict=True)
            copied_seed = stage / 'seed-copy.sav'
            shutil.copyfile(seed, copied_seed)
            shutil.copyfile(route, stage / route.name)
            inputs.append((copied_seed, digest(seed)))
            native = stage / 'native'
            command = launcher + [str(exe), '--m8-checkpoint-test', runtime_path(copied_seed),
                                  runtime_path(route), runtime_path(native)]
            entry = {'stage': name, 'command': command, 'frames': frames, 'route_sha256': route_sha}
            report['stages'].append(entry)
            with (stage / 'native.log').open('xb') as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=600, check=False)
            entry['native_returncode'] = result.returncode
            if result.returncode:
                raise RuntimeError(f'{name}: native replay failed: {result.returncode}')
            seed = native / 'checkpoint.sav'
            check_file(seed, save_sha, 32768)
            text = (stage / 'native.log').read_text(encoding='utf-8', errors='replace')
            for marker in ('M8_TRACE_REPLAY_PASS', 'M8_FRESH_CONTINUE_PASS', 'M8_CHECKPOINT_PASS',
                           f'frame={frames} mode=1:0 {location} party=3'):
                if marker not in text:
                    raise ValueError(f'{name}: missing native evidence: {marker}')
            validate_creatures(native, party, hp)
            entry.update(status='passed', save_sha256=save_sha, active_party_records=party,
                         hp=hp, persistent_creature_bytes=154)
        ram = (native / 'fresh_continue/m8_0.ram').read_bytes()
        if not ram[0xCBE4] & 0x40:
            raise ValueError('Original village dance-introduction flag did not survive Continue')
        for path, expected in inputs:
            check_file(path, expected)
        identity.verify(exe)
        report['status'] = 'passed'
        print(f'M8_FARM_DANCER_PASS platform={report["platform"]} original_farm_flee_Journal_fresh_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_FARM_DANCER_FAIL', error)
        return 1
    finally:
        (out / 'farm-dancer-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
