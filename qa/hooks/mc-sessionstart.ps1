# maker-checker Layer 2 — session-start directive (pending-state aware, AUTO-CONTINUE)
# SessionStart stdout is injected into the agent's context — a directive here is read as an
# instruction, not just a status line.
$LEDGER = 'qa/issues.jsonl'
$ROOT = (Get-Location).Path
$n = -1
if (Test-Path $LEDGER) { $n = @(Get-Content $LEDGER | Where-Object { $_ -match '"status":\s*"(open|Open)"' }).Count }
# Pending handshake (cycle-aware): ready-for-check with no verdict, or a verdict for an older
# cycle, or a PASS verdict whose manifest was never flipped to checked-PASS.
$pending = @(); $unclosed = @()
if (Test-Path 'qa/manifests') {
  foreach ($m in Get-ChildItem 'qa/manifests' -Filter *.md -ErrorAction SilentlyContinue) {
    $v = "qa/verdicts/" + $m.Name
    if (-not (Select-String -Path $m.FullName -Pattern 'Status: ready-for-check' -Quiet)) { continue }
    if (-not (Test-Path $v)) { $pending += $m.BaseName; continue }
    $mc = 0; $a = Select-String -Path $m.FullName -Pattern 'Fix cycle[:*\s]+(\d+)' | Select-Object -First 1
    if ($a) { $mc = [int]$a.Matches[0].Groups[1].Value }
    $vc = -1; $b = Select-String -Path $v -Pattern '(Cycle checked|Fix cycle judged)[:*\s]+(\d+)' | Select-Object -First 1
    if ($b) { $vc = [int]$b.Matches[0].Groups[2].Value }
    if ($vc -lt $mc) { $pending += $m.BaseName; continue }
    if (Select-String -Path $v -Pattern 'VERDICT:\s*PASS' -Quiet) { $unclosed += $m.BaseName }
  }
}
$queue = 0
if (Test-Path 'qa/QUEUE.md') { $queue = @(Select-String -Path 'qa/QUEUE.md' -Pattern '\|\s*TODO\s*\|').Count }
function AgeMin($f) { if (Test-Path $f) { [int]((Get-Date) - (Get-Item $f).LastWriteTime).TotalMinutes } else { -1 } }
$tickAge = AgeMin 'qa/.last-tick'; $sweepAge = AgeMin 'qa/.last-sweep'
$tickTxt = 'NEVER'; if ($tickAge -ge 0) { $tickTxt = "$tickAge min ago" }
$sweepTxt = 'NEVER'; if ($sweepAge -ge 0) { $sweepTxt = "$sweepAge min ago" }
$backlog = ($n -gt 0) -or ($queue -gt 0) -or ($pending.Count -gt 0) -or ($unclosed.Count -gt 0)
$asleep = $backlog -and (($tickAge -lt 0) -or ($tickAge -gt 120))
$openTxt = 'UNKNOWN (no ledger)'; if ($n -ge 0) { $openTxt = "$n" }
$pendTxt = ''; if ($pending.Count) { $pendTxt = ' [' + ($pending -join ', ') + ']' }
Write-Output ("MAKER-CHECKER ACTIVE: substantive dev work routes through /maker (say 'normal' to opt out). Open issues: $openTxt | Checks pending: $($pending.Count)$pendTxt | PASS not closed out: $($unclosed.Count) | Queue TODO: $queue | Last tick: $tickTxt | Last sweep: $sweepTxt | Ledger: $LEDGER")
if (Test-Path 'qa/.paused') {
  Write-Output ("PAUSED by user: " + (Get-Content 'qa/.paused' -TotalCount 1) + " - auto-continue SUSPENDED. Do not run /maker continue; the user lifts it with /maker resume (or by deleting qa/.paused).")
} elseif ($pending.Count -or $unclosed.Count -or $asleep -or ($sweepAge -lt 0) -or ($sweepAge -gt 120)) {
  Write-Output ("AUTO-CONTINUE REQUIRED: pending maker-checker state found. Run /maker continue " + [char]34 + $ROOT + [char]34 + " BEFORE anything else this session (it reconciles close-outs, dispatches pending checks and the due sweep, then pulls the next unit and self-continues via ScheduleWakeup). Do not wait to be asked.")
}

