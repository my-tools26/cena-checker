#!/usr/bin/env bash
#
# Bootstrap Cena Checker tren VM Oracle Cloud (Ubuntu 22.04).
# Chay MOT LAN, cai het: Python deps, Caddy (HTTPS), systemd service,
# auto-deploy git-poll, DuckDNS updater, mo firewall.
#
# Dung:
#   sudo bash deploy/bootstrap.sh <subdomain>.duckdns.org <duckdns-token>
# Vi du:
#   sudo bash deploy/bootstrap.sh cena-checker.duckdns.org 1a2b3c4d-....
#
set -euo pipefail

DOMAIN="${1:-}"
DUCKDNS_TOKEN="${2:-}"
REPO="/home/ubuntu/cena-checker"

if [ -z "$DOMAIN" ] || [ -z "$DUCKDNS_TOKEN" ]; then
	echo "Thieu tham so. Dung: sudo bash deploy/bootstrap.sh <domain>.duckdns.org <token>"
	exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
	echo "Can chay bang sudo."
	exit 1
fi

DUCKDNS_SUB="${DOMAIN%%.duckdns.org}"
echo "==> Domain: $DOMAIN  (DuckDNS sub: $DUCKDNS_SUB)"

# --- 1. Goi he thong ---
echo "==> Cai goi he thong (python3, pip, git, curl, iptables-persistent)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip git curl debconf-utils
echo "iptables-persistent iptables-persistent/autosave_v4 boolean true"  | debconf-set-selections
echo "iptables-persistent iptables-persistent/autosave_v6 boolean true"  | debconf-set-selections
apt-get install -y iptables-persistent

# --- 2. Caddy (repo chinh thuc) ---
if ! command -v caddy >/dev/null 2>&1; then
	echo "==> Cai Caddy..."
	apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
	apt-get update -y
	apt-get install -y caddy
fi

# --- 3. Mo firewall OS (OCI Ubuntu chan san moi port tru 22) ---
echo "==> Mo port 80/443 tren iptables..."
iptables -C INPUT -p tcp --dport 80  -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport 80  -j ACCEPT
iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport 443 -j ACCEPT
netfilter-persistent save

# --- 4. Repo: clone/pull ---
if [ ! -d "$REPO/.git" ]; then
	echo "==> Clone repo..."
	sudo -u ubuntu git clone https://github.com/my-tools26/cena-checker.git "$REPO"
else
	echo "==> Repo da co, pull ban moi..."
	sudo -u ubuntu git -C "$REPO" pull --ff-only origin master
fi
chown -R ubuntu:ubuntu "$REPO"

# --- 5. Python deps (chi runtime phuc vu trang) ---
echo "==> Cai Python deps..."
pip3 install -r "$REPO/requirements-server.txt" --quiet

# --- 6. DuckDNS config + cap nhat IP lan dau ---
cat > /etc/cena-duckdns.conf <<EOF
DUCKDNS_SUB="$DUCKDNS_SUB"
DUCKDNS_TOKEN="$DUCKDNS_TOKEN"
EOF
chmod 600 /etc/cena-duckdns.conf
echo "==> Cap nhat IP DuckDNS lan dau..."
bash "$REPO/deploy/duckdns-update.sh" || true

# --- 7. systemd: app + auto-deploy + duckdns ---
echo "==> Cai systemd services..."
cp "$REPO/deploy/cena.service"            /etc/systemd/system/
cp "$REPO/deploy/cena-autodeploy.service" /etc/systemd/system/
cp "$REPO/deploy/cena-autodeploy.timer"   /etc/systemd/system/
cp "$REPO/deploy/cena-duckdns.service"    /etc/systemd/system/
cp "$REPO/deploy/cena-duckdns.timer"      /etc/systemd/system/

# Cho phep user ubuntu restart 'cena' khong can mat khau (auto-deploy can)
cat > /etc/sudoers.d/cena-deploy <<'EOF'
ubuntu ALL=(root) NOPASSWD: /usr/bin/systemctl restart cena
EOF
chmod 440 /etc/sudoers.d/cena-deploy

systemctl daemon-reload
systemctl enable --now cena.service
systemctl enable --now cena-autodeploy.timer
systemctl enable --now cena-duckdns.timer

# --- 8. Caddy (HTTPS) ---
echo "==> Cau hinh Caddy cho $DOMAIN..."
CENA_DOMAIN="$DOMAIN" envsubst < "$REPO/deploy/Caddyfile" > /etc/caddy/Caddyfile 2>/dev/null \
	|| sed "s|{\$CENA_DOMAIN}|$DOMAIN|g" "$REPO/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl reload caddy || systemctl restart caddy

echo ""
echo "======================================================"
echo "  XONG! Cho ~30s de Caddy xin chung chi HTTPS."
echo "  Mo:  https://$DOMAIN"
echo ""
echo "  Kiem tra:   systemctl status cena caddy cena-autodeploy.timer"
echo "  Log deploy: tail -f $REPO/deploy/autodeploy.log"
echo "======================================================"
