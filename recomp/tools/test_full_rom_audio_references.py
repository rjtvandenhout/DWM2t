"""Guard measured audio-reference updates without weakening original P1 checks.

The frozen ledger binds 58 original routes and 375 exact audio boundaries to
81cfb26. It preserves every other route byte, allowing only one separately
approved, actual same-Memory-proven Kids raster screen pin. Story/postgame
expectations remain frozen except their resulting route hashes.
Observation receipts are provenance, not a substitute for strict native replay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


BASELINE_SOURCE = '81cfb26e2e30815640a5c80463c662eaf2f11ead'
WINDOWS_REFERENCE_EXE_SHA = 'b1c141d5b3cbb9640ae0af8831e7d369560a3785097cc6834f1734417b2538b3'
WINDOWS_REFERENCE_EXE_BYTES = 730169344
BASELINE_SHA256 = '79f7b8e5df69022e3864815f7f36d6b98ac065ddda374a7d48a4d7feef83fa57'
CONSUMER_BASELINE_SHA256 = '9c1234ae2fb6f6080cd946515feaf701075bc7e4d55d05cf51f5017532e32d3d'
# Filled only after all actual observation receipts have been independently
# checked against the frozen inputs; an incomplete ledger cannot pass.
MEASURED_REFERENCE_SHA256 = '65ceb2828e8bfd8e105c678e5d830697e5b64a01f9788f78dba49977bce4e63a'
ROUTE_COUNT = 58
PIN_COUNT = 375
MANIFESTS = ('recomp/tests/m8_sea_story_checkpoints.json',
             'recomp/tests/m8_postgame_supplemental.json')
CONSUMERS = ('recomp/tools/test_m8_farm_dancer.py', 'recomp/tools/test_m8_party_preparation.py',
             'recomp/tools/test_m8_pirate_pinned.py', 'recomp/tools/test_m8_pirate_village.py')
P1_COMMANDS = frozenset(('-', 'R', 'L', 'U', 'D', 'A', 'B', 'Start', 'Select'))
BASELINE_ROUTE_FIELDS = ('before_sha256', 'before_bytes', 'non_audio_bytes_sha256',
                         'baseline_lf_sha256', 'baseline_crlf_sha256',
                         'cumulative_p1_frames', 'audio_pin_count')
BASELINE_PIN_FIELDS = ('index', 'original_line_number', 'cumulative_p1_frames',
                       'before_line', 'before')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def is_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def baseline_projection(ledger: dict) -> dict:
    """The independent constant prevents accidentally moving the baseline."""
    return dict(
        source=ledger['baseline_source_commit'], routes={name:dict(
            **{key:route[key] for key in BASELINE_ROUTE_FIELDS},
            pins=[{key:pin[key] for key in BASELINE_PIN_FIELDS} for pin in route['pins']])
            for name, route in ledger['routes'].items()},
        manifests={name:{key:manifest[key] for key in (
            'before_sha256', 'non_route_sha256_invariants_sha256', 'stage_count')}
            for name, manifest in ledger['manifests'].items()})


def measured_projection(ledger: dict) -> dict:
    return dict(source=ledger['observation_source_commit'],
        windows_reference_executable_sha256=ledger['windows_reference_executable_sha256'],
        windows_reference_executable_bytes=ledger['windows_reference_executable_bytes'],
        producers=ledger['producer_registry'],
        failed_discovery_attempts=ledger['failed_discovery_attempts'],
        causal_probe=ledger['causal_probe'],
        approved_screen_changes=ledger['approved_screen_changes'],
        consumers={name:{key:consumer[key] for key in ('after_sha256', 'after_crlf_sha256', 'after_tokens')}
                   for name, consumer in ledger['consumers'].items()},
        routes={name:dict(after_sha256=route['after_sha256'],
            after_crlf_sha256=route['after_crlf_sha256'], observation=route['observation'],
            pins=[dict(after=pin['after'], after_line=pin['after_line'],
                       capture=pin['observation_capture']) for pin in route['pins']])
            for name, route in ledger['routes'].items()},
        manifests={name:manifest['after_sha256'] for name, manifest in ledger['manifests'].items()})


def consumer_baseline_projection(ledger: dict) -> dict:
    return dict(source=ledger['consumer_baseline_source_commit'],
                files={name:{key:value for key, value in consumer.items()
                             if key not in ('after_sha256', 'after_crlf_sha256', 'after_tokens')}
                       for name, consumer in ledger['consumers'].items()})


def audio_values(line: str) -> dict:
    match = re.fullmatch(r'expect_audio ([0-9]+) ([0-9]+) ([0-9]+) ([0-9a-f]{1,16})', line)
    require(match is not None, 'Malformed exact audio pin')
    samples, nonzero, peak = (int(match[index]) for index in (1, 2, 3))
    require(samples <= (1 << 64)-1 and samples % 2 == 0 and 0 <= nonzero <= samples
            and 0 <= peak <= 32768, 'Invalid stereo sample count, nonzero count or peak')
    return dict(sample_values=samples, nonzero=nonzero, peak=peak,
                hash=match[4].zfill(16))


def parse_route(data: bytes) -> tuple[int, list[dict], bytes]:
    frames, pins, other = 0, [], []
    for number, raw in enumerate(data.splitlines(keepends=True), 1):
        line = raw.decode('utf-8').rstrip('\r\n')
        if raw.startswith(b'expect_audio '):
            pins.append(dict(line=number, frames=frames, text=line, values=audio_values(line)))
            continue
        other.append(raw)
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        if words[0] in P1_COMMANDS:
            require(len(words) == 3 and all(re.fullmatch(r'[0-9]+', item) for item in words[1:]),
                    'Malformed original P1 command')
            frames += int(words[1])+int(words[2])
        else:
            require(words[0] in ('expect', 'expect_sram', 'expect_screen'),
                    'Unrecognized non-audio route command')
    return frames, pins, b''.join(other)


def manifest_invariants(data: dict) -> str:
    # Copy through canonical JSON; remove only this one allowed field.
    invariant = json.loads(canonical(data))
    for stage in invariant['stages']:
        require(is_sha(stage.get('route_sha256')), 'Missing exact manifest route hash')
        del stage['route_sha256']
    return digest(canonical(invariant))


def repository_file(root: Path, name: str) -> Path:
    require(isinstance(name, str) and name.startswith(('recomp/tests/', 'recomp/tools/')) and '\\' not in name
            and ':' not in name and PurePosixPath(name).as_posix() == name
            and not any(part in ('', '.', '..') for part in name.split('/')),
            'Unsafe original route/manifest path')
    path = root/name
    require(path.is_file() and not path.is_symlink()
            and path.resolve().is_relative_to(root.resolve()), 'Missing original route/manifest: '+name)
    return path


def evidence_identity(value: object, label: str) -> None:
    require(isinstance(value, dict) and isinstance(value.get('path'), str) and bool(value['path'])
            and is_sha(value.get('sha256')) and type(value.get('bytes')) is int
            and value['bytes'] > 0, 'Missing retained observation evidence identity: '+label)


def producer_registry(ledger: dict) -> dict:
    """Keep actual Windows PE and instrumented sparse Linux ELF identities separate."""
    registry = ledger.get('producer_registry')
    require(isinstance(registry, dict) and bool(registry), 'Missing measured producer registry')
    windows = 0
    for name, producer in registry.items():
        require(isinstance(name, str) and re.fullmatch(r'[a-z0-9_-]+', name) is not None
                and isinstance(producer, dict) and producer.get('status') == 'verified_discovery_producer'
                and producer.get('source_commit') == BASELINE_SOURCE
                and producer.get('acceptance') is False and producer.get('fixed_bank') == 0
                and producer.get('game_rom_cpu_memory_runtime_unchanged') is True,
                'Unverified or misidentified observation producer')
        evidence_identity(producer.get('executable'), name+':executable')
        evidence_identity(producer.get('source_input_manifest'), name+':source inputs')
        evidence_identity(producer.get('build_provenance'), name+':build provenance')
        banks = producer.get('compiled_romx_banks')
        require(isinstance(banks, list) and banks and banks == sorted(set(banks))
                and all(type(bank) is int and bank in range(1, 256) for bank in banks),
                'Actual compiled ROMX bank set is required')
        if producer.get('kind') == 'windows_full_aot_command_observer':
            windows += 1
            require(producer.get('platform') == 'Wine on Linux'
                    and producer.get('executable_format') == 'PE32+ x64'
                    and producer['executable']['sha256'] == WINDOWS_REFERENCE_EXE_SHA
                    and producer['executable']['bytes'] == WINDOWS_REFERENCE_EXE_BYTES
                    and banks == list(range(1, 256))
                    and producer.get('complete_255_bank_coverage') is True
                    and producer.get('instrumentation_diff') is None
                    and producer.get('non_audio_assertions_enforced') is False
                    and producer.get('non_audio_assertions_compared') is True,
                    'The Windows reference must identify its actual complete unmodified executable')
        elif producer.get('kind') == 'linux_sparse_aot_audio_comparator_logger':
            require(producer.get('platform') == 'Linux'
                    and producer.get('executable_format') == 'ELF64 x86-64'
                    and len(banks) < 255 and producer.get('complete_255_bank_coverage') is False
                    and producer.get('audio_assertions_enforced') is False
                    and producer.get('non_audio_assertions_enforced') is True
                    and producer.get('missing_bank_and_runtime_failures_retained') is True
                    and producer.get('frozen_source_inputs_verified') is True
                    and producer.get('instrumentation_scope') == 'Only expect_audio comparison emits actual tuple'
                    and producer.get('original_m8_sha256') == '4e54a616232c4d7d549cd54510758683a212905959a539366885ff0ff33fdf68'
                    and producer.get('observer_m8_sha256') == '288f80544195ed2d72ebadcacf149a93fc89b9f6238522f169795085f8f8ce1e',
                    'Sparse Linux discovery cannot claim Windows identity or complete-AOT acceptance')
            evidence_identity(producer.get('instrumentation_diff'), name+':audio-only instrumentation')
            require(producer['instrumentation_diff']['sha256'] == 'e54887281a8b006bb3c8daa73a26ee1c587696d928f3fce475cd489716022869',
                    'The Linux producer must retain the exact reviewed audio-only instrumentation')
            checks = producer.get('windows_crosschecks')
            require(isinstance(checks, list) and len(checks) >= 3
                    and len({check.get('route') for check in checks if isinstance(check, dict)}) == len(checks),
                    'Three distinct whole-route Windows/Linux crosschecks are required')
            for check in checks:
                require(isinstance(check, dict) and check.get('source_commit') == BASELINE_SOURCE
                        and check.get('linux_executable_sha256') == producer['executable']['sha256']
                        and check.get('windows_executable_sha256') == WINDOWS_REFERENCE_EXE_SHA
                        and check.get('all_audio_tuples_equal') is True
                        and check.get('all_non_audio_assertions_passed') is True
                        and check.get('whole_route_frames_equal') is True
                        and check.get('final_sram_equal') is True
                        and check.get('final_bitmap_equal') is True
                        and check.get('final_non_hardware_ram_equal') is True
                        and check.get('acceptance') is False,
                        'Linux producer crosscheck is incomplete or belongs to another executable')
                for key in ('report', 'linux_receipt', 'windows_receipt'):
                    evidence_identity(check.get(key), name+':crosscheck '+key)
        else:
            raise ValueError('Unknown observation producer kind')
    require(windows == 1, 'Exactly one pinned complete Windows reference producer is required')
    return registry


def approved_screens(ledger: dict) -> list[dict]:
    """Dormant until one independently proven exact raster correction is approved."""
    changes = ledger.get('approved_screen_changes')
    require(isinstance(changes, list) and len(changes) <= 1,
            'At most the separately approved Kids raster screen change is allowed')
    for change in changes:
        expected = dict(route='recomp/tests/m8_kids_class_victory_p1.txt',
                        original_line_number=535, cumulative_p1_frames=14370,
                        before_line='expect_screen 9a38ae3eef2d8568',
                        after_line='expect_screen be55670a278cea50',
                        approved=True, approved_by='root',
                        approval_scope='Actual same-Memory renderer A/B and completed per-line SCY proof')
        require(isinstance(change, dict) and all(change.get(key) == value
                and type(change.get(key)) is type(value) for key, value in expected.items()),
                'Unapproved or expanded screen-reference exception')
        mismatch = change.get('original_mismatch')
        require(isinstance(mismatch, dict)
                and mismatch.get('route_line') == expected['original_line_number']
                and mismatch.get('frame') == expected['cumulative_p1_frames']
                and mismatch.get('original_line') == expected['before_line']
                and mismatch.get('expected') == int(expected['before_line'].split()[1], 16)
                and mismatch.get('actual') == int(expected['after_line'].split()[1], 16)
                and mismatch.get('equal') is False and type(mismatch.get('capture')) is int,
                'The original screen mismatch must remain recorded without alteration')
        evidence = change.get('approval_evidence')
        require(isinstance(evidence, dict), 'Missing independently approved raster evidence')
        for key in ('same_memory_renderer_ab', 'completed_scanline_scroll', 'original_observation_receipt'):
            evidence_identity(evidence.get(key), 'approved Kids screen: '+key)
    return changes


def restore_approved_screens(data: bytes, name: str, changes: list[dict]) -> bytes:
    """Inverse only an exact approved line before checking the frozen other bytes."""
    lines = data.splitlines(keepends=True)
    for change in changes:
        if change['route'] != name:
            continue
        number = change['original_line_number']
        require(0 < number <= len(lines), 'Approved screen boundary was removed')
        raw = lines[number-1]
        require(raw.decode().rstrip('\r\n') == change['after_line'],
                'Approved screen line differs from the exact measured correction')
        frames = sum(int(words[1])+int(words[2]) for line in lines[:number-1]
                     if (words := line.split()) and words[0].decode() in P1_COMMANDS)
        require(frames == change['cumulative_p1_frames'], 'Approved screen P1 boundary moved')
        ending = b'\r\n' if raw.endswith(b'\r\n') else b'\n' if raw.endswith(b'\n') else b''
        lines[number-1] = change['before_line'].encode()+ending
    return b''.join(lines)


def observation_provenance(route: dict, name: str, changes: list[dict], registry: dict) -> dict:
    observation = route.get('observation')
    require(isinstance(observation, dict), 'Missing actual measured observation: '+name)
    producer = registry.get(observation.get('producer_id'))
    require(isinstance(producer, dict), 'Route does not identify its actual observation producer')
    expected = dict(source_commit=producer['source_commit'],
                    executable_sha256=producer['executable']['sha256'],
                    executable_bytes=producer['executable']['bytes'], platform=producer['platform'],
                    observer_kind=producer['kind'], native_returncode=0,
                    original_p1_preserved=True,
                    non_audio_differences=[change['original_mismatch'] for change in changes
                                           if change['route'] == name],
                    original_assertions_executed=False, acceptance=False,
                    audio_pin_count=route['audio_pin_count'],
                    frames=route['cumulative_p1_frames'])
    require(all(observation.get(key) == value and type(observation.get(key)) is type(value)
                for key, value in expected.items()), 'Observation source/executable/input checks differ: '+name)
    require(observation.get('baseline_route_sha256') == route['before_sha256']
            and observation.get('observed_route_sha256') in (
                route['before_sha256'], route['baseline_lf_sha256'], route['baseline_crlf_sha256'])
            and observation.get('original_route_newline_equivalence_verified') is True,
            'Observed route is not the frozen original route: '+name)
    require(type(observation.get('non_audio_assertions_compared')) is int
            and observation['non_audio_assertions_compared'] > 0
            and is_sha(observation.get('seed_sha256'))
            and is_sha(observation.get('frame_input_sha256'))
            and is_sha(observation.get('p1_lines_sha256')),
            'Original P1/seed/non-audio provenance is incomplete: '+name)
    keys = ('plan', 'receipt', 'raw_log', 'original_route', 'invocation', 'genuine_seed')
    if producer['kind'] == 'windows_full_aot_command_observer':
        keys += ('build_identity', 'all_audio_observations', 'non_audio_comparisons', 'executed_commands')
    else:
        keys += ('build_provenance', 'source_input_manifest', 'instrumentation_diff')
        require(observation.get('all_non_audio_assertions_enforced') is True
                and observation.get('all_non_audio_assertions_passed') is True
                and observation.get('missing_bank') is None
                and observation.get('immutable_inputs_unchanged') is True,
                'Linux discovery must retain every original non-audio/runtime failure')
        require(observation.get('source_input_manifest') == producer['source_input_manifest']
                and observation.get('instrumentation_diff') == producer['instrumentation_diff']
                and observation.get('build_provenance') == producer['build_provenance'],
                'Linux route inputs/instrumentation do not bind its sealed actual producer')
    for key in keys:
        evidence_identity(observation.get(key), name+':'+key)
    return producer


def verify_consumers(root: Path, ledger: dict) -> int:
    require(ledger.get('consumer_baseline_source_commit') == BASELINE_SOURCE
            and ledger.get('consumer_route_token_count') == 7
            and set(ledger['consumers']) == set(CONSUMERS)
            and digest(canonical(consumer_baseline_projection(ledger))) == CONSUMER_BASELINE_SHA256,
            'The separate four-wrapper/seven-token baseline changed')
    count = 0
    for name, record in ledger['consumers'].items():
        raw = repository_file(root, name).read_bytes()
        actual_sha = digest(raw)
        require(is_sha(record.get('after_sha256')) and is_sha(record.get('after_crlf_sha256'))
                and actual_sha in (record['after_sha256'], record['after_crlf_sha256']),
                'An active strict route-SHA wrapper changed outside its exact approved tokens: '+name)
        data = raw if actual_sha == record['after_sha256'] else raw.replace(b'\r\n', b'\n')
        require(len(record['tokens']) == len(record['after_tokens']), 'Missing active route-SHA consumer token')
        other, cursor = [], 0
        for index, (before, after) in enumerate(zip(record['tokens'], record['after_tokens'], strict=True)):
            offset = before['byte_offset']
            route = ledger['routes'][before['route']]
            expected = dict(index=index, line_number=before['line_number'], byte_offset=offset,
                            route=before['route'], after_sha256=route['after_sha256'])
            require(after == expected and before['before_sha256'] == route['before_sha256']
                    and cursor <= offset and data.count(b'\n', 0, offset)+1 == before['line_number']
                    and data[offset:offset+64] == after['after_sha256'].encode(),
                    'Active route-SHA wrapper token moved or names another route: '+name)
            other.append(data[cursor:offset])
            cursor = offset+64
            count += 1
        other.append(data[cursor:])
        require(digest(b''.join(other)) == record['non_route_token_bytes_sha256'],
                'Executable/Save/party/HP/flag/test-logic or another wrapper byte changed: '+name)
    require(count == 7, 'All seven original active wrapper route hashes must be migrated exactly')
    return count


def verify_audio_references(root: Path, ledger_path: Path) -> dict:
    root = root.resolve(strict=True)
    ledger = json.loads(ledger_path.read_bytes())
    require(isinstance(ledger, dict) and ledger.get('schema') == 1
            and ledger.get('kind') == 'full_rom_exact_audio_reference_update'
            and ledger.get('status') == 'complete_measured_audio_references'
            and ledger.get('baseline_source_commit') == BASELINE_SOURCE
            and ledger.get('observation_source_commit') == BASELINE_SOURCE
            and ledger.get('windows_reference_executable_sha256') == WINDOWS_REFERENCE_EXE_SHA
            and ledger.get('windows_reference_executable_bytes') == WINDOWS_REFERENCE_EXE_BYTES
            and ledger.get('blocked_observations') == [],
            'A complete measured exact-source reference ledger is required')
    require(digest(canonical(baseline_projection(ledger))) == BASELINE_SHA256,
            'Frozen original route or manifest baseline changed')
    require(is_sha(MEASURED_REFERENCE_SHA256)
            and digest(canonical(measured_projection(ledger))) == MEASURED_REFERENCE_SHA256,
            'Measured references/provenance are incomplete or changed')
    changes = approved_screens(ledger)
    registry = producer_registry(ledger)
    failures = ledger.get('failed_discovery_attempts')
    require(isinstance(failures, list), 'Historical partial-AOT failures must remain explicit')
    for failure in failures:
        require(isinstance(failure, dict) and failure.get('accepted_as_reference') is False
                and type(failure.get('native_returncode')) is int and failure['native_returncode'] != 0
                and failure.get('executable_sha256') in {p['executable']['sha256'] for p in registry.values()},
                'A failed sparse discovery attempt cannot be relabeled as a passing reference')
        evidence_identity(failure.get('receipt'), 'failed discovery receipt')
    consumer_tokens = verify_consumers(root, ledger)
    routes = ledger['routes']
    require(len(routes) == ROUTE_COUNT and ledger.get('baseline_route_count') == ROUTE_COUNT
            and ledger.get('baseline_audio_pin_count') == PIN_COUNT,
            'All 58 original audio routes / 375 pins are required')
    actual_names = {path.relative_to(root).as_posix()
                    for path in (root/'recomp/tests').glob('*_p1.txt')
                    if any(line.startswith(b'expect_audio ') for line in path.read_bytes().splitlines())}
    require(actual_names == set(routes), 'Added, removed or unguarded original audio route')
    pin_count = 0
    for name, route in routes.items():
        raw = repository_file(root, name).read_bytes()
        actual_sha = digest(raw)
        require(is_sha(route.get('after_sha256')) and is_sha(route.get('after_crlf_sha256'))
                and actual_sha in (route['after_sha256'], route['after_crlf_sha256']),
                'Exact measured route bytes changed: '+name)
        # The only alternate representation is the already sealed complete
        # uniform CRLF checkout. No arbitrary newline/whitespace normalization.
        data = raw if actual_sha == route['after_sha256'] else raw.replace(b'\r\n', b'\n')
        frames, actual, _ = parse_route(data)
        non_audio = parse_route(restore_approved_screens(data, name, changes))[2]
        require(digest(non_audio) == route['non_audio_bytes_sha256'],
                'P1/state/screen/Save or other non-audio route bytes changed: '+name)
        require(frames == route['cumulative_p1_frames'] and len(actual) == route['audio_pin_count']
                and len(route['pins']) == len(actual), 'Audio/P1 boundary count changed: '+name)
        producer = observation_provenance(route, name, changes, registry)
        for index, (pin, current) in enumerate(zip(route['pins'], actual, strict=True)):
            require(pin['index'] == index and current['line'] == pin['original_line_number']
                    and current['frames'] == pin['cumulative_p1_frames']
                    and current['values'] == pin['after']
                    and current['text'] == pin['after_line']
                    and audio_values(pin['after_line']) == pin['after'],
                    'Measured audio value, position or frame changed: '+name)
            require((type(pin.get('observation_capture')) is int and pin['observation_capture'] >= 0)
                    if producer['kind'] == 'windows_full_aot_command_observer'
                    else pin.get('observation_capture') is None,
                    'Audio boundary provenance differs from its actual producer')
            pin_count += 1
    require(pin_count == PIN_COUNT, 'Missing measured audio pins')
    require(set(ledger['manifests']) == set(MANIFESTS), 'Both original manifests must be retained')
    stages = 0
    for name in MANIFESTS:
        record = ledger['manifests'][name]
        raw = repository_file(root, name).read_bytes()
        data = json.loads(raw)
        require(digest(raw.replace(b'\r\n', b'\n')) == record['after_sha256']
                and len(data['stages']) == record['stage_count']
                and manifest_invariants(data) == record['non_route_sha256_invariants_sha256'],
                'Original manifest expectation changed: '+name)
        for stage in data['stages']:
            route_name = 'recomp/tests/'+stage['route']
            require(route_name in routes and stage['route_sha256'] == routes[route_name]['after_sha256'],
                    'Manifest does not pin the exact measured route: '+stage['name'])
            observed = routes[route_name]['observation']
            require(observed.get('expected_final_save_sha256') == stage['save_sha256']
                    and observed.get('observed_final_sram_sha256') == stage['save_sha256']
                    and observed.get('expected_final_save_verified') is True,
                    'Observed final original Journal differs from its existing pin: '+stage['name'])
            stages += 1
    return dict(status='passed_reference_integrity', baseline_source_commit=BASELINE_SOURCE,
                measured_source_commit=BASELINE_SOURCE,
                windows_reference_executable_sha256=WINDOWS_REFERENCE_EXE_SHA,
                producer_route_counts={name:sum(route['observation']['producer_id'] == name
                                               for route in routes.values()) for name in registry},
                original_routes=ROUTE_COUNT, exact_audio_pins=pin_count, manifest_stages=stages,
                active_wrapper_route_tokens=consumer_tokens, all_other_wrapper_bytes_preserved=True,
                non_audio_route_bytes_preserved=not changes,
                approved_raster_screen_reference_changes=len(changes),
                all_other_p1_state_save_screen_bytes_preserved=True,
                original_observation_non_audio_mismatches=len(changes),
                manifest_expectations_preserved=True,
                strict_native_replay_still_required=True, game_acceptance_claimed=False,
                ledger_sha256=digest(ledger_path.read_bytes()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--ledger', type=Path)
    args = parser.parse_args()
    try:
        path = args.ledger or args.root/'recomp/tests/full_rom_audio_references.json'
        print(json.dumps(verify_audio_references(args.root, path), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('FULL_ROM_AUDIO_REFERENCE_GUARD_FAIL', str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
