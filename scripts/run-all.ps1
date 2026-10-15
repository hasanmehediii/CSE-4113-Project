[CmdletBinding()]
param([ValidateRange(30, 1800)][int]$StartupTimeoutSeconds = 600)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$shellPath = (Get-Process -Id $PID).Path
$services = @(
    @{ Name = 'api'; Port = 8000; ReadyUrl = 'http://127.0.0.1:8000/health' },
    @{ Name = 'ml-service'; Port = 8001; ReadyUrl = 'http://127.0.0.1:8001/ready' },
    @{ Name = 'project-events'; Worker = 'project_events' },
    @{ Name = 'classify-reports'; Worker = 'classify_reports' },
    @{ Name = 'web'; Port = 3000; ReadyUrl = 'http://127.0.0.1:3000/login' }
)
$script:started = @()

# Check before launching anything; never terminate an unrelated server.
foreach ($command in @('node', 'npx.cmd', 'uv')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Missing $command. Install Node.js and uv, then reopen PowerShell."
    }
}
$listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
foreach ($service in $services) {
    if ($service.Port -and $listeners.Port -contains $service.Port) {
        throw "Port $($service.Port) is already in use. Stop that server before running all apps."
    }
}

$logDirectory = Join-Path $repoRoot ('.cache/run-all/' + [guid]::NewGuid().ToString('N'))
[System.IO.Directory]::CreateDirectory($logDirectory) | Out-Null
Write-Host "Logs: $logDirectory"

function Show-ServiceLog {
    param([string]$Name)
    foreach ($stream in @('out', 'err')) {
        $path = Join-Path $logDirectory "$Name.$stream.log"
        if (Test-Path -LiteralPath $path) {
            Write-Host "--- $Name ($stream) ---"
            Get-Content -LiteralPath $path -Tail 20
        }
    }
}

function Assert-ServicesRunning {
    foreach ($service in $script:started) {
        if ($service.Process.HasExited) {
            Show-ServiceLog $service.Name
            throw "$($service.Name) exited (code $($service.Process.ExitCode)). Check logs in $logDirectory."
        }
    }
}

function Start-DevService {
    param([hashtable]$Service)
    $scriptPath = if ($Service.Worker) { Join-Path $repoRoot 'apps/api/run-worker.ps1' } else { Join-Path $repoRoot "apps/$($Service.Name)/run.ps1" }
    $launchArguments = @('-NoProfile', '-File', ('"' + $scriptPath + '"'), '-SkipInstall')
    if ($Service.Worker) { $launchArguments += @('-Worker', $Service.Worker) }
    $process = Start-Process -FilePath $shellPath -WindowStyle Hidden -PassThru `
        -ArgumentList $launchArguments `
        -WorkingDirectory (Split-Path $scriptPath -Parent) `
        -RedirectStandardOutput (Join-Path $logDirectory "$($Service.Name).out.log") `
        -RedirectStandardError (Join-Path $logDirectory "$($Service.Name).err.log")
    $script:started += @{ Name = $Service.Name; Process = $process }
    Write-Host "Started $($Service.Name) (PID $($process.Id))."
}

function Wait-DevService {
    param([hashtable]$Service)
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host "Waiting for $($Service.Name): $($Service.ReadyUrl)"
    while ($timer.Elapsed.TotalSeconds -lt $StartupTimeoutSeconds) {
        Assert-ServicesRunning
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Service.ReadyUrl -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch {
            # Reload servers may not have bound their sockets yet.
        }
        Start-Sleep -Milliseconds 300
    }
    Show-ServiceLog $Service.Name
    throw "$($Service.Name) was not ready after $StartupTimeoutSeconds seconds. Check $logDirectory."
}

try {
    # Sync shared API dependencies once before launching the API and its workers.
    foreach ($app in @('api', 'ml-service', 'web')) {
        Write-Host "Installing locked dependencies: $app"
        Push-Location (Join-Path $repoRoot "apps/$app")
        try {
            if ($app -eq 'web') { & npx.cmd --yes pnpm@10.34.5 install --frozen-lockfile }
            else { & uv sync --locked }
            if ($LASTEXITCODE -ne 0) { throw "$app dependency installation failed." }
        } finally { Pop-Location }
    }

    # API startup applies migrations and bootstraps the catalog/admin. ML startup
    # trains only a missing artifact. Workers need both services ready first.
    foreach ($service in $services | Where-Object { $_.Name -in @('api', 'ml-service') }) {
        Start-DevService $service
    }
    foreach ($service in $services | Where-Object { $_.Name -in @('api', 'ml-service') }) {
        Wait-DevService $service
    }
    foreach ($service in $services | Where-Object { $_.Name -notin @('api', 'ml-service') }) {
        Start-DevService $service
    }
    Wait-DevService ($services | Where-Object { $_.Name -eq 'web' })
    Assert-ServicesRunning

    Write-Host 'DubsiBhai is ready: http://localhost:3000' -ForegroundColor Green
    Write-Host 'API docs: http://localhost:8000/docs | ML docs: http://localhost:8001/docs'
    Write-Host 'Development email inbox: http://localhost:8025'
    Write-Host "Logs: $logDirectory"
    Write-Host 'Press Ctrl+C to stop all host apps and both workers. Docker data services keep running.'
    while ($true) {
        Assert-ServicesRunning
        Start-Sleep -Milliseconds 500
    }
} finally {
    foreach ($service in $script:started) {
        try {
            if (-not $service.Process.HasExited) {
                # Only the processes launched above, including their child servers.
                & taskkill.exe /PID $service.Process.Id /T /F 2>&1 | Out-Null
            }
        } catch {
            Write-Warning "Could not stop $($service.Name) (PID $($service.Process.Id)): $($_.Exception.Message)"
        } finally { $service.Process.Dispose() }
    }
}
