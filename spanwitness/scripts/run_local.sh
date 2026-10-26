#!/bin/sh
set -eu
task_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$task_root"
exec .venv/bin/python -m uvicorn spanwitness.app:app --host 127.0.0.1 --port 8765
