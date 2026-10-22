@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch.ps1" %*
set "DWM2T_EXIT=%ERRORLEVEL%"
if not "%DWM2T_EXIT%"=="0" pause
exit /b %DWM2T_EXIT%
