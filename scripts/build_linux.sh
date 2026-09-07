#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src"

python -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "smilestranslate-Linux-x86_64" \
  --paths "$ROOT/src" \
  --collect-all rdkit \
  --collect-all numpy \
  "$ROOT/src/main.py"

chmod +x "dist/smilestranslate-Linux-x86_64"
echo "Build complete: dist/smilestranslate-Linux-x86_64"