# AT-383 part A (D-048, Approved-by Umesh, gate at383 answer C): surface
# `autotester loop-status --strict` at session start so a silent loop
# (AT-368) announces itself at the first moment anyone could act, instead of
# waiting for a human to type the command. Read-only (LS4), bounded by a
# timeout, and MUST NOT change this hook's own exit code either way -- a
# liveness check that can hang or fail the session start would be worse than
# the silence it replaces (same reasoning as loop_status.py's own doctor
# exclusion). `--project $ROOT` pins uv to this project regardless of the
# hook's cwd; AUTOTESTER_ROOT (if the caller set it, e.g. tests) still governs
# which qa/.last-tick loop-status actually reads.
$lsTimeoutMs = 15000
if ($env:AUTOTESTER_LOOPSTATUS_TIMEOUT_MS) {
  # Test-only override (AT-622): lets a behavioural test bound a real hung
  # grandchild to a couple of seconds instead of waiting out the real 15s.
  $lsParsedTimeout = 0
  if ([int]::TryParse($env:AUTOTESTER_LOOPSTATUS_TIMEOUT_MS, [ref]$lsParsedTimeout) -and $lsParsedTimeout -gt 0) {
    $lsTimeoutMs = $lsParsedTimeout
  }
}
try {
  $lsPsi = New-Object System.Diagnostics.ProcessStartInfo
  $lsPsi.FileName = "uv"
  $lsPsi.Arguments = "run --project `"$ROOT`" autotester loop-status --strict"
  $lsPsi.WorkingDirectory = $ROOT
  $lsPsi.UseShellExecute = $false
  $lsPsi.RedirectStandardOutput = $true
  $lsPsi.RedirectStandardError = $true
  $lsProc = New-Object System.Diagnostics.Process
  $lsProc.StartInfo = $lsPsi
  [void]$lsProc.Start()
  $lsStdout = $lsProc.StandardOutput.ReadToEndAsync()
  $lsStderr = $lsProc.StandardError.ReadToEndAsync()
  $lsExited = $lsProc.WaitForExit($lsTimeoutMs)
  if (-not $lsExited) {
    # AT-622: Windows PowerShell 5.1/.NET Framework's Process.Kill() has no
    # entireProcessTree overload -- it kills only this `uv` process, and `uv
    # run` always starts python as a child, which would otherwise survive.
    # taskkill /T stops the whole tree; its own failures (already exited,
    # etc.) are swallowed here -- this path must still reach the skip line
    # below and must never fail the hook.
    try { & taskkill /T /F /PID $lsProc.Id *> $null } catch {}
    Write-Output ("loop-status: skipped (timed out after " + ($lsTimeoutMs / 1000) + "s)")
  } else {
    $lsStdout.Result -split "`r?`n" | Where-Object { $_ -ne "" } | ForEach-Object { Write-Output ("  " + $_) }
    if ($lsProc.ExitCode -ne 0) {
      Write-Output ("LOOP UNHEALTHY (loop-status --strict exit " + $lsProc.ExitCode + ")")
      $lsErrTail = $lsStderr.Result -split "`r?`n" | Where-Object { $_ -ne "" } | Select-Object -Last 1
      if ($lsErrTail) { Write-Output ("  stderr: " + $lsErrTail) }
    }
  }
} catch {
  Write-Output "loop-status: skipped (uv/autotester unavailable)"
}

# Living map (L5): regenerate + inject the snapshot so reading it is not optional.
if (Test-Path 'docs/SNAPSHOT.md') {
  try { & uv run autotester snapshot 2>$null | Out-Null } catch {}
  Write-Output "--- docs/SNAPSHOT.md (generated; router in CLAUDE.md) ---"
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  Get-Content 'docs/SNAPSHOT.md' -Encoding UTF8 | Write-Output
}
exit 0
