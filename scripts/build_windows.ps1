$ErrorActionPreference = "Stop"

Write-Host "==============================================="
Write-Host "Building smilestranlates-win.exe"
Write-Host "==============================================="

$env:PYTHONPATH = "$PSScriptRoot\..\src"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "smilestranlates-win" `
  --paths "$PSScriptRoot\..\src" `
  --collect-all rdkit `
  --collect-all numpy `
  "$PSScriptRoot\..\src\main.py"

Write-Host ""
Write-Host "Build complete:"
Write-Host "dist\smilestranlates-win.exe"
