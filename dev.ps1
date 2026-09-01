$ErrorActionPreference = "Stop"
$repositoryRoot = $PSScriptRoot
$backendDirectory = Join-Path $repositoryRoot "backend"
$frontendDirectory = Join-Path $repositoryRoot "frontend"
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python environment not found at $pythonPath. Create it and install backend/requirements.txt first."
}

Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$backendDirectory'; & '$pythonPath' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$frontendDirectory'; npm.cmd run dev -- --hostname 127.0.0.1 --port 3000"
)

Write-Host "FinSync frontend: http://127.0.0.1:3000"
Write-Host "FinSync backend:  http://127.0.0.1:8000"
Write-Host "Backend health:   http://127.0.0.1:8000/health"
