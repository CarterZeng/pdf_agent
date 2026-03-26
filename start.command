#!/bin/zsh
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" "run_all.py"
else
  exec python3 "run_all.py"
fi
