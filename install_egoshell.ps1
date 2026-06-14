# EgoShell PowerShell Installer for Windows
$ErrorActionPreference = "Stop"

Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ⟨ E G O S H E L L ⟩ Setup       ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if setup.py is present in the current folder, otherwise clone it
$RepoUrl = "https://github.com/prettymuchgavin/EGOSHELL.git"
$DirName = "EGOSHELL"

if (Test-Path "setup.py") {
    Write-Host "Running installation from current directory..." -ForegroundColor Green
} else {
    $InstallDir = Join-Path $HOME $DirName
    Write-Host "Cloning EGOSHELL repository to $InstallDir..." -ForegroundColor Cyan
    if (Test-Path $InstallDir) {
        Write-Host "Directory $DirName already exists. Pulling latest changes..." -ForegroundColor Yellow
        Set-Location $InstallDir
        git pull
    } else {
        git clone $RepoUrl $InstallDir
        Set-Location $InstallDir
    }
}

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Cyan
$pythonCmd = "python"
try {
    $version = & $pythonCmd --version 2>&1
    Write-Host "Using: $version" -ForegroundColor Green
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10+."
    exit 1
}

# Create and activate Python virtual environment
Write-Host "Setting up Python virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    & $pythonCmd -m venv .venv
    Write-Host "Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
}

# Activate and run setup.py
Write-Host "Running setup.py..." -ForegroundColor Cyan
& .venv\Scripts\python.exe setup.py

Write-Host "Setup complete!" -ForegroundColor Green
