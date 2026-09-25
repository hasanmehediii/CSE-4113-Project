$ErrorActionPreference = 'Stop'

if (-not (Get-Command node -ErrorAction SilentlyContinue) -or
    -not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
    throw 'Install Node.js 20.9+ (22 recommended), then reopen PowerShell.'
}

Push-Location $PSScriptRoot
try {
    & npx.cmd --yes pnpm@10.34.5 install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }

    & npx.cmd --yes pnpm@10.34.5 dev --hostname 127.0.0.1 --port 3000
    if ($LASTEXITCODE -ne 0) { throw "Next.js exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
}
