from book_tools.format.bookfile import BookFile


class Dummy(BookFile):
    def __init__(self, file, original_filename, mimetype):
        BookFile.__init__(self, file, original_filename, mimetype)

    def __exit__(self, kind, value, traceback):
        pass


class Dummy_new(object):
    def __init__(self, file, original_filename, mimetype):
        pass

    def parse_book_data(self, file, original_filename, mimetype) -> BookFile:
        return BookFile(file, original_filename, mimetype)

    def __exit__(self, kind, value, traceback):
        pass
