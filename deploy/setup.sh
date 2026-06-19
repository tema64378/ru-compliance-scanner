#!/usr/bin/env bash
# Turnkey-установка 152чек на свежий Ubuntu-VPS.
# Перед запуском: замени ВАШ_ДОМЕН в deploy/nginx.conf и положи .env (BOT_TOKEN, ROBOKASSA_*).
#
#   sudo bash deploy/setup.sh
set -e

APP=/var/www/152check
REPO=https://github.com/tema64378/ru-compliance-scanner

echo "[1/6] Пакеты…"
apt update
apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx git

echo "[2/6] Код…"
mkdir -p /var/www
if [ -d "$APP/.git" ]; then cd "$APP" && git pull; else git clone "$REPO" "$APP" && cd "$APP"; fi

echo "[3/6] Зависимости…"
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"

echo "[4/6] .env"
[ -f "$APP/.env" ] || { echo "‼️  Положи $APP/.env (BOT_TOKEN, ROBOKASSA_LOGIN/PASS1/PASS2). Прервал."; exit 1; }
chown -R www-data:www-data "$APP"

echo "[5/6] systemd-сервисы (API + бот)…"
cp "$APP/deploy/compliance-api.service" /etc/systemd/system/
cp "$APP/deploy/compliance-bot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now compliance-api compliance-bot

echo "[6/6] nginx…"
cp "$APP/deploy/nginx.conf" /etc/nginx/sites-available/152check
ln -sf /etc/nginx/sites-available/152check /etc/nginx/sites-enabled/152check
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo
echo "✅ Готово. Дальше — HTTPS:  certbot --nginx -d ВАШ_ДОМЕН"
echo "   Логи:  journalctl -u compliance-api -f   |   journalctl -u compliance-bot -f"
