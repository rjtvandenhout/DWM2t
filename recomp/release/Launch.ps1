# Windows PowerShell 5.1. Changes host files/options only, never game state.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9_-]{1,48}$')][string]$Profile = 'default',
    [ValidateRange(0, 100)][int]$Volume = 5,
    [ValidateRange(-1, 1024)][int]$AudioDevice = -1,
    [switch]$RawAudio,
    [switch]$ListAudioDevices,
    [string]$ImportSave,
    [string]$DataRoot
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$lock = $null
$process = $null

function Copy-OriginalSave([string]$Source, [string]$Destination) {
    # CreateNew prevents replacing any current save or previous backup.
    $inputFile = [IO.File]::Open($Source, [IO.FileMode]::Open,
        [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $outputFile = $null
    try {
        if ($inputFile.Length -ne 32768) { throw 'The source must be an exact 32 KiB SRAM file.' }
        $outputFile = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write, [IO.FileShare]::None)
        $inputFile.CopyTo($outputFile)
        $outputFile.Flush($true)
    } finally {
        if ($outputFile) { $outputFile.Dispose() }
        $inputFile.Dispose()
    }
}

try {
    if ($Profile -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$') { throw 'Reserved Windows profile name.' }
    $manifestPath = Join-Path $PSScriptRoot 'manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 1 -or $manifest.status -ne 'UNTESTED_CANDIDATE' -or
        $manifest.source_commit -notmatch '^[0-9a-f]{40}$') {
        throw 'Missing or unsupported package manifest. Use an intact candidate package.'
    }
    if (@($manifest.romx_banks).Count -ne 255) { throw 'This is not the complete-AOT package.' }
    for ($bank = 1; $bank -le 255; $bank++) {
        if ($manifest.romx_banks[$bank - 1] -ne $bank) { throw 'Incomplete AOT bank inventory.' }
    }
    $requiredFiles = @('DWM2tRecomp.exe', 'Launch.ps1', 'Play.cmd', 'README.txt',
        'LICENSE-NOTICE.md', 'source-manifest.json')
    foreach ($name in $requiredFiles) {
        $property = $manifest.files.PSObject.Properties[$name]
        if ($null -eq $property -or $property.Value -notmatch '^[0-9a-f]{64}$') {
            throw "Missing package checksum: $name"
        }
        $path = Join-Path $PSScriptRoot $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing package file: $name" }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        if ($actual -ne $property.Value) { throw "Package file changed: $name. Re-extract the package." }
    }
    if (-not $DataRoot) {
        if (-not $env:LOCALAPPDATA) { throw 'LOCALAPPDATA is unavailable. Specify -DataRoot explicitly.' }
        $DataRoot = Join-Path $env:LOCALAPPDATA 'DWM2t'
    }
    $DataRoot = [IO.Path]::GetFullPath($DataRoot)
    $saveDirectory = Join-Path $DataRoot 'saves'
    $logDirectory = Join-Path $DataRoot 'logs'
    [IO.Directory]::CreateDirectory($saveDirectory) | Out-Null
    [IO.Directory]::CreateDirectory($logDirectory) | Out-Null
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [guid]::NewGuid().ToString('N')
    $logPath = Join-Path $logDirectory "$Profile-$stamp.stdout.log"
    $errorPath = Join-Path $logDirectory "$Profile-$stamp.stderr.log"
    $sessionPath = Join-Path $logDirectory "$Profile-$stamp.session.json"
    $exe = Join-Path $PSScriptRoot 'DWM2tRecomp.exe'
    $save = Join-Path $saveDirectory "$Profile.sav"
    $backup = $null
    Write-Host "DWM2t M8 candidate $($manifest.source_commit.Substring(0,12)) - TESTING PENDING"
    Write-Host 'Use the original Journal in game. Closing the window is not an in-game Save.'

    if ($ListAudioDevices) {
        if ($ImportSave) { throw 'Do not combine -ListAudioDevices with -ImportSave.' }
        $nativeArguments = '--audio-devices'
    } else {
        # Keep this handle open until the launched game exits. A second launcher
        # cannot use the same profile; different profiles have independent locks.
        $lock = [IO.File]::Open((Join-Path $saveDirectory "$Profile.lock"),
            [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        if ($ImportSave) {
            $source = (Get-Item -LiteralPath $ImportSave).FullName
            if (Test-Path -LiteralPath $save) { throw 'The profile already has a save. Use a NEW -Profile to import.' }
            Copy-OriginalSave $source $save
            Write-Host "Imported a copy to $save. The original is unchanged."
        }
        if (Test-Path -LiteralPath $save) {
            $info = Get-Item -LiteralPath $save
            if ($info.PSIsContainer -or ($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
                $info.Length -ne 32768) { throw 'The current save is malformed or linked. Refusing to overwrite it.' }
            $backupDirectory = Join-Path (Join-Path $saveDirectory 'backups') $Profile
            [IO.Directory]::CreateDirectory($backupDirectory) | Out-Null
            $backup = Join-Path $backupDirectory "$stamp.sav"
            Copy-OriginalSave $save $backup
            Write-Host "Pre-launch backup: $backup"
        }
        # Windows filenames cannot contain a double quote; explicit quoting
        # preserves paths with spaces when Start-Process builds its command line.
        $nativeArguments = '--play "' + $save + '" --audio-volume ' + $Volume
        if ($AudioDevice -ge 0) { $nativeArguments += ' --audio-device ' + $AudioDevice }
        if ($RawAudio) { $nativeArguments += ' --audio-raw' }
        Write-Host "Profile: $Profile | Save: $save | Volume: $Volume%"
    }
    $session = [ordered]@{
        source_commit = $manifest.source_commit
        package_status = $manifest.status
        profile = $Profile
        save = $save
        backup = $backup
        started_utc = [DateTime]::UtcNow.ToString('o')
        stdout = $logPath
        stderr = $errorPath
        exit_code = $null
    }
    $session | ConvertTo-Json | Set-Content -LiteralPath $sessionPath -Encoding UTF8
    $process = Start-Process -FilePath $exe -ArgumentList $nativeArguments -WorkingDirectory $PSScriptRoot `
        -RedirectStandardOutput $logPath -RedirectStandardError $errorPath -PassThru
    $null = $process.Handle
    $process.WaitForExit()
    $process.Refresh()
    if ($null -eq $process.ExitCode) { throw 'The native process exit status is unavailable.' }
    $code = $process.ExitCode
    $session['exit_code'] = $code
    $session['finished_utc'] = [DateTime]::UtcNow.ToString('o')
    $session | ConvertTo-Json | Set-Content -LiteralPath $sessionPath -Encoding UTF8
    if ($ListAudioDevices) { Get-Content -LiteralPath $logPath }
    if ($code -ne 0) {
        Write-Host "The native game exited with code $code. Diagnostics: $errorPath"
        if ($backup) { Write-Host "Preserved backup: $backup" }
    }
    exit $code
} catch {
    [Console]::Error.WriteLine('DWM2t could not start or complete safely: ' + $_.Exception.Message)
    [Console]::Error.WriteLine('No existing save is deliberately replaced by the launcher. Check the profile and package.')
    exit 1
} finally {
    # Normal interruption of the launcher must not release its profile lock
    # while its child still runs. Forced process termination cannot be guarded.
    if ($process -and -not $process.HasExited) { $process.WaitForExit() }
    if ($lock) { $lock.Dispose() }
}
