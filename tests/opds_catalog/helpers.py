"""Helper functions for testing purpose."""

from lxml.etree import _ElementTree
from lxml import etree
from io import BytesIO
import zipfile

# from codecs import open

from opds_catalog import opdsdb
from opds_catalog.models import Book, Catalog


def read_file_as_iobytes(file: str) -> BytesIO:
    """Чтение содержимого файла из файловой системы в BytesIO."""
    with open(file, "rb") as f:
        content = BytesIO(f.read())

    content.seek(0)
    return content


def read_book_from_zip_file(zip_file: str, bookname: str) -> BytesIO:
    """Чтение книги из zip архива."""
    with open(zip_file, "rb") as f:
        with zipfile.ZipFile(f, "r", allowZip64=True) as zf:
            with zf.open(bookname, "r") as book:
                content = BytesIO(book.read())

    content.seek(0)
    return content


class BookFactoryMixin:
    def setup_regular_book(self, filename="", path="") -> Book:
        """Генерирует книгу, размещенную в обычном файле в файловой системе."""
        return self.setup_book(filename=filename, cat_type=opdsdb.CAT_NORMAL, path=path)

    def setup_zipped_book(self, filename="", path="") -> Book:
        """Генерирует книгу, размещенную в zip файле в файловой системе."""
        return self.setup_book(filename=filename, cat_type=opdsdb.CAT_ZIP, path=path)

    def setup_book(self, title="", format="", filename="", cat_type=0, path="") -> Book:
        return Book(
            title=title, format=format, filename=filename, cat_type=cat_type, path=path
        )


def create_catalog(
    cat_name: str = "Test catalog",
    path: str = "test_path",
) -> Catalog:
    catalog = Catalog(cat_name=cat_name, path=path)
    catalog.save()
    return catalog


def create_book(
    filename: str = "test_book",
    path: str = "test_path",
    filesize: int = 0,
    format: str = "fb2",
    catalog: str = "test_catalog",
    cat_type: int = opdsdb.CAT_NORMAL,
    doc_date: str = "2025-01-01 00:00:00",
    lang: str = "ru",
    title: str = "Test Book",
    annotation: str = "Lorem ipsum dolor sit....",
    lang_code: int = 2,
    avail: int = 2,
) -> Book:
    cat = create_catalog(catalog, path)

    book = Book(
        filename=filename,
        path=path,
        filesize=filesize,
        format=format,
        catalog=cat,
        cat_type=cat_type,
        docdate=doc_date,
        lang=lang,
        title=title,
        search_title=title.upper(),
        annotation=annotation,
        lang_code=lang_code,
        avail=avail,
    )
    book.save()
    return book


def opds_requirement_links(feed: _ElementTree) -> bool:
    """Каждая запись entry должна содержать ссылки."""
    for entry in feed.findall("{*}entry"):
        if len(entry.findall("{*}link")) == 0:
            print(etree.tostring(entry))
            return False
    return True


def opds_acquisition_links(feed: _ElementTree) -> bool:
    """Каждая acquisition ссылка должна иметь тип."""
    for link in feed.findall("{*}entry/{*}link"):
        rel = link.attrib["rel"] if "rel" in link.attrib.keys() else None
        ltype = link.attrib["type"] if "type" in link.attrib.keys() else None
        if (rel is not None and "opds-spec.org/acquisition" in rel) and (
            ltype is None or "/" not in ltype
        ):
            print(etree.tostring(link))
            return False
    return True


def opds_search_rel(feed: _ElementTree) -> bool:
    """Каждая поисковая ссылка должна иметь opensearch mimetype."""
    for link in feed.findall("{*}entry/{*}link"):
        rel = link.attrib["rel"] if "rel" in link.attrib.keys() else None
        ltype = link.attrib["type"] if "type" in link.attrib.keys() else None
        if (rel is not None and "search" in rel) and (
            ltype is None or "application/opensearchdescription+xml" not in ltype
        ):
            return False
    return True


def opds_acquisition_or_navigation_feed(feed: _ElementTree) -> bool:
    """Фид не может быть одновременно навигационным и потребительским."""
    navigation_links = 0
    acquisition_links = 0

    for link in feed.findall("{*}entry/{*}link"):
        rel = link.attrib["rel"] if "rel" in link.attrib.keys() else None
        if rel is not None and "opds-spec.org/acquisition" in rel:
            acquisition_links += 1
        else:
            navigation_links += 1

    if acquisition_links > 0 and navigation_links > 0:
        return False
    return True


def opds_summary_is_plain_text(feed: _ElementTree) -> bool:
    """Тэг summary может содержать только текст, без разметки."""
    for summary in feed.findall(".//{*}summary"):
        if len(summary.getchildren()) > 0:
            return False
    return True


def opds_image_rel(feed: _ElementTree) -> bool:
    """Ссылка на изображения не должна иметь устарешие типы."""
    for link in feed.findall(".//{*}link"):
        rel = link.attrib["rel"] if "rel" in link.attrib.keys() else None
        if rel is not None and (
            "http://opds-spec.org/cover" in rel or "x-stanza-cover-image" in rel
        ):
            print(etree.tostring(link))
            return False

    return True


def opds_image_bitmap(feed: _ElementTree) -> bool:
    """Каждая ссылка на изображение должна иметь корректный тип bitmap."""
    for link in feed.findall(".//{*}link"):
        rel = link.attrib["rel"] if "rel" in link.attrib.keys() else None
        ltype = link.attrib["type"] if "type" in link.attrib.keys() else None
        if (rel is not None and "http://opds-spec.org/image" in rel) and (
            ltype is None
            or ltype
            not in ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/bmp"]
        ):
            print(etree.tostring(link))
            return False
    return True


def opds_dc_namespace(feed: _ElementTree) -> bool:
    """Элементы пространства имен Dublin Core должны дублироваться элементами пространства имен Atom."""
    for entry in feed.findall("{*}entry"):
        dc_title = entry.find("{dcterm}title")
        if dc_title is not None:
            return False
        dc_creator = entry.find("{dcterm}creator")
        if dc_creator is not None:
            return False
        dc_subject = entry.find("{dcterm}subject")
        if dc_subject is not None:
            return False
    return True


def opds_content_duplication(feed: _ElementTree) -> bool:
    """Элементы title, summary и content не должны содержать одинаковые значения."""
    for entry in feed.findall("{*}entry"):
        title = entry.find(".//{*}title")
        summary = entry.find("{*}summary")
        content = entry.find("{*}content")

        if content is not None:
            text = content.text
            if summary is not None and summary.text == text:
                print(etree.tostring(entry))
                return False
            if title is not None and title.text == text:
                print(etree.tostring(entry))
                return False
    return True


def opds_root_link(feed: _ElementTree) -> bool:
    """В каталоге должна быть только одна ссылка на стартовый фид."""
    return len(feed.findall('{*}link[@rel="start"]')) == 1


def opds_link_profile_kind(feed: _ElementTree) -> bool:
    """Ссылки каталога должны включать профиль и вид."""
    for link in feed.findall(".//{*}link"):
        rel = link.attrib["rel"] if "rel" in link.attrib.keys() else None
        ltype = link.attrib["type"] if "type" in link.attrib.keys() else None
        if ltype is not None and "application/atom+xml" in ltype:
            if "profile=opds-catalog" not in ltype:
                return False
            if "kind=" not in ltype and "type=entry" not in ltype:
                return False

    return True
