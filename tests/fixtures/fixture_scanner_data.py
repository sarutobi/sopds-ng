"""Фикстуры для данных сканера.

Этот модуль предоставляет инструменты для генерации граничных случаев данных,
которые используются для проверки расхождений между путями записи (INPX и raw_scan).
"""

import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import pytest

from tests.book_tools.format.helpers import Author, fb2_book_fabric


@dataclass
class InpRecord:
    """Запись в формате INP.

    Атрибуты:
        author (list[str]): Список авторов
        genre (list[str]): Список жанров
        title (str): Заголовок
        series (list[str]): Список серий
        serno (list[str]): Номера серий (соответствуют списку series)
        file (str): Имя файла книги
        size (str): Размер файла
        libid (str): ID в библиотеке
        del_flag (str): Флаг удаления ('0' - нет, '1' - да)
        ext (str): Расширение файла
        date (str): Дата
        lang (str): Язык
    """

    author: list[str] = field(default_factory=lambda: ["Author"])
    genre: list[str] = field(default_factory=lambda: ["Genre"])
    title: str = "Test Book"
    series: list[str] = field(default_factory=list)
    serno: list[str] = field(default_factory=list)
    file: str = "book"
    size: str = "1024"
    libid: str = "1"
    del_flag: str = "0"
    ext: str = "fb2"
    date: str = "2023-01-01"
    lang: str = "ru"

    def to_inp_line(self) -> bytes:
        """Сериализует запись в строку формата INP.

        Разделитель полей: \\x04
        Разделитель элементов списка: :
        """
        # Формат по умолчанию из inpx_parser.py:
        # [AUTHOR, GENRE, TITLE, SERIES, SERNO, FILE, SIZE, LIBID, DEL, EXT, DATE, LANG]
        fields = [
            ":".join(self.author),
            ":".join(self.genre),
            self.title,
            ":".join(self.series),
            ":".join(self.serno),
            self.file,
            self.size,
            self.libid,
            self.del_flag,
            self.ext,
            self.date,
            self.lang,
        ]
        return "\x04".join(fields).encode("utf-8") + b"\n"


def make_inpx(records: list[InpRecord], filename: str = "collection.inpx") -> bytes:
    """Создаёт ZIP-архив формата INPX из списка записей.

    :param records: Список записей InpRecord
    :param filename: Имя итогового файла
    :returns: Байты ZIP-архива
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # По умолчанию используем один .inp файл
        inp_content = b"".join(r.to_inp_line() for r in records)
        zf.writestr("books.inp", inp_content)
        # structure.info не создаём, чтобы проверить default format
    return buf.getvalue()


@pytest.fixture
def scanner_boundary_cases():
    """Набор граничных случаев для тестирования путей записи.

    Каждый кейс содержит:
    - 'id': ID из таблицы расхождений §3.1 (R-1...R-15)
    - 'inpx': InpRecord
    - 'fb2': Параметры для build_fb2_book (передаются в fabric)
    - 'desc': Описание кейса
    """
    return [
        {
            "id": "R-1",
            "desc": "Автор с запятой в имени",
            "inpx": InpRecord(author=["Иванов, Иван"]),
            "fb2": {"authors": [Author(last_name="Иванов, Иван")]},
        },
        {
            "id": "R-2",
            "desc": "Автор без запятой (только фамилия)",
            "inpx": InpRecord(author=["Пушкин"]),
            "fb2": {"authors": [Author(last_name="Пушкин")]},
        },
        {
            "id": "R-3",
            "desc": "Пустой автор",
            "inpx": InpRecord(author=[]),
            "fb2": {"authors": []},
        },
        {
            "id": "R-4",
            "desc": "Автор с sortkey, отличным от фамилии",
            "inpx": InpRecord(author=["фон Бисмарк"]),
            "fb2": {"authors": [Author(last_name="Бисмарк", first_name="фон")]},
        },
        {
            "id": "R-5",
            "desc": "Несколько авторов в книге",
            "inpx": InpRecord(author=["Автор 1", "Автор 2"]),
            "fb2": {
                "authors": [Author(last_name="Автор 1"), Author(last_name="Автор 2")]
            },
        },
        {
            "id": "R-6",
            "desc": "Книга с аннотацией",
            "inpx": InpRecord(title="С аннотацией"),
            "fb2": {"title": "С аннотацией", "annotation": "Очень важная аннотация"},
        },
        {
            "id": "R-7",
            "desc": "Разные языки",
            "inpx": InpRecord(lang="en"),
            "fb2": {"lang": "en"},
        },
        {
            "id": "R-8",
            "desc": "Несколько жанров",
            "inpx": InpRecord(genre=["Фантастика", "Детектив"]),
            "fb2": {"genres": ["Фантастика", "Детектив"]},
        },
        {
            "id": "R-9",
            "desc": "Расширение в верхнем регистре",
            "inpx": InpRecord(ext="FB2"),
            "fb2": {},  # FB2 fabric всегда создаёт fb2, проверка на уровне расширения файла
        },
        {
            "id": "R-10",
            "desc": "Разный cat_type",
            "inpx": InpRecord(file="book_raw"),
            "fb2": {},
        },
        {
            "id": "R-11",
            "desc": "Спецсимволы в именах (strip_symbols)",
            "inpx": InpRecord(author=["Автор_!@#"]),
            "fb2": {"authors": [Author(last_name="Автор_!@#")]},
        },
        {
            "id": "R-12",
            "desc": "Несколько серий с разными номерами",
            "inpx": InpRecord(series=["Серия 1", "Серия 2"], serno=["1", "5"]),
            "fb2": {
                "series_name": "Серия 1",
                "series_no": 1,
            },  # Текущий fb2_book_fabric поддерживает одну серию
        },
        {
            "id": "R-13",
            "desc": "Ошибки источника (битый файл)",
            "inpx": InpRecord(title="Bad Book"),
            "fb2": "CORRUPT",
        },
        {
            "id": "R-14",
            "desc": "Пропуск записи (DEL=1)",
            "inpx": InpRecord(del_flag="1"),
            "fb2": {},
        },
        {
            "id": "R-15",
            "desc": "Имя автора > 128 символов (усечение)",
            "inpx": InpRecord(author=["А" * 130]),
            "fb2": {"authors": [Author(last_name="А" * 130)]},
        },
    ]
