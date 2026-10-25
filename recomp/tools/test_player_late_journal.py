"""Exercise a pinned production player's later original Continue and Journal.

Only a copy of a genuine Journal and normal window keyboard messages enter
the player. Screenshots and saved files are read-only observations. This is
not an ending or complete-M8 certificate.
"""
from __future__ import annotations

import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bitmap(path: Path) -> bytes:
    data = path.read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    width, height = struct.unpack_from('<ii', data, 18)
    if data[:2] != b'BM' or (width, abs(height)) != (160, 144) or struct.unpack_from('<H', data, 28)[0] != 32:
        raise ValueError('Reference must be an original 160x144, 32-bit BMP')
    rows = [data[offset+y*640:offset+(y+1)*640] for y in range(144)]
    if height > 0:
        rows.reverse()
    return bytes(value for row in rows for i, value in enumerate(row) if i % 4 != 3)


class Window:
    def __init__(self) -> None:
        self.user = c.WinDLL('user32', use_last_error=True)
        self.gdi = c.WinDLL('gdi32', use_last_error=True)
        self.callback = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        signatures = [
            (self.user, 'EnumWindows', w.BOOL, [self.callback, w.LPARAM]),
            (self.user, 'GetWindowThreadProcessId', w.DWORD, [w.HWND, c.POINTER(w.DWORD)]),
            (self.user, 'GetClassNameW', c.c_int, [w.HWND, w.LPWSTR, c.c_int]),
            (self.user, 'PostMessageW', w.BOOL, [w.HWND, w.UINT, w.WPARAM, w.LPARAM]),
            (self.user, 'GetClientRect', w.BOOL, [w.HWND, c.POINTER(w.RECT)]),
            (self.user, 'GetDC', w.HDC, [w.HWND]),
            (self.user, 'ReleaseDC', c.c_int, [w.HWND, w.HDC]),
            (self.gdi, 'CreateCompatibleDC', w.HDC, [w.HDC]),
            (self.gdi, 'CreateCompatibleBitmap', w.HANDLE, [w.HDC, c.c_int, c.c_int]),
            (self.gdi, 'SelectObject', w.HANDLE, [w.HDC, w.HANDLE]),
            (self.gdi, 'BitBlt', w.BOOL, [w.HDC, c.c_int, c.c_int, c.c_int, c.c_int,
                                        w.HDC, c.c_int, c.c_int, w.DWORD]),
            (self.gdi, 'GetDIBits', c.c_int, [w.HDC, w.HANDLE, w.UINT, w.UINT,
                                           c.c_void_p, c.c_void_p, w.UINT]),
            (self.gdi, 'DeleteObject', w.BOOL, [w.HANDLE]),
            (self.gdi, 'DeleteDC', w.BOOL, [w.HDC]),
        ]
        for dll, name, result, arguments in signatures:
            method = getattr(dll, name)
            method.restype, method.argtypes = result, arguments

    def find(self, process: subprocess.Popen) -> int:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Player exited before creating its window: {process.returncode}')
            owned = []

            @self.callback
            def visit(hwnd, unused):
                pid = w.DWORD()
                self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
                if pid.value == process.pid:
                    name = c.create_unicode_buffer(256)
                    self.user.GetClassNameW(hwnd, name, len(name))
                    owned.append((hwnd, name.value))
                return True

            self.user.EnumWindows(visit, 0)
            if any(name == '#32770' for _, name in owned):
                raise RuntimeError('Production player displayed an error dialog')
            found = next((hwnd for hwnd, name in owned if name == 'DWM2tRecompWindow'), None)
            if found:
                return found
            time.sleep(.1)
        raise RuntimeError('Production window creation timed out')

    def pulse(self, hwnd: int, key: int, idle: float = .6) -> None:
        if not self.user.PostMessageW(hwnd, 0x100, key, 0):
            raise RuntimeError('Original keyboard press could not be delivered')
        time.sleep(.14)
        if not self.user.PostMessageW(hwnd, 0x101, key, 0):
            raise RuntimeError('Original keyboard release could not be delivered')
        time.sleep(idle)

    def capture(self, hwnd: int, path: Path) -> bytes:
        rect = w.RECT()
        if not self.user.GetClientRect(hwnd, c.byref(rect)) or (rect.right, rect.bottom) != (160, 144):
            raise RuntimeError('Production --scale 1 client is not exactly 160x144')
        screen = self.user.GetDC(hwnd)
        dc = self.gdi.CreateCompatibleDC(screen)
        handle = self.gdi.CreateCompatibleBitmap(screen, 160, 144)
        old = self.gdi.SelectObject(dc, handle)
        try:
            if not self.gdi.BitBlt(dc, 0, 0, 160, 144, screen, 0, 0, 0x00CC0020):
                raise RuntimeError('Production framebuffer capture failed')
            self.gdi.SelectObject(dc, old)
            header = struct.pack('<IiiHHIIiiII', 40, 160, -144, 1, 32, 0, 92160, 0, 0, 0, 0)
            info = c.create_string_buffer(header + bytes(16))
            pixels = c.create_string_buffer(92160)
            if self.gdi.GetDIBits(screen, handle, 0, 144, pixels, info, 0) != 144:
                raise RuntimeError('Production framebuffer readback failed')
            path.write_bytes(struct.pack('<2sIHHI', b'BM', 92214, 0, 0, 54) + header + pixels.raw)
            return bitmap(path)
        finally:
            self.gdi.DeleteObject(handle)
            self.gdi.DeleteDC(dc)
            self.user.ReleaseDC(hwnd, screen)

    def close(self, hwnd: int, process: subprocess.Popen) -> None:
        if not self.user.PostMessageW(hwnd, 0x10, 0, 0) or process.wait(timeout=30) != 0:
            raise RuntimeError('Production player did not close normally')


