from io import BytesIO
from unittest.mock import MagicMock

import pytest

from book_tools.format.mobi import Mobipocket


def test_mobipocket_init_none_date():
    # Mocking BookMobi and the file object
    mock_file = BytesIO(b"fake mobi content")

    # We need to patch BookMobi because it's used inside Mobipocket.__init__
    # Since we can't easily patch the import in this simple test without mock.patch,
    # we will use a trick: replace the class in the module if necessary or mock the instance.
    # But the cleanest way is to use mock.patch.

    from unittest.mock import patch

    with patch("book_tools.format.mobi.BookMobi") as MockBookMobi:
        mock_bm = MagicMock()
        # Simulate modificationDate = None
        mock_bm.__getitem__.side_effect = lambda key: {
            "encryption": "no encryption",
            "title": "Test Title",
            "author": "Test Author",
            "modificationDate": None,
            "subject": [],
            "description": "Test Description",
        }.get(key)
        MockBookMobi.return_value = mock_bm

        # This should not raise AttributeError: 'NoneType' object has no attribute 'strftime'
        book = Mobipocket(mock_file, "test.mobi")
        # If the date is None, docdate should be set to a default (like empty string)
        # Depending on how _set_docdate is implemented in BookFile.
        # We just check that it doesn't crash.


def test_mobipocket_init_invalid_date():
    mock_file = BytesIO(b"fake mobi content")
    from unittest.mock import patch

    with patch("book_tools.format.mobi.BookMobi") as MockBookMobi:
        mock_bm = MagicMock()
        # Simulate modificationDate being something that crashes strftime or isn't a datetime object
        mock_bm.__getitem__.side_effect = lambda key: {
            "encryption": "no encryption",
            "title": "Test Title",
            "author": "Test Author",
            "modificationDate": "not-a-datetime-object",
            "subject": [],
            "description": "Test Description",
        }.get(key)
        MockBookMobi.return_value = mock_bm

        # This should not raise AttributeError: 'str' object has no attribute 'strftime'
        book = Mobipocket(mock_file, "test.mobi")


def test_mobipocket_parse_book_data_none_date():
    mock_file = BytesIO(b"fake mobi content")
    from unittest.mock import patch

    with patch("book_tools.format.mobi.BookMobi") as MockBookMobi:
        mock_bm = MagicMock()
        mock_bm.__getitem__.side_effect = lambda key: {
            "encryption": "no encryption",
            "title": "Test Title",
            "author": "Test Author",
            "modificationDate": None,
            "subject": [],
            "description": "Test Description",
        }.get(key)
        MockBookMobi.return_value = mock_bm

        # Should not crash
        Mobipocket.parse_book_data(mock_file, "test.mobi")
