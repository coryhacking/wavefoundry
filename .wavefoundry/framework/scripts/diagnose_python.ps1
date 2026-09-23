# Read-only workstation prerequisite diagnosis; does not require Python or MCP.
# Run from a checkout: powershell -NoProfile -File ".../diagnose_python.ps1"
# Respect execution policy. Do not use -ExecutionPolicy Bypass to run this script.
[CmdletBinding()]
param([switch]$Json)

$ErrorActionPreference = 'Stop'

function Get-PythonProbe([string]$Name) {
    $result = [ordered]@{ command = $Name; resolved = $null; stage = 'command resolution'; state = 'missing' }
    $candidate = Get-Command "$Name.exe" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $candidate) { return [pscustomobject]$result }
    $result.resolved = $candidate.Source
    $result.stage = 'interpreter execution/version'
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = $Name
    # Fixed arguments; no shell, user-provided code, profile, site imports or bytecode.
    $process.StartInfo.Arguments = '-I -S -B -c "import sys,json;print(json.dumps({''version'':list(sys.version_info[:2]),''executable'':sys.executable}))"'
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardInput = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    try {
        [void]$process.Start()
        $process.StandardInput.Close()
        $outTask = $process.StandardOutput.ReadToEndAsync()
        $errTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(15000)) {
            $result.state = 'timeout'
            $result.detail = 'Interpreter probe exceeded 15 seconds; cause undetermined.'
            try { $process.Kill() } catch { $result.detail += ' Child termination failed: ' + $_.Exception.Message }
            # Drain each stream independently after termination, with its own
            # bound; descendants may keep a pipe open, so never wait forever.
            foreach ($stream in @(@('stdout', $outTask), @('stderr', $errTask))) {
                try {
                    if ($stream[1].Wait(1000)) {
                        $output = $stream[1].Result
                        $result[$stream[0]] = $output.Substring(0, [Math]::Min(2000, $output.Length))
                    }
                } catch { $result.detail += ' Stream capture unavailable: ' + $_.Exception.Message }
            }
            return [pscustomobject]$result
        }
        $result.exit_code = $process.ExitCode
        $outComplete = $outTask.Wait(1000)
        $errComplete = $errTask.Wait(1000)
        foreach ($stream in @(@('stdout', $outTask, $outComplete), @('stderr', $errTask, $errComplete))) {
            if ($stream[2]) {
                $output = $stream[1].Result
                $result[$stream[0]] = $output.Substring(0, [Math]::Min(2000, $output.Length))
            }
        }
        if (-not $outComplete -or -not $errComplete) {
            $result.state = 'timeout'
            $result.detail = 'Probe exited but output streams did not close within the deadline.'
            return [pscustomobject]$result
        }
        $stdout = $outTask.Result
        if ($result.exit_code -ne 0) {
            $result.state = 'failed_exit'
            return [pscustomobject]$result
        }
        try {
            $identity = $stdout | ConvertFrom-Json
            if ($identity.version.Count -ne 2 -or
                $identity.version[0] -isnot [int] -or $identity.version[1] -isnot [int] -or
                $identity.version[0] -lt 0 -or $identity.version[1] -lt 0 -or
                $identity.executable -isnot [string] -or [string]::IsNullOrWhiteSpace($identity.executable)) {
                throw 'Invalid interpreter identity'
            }
            $result.version = $identity.version
            $result.executable = $identity.executable
            $result.state = 'too_old'
            if ($identity.version[0] -gt 3 -or ($identity.version[0] -eq 3 -and $identity.version[1] -ge 11)) {
                $result.state = 'ok'
            }
        } catch {
            $result.state = 'invalid_output'
        }
    } catch {
        $result.state = 'launch_error'
        $result.detail = $_.Exception.Message
    } finally {
        $process.Dispose()
    }
    return [pscustomobject]$result
}

$canonical = Get-PythonProbe 'python3'
$probes = @($canonical)
if ($canonical.state -ne 'ok') { $probes += Get-PythonProbe 'python' }
$guidance = @(
    'These observations describe this workstation, even if this checkout is already seeded.',
    'python.exe is discovery only: MCP configuration must continue to launch python3.',
    'If a probe failed, its cause is undetermined unless the reported error establishes it. Inspect PATH and Manage app execution aliases; a Store redirect is not a working interpreter.',
    'Prefer an existing approved python3 executable/alias and permitted user PATH repair. No administrator rights, Store access or Developer Mode are assumed.',
    'If policy prevents repair or only python.exe works, ask IT to expose the approved Python 3.11+ installation as python3 to the agent host. Include command, resolved path, result, exit/error and interpreter identity from this report.',
    'After repair use a fresh terminal to verify python3 --version, then python3 .wavefoundry/framework/scripts/server.py --dry-run; fully quit and reopen the agent host and verify MCP initialization. Interpreter success alone does not prove MCP bootstrap readiness.',
    'Do not change the MCP command, bypass execution policy, reseed or rebuild an index to repair command resolution. This diagnostic does not intentionally write configuration, install dependencies or change the environment.'
)
$report = [ordered]@{ interpreter_ready = ($canonical.state -eq 'ok'); probes = $probes; next_steps = $guidance }
if ($Json) { $report | ConvertTo-Json -Depth 6 } else {
    foreach ($probe in $probes) { $probe | Format-List | Out-String | Write-Output }
    $guidance | Write-Output
}
if ($canonical.state -ne 'ok') { exit 2 }
exit 0