def verify_saved_roster(initial: bytes, saved: bytes) -> None:
    if len(initial) != 32768 or len(saved) != 32768:
        raise ValueError('Original Journal size differs')
    for record in range(40):
        base = record * 0xA5
        if initial[base] not in (1, 2):
            if saved[base] in (1, 2):
                raise ValueError('Production Journal changed the owned roster')
            continue
        if (initial[base] != saved[base] or
                initial[base+1:base+11].split(b'\xf0', 1)[0] !=
                saved[base+1:base+11].split(b'\xf0', 1)[0]):
            raise ValueError(f'Production Journal changed owned name/status: {record}')
        for start, end in ((0x0B, 0x0D), (0x19, 0x3C), (0x55, 0xA5)):
            if initial[base+start:base+end] != saved[base+start:base+end]:
                raise ValueError(f'Production Journal changed persistent creature data: {record}')
    # Original bank 2:$7636/$76AC saves/restores CBD7 with length 0x6B.
    # Independently matched against original native Save/Continue captures.
    if initial[0x3DA0:0x3E0B] != saved[0x3DA0:0x3E0B]:
        raise ValueError('Production Journal changed the original 107 quest bytes')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--environment', choices=('Windows', 'Wine on Linux'), default='Windows')
    args = parser.parse_args()
    if os.name != 'nt':
        print('PLAYER_LATE_JOURNAL_UNAVAILABLE requires Windows APIs')
        return 77
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    process = None
    report = dict(status='running', platform=args.environment, full_game_verified=False,
                  scope='Production later original Continue, Journal and fresh process reload')
    try:
        spec = json.loads(args.manifest.read_text(encoding='utf-8'))
        exe, seed = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
        references = [args.manifest.parent / spec[key] for key in ('field_reference', 'menu_reference')]
        for path, expected in ((exe, spec['executable_sha256']), (seed, spec['seed_sha256']),
                               *zip(references, spec['reference_sha256'], strict=True)):
            if digest(path) != expected:
                raise ValueError(f'Pinned production input hash differs: {path.name}')
        initial = seed.read_bytes()
        saved = out / 'late-copy.sav'
        shutil.copyfile(seed, saved)
        field, menu = map(bitmap, references)
        api = Window()

        def reach_field(round_name: str) -> int:
            nonlocal process
            log = (out / (round_name+'.log')).open('wb')
            process = subprocess.Popen([str(exe), '--play', str(saved), '--scale', '1',
                                        '--audio-volume', '0'], cwd=out, stdout=log,
                                       stderr=subprocess.STDOUT)
            hwnd = api.find(process)
            # The accepted original boot transcript waits 1,921 frames before
            # Start. Let the normal production frame loop show those screens.
            time.sleep(35)
            for key in (0x0D, 0x5A, 0x5A):
                api.pulse(hwnd, key, 2)
            deadline = time.monotonic()+20
            best = 0
            while time.monotonic() < deadline:
                pixels = api.capture(hwnd, out/(round_name+'-field.bmp'))
                match = sum(a == b for a, b in zip(field, pixels, strict=True))/len(field)
                best = max(best, match)
                if match >= .85:
                    report[round_name+'_field_match'] = match
                    api.pulse(hwnd, 0x5A, 1.8)
                    hud = api.capture(hwnd, out/(round_name+'-menu.bmp'))
                    if hud[104*480:] != menu[104*480:]:
                        raise ValueError('Original later party HUD differs in production player')
                    return hwnd
                time.sleep(.25)
            raise RuntimeError(f'Later original field was not reached; best pixel match {best:.3f}')

        hwnd = reach_field('continue')
        for key in (0x27, 0x28, 0x5A):
            api.pulse(hwnd, key, 1.8 if key == 0x5A else .5)
        for _ in range(5):
            api.pulse(hwnd, 0x28, .5)
        for _ in range(3):
            api.pulse(hwnd, 0x5A, 1.8)
        api.capture(hwnd, out/'original-journal.bmp')
        for key in (0x5A, 0x58, 0x58):
            api.pulse(hwnd, key, 1)
        api.close(hwnd, process)
        process = None
        if digest(saved) == spec['seed_sha256']:
            raise ValueError('Original GUI Journal did not change the copied save')
        verify_saved_roster(initial, saved.read_bytes())
        saved_hash = digest(saved)
        hwnd = reach_field('reload')
        api.close(hwnd, process)
        process = None
        if digest(saved) != saved_hash or digest(seed) != spec['seed_sha256'] or digest(exe) != spec['executable_sha256']:
            raise ValueError('Original source, production binary or saved Journal changed unexpectedly')
        report.update(status='passed', source=spec['source'], executable_sha256=digest(exe),
                      input_journal_sha256=digest(seed), production_journal_sha256=saved_hash,
                      original_owned_creatures=sum(initial[i*165] in (1, 2) for i in range(40)),
                      quest_bytes=107, original_p1_only=True, fresh_process_reload=True,
                      normal_shutdowns=2)
        print('PLAYER_LATE_JOURNAL_PASS original_P1 original_Journal fresh_production_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('PLAYER_LATE_JOURNAL_FAIL', error)
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=15)
        (out/'player-late-journal.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
