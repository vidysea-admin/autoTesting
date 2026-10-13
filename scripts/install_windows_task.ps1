<#
.SYNOPSIS
  Register (or remove) the AutoTester Scheduled Task: start at boot, restart on failure (HO39, HO40).
.DESCRIPTION
  Needs an elevated shell. Supports -WhatIf (prints what would be registered, changes nothing).
  -Uninstall removes the task. The task runs scripts\serve_windows.ps1 as -UserName.
.EXAMPLE
  powershell -File scripts\install_windows_task.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
  [string]$TaskName = 'AutoTester',
  [string]$UserName = "$env:USERDOMAIN\$env:USERNAME",
  [switch]$Lan,
  [int]$Port = 8000,
  [int]$RestartCount = 5,
  [int]$RestartIntervalMinutes = 1,
  [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$Serve = Join-Path $PSScriptRoot 'serve_windows.ps1'
$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$Serve`" -Port $Port"
if ($Lan) { $argLine += ' -Lan' }

if ($Uninstall) {
  if ($PSCmdlet.ShouldProcess($TaskName, 'Unregister-ScheduledTask')) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }
  return
}

Write-Output "task=$TaskName user=$UserName trigger=AtStartup restart=${RestartCount}x/${RestartIntervalMinutes}min"
Write-Output "action=powershell.exe $argLine"
if ($PSCmdlet.ShouldProcess($TaskName, 'Register-ScheduledTask (at startup, restart on failure)')) {
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argLine `
    -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $settings = New-ScheduledTaskSettingsSet -RestartCount $RestartCount `
    -RestartInterval (New-TimeSpan -Minutes $RestartIntervalMinutes) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries
  # A boot task must run without an interactive logon (HO39), so it needs the account password.
  $cred = Get-Credential -UserName $UserName -Message 'Account the AutoTester task runs as'
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -User $UserName -Password $cred.GetNetworkCredential().Password -RunLevel Limited | Out-Null
  Write-Output "registered $TaskName"
}
