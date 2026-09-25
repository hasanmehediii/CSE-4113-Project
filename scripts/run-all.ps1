$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$shellPath = (Get-Process -Id $PID).Path
$services = @(
    @{ Name = 'api'; Port = 8000 },
    @{ Name = 'ml-service'; Port = 8001 },
    @{ Name = 'web'; Port = 3000 }
)
$started = @()

# Check before launching anything; never terminate an unrelated server.
foreach ($command in @('node', 'npx.cmd', 'uv')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Missing $command. Install Node.js and uv, then reopen PowerShell."
    }
}
$listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
foreach ($service in $services) {
    if ($listeners.Port -contains $service.Port) {
        throw "Port $($service.Port) is already in use. Stop that server before running all apps."
    }
}

$logDirectory = Join-Path $repoRoot ('.cache/run-all/' + [guid]::NewGuid().ToString('N'))
[System.IO.Directory]::CreateDirectory($logDirectory) | Out-Null

try {
    foreach ($service in $services) {
        $scriptPath = Join-Path $repoRoot "apps/$($service.Name)/run.ps1"
        $stdout = Join-Path $logDirectory "$($service.Name).out.log"
        $stderr = Join-Path $logDirectory "$($service.Name).err.log"
        $process = Start-Process -FilePath $shellPath -WindowStyle Hidden -PassThru `
            -ArgumentList @('-NoProfile', '-File', ('"' + $scriptPath + '"')) `
            -WorkingDirectory (Split-Path $scriptPath -Parent) `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $started += @{ Name = $service.Name; Process = $process }
        Write-Host "Starting $($service.Name): http://localhost:$($service.Port)"
    }

    Write-Host "Logs: $logDirectory"
    Write-Host 'Press Ctrl+C to stop all three apps.'
    while ($true) {
        foreach ($service in $started) {
            if ($service.Process.HasExited) {
                Get-Content -LiteralPath (Join-Path $logDirectory "$($service.Name).err.log") -Tail 20
                throw "$($service.Name) exited. Stopping the other apps. See the logs above."
            }
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    foreach ($service in $started) {
        if (-not $service.Process.HasExited) {
            # Include uvicorn's reload worker and Next.js child processes.
            & taskkill.exe /PID $service.Process.Id /T /F 2>&1 | Out-Null
        }
        $service.Process.Dispose()
    }
}
