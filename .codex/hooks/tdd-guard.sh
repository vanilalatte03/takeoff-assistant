#!/usr/bin/env bash
set -u

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if [ -n "${CODEX_PROJECT_PYTHON:-}" ] && [ -x "${CODEX_PROJECT_PYTHON:-}" ]; then
  exec "$CODEX_PROJECT_PYTHON" "$repo_root/scripts/guard.py" "${1:-}"
fi

for candidate in "$repo_root/.venv/Scripts/python.exe" "$repo_root/.venv/bin/python" python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
    exec "$candidate" "$repo_root/scripts/guard.py" "${1:-}"
  fi
done

if command -v py >/dev/null 2>&1; then
  exec py -3 "$repo_root/scripts/guard.py" "${1:-}"
fi

echo "WARNING: Python was not found; skipping Codex template guard." >&2
exit 0
