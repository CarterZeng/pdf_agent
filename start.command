#!/bin/zsh
cd "$(dirname "$0")"

if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" "run_all.py"
else
  exec python3 "run_all.py"
fi
