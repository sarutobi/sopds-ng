import gc
import os

import pytest

from book_tools.pymobi.mobi import BookMobi


def get_open_fds():
    return len(os.listdir("/proc/self/fd"))


def test_mobi_file_descriptor_leak(tmp_path):
    # Palm DB header: 78 bytes.
    # numberOfRecords (offset 76) = 1
    header = bytearray(78)
    header[76] = 0
    header[77] = 1  # 1 record

    # Record info: 8 bytes for the first record
    # Offset 0: offset (4 bytes), value (4 bytes)
    # Let's say the record is at offset 78.
    record_info = bytearray(8)
    record_info[0] = 0
    record_info[1] = 0
    record_info[2] = 0
    record_info[3] = 78

    # The actual record at offset 78: needs to be long enough for loadRecord(0)
    record_data = bytearray(100)

    full_content = header + record_info + record_data

    mobi_file = tmp_path / "leak_test.mobi"
    mobi_file.write_bytes(full_content)

    fds_before = get_open_fds()

    # The leak happens in __init__ when a path is passed
    mobi = BookMobi(str(mobi_file))

    # Ensure the object is deleted and GC runs to trigger __del__
    del mobi
    gc.collect()

    fds_after = get_open_fds()

    assert fds_after == fds_before, (
        f"File descriptor leak detected: before={fds_before}, after={fds_after}"
    )
