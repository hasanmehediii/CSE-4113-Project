[CmdletBinding()]
param([switch]$Stop, [switch]$Logs, [switch]$NoBuild)

$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([string[]]$DockerArguments)
    & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) { throw "Docker failed (exit $LASTEXITCODE). Check the output above." }
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install Docker Desktop with the WSL 2 backend, then reopen PowerShell: https://www.docker.com/products/docker-desktop/'
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop, wait for its engine to start, then retry.' }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required. Update Docker Desktop.' }

    foreach ($relativePath in @('.env', 'apps/web/.env.local')) {
        $targetPath = Join-Path $PSScriptRoot $relativePath
        if (-not (Test-Path -LiteralPath $targetPath)) {
            $examplePath = if ($relativePath -eq '.env') { Join-Path $PSScriptRoot '.env.example' } else { Join-Path $PSScriptRoot 'apps/web/.env.example' }
            Copy-Item -LiteralPath $examplePath -Destination $targetPath
            Write-Host "Created $relativePath from its example."
        }
    }
    $clientIds = @{}
    foreach ($relativePath in @('.env', 'apps/web/.env.local')) {
        foreach ($configLine in Get-Content -LiteralPath (Join-Path $PSScriptRoot $relativePath)) {
            if ($configLine -match '^\s*(GOOGLE_CLIENT_ID|NEXT_PUBLIC_GOOGLE_CLIENT_ID)\s*=\s*(.*?)\s*$') {
                $clientIds[$Matches[1]] = $Matches[2].Trim([char]34).Trim([char]39)
            }
        }
    }
    if (-not $Stop -and -not $Logs -and $clientIds['GOOGLE_CLIENT_ID'] -and $clientIds['NEXT_PUBLIC_GOOGLE_CLIENT_ID'] -and $clientIds['GOOGLE_CLIENT_ID'] -ne $clientIds['NEXT_PUBLIC_GOOGLE_CLIENT_ID']) {
        throw 'The Google client IDs in .env and apps/web/.env.local differ. Set them to the same OAuth web client ID.'
    }
    $composeArguments = @(
        'compose', '--project-directory', (Join-Path $PSScriptRoot 'infra'),
        '--env-file', (Join-Path $PSScriptRoot '.env'),
        '--env-file', (Join-Path $PSScriptRoot 'apps/web/.env.local'),
        '-f', (Join-Path $PSScriptRoot 'infra/docker-compose.local.yml')
    )
    Invoke-Docker ($composeArguments + @('config', '--quiet'))
    if ($Stop) {
        Invoke-Docker ($composeArguments + @('down'))
        Write-Host 'Stopped. Database and model volumes are preserved.'
        return
    }
    if ($Logs) { Invoke-Docker ($composeArguments + @('logs', '--follow', '--tail', '100')); return }
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $appListeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalPort -in @(3000, 8000, 8001) }
        foreach ($listener in $appListeners) {
            $listenerProcess = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
            if ($listenerProcess -and $listenerProcess.ProcessName -notmatch 'docker|wsl|vpnkit' -and $listener.OwningProcess -ne 4) {
                throw "Port $($listener.LocalPort) is used by $($listenerProcess.ProcessName). Stop that app with Ctrl+C in its terminal, then retry."
            }
        }
    }
    Write-Host 'Starting DubsiBhai. First startup downloads images, installs dependencies, and trains the synthetic ML model.'
    Write-Host 'Stop existing npm/uvicorn servers on ports 3000, 8000 and 8001 first.'
    $upArguments = @('up', '--detach', '--wait', '--wait-timeout', '600')
    if (-not $NoBuild) { $upArguments += '--build' }
    Invoke-Docker ($composeArguments + $upArguments)
    Write-Host 'Frontend: http://localhost:3000'
    Write-Host 'API docs: http://localhost:8000/docs | ML docs: http://localhost:8001/docs'
    Write-Host 'Email inbox: http://localhost:8025 | API proxy: http://localhost:8080'
    Write-Host 'PostgreSQL: localhost:5432 (database/user dubsibhai, password local-dev-only)'
    Write-Host 'Redis: localhost:6379 | MongoDB: mongodb://localhost:27017/dubsibhai'
    Write-Host 'Logs: ./start.ps1 -Logs | Stop: ./start.ps1 -Stop'
} catch {
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Run ./start.ps1 -Logs for service errors. Stop competing services for port conflicts.'
    exit 1
}
