#!/bin/bash
# Local cron wrapper — backup to GitHub Actions hourly sync.
# Pulls latest first to avoid conflicts with cloud-side commits.
set -e
cd /Users/chris/AthleteDashboard

export GIT_AUTHOR_NAME="Chris Lombardi"
export GIT_AUTHOR_EMAIL="chris@ouiaresocial.com"
export GIT_COMMITTER_NAME="Chris Lombardi"
export GIT_COMMITTER_EMAIL="chris@ouiaresocial.com"

echo "===== $(date) ====="

# Pull any cloud-pushed updates first
git pull --rebase --autostash origin main || true

/opt/homebrew/bin/python3 garmin_fetch.py

if git diff --quiet garmin_data.json; then
  echo "No data changes, skipping push"
else
  git add garmin_data.json
  git commit -m "Local sync: $(date +%Y-%m-%d\ %H:%M)"
  /opt/homebrew/bin/gh auth setup-git 2>/dev/null || true
  git pull --rebase --autostash origin main || true
  git push origin main
  echo "Pushed to GitHub"
fi
