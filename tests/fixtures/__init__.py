"""Фикстуры для тестов.

Пакет реэкспортирует все фикстуры из модулей:

- fixture_real_book
- fixture_opds_models
- fixture_settings
- fixture_django
- fixture_opds_feeds
- fixture_book_tools
"""

from .fixture_book_tools import (
    epub_parser,
    fb2_params,
    invalid_epub,
    test_tag,
    virtual_fb2_book,
)
from .fixture_django import (
    create_regular_book,
    django_user,
    load_db_data,
    unexisted_book,
)
from .fixture_opds_feeds import opds_1_2
from .fixture_opds_models import (
    catalog,
    multiple_authors,
    parametrized_author,
    parametrized_author_with_books,
)
from .fixture_real_book import (
    book_from_fs,
    epub_book,
    fb2_book_from_fs,
    get_file_content,
    mobi_book,
    simple_fb2,
    zipped_fb2,
    zipped_fb2_book_from_fs,
)
from .fixture_settings import fake_sopds_root_lib, test_rootlib

# Новые фикстуры для моделей
from .model_fixtures import (
    author,
    book,
    book_with_relations,
    bookshelf_entry,
    catalog,
    genre,
    series,
    test_datetime,
    update_counters,
    user,
)
