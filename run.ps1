<#
.SYNOPSIS
Starts the complete local development environment.
.DESCRIPTION
Starts PostgreSQL, MongoDB, Redis and Mailpit in Docker, then runs the API,
ML service and frontend on the host with reload, plus both background workers.
Installs locked dependencies and applies migrations. Ctrl+C stops the host
processes started by this launcher; Docker data services keep running.
.EXAMPLE
.\run.ps1
.EXAMPLE
.\run.ps1 -Check
#>
[CmdletBinding()]
param(
    [switch]$Check,
    [ValidateRange(30, 1800)][int]$StartupTimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
try {
    foreach ($command in @('docker', 'node', 'npx.cmd', 'uv')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            throw "Missing $command. See DEVELOPMENT.md for prerequisites, then reopen PowerShell."
        }
    }
    & node -e 'const [major, minor] = process.versions.node.split(String.fromCharCode(46)).map(Number); process.exit(major > 20 || (major === 20 && minor >= 9) ? 0 : 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Node.js 20.9+ is required; Node.js 22 matches the Docker image.' }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop with Linux containers and wait for its engine.' }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required. Update Docker Desktop.' }

    $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    foreach ($port in @(3000, 8000, 8001)) {
        if ($listeners.Port -contains $port) {
            throw "Port $port is already in use. Stop that app in its terminal, or run ./start.ps1 -Stop if it is the Docker app stack."
        }
    }
    if ($Check) {
        Write-Host 'Prerequisites, Docker engine/Compose and app ports passed. No services were started.'
        return
    }

    & (Join-Path $PSScriptRoot 'start.ps1') -DataOnly -StartupTimeoutSeconds $StartupTimeoutSeconds
    if ($LASTEXITCODE -ne 0) { throw 'Docker data services did not start.' }
    & (Join-Path $PSScriptRoot 'scripts/run-all.ps1') -StartupTimeoutSeconds $StartupTimeoutSeconds
} catch {
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'See DEVELOPMENT.md. Docker data is retained; this launcher does not stop pre-existing app servers.'
    exit 1
}
