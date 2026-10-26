"""Observe the production Windows local-link host using genuine ending Journals.

Two original cartridge instances receive ordinary focused window key presses.
This checks host isolation, original Continue, persistence and lifecycle. It
does not certify that an original in-game serial transaction has succeeded.
No debugger, RAM writes, fabricated saves or protocol responses are used.
"""
from __future__ import annotations

import argparse
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from test_player_late_journal import Window, bitmap, digest, verify_saved_roster


class LinkWindows(Window):
    def __init__(self) -> None:
        super().__init__()
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        for dll, name, result, arguments in (
            (self.user, 'GetWindowTextW', c.c_int, [w.HWND, w.LPWSTR, c.c_int]),
            (self.user, 'GetForegroundWindow', w.HWND, []),
            (self.user, 'SetForegroundWindow', w.BOOL, [w.HWND]),
            (self.user, 'SetFocus', w.HWND, [w.HWND]),
            (self.user, 'ShowWindow', w.BOOL, [w.HWND, c.c_int]),
            (self.user, 'BringWindowToTop', w.BOOL, [w.HWND]),
            (self.user, 'AttachThreadInput', w.BOOL, [w.DWORD, w.DWORD, w.BOOL]),
            (self.user, 'SetWindowPos', w.BOOL, [w.HWND, w.HWND, c.c_int, c.c_int,
                                               c.c_int, c.c_int, w.UINT]),
            (self.user, 'GetDlgItem', w.HWND, [w.HWND, c.c_int]),
            (self.kernel, 'GetCurrentThreadId', w.DWORD, []),
            (self.kernel, 'CreateFileW', w.HANDLE, [w.LPCWSTR, w.DWORD, w.DWORD,
                                                  c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]),
            (self.kernel, 'CloseHandle', w.BOOL, [w.HANDLE]),
        ):
            function = getattr(dll, name)
            function.restype, function.argtypes = result, arguments

    def owned(self, process: subprocess.Popen) -> list[dict]:
        found = []

        @self.callback
        def visit(hwnd, unused):
            pid = w.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
            if pid.value == process.pid:
                kind, title = c.create_unicode_buffer(256), c.create_unicode_buffer(256)
                self.user.GetClassNameW(hwnd, kind, len(kind))
                self.user.GetWindowTextW(hwnd, title, len(title))
                found.append(dict(hwnd=int(hwnd), pid=pid.value, kind=kind.value, title=title.value))
            return True

        if not self.user.EnumWindows(visit, 0):
            raise RuntimeError('Could not enumerate the owned production windows')
        return found

    def pair(self, process: subprocess.Popen) -> list[int]:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Local player exited before creating both windows: {process.returncode}')
            owned = self.owned(process)
            if any(entry['kind'] == '#32770' for entry in owned):
                raise RuntimeError('Local player displayed an error dialog')
            games = [entry for entry in owned if entry['kind'] == 'DWM2tRecompWindow']
            if len(games) > 2:
                raise RuntimeError('Local player unexpectedly created more than two game windows')
            if len(games) == 2:
                result = []
                for player in (1, 2):
                    matches = [entry for entry in games if f' - Player {player} (local link)' in entry['title']]
                    if len(matches) != 1:
                        raise RuntimeError('The two local windows do not have distinct player identities')
                    result.append(matches[0]['hwnd'])
                for index, hwnd in enumerate(result):
                    # Both clients remain 160x144; move their outer windows
                    # apart so a GDI observation never captures an overlap.
                    if not self.user.SetWindowPos(hwnd, None, 40 + index * 240, 80, 0, 0, 0x55):
                        raise RuntimeError('Could not position the two production windows')
                return result
            time.sleep(.1)
        raise RuntimeError('Two production windows were not created within 60 seconds')

    def focus(self, hwnd: int) -> None:
        for _ in range(20):
            current = self.kernel.GetCurrentThreadId()
            foreground = self.user.GetForegroundWindow()
            target_thread = self.user.GetWindowThreadProcessId(hwnd, None)
            foreground_thread = self.user.GetWindowThreadProcessId(foreground, None) if foreground else 0
            attached = []
            try:
                for thread in sorted({target_thread, foreground_thread} - {0, current}):
                    if self.user.AttachThreadInput(current, thread, True):
                        attached.append(thread)
                self.user.ShowWindow(hwnd, 9)
                self.user.BringWindowToTop(hwnd)
                self.user.SetForegroundWindow(hwnd)
                self.user.SetFocus(hwnd)
            finally:
                for thread in reversed(attached):
                    self.user.AttachThreadInput(current, thread, False)
            if self.user.GetForegroundWindow() == hwnd:
                return
            time.sleep(.05)
        raise RuntimeError('The Windows desktop did not give focus to the selected player')

    def save_lock(self, save: Path, held: bool) -> int:
        path = str(save) + '.lock'
        handle = self.kernel.CreateFileW(path, 0x80000000, 0, None, 3, 0x80, None)
        error = c.get_last_error()
        invalid = c.c_void_p(-1).value
        if handle != invalid:
            self.kernel.CloseHandle(handle)
        if held and (handle != invalid or error != 32):
            raise RuntimeError(f'Native lock did not protect {save.name}: error={error}')
        if not held and handle == invalid:
            raise RuntimeError(f'Native lock was not released for {save.name}: error={error}')
        return error if held else 0


