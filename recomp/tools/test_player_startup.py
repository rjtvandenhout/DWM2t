"""Exercise the real Windows player CLI, isolated startup and save lock.

This is not a later-world, ending, audio-fidelity or Journal acceptance test.
No existing save is loaded. The only live control is closing the owned window.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--no-arguments', action='store_true',
                        help='Launch the copied EXE directly with no arguments and its default profile')
    parser.add_argument('--environment', choices=('Windows', 'Wine on Linux'), default='Windows')
    args = parser.parse_args()
    if os.name != 'nt':
        print('PLAYER_STARTUP_UNAVAILABLE requires Windows')
        return 77
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    exe = args.exe.resolve(strict=True)
    report = {'status': 'running', 'source': args.source, 'checks': [], 'platform': args.environment,
              'scope': 'production startup only; full M8 remains unproven',
              'executable_sha256': digest(exe), 'no_argument_start': args.no_arguments}
    process = None

    def require(condition: bool, label: str) -> None:
        if not condition:
            raise RuntimeError(label)
        report['checks'].append(label)
        print('PLAYER_CHECK_PASS', label, flush=True)

    env = dict(os.environ, LOCALAPPDATA=str(out / 'user data-\u00e9-\u2603'))
    try:
        for flag, required in [('--help', ['PLAN > Journal', '--profile']),
                               ('--version', ['romx_banks=255',
                                              'source=' + args.source])]:
            result = subprocess.run([str(exe), flag], env=env, cwd=out,
                                    capture_output=True, text=True, encoding='utf-8',
                                    errors='replace', timeout=30, check=False)
            (out / (flag[2:] + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
            (out / (flag[2:] + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
            require(result.returncode == 0 and all(x in result.stdout for x in required) and
                    (flag != '--version' or any(marker in result.stdout for marker in
                     ('full_game_verified=false', 'validation=external_package_record'))), flag)
        require(not Path(env['LOCALAPPDATA']).exists(), 'informational_commands_do_not_create_profile')

        user = ctypes.WinDLL('user32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user.EnumWindows.restype = wintypes.BOOL
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.PostMessageW.restype = wintypes.BOOL
        user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
            wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
        user.SendMessageTimeoutW.restype = ctypes.c_ssize_t
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        invalid = ctypes.c_void_p(-1).value
        with (out / 'startup.stdout.txt').open('wb') as stdout, (out / 'startup.stderr.txt').open('wb') as stderr:
            profile = 'default' if args.no_arguments else 'smoke'
            command = [str(exe)] if args.no_arguments else [str(exe), '--profile', profile, '--audio-volume', '0']
            report['command'] = command
            process = subprocess.Popen(command,
                                       cwd=out, env=env, stdout=stdout, stderr=stderr)
            hwnd = None
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f'player exited before window creation: {process.returncode}')
                owned = []

                @callback_type
                def visit(window, unused):
                    pid = wintypes.DWORD()
                    user.GetWindowThreadProcessId(window, ctypes.byref(pid))
                    if pid.value == process.pid:
                        name = ctypes.create_unicode_buffer(256)
                        user.GetClassNameW(window, name, len(name))
                        owned.append((window, name.value))
                    return True

                user.EnumWindows(visit, 0)
                if any(name == '#32770' for _, name in owned):
                    raise RuntimeError('player displayed an error dialog during startup')
                hwnd = next((w for w, name in owned if name == 'DWM2tRecompWindow'), None)
                if hwnd:
                    break
                time.sleep(0.1)
            require(hwnd is not None, 'real_production_window_created')
            time.sleep(2)
            response = ctypes.c_size_t()
            require(process.poll() is None and bool(user.SendMessageTimeoutW(
                hwnd, 0, 0, 0, 2, 5000, ctypes.byref(response))), 'window_message_loop_responsive')
            lock = Path(env['LOCALAPPDATA']) / ('DWM2t/saves/'+profile+'.sav.lock')
            held = kernel.CreateFileW(str(lock), 0x80000000, 0, None, 3, 0x80, None)
            error = ctypes.get_last_error()
            if held != invalid:
                kernel.CloseHandle(held)
            require(held == invalid and error == 32, 'native_save_lock_blocks_competing_access')
            require(bool(user.PostMessageW(hwnd, 0x10, 0, 0)), 'close_message_delivered')
            require(process.wait(timeout=30) == 0, 'normal_player_shutdown')
            released = kernel.CreateFileW(str(lock), 0x80000000, 0, None, 3, 0x80, None)
            require(released != invalid, 'native_save_lock_released')
            kernel.CloseHandle(released)
        saves = list(Path(env['LOCALAPPDATA']).rglob('*.sav'))
        require(all(p.stat().st_size == 32768 for p in saves), 'any_original_boot_sram_is_exact_size')
        require(not list(Path(env['LOCALAPPDATA']).rglob('*.tmp-*')), 'no_pending_save_temporaries')
        require(digest(exe) == report['executable_sha256'], 'player_binary_unchanged')
        report['status'] = 'passed'
        print('PLAYER_STARTUP_PASS checks=' + str(len(report['checks'])), flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('PLAYER_STARTUP_FAIL', error, flush=True)
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=15)
        (out / 'player-startup.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
