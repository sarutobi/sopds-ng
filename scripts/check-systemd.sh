#!/usr/bin/env bash
#
# check-systemd.sh — проверка systemd-сервиса SOPDS NG после установки
# Использование: ./check-systemd.sh
# Exit code: 0 = всё OK, 1 = ошибка

set -e

SERVICE="sopds"
PORT="8008"

echo "=== Проверка systemd-сервиса SOPDS NG ==="
echo ""

# 1. Проверка: сервис активен
echo -n "[1/4] Проверка активности сервиса $SERVICE ... "
if systemctl is-active --quiet "$SERVICE"; then
    echo "OK (active)"
else
    echo "ОШИБКА: сервис $SERVICE не активен"
    systemctl status "$SERVICE" --no-pager 2>&1 | head -5
    exit 1
fi

# 2. Проверка: сервис включён в автозапуск
echo -n "[2/4] Проверка автозапуска сервиса $SERVICE ... "
if systemctl is-enabled --quiet "$SERVICE"; then
    echo "OK (enabled)"
else
    echo "ОШИБКА: сервис $SERVICE не включён в автозапуск"
    exit 1
fi

# 3. Проверка: в journal нет ошибок
echo -n "[3/4] Проверка journal на наличие ошибок ... "
if journalctl -u "$SERVICE" -n 5 --no-pager 2>/dev/null | grep -qi "error"; then
    echo "ОШИБКА: в journal сервиса $SERVICE обнаружены ошибки"
    journalctl -u "$SERVICE" -n 10 --no-pager
    exit 1
else
    echo "OK (ошибок не найдено)"
fi

# 4. Проверка: порт 8008 слушается
echo -n "[4/4] Проверка порта $PORT ... "
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "OK (порт $PORT открыт)"
else
    echo "ОШИБКА: порт $PORT не слушается"
    echo "Проверьте, что gunicorn запущен и настроен на порт $PORT"
    exit 1
fi

echo ""
echo "=== Все проверки пройдены успешно ==="
exit 0
