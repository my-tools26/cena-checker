#!/usr/bin/env bash
# Auto-deploy: keo commit moi tu GitHub roi restart service (git-poll).
# Duoc goi moi 2 phut boi cena-autodeploy.timer.
set -euo pipefail

REPO="/home/ubuntu/cena-checker"
BRANCH="master"
LOG="$REPO/deploy/autodeploy.log"

cd "$REPO"

# Lay commit moi nhat tu remote
git fetch --quiet origin "$BRANCH"
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse "origin/$BRANCH")"

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0  # khong co gi moi
fi

echo "[$(date '+%F %T')] Deploy $LOCAL -> $REMOTE" >> "$LOG"
git pull --ff-only --quiet origin "$BRANCH"

# Cai lai deps neu requirements-server.txt doi (khong sao neu khong doi)
pip3 install -r requirements-server.txt --quiet 2>>"$LOG" || true

sudo systemctl restart cena
echo "[$(date '+%F %T')] Da restart cena, version moi deploy xong." >> "$LOG"
