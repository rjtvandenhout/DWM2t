@echo off
setlocal
set "PSModulePath=%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch.ps1" %*
set "DWM2T_EXIT=%ERRORLEVEL%"
if not "%DWM2T_EXIT%"=="0" pause
exit /b %DWM2T_EXIT%
