#!/bin/bash
cd "$(dirname "$0")"
git fetch origin --quiet 2>/dev/null || true
if git rev-parse --verify origin/main >/dev/null 2>&1; then
  git reset --mixed origin/main --quiet
fi
git add -A
git diff --cached --quiet && exit 0
git commit -m "Aggiornamento automatico $(date '+%Y-%m-%d %H:%M')" -q
git push -q
