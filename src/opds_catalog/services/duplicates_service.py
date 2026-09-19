"""Сервис определения дубликатов книг.

Единая точка логики обнаружения дубликатов. В дальнейшем
планируется вынести в плагин (Release 2.0).
"""

from __future__ import annotations

from django.db.models import QuerySet

from opds_catalog.models import Book


class DuplicatesService:
    """Сервис определения дубликатов книг.

    Критерии идентичности двух книг:
    - Одинаковое название (нормализованное).
    - Одинаковый язык.
    - Одинаковый состав авторов (порядок не важен).

    Книги на разных языках — это РАЗНЫЕ книги, даже если
    у них совпадают название и авторы.
    """

    @staticmethod
    def _make_signature(book: Book) -> str:
        """Формирует сигнатуру книги для сравнения.

        Использует ``search_full_name`` авторов вместо их ID,
        чтобы сравнение было устойчиво при наличии разных записей
        авторов с одинаковыми именами.

        :param book: Книга для анализа.
        :returns: Строка-сигнатура: ``title|lang|sorted_author_names``.
        """
        title = (book.title or "").lower().strip()
        lang = book.lang or ""
        author_names = sorted(book.authors.values_list("search_full_name", flat=True))
        return f"{title}|{lang}|{','.join(author_names)}"

    @staticmethod
    def find_doubles_for_book(book_id: int) -> QuerySet[Book]:
        """Возвращает дубликаты для указанной книги.

        :param book_id: Идентификатор книги.
        :returns: QuerySet книг-дублей (без учёта текущей).
        """
        try:
            book = Book.objects.only("title", "lang").get(id=book_id)
        except Book.DoesNotExist:
            return Book.objects.none()

        target_authors = set(book.authors.values_list("search_full_name", flat=True))
        target_lang = book.lang or ""

        candidates = (
            Book.objects.filter(lang=target_lang)
            .exclude(id=book_id)
            .prefetch_related("authors")
        )

        ids = []
        for candidate in candidates:
            if (candidate.title or "").lower().strip() != (
                book.title or ""
            ).lower().strip():
                continue
            cand_authors = set(
                candidate.authors.values_list("search_full_name", flat=True)
            )
            if cand_authors == target_authors:
                ids.append(candidate.id)

        if not ids:
            return Book.objects.none()
        return Book.objects.filter(id__in=ids)

    @staticmethod
    def find_first_double_ids(book_ids: list[int]) -> dict[int, int]:
        """Для каждого id книги возвращает id её первого дубля (если есть).

        Оптимизация: загружает книги из ``book_ids`` плюс их потенциальных
        дублей (по ``title`` и ``lang``) одним запросом с ``prefetch_related``.

        :param book_ids: Список идентификаторов книг.
        :returns: ``{book_id: first_double_id}`` — только для книг, у которых
                  есть хотя бы один дубль.
        """
        if not book_ids:
            return {}

        target_books = list(
            Book.objects.filter(id__in=book_ids).prefetch_related("authors")
        )
        if not target_books:
            return {}

        # Загружаем потенциальных дублей по title (iexact) и lang за один запрос.
        from django.db.models import Q

        query = Q()
        for book in target_books:
            query |= Q(title__iexact=book.title or "", lang=book.lang or "")

        candidates = list(
            Book.objects.filter(query)
            .exclude(id__in=book_ids)
            .prefetch_related("authors")
        )

        candidates_by_key: dict[tuple[str, str], list[Book]] = {}
        for cand in candidates:
            key = ((cand.title or "").lower().strip(), cand.lang or "")
            candidates_by_key.setdefault(key, []).append(cand)

        result: dict[int, int] = {}
        for book in target_books:
            target_authors = set(
                book.authors.values_list("search_full_name", flat=True)
            )
            key = ((book.title or "").lower().strip(), book.lang or "")
            for cand in candidates_by_key.get(key, []):
                cand_authors = set(
                    cand.authors.values_list("search_full_name", flat=True)
                )
                if cand_authors == target_authors:
                    result[book.id] = cand.id
                    break

        return result

    @staticmethod
    def find_all_duplicates() -> dict[int, QuerySet[Book]]:
        """Находит все группы дублей в системе.

        :returns: Словарь ``{book_id: QuerySet дублей этой книги}``.
                  В результат попадают только книги, у которых есть хотя бы
                  один дубль.
        """
        result: dict[int, QuerySet[Book]] = {}

        # Группируем книги по сигнатуре.
        groups: dict[str, list[Book]] = {}
        for book in Book.objects.all().prefetch_related("authors"):
            sig = DuplicatesService._make_signature(book)
            groups.setdefault(sig, []).append(book)

        # Для каждой группы с более чем одной книгой заполняем результат.
        for sig, books in groups.items():
            if len(books) < 2:
                continue
            for book in books:
                doubles_ids = [b.id for b in books if b.id != book.id]
                if doubles_ids:
                    result[book.id] = Book.objects.filter(id__in=doubles_ids)

        return result
