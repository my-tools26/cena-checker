#!/usr/bin/env bash
# Cap nhat IP DuckDNS (phong khi IP public cua VM doi). Doc domain + token
# tu /etc/cena-duckdns.conf (do bootstrap.sh ghi).
set -euo pipefail
CONF="/etc/cena-duckdns.conf"
[ -f "$CONF" ] || exit 0
# shellcheck disable=SC1090
source "$CONF"   # dinh nghia DUCKDNS_SUB va DUCKDNS_TOKEN
curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_SUB}&token=${DUCKDNS_TOKEN}&ip=" >/dev/null || true
