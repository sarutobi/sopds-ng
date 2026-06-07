"""Фикстуры для тестов.

Пакет реэкспортирует все фикстуры из модулей:

- fixture_real_book
- fixture_opds_models
- fixture_settings
- fixture_django
- fixture_opds_feeds
- fixture_book_tools
"""

from .fixture_real_book import (
    simple_fb2,
    zipped_fb2,
    epub_book,
    mobi_book,
    get_file_content,
    fb2_book_from_fs,
    zipped_fb2_book_from_fs,
    book_from_fs,
)
from .fixture_opds_models import (
    catalog,
    parametrized_author,
    parametrized_author_with_books,
    multiple_authors,
)
from .fixture_settings import test_rootlib, fake_sopds_root_lib
from .fixture_django import (
    django_user,
    load_db_data,
    unexisted_book,
    create_regular_book,
)
from .fixture_opds_feeds import opds_1_2
from .fixture_book_tools import (
    epub_parser,
    invalid_epub,
    test_tag,
    virtual_fb2_book,
    fb2_params,
)
