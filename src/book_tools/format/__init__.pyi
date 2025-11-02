from book_tools.format.epub import EPub as EPub
from book_tools.format.fb2 import FB2 as FB2, FB2Zip as FB2Zip
from book_tools.format.fb2sax import FB2sax as FB2sax
from book_tools.format.mimetype import Mimetype as Mimetype
from book_tools.format.mobi import Mobipocket as Mobipocket
from book_tools.format.other import Dummy as Dummy
from book_tools.format.util import list_zip_file_infos as list_zip_file_infos

class mime_detector:
    @staticmethod
    def fmt(fmt): ...
    @staticmethod
    def file(filename): ...

def detect_mime(file, original_filename): ...
def create_bookfile(file, original_filename): ...
