import abc
import types
from _typeshed import Incomplete
from abc import ABCMeta, abstractmethod
from book_tools.format.util import minify_cover as minify_cover

class BookFile(metaclass=abc.ABCMeta):
    __metaclass__ = ABCMeta
    file: Incomplete
    mimetype: Incomplete
    original_filename: Incomplete
    title: Incomplete
    description: Incomplete
    authors: Incomplete
    tags: Incomplete
    series_info: Incomplete
    language_code: Incomplete
    issues: Incomplete
    docdate: str
    def __init__(self, file, original_filename, mimetype) -> None: ...
    def __enter__(self): ...
    @abstractmethod
    def __exit__(self, kind: type[BaseException] | None, value: BaseException | None, traceback: types.TracebackType | None): ...
    def extract_cover(self, working_dir): ...
    def extract_cover_internal(self, working_dir): ...
    def extract_cover_memory(self) -> None: ...
    def __set_title__(self, title) -> None: ...
    def __set_docdate__(self, docdate) -> None: ...
    def __add_author__(self, name, sortkey=None) -> None: ...
    def __add_tag__(self, text) -> None: ...
    @staticmethod
    def __normalise_string__(text): ...
    def get_encryption_info(self): ...
    def repair(self, working_dir) -> None: ...
    def __eq__(self, other) -> bool: ...

class BookMetaInfo:
    authors: Incomplete
    genres: Incomplete
    title: str
    description: str
    series: str
    series_index: int
    cover_file_type: str
    cover_image: bytes
    mimetype: Incomplete
    tags: Incomplete
    language_code: str
    docdate: str
    def __init__(self, mimetype: str) -> None: ...
