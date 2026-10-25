DWM2t - Native Windows x64 player
M8 RELEASE CANDIDATE - TESTING PENDING

This is a build candidate, not a verified full-game release. Its executable
contains fixed bank 0 and all 255 switchable banks translated ahead of time.
Complete code coverage does not prove that every game path works correctly.
No runtime instruction-interpreter fallback is added.

START
Extract the entire package into a new directory. Run Play.cmd for checksum
verification, session logs and profile handling. Python, CMake and Visual
Studio are not needed for playing a built package. The executable also starts
the game directly with no arguments; it does not run the old self-test harness.
Keep older packages until the new candidate has been tested.

CONTROLS
Arrow keys: D-pad. Z: A. X: B. Enter: Start. Backspace: Select.
The field menu opens with A while facing an empty tile, NOT with Start.
Use PLAN > Journal and complete the original confirmation to save progress.
Closing the window flushes cartridge SRAM; it is NOT an in-game Journal Save.

SAVES AND PROFILES
Default: %LOCALAPPDATA%\DWM2t\saves\default.sav
Backups: %LOCALAPPDATA%\DWM2t\saves\backups\<profile>\
Logs:    %LOCALAPPDATA%\DWM2t\logs\
Native failure reports: %LOCALAPPDATA%\DWM2t\saves\diagnostics\

Examples from a command prompt inside this package:
  Play.cmd -Profile rick
  Play.cmd -Profile imported -ImportSave "C:\My Games\original.sav"
  Play.cmd -Profile recovery -ImportSave "C:\path\to\a\backup.sav"

Import requires a NEW profile and an exact 32768-byte SRAM file. It copies;
it never moves or deletes the source. There are no bundled user/test saves.
Old files are not searched for or imported automatically. Profiles stay outside
the installation directory, so extracting an update does not replace them.

The native player locks its selected save and creates a pre-launch backup.
The launcher also retains its own pre-launch copy and profile lock. Extra
32-KiB backups are intentional and are not automatically deleted. Keep the
launcher running while its child game is open. Do not modify a save externally
while playing. Backups protect prior sessions; they do not replace Journal.
Native writes use a separate temporary file, flush, then same-directory
replacement. Storage errors leave writes pending rather than marking success.
Filesystem/hardware failures and later-game behavior still require testing.

AUDIO
Default game volume: 5%, with smoothing and the retained playback prebuffer.
These options do not change Windows system settings:
  Play.cmd -Volume 1
  Play.cmd -ListAudioDevices
  Play.cmd -AudioDevice 0 -Volume 5
  Play.cmd -RawAudio -Volume 5

DIRECT EXECUTABLE
  DWM2tRecomp.exe --help
  DWM2tRecomp.exe --version
  DWM2tRecomp.exe --profile rick --scale 4
  DWM2tRecomp.exe --play "C:\My Games\copy.sav" --audio-volume 5

Use either --profile or an explicit save path. Direct launch retains native
save locking/backups but not the launcher's package checks and session logs.
Diagnostic --m7/--m8 replay commands are deliberately absent from this player;
they remain in the separate development executable built from recomp/.

IF THE GAME STOPS
Do not overwrite your old package or original save. Keep the launcher logs,
source commit shown by --version, and native diagnostics/last-frame.bmp.
Import a preserved backup into a NEW profile rather than replacing evidence.
An unexpected missing bank, CPU trap or frame-budget failure remains an error;
it is never silently bypassed. No fabricated recovery state is created.

BUILD INFORMATION
manifest.json records the source commit, all-bank inventory and file SHA-256s.
source-manifest.json records the committed input files. Checksums detect
accidental changes; they are not a digital signature or full-game certification.
The build report and compiler logs are distributed as a separate build artifact.
All validation is pending for this candidate. No final M8 restore is asserted.
See LICENSE-NOTICE.md. The build embeds original game data; keep this package
within the authorized project/owned-ROM workflow. No public release is automated.
