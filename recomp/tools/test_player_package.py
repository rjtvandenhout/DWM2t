"""Validate a copied Windows package's launcher, imports, locks and exit logs.

Only an authentic pinned Journal is imported, always into new test profiles.
The original Journal and package remain immutable. This is host integration
evidence; ending and original in-game Journal checks are separate gates.
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
import time

from m8_build_identity import digest
from prepare_m8_player_validation import prepare
from test_player_late_journal import Window, verify_saved_roster


class Processes:
    class Entry(c.Structure):
        _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('pid', w.DWORD),
                    ('heap', c.c_size_t), ('module', w.DWORD), ('threads', w.DWORD),
                    ('parent', w.DWORD), ('priority', w.LONG), ('flags', w.DWORD),
                    ('name', w.WCHAR*260)]

    def __init__(self):
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        for name, result, parameters in (
            ('CreateToolhelp32Snapshot', w.HANDLE, [w.DWORD, w.DWORD]),
            ('Process32FirstW', w.BOOL, [w.HANDLE, c.POINTER(self.Entry)]),
            ('Process32NextW', w.BOOL, [w.HANDLE, c.POINTER(self.Entry)]),
            ('CloseHandle', w.BOOL, [w.HANDLE]),
            ('OpenProcess', w.HANDLE, [w.DWORD, w.BOOL, w.DWORD]),
            ('GetExitCodeProcess', w.BOOL, [w.HANDLE, c.POINTER(w.DWORD)]),
            ('TerminateProcess', w.BOOL, [w.HANDLE, w.UINT]),
        ):
            function = getattr(self.kernel, name)
            function.restype, function.argtypes = result, parameters

    def child(self, launcher):
        deadline = time.monotonic()+60
        while time.monotonic() < deadline:
            if launcher.poll() is not None:
                raise RuntimeError('Launcher exited before starting its native child')
            snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)
            if snapshot == c.c_void_p(-1).value:
                raise RuntimeError('Cannot inspect owned native child processes')
            entry = self.Entry()
            entry.size = c.sizeof(entry)
            found = []
            try:
                more = self.kernel.Process32FirstW(snapshot, c.byref(entry))
                while more:
                    if entry.parent == launcher.pid and entry.name.lower() == 'dwm2trecomp.exe':
                        found.append(entry.pid)
                    more = self.kernel.Process32NextW(snapshot, c.byref(entry))
            finally:
                self.kernel.CloseHandle(snapshot)
            if len(found) == 1:
                return Child(self.kernel, found[0])
            if len(found) > 1:
                raise RuntimeError('Launcher unexpectedly started multiple native children')
            time.sleep(.1)
        raise RuntimeError('Native child creation timed out')


class Child:
    def __init__(self, kernel, pid):
        self.kernel, self.pid, self.returncode = kernel, pid, None
        self.handle = kernel.OpenProcess(0x100000 | 0x1000 | 1, False, pid)
        if not self.handle:
            raise RuntimeError('Cannot observe owned native child')

    def poll(self):
        code = w.DWORD()
        if not self.kernel.GetExitCodeProcess(self.handle, c.byref(code)):
            raise RuntimeError('Cannot read owned native child exit status')
        self.returncode = None if code.value == 259 else code.value
        return self.returncode

    def wait(self, timeout=30):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            if self.poll() is not None:
                return self.returncode
            time.sleep(.1)
        raise RuntimeError('Owned native child did not exit')

    def close_handle(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'seed', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--environment', choices=('Windows', 'Wine on Linux'), default='Windows')
    args = parser.parse_args()
    if os.name != 'nt':
        print('PLAYER_PACKAGE_UNAVAILABLE requires Windows APIs and PowerShell')
        return 77
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', platform=args.environment, source=args.source,
                  full_game_verified=False, checks=[])
    launchers, children = [], []
    api, processes = Window(), Processes()

    def require(condition, label):
        if not condition:
            raise RuntimeError(label)
        report['checks'].append(label)
        print('PLAYER_PACKAGE_CHECK_PASS', label, flush=True)

    try:
        package, seed = args.package.resolve(strict=True), args.seed.resolve(strict=True)
        reference = Path(__file__).resolve().parents[1]/'tests/m8_player_late_journal.json'
        spec = prepare(package, args.source, reference, out/'package-gui-spec.json')
        require(seed.stat().st_size == 32768 and digest(seed) == spec['seed_sha256'], 'authentic_later_journal_seed')
        original = seed.read_bytes()
        immutable = {path: digest(path) for path in package.iterdir() if path.is_file()}
        powershell = shutil.which('powershell.exe')
        require(bool(powershell), 'windows_powershell_available')
        # A PowerShell 7 Actions parent exports its own module search path.
        # Let Windows PowerShell initialize its standard modules as it does
        # when Play.cmd is started from Explorer or a normal command prompt.
        launcher_env = dict(os.environ)
        launcher_env.pop('PSModulePath', None)
        report['powershell'] = powershell
        data = out/'profiles with spaces-é-☃'

        def command(folder, profile, imported=True):
            result = [powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                      '-File', str(folder/'Launch.ps1'), '-Profile', profile, '-DataRoot', str(data), '-Volume', '0']
            if imported:
                result += ['-ImportSave', str(seed)]
            return result

        def launch(profile):
            with (out/(profile+'-launcher.log')).open('wb') as log:
                launcher = subprocess.Popen(command(package, profile), stdout=log, stderr=subprocess.STDOUT,
                                            env=launcher_env)
            launchers.append(launcher)
            child = processes.child(launcher)
            children.append(child)
            hwnd = api.find(child)
            require(child.poll() is None, profile+'_native_window_created')
            return launcher, child, hwnd

        first = launch('first')
        second = launch('second')
        require(first[1].poll() is None and second[1].poll() is None, 'separate_profiles_run_concurrently')
        saved = data/'saves/first.sav'
        before_duplicate = digest(saved)
        with (out/'duplicate.stdout.log').open('wb') as stdout, (out/'duplicate.stderr.log').open('wb') as stderr:
            duplicate = subprocess.Popen([str(package/'DWM2tRecomp.exe'), '--play', str(saved),
                                          '--audio-volume', '0'], stdout=stdout, stderr=stderr)
        launchers.append(duplicate)
        deadline, dialog = time.monotonic()+30, None
        while time.monotonic() < deadline and duplicate.poll() is None:
            owned = []

            @api.callback
            def visit(hwnd, unused):
                pid = w.DWORD()
                api.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
                if pid.value == duplicate.pid:
                    name = c.create_unicode_buffer(256)
                    api.user.GetClassNameW(hwnd, name, len(name))
                    owned.append((hwnd, name.value))
                return True

            api.user.EnumWindows(visit, 0)
            if any(name == 'DWM2tRecompWindow' for _, name in owned):
                raise RuntimeError('Duplicate unexpectedly created a game window')
            dialog = next((hwnd for hwnd, name in owned if name == '#32770'), None)
            if dialog:
                api.user.PostMessageW(dialog, 0x111, 1, 0)  # dismiss this owned error dialog with OK
                break
            time.sleep(.1)
        require(duplicate.wait(timeout=15) != 0 and first[1].poll() is None,
                'actual_duplicate_native_instance_is_refused')
        require(True, 'duplicate_never_creates_game_window')
        require('locked' in (out/'duplicate.stderr.log').read_text(errors='replace').lower()
                and digest(saved) == before_duplicate, 'duplicate_lock_preserves_active_save')
        for profile, (launcher, child, hwnd) in (('first', first), ('second', second)):
            api.close(hwnd, child)
            require(launcher.wait(timeout=30) == 0, profile+'_launcher_reports_normal_exit')
            current = data/('saves/'+profile+'.sav')
            verify_saved_roster(original, current.read_bytes())
            sessions = list((data/'logs').glob(profile+'-*.session.json'))
            require(len(sessions) == 1, profile+'_session_log_created')
            session = json.loads(sessions[0].read_text(encoding='utf-8-sig'))
            require(session['exit_code'] == 0 and session['source_commit'] == args.source
                    and bool(session.get('finished_utc')), profile+'_session_log_has_actual_exit_status')
            backups = list((data/'saves/backups'/profile).glob('*.sav'))
            require(len(backups) >= 2 and all(digest(path) == spec['seed_sha256'] for path in backups),
                    profile+'_launcher_and_native_prelaunch_backups_are_recoverable')
        old_hash = digest(saved)
        result = subprocess.run(command(package, 'first'), capture_output=True, timeout=30, env=launcher_env)
        (out/'refuse-overwrite.log').write_bytes(result.stdout+result.stderr)
        require(result.returncode != 0 and digest(saved) == old_hash, 'import_refuses_existing_profile_without_replacement')
        bad = out/'checksum mismatch package'
        bad.mkdir()
        for path in package.iterdir():
            if path.name == 'DWM2tRecomp.exe':
                os.link(path, bad/path.name)
            else:
                shutil.copyfile(path, bad/path.name)
        with (bad/'README.txt').open('ab') as stream:
            stream.write(b'\nIntentional checksum rejection fixture.\n')
        result = subprocess.run(command(bad, 'checksum'), capture_output=True, timeout=30, env=launcher_env)
        (out/'checksum-mismatch.log').write_bytes(result.stdout+result.stderr)
        require(result.returncode != 0 and not (data/'saves/checksum.sav').exists(), 'changed_package_is_refused_before_import')
        require(digest(seed) == spec['seed_sha256'] and all(digest(path) == sha for path, sha in immutable.items()),
                'original_journal_and_package_are_unchanged')
        report.update(status='passed', executable_sha256=spec['executable_sha256'],
                      seed_sha256=spec['seed_sha256'], package_manifest_sha256=spec['package_manifest_sha256'])
        print('PLAYER_PACKAGE_PASS original_import profiles locks backups checksum exit_logs', flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('PLAYER_PACKAGE_FAIL', error, flush=True)
        return 1
    finally:
        for child in children:
            if child.handle:
                if child.poll() is None:
                    processes.kernel.TerminateProcess(child.handle, 99)
                child.close_handle()
        for process in launchers:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=15)
        # The unchanged EXE already exists in the archived package. Do not
        # upload a second 725-MB hard link with the checksum rejection fixture.
        redundant = out/'checksum mismatch package/DWM2tRecomp.exe'
        if redundant.is_file():
            redundant.unlink()
        (out/'player-package.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
