"""Audit a passed Windows story prefix, then replay its later original Journals.

The boundary seed must be the exact original Journal from that prefix. This
avoids replaying unchanged, already archived routes for every later checkpoint.
It never seeds observational dumps or changes game state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from test_m8_farm_dancer import EXE_SHA, check_file, digest
from test_m8_story_checkpoints import main as replay, verify_creatures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'prefix-evidence', 'manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--prefix-run-id', required=True)
    parser.add_argument('--prefix-stage', required=True)
    parser.add_argument('--wine', type=Path)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('Refusing to overwrite existing suffix evidence')
    audit = dict(status='running', full_game_verified=False,
                 prefix_run_id=args.prefix_run_id, boundary_stage=args.prefix_stage,
                 prefix_checkpoints=0, replayed_checkpoints=0)
    try:
        manifest = args.manifest.resolve(strict=True)
        check_file(args.exe.resolve(strict=True), EXE_SHA, 725318144)
        manifest_hash = digest(manifest)
        data = json.loads(manifest.read_text(encoding='utf-8'))
        names = [stage['name'] for stage in data['stages']]
        if names.count(args.prefix_stage) != 1:
            raise ValueError('Prefix boundary must be a unique tracked checkpoint')
        count = names.index(args.prefix_stage)+1
        expected_saves = {stage['name']: stage['save_sha256'] for stage in data['stages']}
        prefix = args.prefix_evidence.resolve(strict=True)
        report_path = prefix/'story-checkpoints-validation.json'
        previous = json.loads(report_path.read_text(encoding='utf-8'))
        if (previous['status'] != 'passed' or previous['platform'] != 'Windows' or
                previous['executable_sha256'] != EXE_SHA or
                len(previous['stages']) != count):
            raise ValueError('Prefix must be a complete passed Windows chain on the pinned executable')
        for expected, observed in zip(data['stages'][:count], previous['stages'], strict=True):
            if (observed['stage'] != expected['name'] or observed['status'] != 'passed' or
                    observed['native_returncode'] != 0 or
                    observed['frames'] != expected['frames'] or
                    observed['route_sha256'] != expected['route_sha256'] or
                    observed['save_sha256'] != expected['save_sha256']):
                raise ValueError('Archived Windows checkpoint differs from the tracked prefix')
            stage = prefix/expected['name']
            source_hash = expected_saves[expected['seed_stage']] if 'seed_stage' in expected else data['seed_sha256']
            check_file(stage/'seed-copy.sav', source_hash, 32768)
            check_file(stage/'native/checkpoint.sav', expected['save_sha256'], 32768)
            check_file(stage/expected['route'], expected['route_sha256'])
            # Reapply the current read-only assertions, including all 64 quest
            # bytes and inherited records, to the archived native captures.
            verify_creatures(stage/'native', stage/'seed-copy.sav', expected)
        audit.update(prefix_checkpoints=count, prefix_report_sha256=digest(report_path),
                     prefix_executable_sha256=EXE_SHA,
                     boundary_save_sha256=data['stages'][count-1]['save_sha256'])
        later = json.loads(json.dumps(data['stages'][count:]))
        if not later:
            raise ValueError('No later tracked checkpoints remain to replay')
        available = set()
        for stage in later:
            dependency = stage.get('seed_stage')
            if dependency == args.prefix_stage:
                del stage['seed_stage']
            elif dependency not in available:
                raise ValueError('Later route requires a different earlier Journal')
            stage['route'] = str((manifest.parent/stage['route']).resolve(strict=True))
            available.add(stage['name'])
        inputs = out.with_name(out.name+'-inputs')
        inputs.mkdir(parents=True, exist_ok=False)
        derived = inputs/'suffix-manifest.json'
        derived.write_text(json.dumps(dict(data, seed_sha256=audit['boundary_save_sha256'],
                                           stages=later), indent=2)+'\n', encoding='utf-8')
        audit['suffix_manifest_sha256'] = digest(derived)
        if args.audit_only:
            audit.update(status='prefix-audited', later_checkpoints_unrun=len(later))
            print(f'M8_PREFIX_AUDIT_PASS original_Windows_Journals={count} suffix_not_run')
            return 0
        arguments = ['test_m8_story_checkpoints.py', '--exe', str(args.exe),
                     '--seed', str(prefix/args.prefix_stage/'native/checkpoint.sav'),
                     '--manifest', str(derived), '--output', str(out)]
        if args.wine:
            arguments += ['--wine', str(args.wine)]
        original_arguments = sys.argv
        try:
            sys.argv = arguments
            result = replay()
        finally:
            sys.argv = original_arguments
        check_file(manifest, manifest_hash)
        if result:
            raise RuntimeError('Later original replay did not pass')
        audit.update(status='passed', replayed_checkpoints=len(later),
                     cumulative_checkpoints=count+len(later))
        print(f'M8_STORY_SUFFIX_PASS audited_prefix={count} original_replayed={len(later)}')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        audit.update(status='failed', error=str(error))
        print('M8_STORY_SUFFIX_FAIL', error)
        return 1
    finally:
        out.mkdir(parents=True, exist_ok=True)
        (out/'prefix-audit.json').write_text(json.dumps(audit, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
