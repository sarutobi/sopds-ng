"""Фикстуры для книг, размещенных в файловой системе."""

from typing import Callable

import os
from io import BytesIO
import zipfile

import pytest


@pytest.fixture(scope="session")
def simple_fb2() -> str:
    """Имя файла обычной FB2 книги.

    :scope: session
    :returns: строка с именем файла
    :rtype: str
    """
    return "262001.fb2"


@pytest.fixture(scope="session")
def zipped_fb2() -> str:
    """Имя файла FB2 книги, сжатой ZIP.

    :scope: session
    :returns: строка с именем файла
    :rtype: str
    """
    return "262001.zip"


@pytest.fixture(scope="session")
def bad_fb2() -> str:
    """Имя файла с некорректной книгой в формате FB2.

    :scope: session
    :returns: строка с именем файла
    :rtype: str
    """
    return "badfile.fb2"


@pytest.fixture(scope="session")
def epub_book() -> str:
    """Имя файла книги в формате epub.

    :scope: session
    :returns: строка с именем файла
    :rtype: str
    """
    return "mirer.epub"


@pytest.fixture(scope="session")
def mobi_book() -> str:
    """Имя книги в формате .mobi.

    :scope: session
    :returns: строка с именем файла
    :rtype: str
    """
    return "robin_cook.mobi"


@pytest.fixture(scope="session")
def obsolete_fb2_zip() -> str:
    """Имя файла ZIP архива, кодировка имен файлов в котором отличается от UTF-8.

    :scope: session
    :returns: строка с именем файла
    :rtype: str
    """
    return "wrong_encoded.zip"


@pytest.fixture(scope="session")
def get_file_content(test_rootlib) -> Callable:
    """Возвращает функцию, считывающую файл из файловой системы.

    Функция принимает имя файла и возвращает ``BytesIO`` с его содержимым.
    Является замыканием над ``test_rootlib``.

    :scope: session
    :returns: функция для чтения файлов
    :rtype: Callable[[str], BytesIO]
    """

    def read_file(filename: str) -> BytesIO:
        fname = os.path.join(test_rootlib, filename)
        with open(fname, "rb") as f:
            content = BytesIO(f.read())

        content.seek(0)
        return content

    return read_file


@pytest.fixture
def fb2_book_from_fs(get_file_content, simple_fb2) -> BytesIO:
    """Книга в формате fb2 из файловой системы.

    Возвращает ``BytesIO`` с содержимым ``simple_fb2``, прочитанным из файловой системы.

    :scope: function
    :returns: BytesIO с содержимым книги
    :rtype: BytesIO
    """
    return get_file_content(simple_fb2)


@pytest.fixture
def zipped_fb2_book_from_fs(fb2_book_from_fs) -> BytesIO:
    """Сжатая zip книга FB2.

    Создаёт ZIP-архив в памяти, содержащий книгу из ``fb2_book_from_fs`` под именем
    ``book.txt``. Позволяет тестировать работу с упакованной книгой.

    :scope: function
    :returns: BytesIO с ZIP-архивом
    :rtype: BytesIO
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("book.txt", fb2_book_from_fs.getvalue())
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture(scope="session")
def book_from_fs(get_file_content, request) -> BytesIO:
    """Обобщенная фикстура для предоставления запрошенной книги из ФС.

    **Параметризуемая** фикстура. Принимает имя фикстуры (например, ``'simple_fb2'``,
    ``'zipped_fb2'``) через ``indirect`` в ``@pytest.mark.parametrize``. Возвращает
    ``BytesIO`` с содержимым запрошенного файла.

    Использование в тесте::

        @pytest.mark.parametrize('book_from_fs', ['simple_fb2', 'zipped_fb2', ...], indirect=True)
        def test_something(book_from_fs):
            ...

    :scope: session
    :param request: объект запроса pytest
    :type request: FixtureRequest
    :returns: BytesIO с содержимым книги
    :rtype: BytesIO
    """
    return get_file_content(request.getfixturevalue(request.param))