def similarity(expected: bytes, observed: bytes) -> float:
    return sum(a == b for a, b in zip(expected, observed, strict=True)) / len(expected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--environment', choices=('Windows', 'Wine on Linux'), default='Windows')
    args = parser.parse_args()
    if os.name != 'nt':
        print('PLAYER_LOCAL_LINK_UNAVAILABLE requires Windows APIs')
        return 77

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = dict(schema=1, kind='production_local_link_gui', status='running',
                  platform=args.environment, source=args.source, players=2,
                  original_p1_only=True, game_memory_edits=False,
                  serial_protocol_success_verified=False, full_game_verified=False,
                  scope='Two-window production host, original ending Continue, input isolation, '
                        'save locks, pending SRAM persistence and fresh-process reload; '
                        'no original linked transaction is claimed',
                  journal_operation_performed=False, fresh_process_reload=False,
                  normal_shutdowns=0, shutdown_players=[], checks=[], commands=[], input_events=[])
    processes = []
    api = None

    def require(condition: bool, label: str) -> None:
        if not condition:
            raise RuntimeError(label)
        report['checks'].append(label)
        print('PLAYER_LOCAL_LINK_CHECK_PASS', label, flush=True)

    try:
        if not re.fullmatch(r'[0-9a-f]{40}', args.source):
            raise ValueError('An exact expected source commit is required')
        exe, seed = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
        exe_hash = digest(exe)
        fixture = Path(__file__).resolve().parents[1] / 'tests/m8_player_ending_journal.json'
        spec = json.loads(fixture.read_text(encoding='utf-8'))
        references = [(fixture.parent / spec[key]).resolve(strict=True)
                      for key in ('field_reference', 'menu_reference')]
        for reference, expected in zip(references, spec['reference_sha256'], strict=True):
            require(digest(reference) == expected, reference.name + '_historical_reference_unchanged')
        initial = seed.read_bytes()
        require(len(initial) == 32768 and digest(seed) == spec['seed_sha256'],
                'genuine_original_ending_journal_is_pinned')
        require(bool(initial[0x3DA0 + 0x25 // 8] & (1 << (0x25 % 8))),
                'original_ending_quest_flag_is_present')
        field, menu = map(bitmap, references)
        report.update(executable_sha256=exe_hash, executable_bytes=exe.stat().st_size,
                      gate_script_sha256=digest(Path(__file__)),
                      gui_helper_sha256=digest(Path(__file__).with_name('test_player_late_journal.py')),
                      input_journal_sha256=digest(seed), input_journal_bytes=len(initial),
                      original_owned_creatures=sum(initial[index * 165] in (1, 2) for index in range(40)),
                      quest_bytes=107, historical_reference_spec_sha256=digest(fixture),
                      reference_sha256=spec['reference_sha256'])
        env = dict(os.environ, LOCALAPPDATA=str(out / 'isolated appdata-é-☃'))
        for option, markers in (
            ('--help', ('--link-profile', '--link-save', 'PLAN > Journal')),
            ('--version', ('source=' + args.source, 'romx_banks=255')),
        ):
            command = [str(exe), option]
            report['commands'].append(dict(label=option, command=command))
            result = subprocess.run(command, cwd=out, env=env, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=30)
            (out / (option[2:] + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
            (out / (option[2:] + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
            require(result.returncode == 0 and all(marker in result.stdout for marker in markers)
                    and (option != '--version' or 'source=' + args.source in result.stdout.splitlines()),
                    option[2:] + '_identifies_production_link_player')
        require(not Path(env['LOCALAPPDATA']).exists(), 'informational_commands_do_not_create_profiles')
        api = LinkWindows()
        folder = out / 'independent cartridges with spaces-é-☃'
        folder.mkdir()
        saves = [folder / f'ending-player{player}.sav' for player in (1, 2)]
        for save in saves:
            shutil.copyfile(seed, save)
            require(digest(save) == spec['seed_sha256'], save.name + '_is_an_unmodified_seed_copy')
        require(not os.path.samefile(*saves), 'players_have_distinct_original_journal_files')

        def launch(command: list[str], label: str) -> subprocess.Popen:
            report['commands'].append(dict(label=label, command=command))
            with (out / (label + '.stdout.log')).open('wb') as stdout, \
                    (out / (label + '.stderr.log')).open('wb') as stderr:
                process = subprocess.Popen(command, cwd=out, env=env, stdout=stdout, stderr=stderr,
                                           stdin=subprocess.DEVNULL)
            processes.append(process)
            return process

        def rejected(command: list[str], label: str, reason: str) -> None:
            process = launch(command, label)
            deadline = time.monotonic() + 30
            saw_dialog = False
            while time.monotonic() < deadline and process.poll() is None:
                owned = api.owned(process)
                if any(entry['kind'] == 'DWM2tRecompWindow' for entry in owned):
                    raise RuntimeError(label + '_unexpectedly_created_a_game_window')
                for entry in owned:
                    if entry['kind'] != '#32770':
                        continue
                    api.focus(entry['hwnd'])
                    button = api.user.GetDlgItem(entry['hwnd'], 1)
                    if button and api.user.PostMessageW(button, 0xF5, 0, 0):
                        saw_dialog = True
                time.sleep(.05)
            if process.poll() is None:
                raise RuntimeError(label + '_did_not_exit_after_its_error_dialog_was_dismissed')
            text = (out / (label + '.stderr.log')).read_text(encoding='utf-8', errors='replace')
            require(process.returncode != 0 and reason in text.lower(), label + '_refused_for_expected_reason')
            require(not api.owned(process), label + '_left_no_owned_windows')
            report.setdefault('rejections', []).append(dict(label=label, exit_code=process.returncode,
                                                            error_dialog_dismissed=saw_dialog, reason=reason))

        # This alias resolves to the same file after native parent/path
        # normalization. The rejection must occur before any game window.
        alias = saves[0].parent / '..' / saves[0].parent.name / saves[0].name
        rejected([str(exe), '--play', str(saves[0]), '--link-save', str(alias)],
                 'same-file-alias', 'two different save')
        require(all(digest(save) == spec['seed_sha256'] for save in saves),
                'same_file_rejection_preserves_both_original_copies')

        command = [str(exe), '--play', str(saves[0]), '--link-save', str(saves[1]),
                   '--scale', '1', '--audio-volume', '0']

        def capture(hwnd: int, label: str) -> bytes:
            api.focus(hwnd)
            time.sleep(.1)
            return api.capture(hwnd, out / (label + '.bmp'))

        def pulse(hwnd: int, player: int, key: int, idle: float = 2) -> None:
            api.focus(hwnd)
            report['input_events'].append(dict(player=player, hwnd=hwnd, virtual_key=key,
                                                foreground_hwnd=int(api.user.GetForegroundWindow()),
                                                monotonic=time.monotonic()))
            api.pulse(hwnd, key, idle)

        def field_screen(hwnd: int, label: str) -> bytes:
            deadline, best = time.monotonic() + 25, 0.0
            while time.monotonic() < deadline:
                pixels = capture(hwnd, label)
                match = similarity(field, pixels)
                best = max(best, match)
                if match >= .85:
                    report.setdefault('field_matches', {})[label] = match
                    return pixels
                time.sleep(.15)
            raise RuntimeError(f'{label}: original ending field was not reached; best match={best:.3f}')

        def continue_player(hwnd: int, player: int, round_name: str) -> None:
            for key in (0x0D, 0x5A, 0x5A):
                pulse(hwnd, player, key)
            field_screen(hwnd, f'{round_name}-player{player}-field')
            require(True, f'{round_name}_player{player}_original_ending_continue')

        def semantic_saves(label: str) -> None:
            results = []
            for player, save in enumerate(saves, 1):
                observed = save.read_bytes()
                verify_saved_roster(initial, observed)
                results.append(dict(player=player, bytes=len(observed), sha256=digest(save),
                                    byte_identical_to_seed=observed == initial,
                                    original_roster_and_107_quest_bytes_preserved=True))
            report.setdefault('saved_journals', {})[label] = results
            require(True, label + '_both_original_rosters_and_quest_bytes_preserved')

        for round_name, closing_player in (('continue', 2), ('reload', 1)):
            process = launch(command, round_name)
            windows = api.pair(process)
            report.setdefault('window_pairs', []).append(dict(round=round_name, pid=process.pid,
                                                              windows=api.owned(process)))
            require(len(set(windows)) == 2, round_name + '_two_distinct_windows_share_one_owned_process')
            for player, save in enumerate(saves, 1):
                require(api.save_lock(save, True) == 32, f'{round_name}_player{player}_native_save_lock_held')
            # Same original production boot wait as the retained Journal GUI
            # gate; neither Runtime receives a fabricated Continue state.
            time.sleep(35)
            continue_player(windows[0], 1, round_name)
            pulse(windows[0], 1, 0x5A, 1.8)
            first_menu = capture(windows[0], round_name + '-player1-menu')
            require(first_menu[104 * 480:] == menu[104 * 480:],
                    round_name + '_player1_original_ending_party_hud')
            untouched = capture(windows[1], round_name + '-player2-without-input')
            require(similarity(field, untouched) < .75 and untouched[104 * 480:] != menu[104 * 480:],
                    round_name + '_player1_inputs_did_not_continue_or_open_player2_menu')
            pulse(windows[0], 1, 0x58, 1)
            field_screen(windows[0], round_name + '-player1-menu-closed')

            continue_player(windows[1], 2, round_name)
            pulse(windows[1], 2, 0x5A, 1.8)
            second_menu = capture(windows[1], round_name + '-player2-menu')
            require(second_menu[104 * 480:] == menu[104 * 480:],
                    round_name + '_player2_original_ending_party_hud')
            untouched = field_screen(windows[0], round_name + '-player1-during-player2-input')
            require(untouched[104 * 480:] != menu[104 * 480:],
                    round_name + '_player2_inputs_did_not_open_player1_menu')
            pulse(windows[1], 2, 0x58, 1)
            field_screen(windows[1], round_name + '-player2-menu-closed')

            if round_name == 'continue':
                time.sleep(2.2)
                before = digest(saves[1])
                rejected([str(exe), '--play', str(saves[1]), '--scale', '1', '--audio-volume', '0'],
                         'competing-player2', 'locked')
                require(process.poll() is None and len(api.owned(process)) == 2,
                        'peer_lock_rejection_keeps_both_original_games_running')
                require(digest(saves[1]) == before, 'competing_process_does_not_replace_player2_save')

            api.close(windows[closing_player - 1], process)
            require(process.returncode == 0 and not api.owned(process),
                    f'{round_name}_close_player{closing_player}_normally_closes_both_windows')
            report['normal_shutdowns'] += 1
            report['shutdown_players'].append(closing_player)
            for player, save in enumerate(saves, 1):
                require(api.save_lock(save, False) == 0,
                        f'{round_name}_player{player}_native_save_lock_released')
            semantic_saves(round_name)

        for player, save in enumerate(saves, 1):
            backups = sorted((save.parent / 'backups' / save.stem).glob('*.sav'))
            require(len(backups) >= 2 and digest(backups[0]) == spec['seed_sha256'],
                    f'player{player}_original_prelaunch_backup_is_recoverable')
            require(all(backup.stat().st_size == 32768 for backup in backups),
                    f'player{player}_all_prelaunch_backups_have_original_size')
        require(not list(folder.rglob('*.tmp-*')), 'both_games_leave_no_pending_save_temporaries')
        require(digest(seed) == spec['seed_sha256'] and digest(exe) == exe_hash,
                'source_journal_and_production_executable_are_unchanged')
        report.update(status='passed', fresh_process_reload=True, input_isolation_verified=True,
                      game_windows_per_launch=2, normal_close_save_integrity_verified=True)
        print('PLAYER_LOCAL_LINK_PASS original_P1 two_players isolated_inputs locks fresh_Continue '
              'serial_protocol_success_verified=false', flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('PLAYER_LOCAL_LINK_FAIL', error, flush=True)
        return 1
    finally:
        for process in processes:
            if process.poll() is None:
                # Failure cleanup is confined to processes started by this
                # gate. It never counts as a successful normal shutdown.
                process.kill()
                process.wait(timeout=15)
        report['screenshots'] = {path.name: digest(path) for path in sorted(out.glob('*.bmp'))}
        (out / 'player-local-link.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
