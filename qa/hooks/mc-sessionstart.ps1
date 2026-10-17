# maker-checker Layer 2 — session-start directive (pending-state aware, AUTO-CONTINUE)
# SessionStart stdout is injected into the agent's context — a directive here is read as an
# instruction, not just a status line.
# AT-858 (D-103): UTF-8 before the FIRST output line, not at the SNAPSHOT tail -- every earlier
# Write-Output (and the loop-status child's stdout) otherwise leaves in the host's OEM/ANSI page.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Get-ManifestStatus($path) {
  # AT-673/AT-669/AT-662: read the Status FIELD, not the phrase. Anchoring alone is not enough --
  # measured on disk, the field has SIX shapes across 263 manifests: 234 `## Status:`,
  # 20 `**Status:**`, 9 bare `Status:`, and t182 writes `## Status` as a bare heading with the
  # value on a LATER line, `- **Status: x**` as a list bullet, and `## Status (cycle 2): x` with a
  # parenthetical before the colon. An anchor that assumed `^## Status:` would have silently skipped ~37
  # manifests -- a worse under-report than the over-report this gate was opened for, and the exact
  # trap the gate warns about. The LAST field wins: manifests keep superseded cycles as history
  # (LS6), so a first match reads a closed unit's earlier state as its current one.
  $lines = @(Get-Content -Path $path -ErrorAction SilentlyContinue)
  $status = $null
  for ($i = 0; $i -lt $lines.Count; $i++) {
    $rest = $null
    if ($lines[$i] -match '^\s*[-*+]?\s*(?:#{1,3}\s*)?\*{0,2}Status\*{0,2}\s*(?:\([^)]*\))?\s*:\s*(.*)$') { $rest = $Matches[1].Trim() }
    elseif ($lines[$i] -match '^\s*[-*+]?\s*(?:#{1,3}\s*)?\*{0,2}Status\*{0,2}\s*(?:\([^)]*\))?\s*\*{0,2}\s*$') { $rest = '' }
    else { continue }
    if ($rest -eq '') {
      for ($j = $i + 1; $j -lt $lines.Count; $j++) {
        if ($lines[$j].Trim() -ne '') { $rest = $lines[$j].Trim(); break }
      }
    }
    $status = ($rest -replace '^\*+', '' -replace '\*+$', '').Trim()
  }
  return $status
}

function Get-CycleNumber($path, $names) {
  # AT-673: read the cycle FIELD wherever it sits on the line, not only at line start.
  # Measured on disk: 45 of 280 verdicts write it mid-line after a `-' separator
  # (`**Date:** ... - **Cycle checked:** 1 - **Commit:** ...`), and some write
  # `**Cycle checked: 1**` with the colon INSIDE the bold. A `^`-anchored read silently
  # skipped all 45 and scored them -1, the same silent-skip class as the Status field.
  # A fully unanchored read is not the answer either: sweep-2026-09-24.md quotes
  # `Cycle checked: 1` inside a code span while describing a DIFFERENT file, and that
  # would be read as this file's value. So the field must BEGIN at line start or just
  # after a separator -- a backtick is neither, which is what excludes the quote. An
  # inline-code strip was tried here first and removed: measured over all 543 manifests
  # and verdicts it changed zero answers, because the boundary already covers the case.
  # LAST field wins (LS6).
  # AT-713 (cycle 2, authorized by D-056): take the MAXIMUM, not the last.
  # LS6 is a rule about MANIFESTS -- they append new cycles BELOW, so last-wins is
  # right there. Verdicts order history the OPPOSITE way, newest on top. Measured
  # over all 280 verdicts: 40 carry more than one cycle value, 39 ascend and exactly
  # one descends -- and that one read 1 when it is 2. Cycle numbers only ever
  # increase, so MAX is correct under BOTH orderings while last-wins is correct
  # under only one.
  #
  # AT-714 (same waiver): the boundary no longer admits a BARE SPACE. It used to,
  # via the \s inside the character class, so ordinary prose counted -- measured on
  # disk, 24 hits sit after a plain word ("manifest Fix cycle: 1 of 3",
  # "manifest's Fix cycle: 1 of 3"), describing ANOTHER file's value. Harmless under
  # last-wins if they happened to agree; actively harmful under MAX, which is why
  # both rows had to land in the same cycle.
  #
  # The boundary is now: line start, or a character that is neither a word character
  # nor whitespace nor a backtick, followed by optional whitespace. Measured over all
  # 546 manifests and verdicts, that admits every real separator (`·` 66, `,` 41,
  # `#` heading 9, `-` 6, `.` 4) and the 533 at line start, while excluding the 23
  # quoted inside a code span and the 24 after a bare word. Written as a negated class
  # rather than a literal separator list so the file stays pure ASCII.
  $lines = @(Get-Content -Path $path -ErrorAction SilentlyContinue)
  $n = -1
  foreach ($line in $lines) {
    foreach ($mm in [regex]::Matches($line, '(?:^|[^\w\s`])\s*\*{0,2}(?:' + $names + ')\*{0,2}\s*(?:\([^)]*\))?\s*:\s*\*{0,2}\s*(\d+)')) {
      $v = [int]$mm.Groups[1].Value
      if ($v -gt $n) { $n = $v }
    }
  }
  return $n
}

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
    # AT-673/AT-669 (gate at673, option A): every read below is ANCHORED to the field it
    # claims to read. Unanchored, these matched the phrase anywhere -- prose ABOUT the handshake
    # counted as state (over-report, t182 stuck as an unclosed PASS forever) and a prose cycle
    # number silenced a manifest that really was awaiting a check (under-report). One root,
    # opposite directions; fixing only the visible half removes the symptom that motivates the
    # other. The LAST `## Status:` heading is the current one -- manifests keep superseded cycles
    # as history (LS6), so first-match would read a closed unit's earlier state as live.
    $status = Get-ManifestStatus $m.FullName
    if ($null -eq $status) { continue }
    if ($status -notmatch 'ready-for-check') { continue }
    if (-not (Test-Path $v)) { $pending += $m.BaseName; continue }
    $mc = Get-CycleNumber $m.FullName 'Fix cycle'
    if ($mc -lt 0) { $mc = 0 }
    $vc = Get-CycleNumber $v 'Cycle checked|Fix cycle judged'
    if ($vc -lt $mc) { $pending += $m.BaseName; continue }
    # The block comment above promises "a PASS verdict whose manifest was never flipped to
    # checked-PASS"; the code never checked the flip. It does now, explicitly, rather than
    # relying on the ready-for-check test above to imply it.
    if (Select-String -Path $v -Pattern '^\s*[-*+]?\s*(?:#{1,3}\s*)?\*{0,2}VERDICT[:*\s]+\s*PASS' -Quiet) {
      $unclosed += $m.BaseName
    }
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
  # AT-858: the child (python) must WRITE UTF-8 and we must READ it as UTF-8, or its non-ASCII
  # separator reaches the now-UTF-8 output as a replacement character.
  $lsPsi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
  $lsPsi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
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
  Get-Content 'docs/SNAPSHOT.md' -Encoding UTF8 | Write-Output
}
exit 0
