import types
from _typeshed import Incomplete
from book_tools.format.aes import encrypt as encrypt
from book_tools.format.bookfile import BookFile as BookFile
from book_tools.format.mimetype import Mimetype as Mimetype
from book_tools.format.util import list_zip_file_infos as list_zip_file_infos

class EPub(BookFile):
    class Issue:
        FIRST_ITEM_NOT_MIMETYPE: int
        MIMETYPE_ITEM_IS_DEFLATED: int
    class Namespace:
        XHTML: str
        CONTAINER: str
        OPF: str
        DUBLIN_CORE: str
        ENCRYPTION: str
        DIGITAL_SIGNATURE: str
        MARLIN: str
        CALIBRE: str
    class Entry:
        MIMETYPE: str
        MANIFEST: str
        METADATA: str
        CONTAINER: str
        ENCRYPTION: str
        RIGHTS: str
        SIGNATURES: str
    TOKEN_URL: str
    CONTENT_ID_PREFIX: str
    ALGORITHM_EMBEDDING: str
    ALGORITHM_AES128: Incomplete
    class StructureException(Exception):
        def __init__(self, message) -> None: ...
    root_filename: Incomplete
    cover_fileinfos: Incomplete
    def __init__(self, file, original_filename) -> None: ...
    def close(self) -> None: ...
    def __exit__(self, kind: type[BaseException] | None, value: BaseException | None, traceback: types.TracebackType | None) -> None: ...
    def get_encryption_info(self): ...
    def encrypt(self, key, content_id, working_dir, files_to_keep=None) -> None: ...
    def repair(self, working_dir) -> None: ...
    def extract_cover_internal(self, working_dir): ...
    def extract_cover_memory(self): ...

class EPub_new:
    class Issue:
        FIRST_ITEM_NOT_MIMETYPE: int
        MIMETYPE_ITEM_IS_DEFLATED: int
    class Namespace:
        XHTML: str
        CONTAINER: str
        OPF: str
        DUBLIN_CORE: str
        ENCRYPTION: str
        DIGITAL_SIGNATURE: str
        MARLIN: str
        CALIBRE: str
    class Entry:
        MIMETYPE: str
        MANIFEST: str
        METADATA: str
        CONTAINER: str
        ENCRYPTION: str
        RIGHTS: str
        SIGNATURES: str
    TOKEN_URL: str
    CONTENT_ID_PREFIX: str
    ALGORITHM_EMBEDDING: str
    ALGORITHM_AES128: Incomplete
    class StructureException(Exception):
        def __init__(self, message) -> None: ...
    file: Incomplete
    root_filename: Incomplete
    cover_fileinfos: Incomplete
    def __init__(self, file, original_filename) -> None: ...
    def parse_book_data(self, file, original_filename: str) -> BookFile: ...
    def close(self) -> None: ...
    def __exit__(self, kind: type[BaseException] | None, value: BaseException | None, traceback: types.TracebackType | None) -> None: ...
    def get_encryption_info(self): ...
    def encrypt(self, key, content_id, working_dir, files_to_keep=None) -> None: ...
    def repair(self, working_dir) -> None: ...
    def extract_cover_internal(self, working_dir): ...
    def extract_cover_memory(self): ...
