$ErrorActionPreference = "Stop"

Write-Host "==============================================="
Write-Host "Building smiles转化器.exe"
Write-Host "==============================================="

$env:PYTHONPATH = "$PSScriptRoot\..\src"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "smiles转化器" `
  --paths "$PSScriptRoot\..\src" `
  --collect-all rdkit `
  --collect-all numpy `
  "$PSScriptRoot\..\src\main.py"

Write-Host ""
Write-Host "Build complete:"
Write-Host "dist\smiles转化器.exe"
