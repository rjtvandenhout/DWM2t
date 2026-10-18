[CmdletBinding()]
param([string]$BuildDirectory = 'recomp/build')

# Offline local equivalent of the hosted Windows milestone gates.
# All acceptance tests must pass; no quota/network error is treated as a pass.
$ErrorActionPreference = 'Stop'
$m7RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$m7Source = Join-Path $m7RepoRoot 'recomp'
if (-not [IO.Path]::IsPathRooted($BuildDirectory)) {
    $BuildDirectory = Join-Path $m7RepoRoot $BuildDirectory
}
$BuildDirectory = [IO.Path]::GetFullPath($BuildDirectory)
$m7CmakeCommand = Get-Command cmake.exe -ErrorAction SilentlyContinue
$m7Cmake = if ($m7CmakeCommand) { $m7CmakeCommand.Source } else {
    Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Python/Python314/Scripts/cmake.exe'
}
if (-not (Test-Path -LiteralPath $m7Cmake -PathType Leaf)) {
    throw 'CMake ontbreekt. Installeer CMake en voeg het toe aan PATH.'
}
$m7Vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$m7VsInstallation = if (Test-Path -LiteralPath $m7Vswhere) {
    & $m7Vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
}
if (-not $m7VsInstallation) { throw 'Visual Studio C++ Build Tools ontbreken.' }
$m7DeveloperPrompt = Join-Path $m7VsInstallation 'Common7/Tools/VsDevCmd.bat'
foreach ($m7Path in @($m7Cmake, $m7Source, $BuildDirectory, $m7DeveloperPrompt)) {
    if ($m7Path -match '["%\r\n]') { throw 'Niet-ondersteund teken in buildpad.' }
}
$m7Configure = ''
if (-not (Test-Path -LiteralPath (Join-Path $BuildDirectory 'CMakeCache.txt'))) {
    $m7Configure = '"' + $m7Cmake + '" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -S "' + $m7Source + '" -B "' + $BuildDirectory + '" && '
}
$m7Command = 'call "' + $m7DeveloperPrompt + '" -arch=x64 && ' + $m7Configure +
    '"' + $m7Cmake + '" --build "' + $BuildDirectory + '" --config Release --target check-m7'
Write-Host 'Lokale M7-validatie: bouwen en alle twaalf controles uitvoeren.'
Write-Host ('Bewijs/logs: ' + (Join-Path $BuildDirectory 'Testing/Temporary/LastTest.log'))
& $env:ComSpec /d /c $m7Command
if ($LASTEXITCODE -ne 0) { throw "M7 niet geaccepteerd: lokale validatie faalde (exit $LASTEXITCODE)." }
Write-Host 'Alle lokale M7-gates zijn geslaagd.'
