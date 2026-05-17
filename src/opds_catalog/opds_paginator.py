"""Модуль для работы c пейджером и постраничной навигацией.

Позволяет строить постраничнуюy навигацию по результатам поиска, справочникам и другим
коллекциям.

Created on 21 нояб. 2016 г.

@author: mitsh
@author Valery A. Ilychev
"""

from typing import TypedDict


class PaginatorData(TypedDict):
    """Данные для пагинации."""

    num_pages: int
    has_previous: bool
    has_next: bool
    previous_page_number: int
    next_page_number: int
    number: int
    page_range: list[int]


class Paginator:
    """Класс пейджера для работы с постраничной навигацией."""

    def __init__(
        self,
        d1_count: int,
        d2_count: int,
        page_num: int = 1,
        maxitems: int = 60,
        half_pages_link: int = 3,
    ):
        """Создание пейджера и расчет результата.

        Параметры:
            d1_count - число элементов для пагинации
            d2_count - число книг в катлоге либо 0 для других элементов
            page_num - текущая страница, которая отображается в пейджере
            maxitems - число объектов на странице пейджера
            half_pages_link -
        """
        self.d1_count = d1_count
        self.d2_count = d2_count
        self.count = self.d1_count + self.d2_count  # зачем?
        self.MAXITEMS = maxitems
        self.HALF_PAGES_LINK = half_pages_link
        self.page_num = page_num
        self.calc_data()

    def _calc_first_pos(self, MAXITEMS: int, limit: int) -> int:
        """Расчет первой позиции для подгрузки элементов."""
        d1_first_pos: int = MAXITEMS * (self.page_num - 1)
        d1_first_pos: int = (
            d1_first_pos if d1_first_pos < limit else (limit - 1 if limit else 0)
        )
        return d1_first_pos

    def _calc_last_pos(self, MAXITEMS: int, limit: int) -> int:
        """Расчет последней позиции для подгрузки элементов."""
        d1_last_pos: int = MAXITEMS * self.page_num - 1
        d1_last_pos: int = (
            d1_last_pos if d1_last_pos < limit else (limit - 1 if limit else 0)
        )
        return d1_last_pos

    def calc_data(self):
        """Расчет данных пейджера."""
        # Первый сегмент (например каталоги)
        d1_MAXITEMS = self.MAXITEMS
        self.d1_first_pos = self._calc_first_pos(d1_MAXITEMS, self.d1_count)
        self.d1_last_pos = self._calc_last_pos(d1_MAXITEMS, self.d1_count)

        # Второй сегмент (книги)
        d2_MAXITEMS = self.MAXITEMS - self.d1_last_pos + self.d1_first_pos
        self.d2_first_pos = self._calc_first_pos(d2_MAXITEMS, self.d2_count)
        self.d2_last_pos = self._calc_last_pos(d2_MAXITEMS, self.d2_count)

        # Общие данные пейджера
        self.num_pages: int = self.count // self.MAXITEMS + 1
        self.firstpage: int = self.page_num - self.HALF_PAGES_LINK
        self.lastpage: int = self.page_num + self.HALF_PAGES_LINK
        # Корректировка диапазонов при приближении к границам
        if self.firstpage < 1:
            self.lastpage = self.lastpage - self.firstpage + 1
            self.firstpage = 1

        if self.lastpage > self.num_pages:
            self.firstpage = self.firstpage - (self.lastpage - self.num_pages)
            self.lastpage = self.num_pages
            self.firstpage = max(self.firstpage, 1)

        self.has_previous: bool = self.page_num > 1
        self.has_next: bool = self.page_num < self.num_pages
        self.previous_page_number: int = (self.page_num - 1) if self.page_num > 1 else 1
        self.next_page_number: int = (
            (self.page_num + 1) if self.page_num < self.num_pages else self.num_pages
        )

        self.page_range: list[int] = [
            i for i in range(self.firstpage, self.lastpage + 1)
        ]

    def get_data_dict(self) -> PaginatorData:
        """Возвращает метаданные пейджера."""
        p: PaginatorData = {
            "num_pages": self.num_pages,
            "has_previous": self.has_previous,
            "has_next": self.has_next,
            "previous_page_number": self.previous_page_number,
            "next_page_number": self.next_page_number,
            "number": self.page_num,
            "page_range": self.page_range,
        }
        return p
