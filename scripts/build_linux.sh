#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src"

python -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "smiles转化器" \
  --paths "$ROOT/src" \
  --collect-all rdkit \
  --collect-all numpy \
  "$ROOT/src/main.py"

chmod +x "dist/smiles转化器"
echo "Build complete: dist/smiles转化器"
