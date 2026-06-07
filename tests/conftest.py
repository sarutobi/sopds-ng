"""Общие настройки для всего проекта."""

import pytest
import io
import zipfile

from django.contrib.auth.models import User

from .fixtures import *  # noqa: F403


@pytest.fixture(scope="session")
def fb2_with_cover():
    """FB2 файл с обложкой.

    Создаёт объект ``BytesIO`` с корректным FB2-файлом, содержащим обложку (binary-изображение).
    Используется для тестов, проверяющих извлечение обложек.

    :scope: session
    :returns: BytesIO с FB2-контентом
    :rtype: io.BytesIO
    """
    fb2_content = """<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:xlink="http://www.w3.org/1999/xlink">
<description>
    <title-info>
        <book-title>Test Book</book-title>
        <author>
            <first-name>Test</first-name>
            <last-name>Author</last-name>
        </author>
        <coverpage>
          <image xlink:href="#cover.jpg"/>
        </coverpage>
    </title-info>
</description>
<body>
</body>
<binary id="cover.jpg" content-type="image/jpeg">/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwC1AAD/2Q==</binary>
</FictionBook>"""
    return io.BytesIO(fb2_content.encode("utf-8"))


@pytest.fixture
def fb2_without_cover():
    """FB2 файл без обложки.

    Создаёт ``BytesIO`` с FB2-файлом без обложки. Подходит для тестов, в которых обложка
    не требуется или должна отсутствовать.

    :scope: function
    :returns: BytesIO с FB2-контентом без обложки
    :rtype: io.BytesIO
    """
    fb2_content = """<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
<description>
    <title-info>
        <book-title>Test Book No Cover</book-title>
        <author>
            <first-name>Test</first-name>
            <last-name>Author</last-name>
        </author>
    </title-info>
</description>
<body>
    <p>Some content without cover.</p>
</body>
</FictionBook>"""
    return io.BytesIO(fb2_content.encode("utf-8"))


@pytest.fixture
def invalid_fb2():
    """Некорректный FB2 файл (не XML).

    Возвращает ``BytesIO`` с данными, не являющимися корректным XML.
    Используется для проверки обработки повреждённых/некорректных FB2-файлов.

    :scope: function
    :returns: BytesIO с невалидным содержимым
    :rtype: io.BytesIO
    """
    return io.BytesIO(b"Not an FB2 file")


@pytest.fixture(scope="session")
def zipped_fb2_with_cover(fb2_with_cover):
    """ZIP архив, содержащий FB2 файл с обложкой.

    ZIP-архив, содержащий один файл ``book.fb2`` (с обложкой). Полезен при тестировании
    распаковки архивов.

    :scope: session
    :returns: BytesIO с ZIP-архивом
    :rtype: io.BytesIO
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("book.fb2", fb2_with_cover.getvalue())
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def not_a_zip_file():
    """Данные, которые is_zipfile() не распознает как ZIP архив.

    Данные с корректным заголовком ZIP, но недостаточной длиной для того чтобы
    ``is_zipfile()`` вернул ``True``.

    :scope: function
    :returns: BytesIO с данными, не являющимися ZIP
    :rtype: io.BytesIO
    """
    # Данные с корректным заголовком ZIP, но недостаточной длиной
    # для того чтобы is_zipfile() вернул True
    return io.BytesIO(b"PK\x03\x04\x14\x00\x00\x00\x00\x00invalid data")


@pytest.fixture
def corrupted_zip_valid_header():
    """ZIP архив с корректным заголовком, но поврежденной структурой.

    ZIP-архив с корректным локальным заголовком, но повреждённым центральным каталогом.
    Выбрасывает ``zipfile.BadZipFile`` при попытке открытия.

    :scope: function
    :returns: BytesIO с повреждённым ZIP-архивом
    :rtype: io.BytesIO
    """
    # Создаем валидный ZIP архив с одним файлом
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("test.txt", b"valid content")

    # Повреждаем архив: изменяем сигнатуру центрального заголовка директории,
    # чтобы вызвать BadZipFile при открытии
    data = zip_buffer.getvalue()
    # Находим позицию центрального заголовка директории (PK\x01\x02)
    pos = data.find(b"PK\x01\x02")
    if pos != -1:
        # Изменяем сигнатуру на неверную (PK\x01\x03)
        data_list = list(data)
        data_list[pos + 3] = 0x03  # Изменяем последний байт сигнатуры
        data = bytes(data_list)

    return io.BytesIO(data)


@pytest.fixture
def zip_with_multiple_files():
    """ZIP архив с несколькими файлами.

    ZIP-архив с несколькими файлами (``file1.txt``, ``file2.txt``). Подходит для тестов,
    где важен порядок или количество файлов.

    :scope: function
    :returns: BytesIO с ZIP-архивом
    :rtype: io.BytesIO
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("file1.txt", b"content1")
        zf.writestr("file2.txt", b"content2")
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def empty_zip():
    """Пустой ZIP архив (без файлов).

    ZIP-архив без добавленных файлов. Используется для проверки поведения
    на пустых архивах.

    :scope: function
    :returns: BytesIO с пустым ZIP-архивом
    :rtype: io.BytesIO
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Не добавляем файлы
        pass
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def zip_with_corrupted_file_content():
    """ZIP архив с поврежденным содержимым файла.

    ZIP-архив, в котором содержимое одного из файлов повреждено (изменены первые байты).
    При чтении такого файла данные будут искажены — фикстура полезна для тестов устойчивости.

    :scope: function
    :returns: BytesIO с ZIP-архивом
    :rtype: io.BytesIO
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("corrupted.txt", b"valid content")

    # Повреждаем содержимое файла внутри архива
    data = zip_buffer.getvalue()
    # Находим позицию данных файла (после локального заголовка)
    # Локальный заголовок имеет фиксированную длину 30 байт + длина имени файла
    # Имя файла 'corrupted.txt' (11 байт)
    local_header_end = data.find(b"corrupted.txt") + 11 + 30
    if local_header_end != -1:
        # Изменяем первые байты данных файла
        data_list = list(data)
        data_list[local_header_end] = 0xFF
        data_list[local_header_end + 1] = 0xFF
        data = bytes(data_list)

    return io.BytesIO(data)


@pytest.fixture
def zip_with_non_fb2():
    """ZIP архив, содержащий не FB2 файл.

    ZIP-архив, содержащий файл ``book.txt`` (не FB2). Позволяет тестировать логику,
    когда архив есть, но внутри не книга.

    :scope: function
    :returns: BytesIO с ZIP-архивом
    :rtype: io.BytesIO
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("book.txt", b"This is not an FB2 file")
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def user():
    """Тестовый пользователь.

    Создаёт тестового пользователя Django с логином ``testuser`` и паролем ``testpass123``.
    Используется там, где требуется аутентифицированный пользователь.

    :scope: function
    :returns: User
    :rtype: django.contrib.auth.models.User
    """
    return User.objects.create_user(username="testuser", password="testpass123")
