[CmdletBinding()]
param(
    [ValidateRange(1, 4)][int]$Jobs = 2,
    [string]$Workspace,
    [string]$Output,
    [string]$Generator
)
$ErrorActionPreference = 'Stop'
$arguments = @((Join-Path $PSScriptRoot 'tools\build_m8_candidate.py'), '--jobs', "$Jobs")
if ($Workspace) { $arguments += @('--workspace', $Workspace) }
if ($Output) { $arguments += @('--output', $Output) }
if ($Generator) { $arguments += @('--generator', $Generator) }
Write-Host 'Building an UNTESTED full-AOT candidate. No tests or gameplay will run.'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @arguments
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python @arguments
} else {
    throw 'Install Python 3.10 or newer and make it available on PATH.'
}
exit $LASTEXITCODE
