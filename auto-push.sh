#!/bin/bash
cd ~/training-dashboard
git add -A
git diff --cached --quiet && exit 0
git commit -m "Aggiornamento automatico $(date '+%Y-%m-%d %H:%M')" -q
git push -q
