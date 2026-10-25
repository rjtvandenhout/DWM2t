"""Verify new original Sea World inputs against an exact previously tested EXE.

This proves the recorded arrival, field battle, recruitment/farm, Journal and
fresh Continue only. It does not prove a Sea World boss, ending or full M8.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from m8_build_identity import load_identity

SOURCE = '697647033b4ce6b00dd8e11759cb85e1ae469a65'
EXE_SHA = '4a12bd3197b414c888f50c606ccf3cb2ede030543f8058df83e0fcd67359e95d'
SEED_SHA = 'a48fb7b52d6b5063f03725d205f96964174b44afbb3600782892ba44caeaa91a'
ROUTE_SHA = '36d3de2795b20b10e7284409990d412f1ef0e25d253f9889a115ea0ba774e474'
FINAL_SHA = '6e05f52f2ead8b2ab7fa9f16d757668c39db924acd2b9295196740ca4ab8addd'


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--route', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build-identity', type=Path,
                        help='Fresh diagnostic build identity; default preserves the historical pin')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'platform': 'Windows', 'executable_source': SOURCE,
              'baseline_run': 39836316030, 'scope': 'Sea World field progression, not full M8',
              'expected_executable_sha256': EXE_SHA, 'expected_seed_sha256': SEED_SHA,
              'expected_route_sha256': ROUTE_SHA, 'expected_final_sha256': FINAL_SHA}
    try:
        exe, route = args.exe.resolve(strict=True), args.route.resolve(strict=True)
        candidates = sorted(args.evidence.resolve(strict=True).glob('local-validation/m8_oasis/oasis-*/story-09/checkpoint.sav'))
        if len(candidates) != 1:
            raise ValueError('Expected exactly one recorded Kids Class Journal')
        original = candidates[0]
        identity = load_identity(args.build_identity)
        identity.verify(exe)
        report.update(identity.report(), expected_executable_sha256=identity.sha256)
        if args.build_identity:
            report.update(baseline_run=None, historical_baseline_run=39836316030,
                          baseline_evidence=str(args.evidence.resolve()))
        if original.stat().st_size != 32768 or digest(original) != SEED_SHA:
            raise ValueError('Original Kids Class checkpoint mismatch')
        if digest(route) != ROUTE_SHA:
            raise ValueError('Recorded controller fixture mismatch')
        seed = out / 'kids-class-copy.sav'
        shutil.copyfile(original, seed)
        shutil.copyfile(route, out / route.name)
        command = [str(exe), '--m8-checkpoint-test', str(seed), str(route), str(out / 'native')]
        report['command'] = command
        with (out / 'native.log').open('xb') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=600, check=False)
        report['native_returncode'] = result.returncode
        if result.returncode != 0:
            raise RuntimeError(f'Native checkpoint failed with exit {result.returncode}')
        final = out / 'native/checkpoint.sav'
        if not final.is_file() or final.stat().st_size != 32768 or digest(final) != FINAL_SHA:
            raise ValueError('Original Sea World Journal did not match discovery/replay')
        log = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
        if 'M8_CHECKPOINT_PASS' not in log or 'M8_FRESH_CONTINUE_PASS' not in log:
            raise ValueError('Native original Save/fresh-Continue evidence missing')
        if digest(original) != SEED_SHA or digest(seed) != SEED_SHA or digest(route) != ROUTE_SHA:
            raise ValueError('Immutable inputs changed during execution')
        identity.verify(exe)
        report.update(status='passed', final_sha256=digest(final), controller_frames=12398,
                      full_game_verified=False, sea_world_completed=False)
        print('M8_PIRATE_WINDOWS_PASS original_P1_battle_recruitment_Journal_and_fresh_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_PIRATE_WINDOWS_FAIL', error)
        return 1
    finally:
        (out / 'pirate-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
