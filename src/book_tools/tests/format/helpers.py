from lxml import etree
from book_tools.format.fb2 import Namespace


class FictionBook(object):
    """Генератор описания книги в формате fb2"""

    class _Image(object):
        def __init__(
            self,
            link: str | None = None,
            type: str | None = None,
            content: bytes | None = None,
        ):
            self.link = link
            self.type = type
            self.content = content

    class _Author(object):
        def __init__(
            self,
            first_name: str | None = None,
            middle_name: str | None = None,
            last_name: str = "",
        ):
            self.first_name = first_name
            self.middle_name = middle_name
            self.last_name = last_name

    def __init__(self):
        self._nsname: str = "fb"
        self.genres: list[str] = []
        self.authors: list[FictionBook._Author] = []
        self.title: str = None
        self.annotation: str = None
        self.docdate: str = None
        self.image: FictionBook._Image = None
        self.lang: str = None

    def add_author(
        self, fname: str | None = None, mname: str | None = None, lname: str = ""
    ) -> None:
        self.authors.append(FictionBook._Author(fname, mname, lname))

    def build(self, namespace: str | None = None) -> bytes:
        if namespace is not None:
            nsmap = {self._nsname: namespace}
        else:
            nsmap = None
        root = etree.Element("FictionBook", nsmap=nsmap)
        description = etree.SubElement(root, "description", nsmap=nsmap)
        title_info = etree.SubElement(description, "title-info", nsmap=nsmap)
        document_info = etree.SubElement(description, "document-info", nsmap=nsmap)

        for g in self.genres:
            ge = etree.SubElement(
                title_info,
                "genre",
                nsmap=nsmap,
            )
            ge.text = g

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
            docdate = etree.SubElement(
                document_info, "date", value=self.docdate, nsmap=nsmap
            )
            docdate.text = self.docdate

        return etree.tostring(root, xml_declaration=True)


def fb2_book_fabric(
    namespace: str | None = Namespace.FICTION_BOOK20,
    title="Generated Book",
    authors=[
        FictionBook._Author("Pytest", last_name="Genius"),
    ],
    genres=["genre1", "genre2"],
    lang="en",
    docdate="01.01.1970",
    series_name=None,
    series_no=None,
    annotation="<p>Somedescription</p>",
) -> bytes:
    book = FictionBook()
    book.title = title
    book.authors = authors
    book.genres = genres
    book.lang = lang
    book.docdate = docdate
    return book.build(namespace)
