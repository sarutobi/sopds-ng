import logging
from typing import Any, Dict, List, Tuple

from opds_catalog.config import catalog_config
from opds_catalog.models import Book

logger = logging.getLogger(__name__)


class BookPager:
    """
    Сервис пагинации книг с логикой дедупликации.
    Работает с объектами Book, не зависит от Telegram API.
    """

    def __init__(
        self,
        queryset,
        page: int,
        query: str,
        max_items: int = None,
        hide_doubles: bool = None,
    ):
        self.queryset = queryset
        self.page = page
        self.query = query

        from django.conf import settings

        self.max_items = (
            max_items
            if max_items is not None
            else getattr(settings, "SOPDS_TELEBOT_MAXITEMS", 10)
        )
        self.hide_doubles = (
            hide_doubles
            if hide_doubles is not None
            else getattr(settings, "SOPDS_DOUBLES_HIDE", True)
        )

    def get_page_items(self) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Возвращает список данных книг для текущей страницы и метаданные пагинации.
        """
        # Принудительно выкачиваем все результаты в список
        all_items = list(self.queryset)
        total_count = len(all_items)

        if total_count == 0:
            return [], {"total": 0, "current": self.page}

        # Расчет границ страницы
        start_idx = (self.page - 1) * self.max_items
        end_idx = start_idx + self.max_items

        if start_idx >= total_count:
            return [], {
                "total": total_count,
                "current": self.page,
                "error": "empty_page",
            }

        # Берем срез объектов для текущей страницы
        page_objects = all_items[start_idx:end_idx]

        # --- Логика дедупликации ---
        items = []
        prev_item = None
        if self.hide_doubles and start_idx > 0:
            prev_item = all_items[start_idx - 1]

        for row in page_objects:
            # Создаем словарь с данными книги
            book_data = {
                "id": row.id,
                "title": row.title,
                "authors": row.authors.values(),
                "doubles": 0,
            }

            if (
                self.hide_doubles
                and prev_item
                and row.title.upper() == prev_item.title.upper()
            ):
                if items:
                    items[-1]["doubles"] += 1
                else:
                    # Если первый элемент страницы — дубль предыдущей, пропускаем его (поведение pop(0))
                    pass
            else:
                items.append(book_data)
            prev_item = row

        # Досчитываем дубликаты со следующей страницы
        if end_idx < total_count and items:
            next_items = all_items[end_idx : end_idx + self.max_items]
            last_item_on_page = page_objects[-1]
            for next_item in next_items:
                if next_item.title.upper() == last_item_on_page.title.upper():
                    items[-1]["doubles"] += 1
                else:
                    break

        return items, {
            "total": total_count,
            "current": self.page,
            "doubles": {it["id"]: it["doubles"] for it in items},
            "has_next": end_idx < total_count,
            "has_prev": start_idx > 0,
        }
