# PowerShell script to start backend with venv activated
$ErrorActionPreference = "Stop"

$backend_dir = "d:\Krishna\STEMbotix\Demo\STEMbotix-AI-new\STEMai-backend"
$venv_path = Join-Path $backend_dir "venv\Scripts\Activate.ps1"

Write-Host "Activating virtual environment..."
& $venv_path

Write-Host "Starting backend server on port 8123..."
Write-Host "Backend directory: $backend_dir"

cd $backend_dir
python run.py
