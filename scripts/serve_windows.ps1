<#
.SYNOPSIS
  Launch the AutoTester UI on this Windows machine (T-203, D-090, hosting.md HO39-HO46).
.DESCRIPTION
  Runs `uv run uvicorn autotester.ui.app:app`. Binds 127.0.0.1 unless -Lan (or env
  AUTOTESTER_BIND_HOST) says otherwise. Data root = AUTOTESTER_ROOT (default
  %ProgramData%\AutoTester), outside the code tree. Logs go to <data root>\logs.
  -DryRun prints the resolved plan and exits without starting anything.
  -Check calls /healthz on the configured port and exits non-zero on failure.
  Never sets AUTOTESTER_AUTH_DISABLED.
#>
[CmdletBinding()]
param(
  [switch]$Lan,
  [int]$Port = 8000,
  [string]$DataRoot,
  [string]$AllowedOrigins,
  [switch]$DryRun,
  [switch]$Check
)
$ErrorActionPreference = 'Stop'
$RepoDir = Split-Path -Parent $PSScriptRoot

if (-not $DataRoot) { $DataRoot = $env:AUTOTESTER_ROOT }
if (-not $DataRoot) { $DataRoot = Join-Path $env:ProgramData 'AutoTester' }
$BindHost = '127.0.0.1'
if ($env:AUTOTESTER_BIND_HOST) { $BindHost = $env:AUTOTESTER_BIND_HOST }
if ($Lan) { $BindHost = '0.0.0.0' }
if (-not $AllowedOrigins) { $AllowedOrigins = $env:AUTOTESTER_ALLOWED_ORIGINS }
if (-not $AllowedOrigins) { $AllowedOrigins = "http://127.0.0.1:$Port,http://localhost:$Port" }

if ($Check) {
  $probe = if ($BindHost -eq '0.0.0.0') { '127.0.0.1' } else { $BindHost }
  try {
    $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri "http://${probe}:$Port/healthz"
    if ($r.StatusCode -ne 200) { Write-Error "healthz status $($r.StatusCode)"; exit 1 }
    Write-Output "healthz ok"; exit 0
  } catch { Write-Error "healthz failed: $_"; exit 1 }
}

$uvArgs = @('run', 'uvicorn', 'autotester.ui.app:app', '--host', $BindHost, '--port', "$Port")
$LogDir = Join-Path $DataRoot 'logs'

if ($DryRun) {
  Write-Output "bind_host=$BindHost"
  Write-Output "port=$Port"
  Write-Output "data_root=$DataRoot"
  Write-Output "allowed_origins=$AllowedOrigins"
  Write-Output "log_dir=$LogDir"
  Write-Output "command=uv $($uvArgs -join ' ')"
  exit 0
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$env:AUTOTESTER_ROOT = $DataRoot
$env:AUTOTESTER_ALLOWED_ORIGINS = $AllowedOrigins
Remove-Item Env:AUTOTESTER_AUTH_DISABLED -ErrorAction SilentlyContinue
$log = Join-Path $LogDir 'serve.log'
$stamp = (Get-Date).ToString('s')
if ($BindHost -ne '127.0.0.1') {
  Add-Content $log "$stamp LAN BINDING ENABLED: listening on ${BindHost}:$Port"
} else {
  Add-Content $log "$stamp loopback binding: 127.0.0.1:$Port"
}
Set-Location $RepoDir
& uv @uvArgs *>> $log
exit $LASTEXITCODE
