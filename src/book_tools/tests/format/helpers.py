from book_tools.format.bookfile import BookFile


def book_file_are_equals(book1: BookFile, book2: BookFile) -> bool:
    """Проверка идентичности полей в разных сущностях BookFile"""
    if book1 is None or book2 is None:
        return False

    return (
        book1.file == book2.file
        and book1.mimetype == book2.mimetype
        and book1.original_filename == book2.original_filename
        and book1.title == book2.title
        and book1.description == book2.description
        and book1.authors == book2.authors
        and book1.tags == book2.tags
        and book1.series_info == book2.series_info
        and book1.language_code == book2.language_code
        and book1.issues == book2.issues
        and book1.docdate == book2.docdate
    )
