#!/usr/bin/env bash
set -e

echo "🔍 Проверка systemd unit sopds..."

systemctl is-active --quiet sopds && echo "✅ Сервис активен" || { echo "❌ Сервис не активен"; exit 1; }
systemctl is-enabled --quiet sopds && echo "✅ Сервис автозапущен" || { echo "❌ Сервис не автозапущен"; exit 1; }

echo "🔍 Проверка логов..."
journalctl -u sopds -n 5 --no-pager | grep -qiE "traceback|error|critical" && { echo "❌ Найдены ошибки в логах"; exit 1; } || echo "✅ Логи без ошибок"

echo "🔍 Проверка порта..."
ss -tlnp | grep -q ":8008" && echo "✅ Порт 8008 слушается" || { echo "❌ Порт 8008 не слушается"; exit 1; }

echo "✅ Все проверки пройдены"
exit 0
