#!/bin/sh
set -e
if [ -d /app/jobs.sqlite ]; then
  echo "jobs.sqlite is a directory. On the host, remove it and run: touch jobs.sqlite" >&2
  exit 1
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8765}"
