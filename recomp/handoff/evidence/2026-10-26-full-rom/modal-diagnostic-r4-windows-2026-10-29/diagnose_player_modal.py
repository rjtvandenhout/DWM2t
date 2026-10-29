"""Diagnose dismissal of the production player's same-save rejection dialog.

This is a diagnostic, not an acceptance gate. It launches the archived player
with a copy of the pinned original Journal, observes its own top-level windows,
and records whether standard Windows messages close the expected modal. It does
not modify game memory or affect the supplied Journal.
"""
from __future__ import annotations

import argparse
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_player_late_journal import digest
from test_player_local_link import LinkWindows


def desktop_name(user, desktop):
    if not desktop:
        return None
    required = w.DWORD()
    user.GetUserObjectInformationW(desktop, 2, None, 0, c.byref(required))
    if not required.value:
        return None
    buf = c.create_unicode_buffer((required.value + 1) // 2)
    if not user.GetUserObjectInformationW(desktop, 2, buf, required.value, c.byref(required)):
        return None
    return buf.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--exe-sha256', required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows APIs are required')
    exe, seed = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).resolve().parents[1] / 'tests/m8_player_ending_journal.json'
    expected_seed = json.loads(fixture.read_text(encoding='utf-8'))['seed_sha256']
    if digest(exe) != args.exe_sha256 or digest(seed) != expected_seed or seed.stat().st_size != 32768:
        raise ValueError('Archived executable or genuine original Journal differs')
    version = subprocess.run([str(exe), '--version'], capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=30, check=True)
    if 'source=' + args.source not in version.stdout.splitlines():
        raise ValueError('Archived executable identifies a different game source')
    api = LinkWindows()
    user, kernel = api.user, api.kernel
    for name, result, signature in (
        ('IsWindowVisible', w.BOOL, [w.HWND]),
        ('IsWindowEnabled', w.BOOL, [w.HWND]),
        ('GetDlgCtrlID', c.c_int, [w.HWND]),
        ('GetThreadDesktop', w.HANDLE, [w.DWORD]),
        ('OpenInputDesktop', w.HANDLE, [w.DWORD, w.BOOL, w.DWORD]),
        ('CloseDesktop', w.BOOL, [w.HANDLE]),
        ('GetUserObjectInformationW', w.BOOL, [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]),
    ):
        function = getattr(user, name)
        function.restype, function.argtypes = result, signature
    current_desktop = desktop_name(user, user.GetThreadDesktop(kernel.GetCurrentThreadId()))
    input_desktop = user.OpenInputDesktop(0, False, 1)
    try:
        input_desktop_name = desktop_name(user, input_desktop)
    finally:
        if input_desktop:
            user.CloseDesktop(input_desktop)
    report = dict(schema=1, kind='player_modal_diagnostic', acceptance_gate=False,
                  source=args.source, executable_sha256=digest(exe), input_journal_sha256=digest(seed),
                  thread_desktop=current_desktop, input_desktop=input_desktop_name,
                  cases=[])
    for method in ('button_click', 'dialog_close'):
        folder = out / (method + ' independent cartridges with spaces-é-☃')
        folder.mkdir()
        save = folder / 'ending-player1.sav'
        shutil.copyfile(seed, save)
        alias = folder / '..' / folder.name / save.name
        log = (out / (method + '.stderr.log')).open('wb')
        proc = subprocess.Popen([str(exe), '--play', str(save), '--link-save', str(alias)],
                                cwd=out, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log)
        case = dict(method=method, pid=proc.pid, observations=[], finished=False)
        start, next_observation, previous_state = time.monotonic(), 0.0, None
        try:
            while time.monotonic() - start < 30 and proc.poll() is None:
                elapsed = time.monotonic() - start
                owned = api.owned(proc)
                snapshots = []
                for entry in owned:
                    hwnd = entry['hwnd']
                    entry.update(visible=bool(user.IsWindowVisible(hwnd)),
                                 enabled=bool(user.IsWindowEnabled(hwnd)),
                                 thread=user.GetWindowThreadProcessId(hwnd, None))
                    entry['desktop'] = desktop_name(user, user.GetThreadDesktop(entry['thread']))
                    if entry['kind'] == '#32770':
                        button = user.GetDlgItem(hwnd, 1)
                        entry.update(button=int(button) if button else None,
                                     button_id=user.GetDlgCtrlID(button) if button else None,
                                     button_visible=bool(user.IsWindowVisible(button)) if button else None,
                                     button_enabled=bool(user.IsWindowEnabled(button)) if button else None)
                        try:
                            api.focus(hwnd)
                            entry['focus_result'] = 'success'
                        except RuntimeError as exc:
                            entry['focus_result'] = str(exc)
                        target, message = (button, 0xF5) if method == 'button_click' else (hwnd, 0x10)
                        c.set_last_error(0)
                        entry['post_result'] = bool(target and user.PostMessageW(target, message, 0, 0))
                        entry['post_error'] = c.get_last_error()
                        entry['message'] = message
                    snapshots.append(entry)
                foreground = user.GetForegroundWindow()
                stderr_size = (out / (method + '.stderr.log')).stat().st_size
                state = (snapshots, int(foreground) if foreground else None, stderr_size)
                if elapsed >= next_observation or state != previous_state:
                    case['observations'].append(dict(seconds=round(elapsed, 3), windows=snapshots,
                                                     foreground=state[1], stderr_bytes=stderr_size))
                    previous_state = state
                    next_observation = elapsed + 1
                time.sleep(.05)
            case['finished'] = proc.poll() is not None
            case['exit_code'] = proc.poll()
            if not case['finished']:
                case['windows_at_timeout'] = api.owned(proc)
                proc.kill()
                proc.wait(timeout=10)
                case['terminated_after_timeout'] = True
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
            log.close()
        case['stderr'] = (out / (method + '.stderr.log')).read_text(encoding='utf-8', errors='replace')
        case['refusal_observed'] = 'two different save' in case['stderr'].lower()
        case['seed_copy_unchanged'] = digest(save) == expected_seed
        case['source_seed_unchanged'] = digest(seed) == expected_seed
        case['game_window_seen'] = any(
            item['kind'] == 'DWM2tRecompWindow'
            for observation in case['observations'] for item in observation['windows'])
        report['cases'].append(case)
        print('MODAL_DIAGNOSTIC', method, 'finished=', case['finished'],
              'exit_code=', case['exit_code'], 'refusal=', case['refusal_observed'], flush=True)
    (out / 'modal-diagnostic.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
