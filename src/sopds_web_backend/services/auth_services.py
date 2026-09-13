"""Сервисы для управления аутентификацией и защитой."""

from django.core.cache import cache
from django.utils.translation import gettext as _

# Конфигурация лимитов
LOGIN_ATTEMPTS_LIMIT = 5
LOGIN_ATTEMPTS_TIMEOUT = 300  # 5 минут


def get_login_attempts_key(ip: str) -> str:
    """Генерирует ключ кэша для счетчика попыток входа."""
    return f"login_attempts_{ip}"


def is_rate_limited(ip: str) -> bool:
    """Проверяет, превышен ли лимит попыток входа для данного IP."""
    attempts = cache.get(get_login_attempts_key(ip), 0)
    return attempts >= LOGIN_ATTEMPTS_LIMIT


def record_failed_attempt(ip: str) -> None:
    """Увеличивает счетчик неудачных попыток входа."""
    key = get_login_attempts_key(ip)
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, LOGIN_ATTEMPTS_TIMEOUT)


def reset_attempts(ip: str) -> None:
    """Сбрасывает счетчик попыток входа при успешной аутентификации."""
    cache.delete(get_login_attempts_key(ip))
