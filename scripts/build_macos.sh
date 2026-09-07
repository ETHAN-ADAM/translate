#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src"

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "smilestranslate-mac" \
  --paths "$ROOT/src" \
  --collect-all rdkit \
  --collect-all numpy \
  "$ROOT/src/main.py"

echo "Build complete: dist/smilestranslate-mac.app"
