"""Централизованная конфигурация SOPDS NG.

Этот модуль предоставляет единую точку доступа ко всем настройкам системы,
инкапсулируя логику получения значений из разных источников:
1. Constance (динамические настройки в БД).
2. Django settings (статические настройки в файлах).
3. Значения по умолчанию.

Использование:
    from opds_catalog.config import catalog_config
    if catalog_config.AUTH_ENABLED:
        ...
"""

from typing import Any

from constance import config as constance_config
from django.conf import settings


class SopdsConfig:
    """Класс конфигурации системы.

    Свойства предоставляют доступ к настройкам с автоматическим
    разрешением приоритетов (Constance -> Settings -> Default).
    """

    # --- Общие настройки ---
    @property
    def VERSION(self) -> str:
        return getattr(settings, "VERSION", "develop")

    @property
    def TITLE(self) -> str:
        return getattr(settings, "SOPDS_TITLE", "SimpleOPDS NG")

    @property
    def SUBTITLE(self) -> str:
        return getattr(
            settings,
            "SOPDS_SUBTITLE",
            f"SimpleOPDS Catalog new generation. Version {self.VERSION}",
        )

    @property
    def ICON(self) -> str:
        return getattr(settings, "SOPDS_ICON", "/static/images/favicon.ico")

    @property
    def LOGLEVEL(self) -> str:
        return getattr(settings, "SOPDS_LOGLEVEL", "info")

    @property
    def THUMB_SIZE(self) -> int:
        return getattr(settings, "THUMB_SIZE", 300)

    # --- Безопасность и доступ ---
    @property
    def AUTH_ENABLED(self) -> bool:
        return constance_config.SOPDS_AUTH

    # --- Кэширование и Лимиты ---
    @property
    def CACHE_TIME(self) -> int:
        return constance_config.SOPDS_CACHE_TIME

    @property
    def MAX_ITEMS(self) -> int:
        return constance_config.SOPDS_MAXITEMS

    # --- Пути и Файловая система ---
    @property
    def ROOT_LIB(self) -> str:
        return constance_config.SOPDS_ROOT_LIB

    @property
    def TEMP_DIR(self) -> str:
        return constance_config.SOPDS_TEMP_DIR

    # --- Конвертеры ---
    @property
    def FB2_TO_EPUB_PATH(self) -> str:
        return constance_config.SOPDS_FB2TOEPUB

    @property
    def FB2_TO_MOBI_PATH(self) -> str:
        return constance_config.SOPDS_FB2TOMOBI

    # --- Логика каталогов и поиска ---
    @property
    def TITLE_AS_FILENAME(self) -> bool:
        return constance_config.SOPDS_TITLE_AS_FILENAME

    @property
    def ALPHABET_MENU_ENABLED(self) -> bool:
        return constance_config.SOPDS_ALPHABET_MENU

    @property
    def SPLIT_ITEMS_THRESHOLD(self) -> int:
        return constance_config.SOPDS_SPLITITEMS

    @property
    def DOUBLES_HIDE(self) -> bool:
        return constance_config.SOPDS_DOUBLES_HIDE

    @property
    def BOOK_EXTENSIONS(self) -> list[str]:
        val = constance_config.SOPDS_BOOK_EXTENSIONS
        return val.split() if isinstance(val, str) else val

    # --- Сканирование ---
    @property
    def DELETE_LOGICAL(self) -> bool:
        return constance_config.SOPDS_DELETE_LOGICAL

    @property
    def ZIP_SCAN_ENABLED(self) -> bool:
        return constance_config.SOPDS_ZIPSCAN

    @property
    def INPX_ENABLED(self) -> bool:
        return constance_config.SOPDS_INPX_ENABLE

    @property
    def INPX_SKIP_UNCHANGED(self) -> bool:
        return constance_config.SOPDS_INPX_SKIP_UNCHANGED

    @property
    def INPX_TEST_ZIP(self) -> str:
        return constance_config.SOPDS_INPX_TEST_ZIP

    @property
    def INPX_TEST_FILES(self) -> bool:
        return constance_config.SOPDS_INPX_TEST_FILES

    # --- Языки ---
    @property
    def CURRENT_LANGUAGE(self) -> str:
        return constance_config.SOPDS_LANGUAGE

    # --- Телеграм-бот ---
    @property
    def BOT_TOKEN(self) -> str:
        return constance_config.SOPDS_TELEBOT_API_TOKEN

    @property
    def BOT_AUTH_ENABLED(self) -> bool:
        return constance_config.SOPDS_TELEBOT_AUTH

    @property
    def BOT_PID_FILE(self) -> str:
        return constance_config.SOPDS_TELEBOT_PID

    @property
    def BOT_LOG_FILE(self) -> str:
        return constance_config.SOPDS_TELEBOT_LOG

    @property
    def BOT_MAX_ITEMS(self) -> int:
        return constance_config.SOPDS_TELEBOT_MAXITEMS

    # --- Сервер и Фоновые задачи ---
    @property
    def SERVER_PID_FILE(self) -> str:
        return constance_config.SOPDS_SERVER_PID

    @property
    def SERVER_LOG_FILE(self) -> str:
        return constance_config.SOPDS_SERVER_LOG

    @property
    def SCANNER_PID_FILE(self) -> str:
        return constance_config.SOPDS_SCANNER_PID

    @property
    def SCANNER_LOG_FILE(self) -> str:
        return constance_config.SOPDS_SCANNER_LOG

    @property
    def SCAN_SHED_DAY(self) -> int:
        return constance_config.SOPDS_SCAN_SHED_DAY

    @property
    def SCAN_SHED_DOW(self) -> int:
        return constance_config.SOPDS_SCAN_SHED_DOW

    @property
    def SCAN_SHED_HOUR(self) -> int:
        return constance_config.SOPDS_SCAN_SHED_HOUR

    @property
    def SCAN_SHED_MIN(self) -> int:
        return constance_config.SOPDS_SCAN_SHED_MIN

    @property
    def SCAN_START_DIRECTLY(self) -> bool:
        return constance_config.SOPDS_SCAN_START_DIRECTLY


catalog_config = SopdsConfig()
