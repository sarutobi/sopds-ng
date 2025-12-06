from lxml import etree
import datetime

# from book_tools.format.fb2 import Namespace
# from pytest_factoryboy import register
from dataclasses import dataclass

import factory
import factory.fuzzy
from faker import Faker


faker = Faker()


@dataclass
class Author(object):
    """Объект Автор для включения в состав книги

    Атрибуты:
        first_name: Имя автора
        middle_name: Среднее имя (отчество)
        last_name: Фамилия автора
    """

    def __init__(
        self,
        first_name: str | None = None,
        middle_name: str | None = None,
        last_name: str = "",
    ):
        self.first_name = first_name
        self.middle_name = middle_name
        self.last_name = last_name


class AuthorFactory(factory.Factory):
    class Meta:
        model = Author

    # first_name = factory.LazyAttribute(lambda x: faker.first_name())
    first_name = factory.LazyAttribute(lambda x: faker.first_name())
    middle_name = factory.LazyAttribute(lambda x: faker.first_name())
    last_name = factory.LazyAttribute(lambda x: faker.last_name())


@dataclass
class Image(object):
    """Информация об обложке книги

    Атрибуты:
        link: ссылка на элемент, в котором хранится обложка
        type: mime-type изображения обложки
        content: Содержимое изображения обложки
    """

    def __init__(
        self,
        link: str | None = None,
        type: str | None = None,
        content: bytes | None = None,
    ):
        self.link = link
        self.type = type
        self.content = content


class ImageFactory(factory.Factory):
    class Meta:
        model = Image

    link = factory.Sequence(lambda n: f"link{n}")
    type = "image/jpeg"
    content = factory.LazyAttribute(lambda x: faker.image(image_format="jpeg"))


@dataclass
class Series(object):
    """Информация о книжной серии, в которую входит книга.

    Атрибуты:
        name: Наименование серии
        no: Порядковый номер книги в серии
    """

    def __init__(self, name: str, no: str):
        self.name = name
        self.no = no


class SeriesFactory(factory.Factory):
    class Meta:
        model = Series

    name = faker.sentence(nb_words=3)
    no = faker.numerify("%")


class EBookData(object):
    """Обобщенная информация об электронной книге для генерации кнг для тестов

    Атрибуты:
        genres: Список жанров книги
        authors: Список авторов книги
        title: Наименование книги
        annotation: Описание книги
        # TODO: уточнить правильное назначение поля
        docdate: Дата создания электронной версии книги
        image: Информация об обложке книги
        lang: Язык книги
        series: Информация о серии, в которую входит книга
    """

    def __init__(
        self,
        genres: list[str],
        authors: list[Author],
        title: str,
        annotation: str,
        docdate: datetime.date,
        image: Image,
        lang: str,
        series: Series,
    ):
        self.genres = genres
        self.authors = authors
        self.title = title
        self.annotation = annotation
        self.docdate = docdate
        self.image: Image = None
        self.lang = lang
        self.series = series

    def as_fb2(self, namespace: str | None = None) -> bytes:
        if namespace is not None:
            nsmap = {"fb": namespace}
        else:
            nsmap = None
        root = etree.Element("FictionBook", nsmap=nsmap)
        description = etree.SubElement(root, "description", nsmap=nsmap)
        title_info = etree.SubElement(description, "title-info", nsmap=nsmap)
        document_info = etree.SubElement(description, "document-info", nsmap=nsmap)

        if self.genres:
            for g in self.genres:
                ge = etree.SubElement(
                    title_info,
                    "genre",
                    nsmap=nsmap,
                )
                ge.text = g
        if self.authors:
            for a in self.authors:
                ae = etree.SubElement(title_info, "author", nsmap=nsmap)
                fn = etree.SubElement(ae, "first-name", nsmap=nsmap)
                fn.text = a.first_name
                mn = etree.SubElement(ae, "middle-name", nsmap=nsmap)
                mn.text = a.middle_name
                ln = etree.SubElement(ae, "last-name", nsmap=nsmap)
                ln.text = a.last_name

        title = etree.SubElement(title_info, "book-title", nsmap=nsmap)
        title.text = self.title
        if self.annotation is not None:
            annotation = etree.SubElement(title_info, "annotation", nsmap=nsmap)
            annotation.text = self.annotation

        lang = etree.SubElement(title_info, "lang", nsmap=nsmap)
        lang.text = self.lang

        if self.docdate is not None:
            strdate = self.docdate.strftime("%Y-%m-%d")
            docdate = etree.SubElement(
                document_info,
                "date",
                value=strdate,
                nsmap=nsmap,
            )
            docdate.text = strdate
        if self.series is not None:
            etree.SubElement(
                title_info,
                "sequence",
                name=self.series.name,
                number=str(self.series.no),
                nsmap=nsmap,
            )
        return etree.tostring(root, xml_declaration=True)


class EBookDataFactory(factory.Factory):
    class Meta:
        model = EBookData

    class Params:
        a1 = factory.SubFactory(AuthorFactory)
        a2 = factory.SubFactory(AuthorFactory)

    genres = [f"genre{n}" for n in range(1, 3)]
    # Solution from https://github.com/pytest-dev/pytest-factoryboy/issues/61
    authors = factory.LazyAttribute(lambda o: [o.a1, o.a2])
    title = faker.sentence(nb_words=3)
    annotation = factory.Faker("text")
    docdate = factory.fuzzy.FuzzyDate(datetime.date(2008, 1, 1))
    image = factory.SubFactory(ImageFactory)
    lang = factory.LazyAttribute(lambda n: "ru")
    series = factory.SubFactory(SeriesFactory)


class FB2_Builder(object):
    """Генерация книг в формате FB2 для тестов"""

    def __init__(self):
        self.book_data = EBookDataFactory()


def fb2_book_fabric(namespace: str | None = None, **kwargs) -> bytes:
    book: EBookData = EBookDataFactory.build()
    if "title" in kwargs.keys():
        book.title = kwargs["title"]
    if "docdate" in kwargs.keys():
        book.docdate = kwargs["docdate"]
    if "authors" in kwargs.keys():
        book.authors = kwargs["authors"]
    return book.as_fb2(namespace)


#     namespace: str | None = Namespace.FICTION_BOOK20,
#     title="Generated Book",
#     authors=[
#         Author("Pytest", last_name="Genius"),
#     ],
#     genres=["genre1", "genre2"],
#     lang="en",
#     docdate="01.01.1970",
#     series_name="test",
#     series_no=0,
#     annotation="<p>Somedescription</p>",
#     correct=True,
# ) -> bytes:
#     book = FictionBook()
#     book.title = title
#     book.authors = authors
#     book.genres = genres
#     book.lang = lang
#     book.docdate = docdate
#     book.annotation = annotation
#     book.series_name = series_name
#     book.series_no = series_no
#     data = book.build(namespace)
#     if not correct:
#         data = data.replace(b"genre>", b"genre", 1)
#     return data
