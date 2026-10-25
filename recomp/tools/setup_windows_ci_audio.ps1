# Ephemeral GitHub Windows runners only. Installs a real signed render device;
# does not modify the game, its tests, Windows test-signing, or user machines.
# Mozilla cubeb Windows-2025 WinMM precedent:
# https://github.com/mozilla/cubeb/blob/dcd7cddafa4b95776cf5d117549ad58e17f23764/.github/scripts/setup_windows_audio.ps1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'This setup is restricted to ephemeral GitHub Windows CI.'
}
if (Test-Path -LiteralPath $Output) { throw 'Audio evidence directory must be new.' }
[IO.Directory]::CreateDirectory($Output) | Out-Null
Add-Type @'
using System.Runtime.InteropServices;
public static class NativeAudioProbe {
    [DllImport("winmm.dll")] public static extern uint waveOutGetNumDevs();
}
'@
$before = [NativeAudioProbe]::waveOutGetNumDevs()
$report = [ordered]@{schema=1; status='not_started'; endpoint_before=$before; physical_audibility_assessed=$false; tests_modified=$false}
try {
    Get-Service -Name AudioEndpointBuilder,Audiosrv | Format-List * | Out-File (Join-Path $Output 'services-before.txt') -Encoding utf8
    Get-CimInstance Win32_SoundDevice | Format-List * | Out-File (Join-Path $Output 'sound-devices-before.txt') -Encoding utf8
    foreach ($name in @('AudioEndpointBuilder','Audiosrv')) {
        Set-Service -Name $name -StartupType Automatic
        Start-Service -Name $name
    }
    $report.endpoint_after_services = [NativeAudioProbe]::waveOutGetNumDevs()
    $downloads = @(
        @{name='VBCABLE_Driver_Pack43.zip'; url='https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip'; sha='66fd0a4d9f4896ff41632b7e3d53892c085c4561f53e8ae8d0f0bc10eedd1cdd'},
        @{name='devcon.exe'; url='https://raw.githubusercontent.com/mozilla/cubeb/dcd7cddafa4b95776cf5d117549ad58e17f23764/.github/tools/windows/devcon.exe'; sha='97cff42f8c0fe4fbdf991273159516bf78090625a933c3983ebd6f62284e329a'}
    )
    foreach ($item in $downloads) {
        $path = Join-Path $Output $item.name
        Invoke-WebRequest -Uri $item.url -OutFile $path -MaximumRetryCount 3 -RetryIntervalSec 2
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $item.sha) { throw "Download identity differs: $($item.name)" }
    }
    $report.downloads = $downloads
    $driver = Join-Path $Output 'driver'
    Expand-Archive -LiteralPath (Join-Path $Output 'VBCABLE_Driver_Pack43.zip') -DestinationPath $driver
    $catalog = Join-Path $driver 'vbaudio_cable64_win7.cat'
    $signature = Get-AuthenticodeSignature -LiteralPath $catalog
    if ($null -eq $signature.SignerCertificate) { throw 'Missing signed driver catalog certificate.' }
    if ($signature.Status -ne 'Valid') { throw 'The pinned driver catalog signature is not valid.' }
    $report.catalog_signature_before = [string]$signature.Status
    $report.catalog_subject = $signature.SignerCertificate.Subject
    $report.catalog_thumbprint = $signature.SignerCertificate.Thumbprint
    $certificate = Join-Path $Output 'publisher.cer'
    [IO.File]::WriteAllBytes($certificate, $signature.SignerCertificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))
    # Trust the pinned publisher only; never add a root or enable test-signing.
    & certutil.exe -addstore -f TrustedPublisher $certificate 2>&1 | Out-File (Join-Path $Output 'trusted-publisher.txt') -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Could not trust the signed driver publisher.' }
    $report.catalog_signature_after = [string](Get-AuthenticodeSignature -LiteralPath $catalog).Status
    & (Join-Path $Output 'devcon.exe') install (Join-Path $driver 'vbMmeCable64_win7.inf') VBAudioVACWDM 2>&1 | Out-File (Join-Path $Output 'device-install.txt') -Encoding utf8
    $report.device_install_exit = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw 'Signed render-device installation failed or requires restart.' }
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        $after = [NativeAudioProbe]::waveOutGetNumDevs()
        if ($after -gt 0) { break }
        Start-Sleep -Seconds 1
    } while ([DateTime]::UtcNow -lt $deadline)
    $report.endpoint_after = $after
    Get-Service -Name AudioEndpointBuilder,Audiosrv | Format-List * | Out-File (Join-Path $Output 'services-after.txt') -Encoding utf8
    Get-CimInstance Win32_SoundDevice | Format-List * | Out-File (Join-Path $Output 'sound-devices-after.txt') -Encoding utf8
    Get-PnpDevice -Class AudioEndpoint,MEDIA | Format-List * | Out-File (Join-Path $Output 'pnp-after.txt') -Encoding utf8
    if ($after -eq 0) { throw 'Windows still reports no genuine WinMM render endpoint.' }
    $report.status = 'passed'
    Write-Host "WINDOWS_CI_AUDIO_HOST_PASS endpoints=$after"
} catch {
    $report.status = 'failed'
    $report.error = $_.Exception.Message
    throw
} finally {
    $report | ConvertTo-Json -Depth 8 | Out-File (Join-Path $Output 'audio-host.json') -Encoding utf8
}
