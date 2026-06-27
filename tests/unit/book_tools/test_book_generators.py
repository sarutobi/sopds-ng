import io

from book_tools.format.fb2 import FB2
from tests.book_tools.format.helpers import Author, fb2_book_fabric


def test_generate_book() -> None:
    """Проверка, что фабрика возвращает корректную структуру FB2 по умолчанию."""
    result = fb2_book_fabric()
    assert result is not None
    assert b"FictionBook" in result
    assert b"<description>" in result
    assert b"<title-info>" in result


def test_book_title() -> None:
    """Проверка, что заголовок книги корректно вставляется в XML."""
    result = fb2_book_fabric(title="Test Book", authors=None)
    assert b"<book-title>" in result
    assert b"Test Book" in result


def test_book_author() -> None:
    """Проверка, что один автор корректно вставляется в XML."""
    result = fb2_book_fabric(title=None, authors=[Author("First", "Middle", "Second")])
    assert b"<author>" in result
    assert b"First" in result
    assert b"Middle" in result
    assert b"Second" in result


def test_book_authors_empty_list() -> None:
    """Проверка, что пустой список авторов не приводит к ошибке."""
    result = fb2_book_fabric(title="No Authors", authors=[])
    assert b"<title-info>" in result
    assert b"<author>" not in result


def test_book_authors_multiple() -> None:
    """Проверка, что несколько авторов корректно вставляются."""
    authors = [
        Author("Ivan", "Petrov", "Sidorov"),
        Author("John", "Doe", ""),
    ]
    result = fb2_book_fabric(title="Multiple", authors=authors)
    assert b"Ivan" in result
    assert b"Petrov" in result
    assert b"Sidorov" in result
    assert b"John" in result
    assert b"Doe" in result
    # Убедимся, что оба автора присутствуют
    assert result.count(b"<author>") == 2


def test_book_author_long_strings() -> None:
    """Проверка, что длинные строки (first‑name, last‑name) обрабатываются без ошибок."""
    long_first = "А" * 500
    long_middle = "Б" * 500
    long_last = "В" * 500
    result = fb2_book_fabric(
        title=None, authors=[Author(long_first, long_middle, long_last)]
    )
    assert long_first.encode("utf-8") in result
    assert long_middle.encode("utf-8") in result
    assert long_last.encode("utf-8") in result


def test_book_author_special_chars() -> None:
    """Проверка, что спецсимволы (кавычки, амперсанд, угловые скобки) экранируются."""
    special_first = 'He said "Hello" & <bye>'
    special_last = "O'Brien"
    result = fb2_book_fabric(
        title=None, authors=[Author(special_first, "", special_last)]
    )
    # В XML эти символы должны быть экранированы
    assert b"&amp;" in result  # амперсанд
    assert b"&lt;" in result  # <
    assert b"&gt;" in result  # >
    # Простые кавычки не требуют экранирования в XML
    assert b"O'Brien" in result


def test_book_namespace_default() -> None:
    """Проверка, что по умолчанию используется пространство имён FictionBook 2.0."""
    result = fb2_book_fabric(title="Default NS")
    assert b'xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"' in result


def test_book_namespace_custom() -> None:
    """Проверка, что можно указать другое пространство имён."""
    custom_ns = "http://example.com/ns"
    result = fb2_book_fabric(title="Custom NS", namespace=custom_ns)
    assert custom_ns.encode("utf-8") in result


def test_book_fabric_returns_bytes() -> None:
    """Проверка, что фабрика возвращает байтовый объект (непустой)."""
    book = fb2_book_fabric(title="Any Book")
    assert isinstance(book, bytes)
    assert len(book) > 0


def test_book_fabric_parsed_correctly() -> None:
    """Проверка, что сгенерированная книга корректно парсится классом FB2."""
    book = fb2_book_fabric(title="Generated Book")
    result = FB2(io.BytesIO(book), "test")
    assert result is not None

    assert result.title == "Generated Book"
