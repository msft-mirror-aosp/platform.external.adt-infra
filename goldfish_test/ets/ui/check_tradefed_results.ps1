# Checks the result XML files Tradefed wrote under a results directory and exits with 1 unless at
# least MinResults invocations are present and every one of them passed completely, like the
# junit_xml_result step of the ETS sequence does on gLinux and macOS.
#
# The exit code of ets-tradefed.bat cannot be used for this: Tradefed's Console exits with 0 when
# tests fail, and on Windows its main thread always dies with "Unknown signal: TSTP" (exit code 1)
# because SIGTSTP does not exist there.
param(
    [Parameter(Mandatory = $true)][string]$ResultsDir,
    [int]$MinResults = 1
)

# Tradefed names the result directories after the invocation time; skip the "latest" link.
$results = @(Get-ChildItem -Path $ResultsDir -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d' } |
    ForEach-Object { Join-Path $_.FullName 'test_result.xml' } |
    Where-Object { Test-Path -Path $_ -PathType Leaf })
if ($results.Count -lt $MinResults) {
    Write-Host "Expected $MinResults Tradefed result(s) under $ResultsDir, found $($results.Count)."
    exit 1
}

$ok = $true
foreach ($file in $results) {
    $summary = ([xml](Get-Content -Path $file)).Result.Summary
    $passed = [int]$summary.pass -ge 1 -and [int]$summary.failed -eq 0 -and
        $summary.modules_done -eq $summary.modules_total
    $verdict = if ($passed) { 'OK' } else { 'FAILED' }
    Write-Host ("Tradefed result {0}: pass={1} failed={2} modules={3}/{4} -> {5}" -f
        (Split-Path -Path (Split-Path -Path $file -Parent) -Leaf), $summary.pass, $summary.failed,
        $summary.modules_done, $summary.modules_total, $verdict)
    if (-not $passed) { $ok = $false }
}
if (-not $ok) { exit 1 }
