"""
Извлечение метаданных из OPF файла EPUB.
"""

import zipfile
from typing import Any

from lxml import etree

from book_tools.format.epub.constants import Namespace
from book_tools.format.util import normalize_string


class EPubMetadataParser:
    def __init__(self, epub: Any) -> None:
        self.epub = epub

    def parse(
        self, tree: etree._Element, root_info: zipfile.ZipInfo
    ) -> dict[str, str | list[str] | dict[str, str | None]]:
        namespaces = {"opf": Namespace.OPF, "dc": Namespace.DUBLIN_CORE}

        metadata: dict[str, str | list[str] | dict[str, str | None]] = {}

        # Title
        res = tree.xpath("/opf:package/opf:metadata/dc:title", namespaces=namespaces)
        if res:
            metadata["title"] = res[0].text

        # Date
        res = tree.xpath(
            '/opf:package/opf:metadata/dc:date[@event="modification"]',
            namespaces=namespaces,
        )
        if not res:
            res = tree.xpath("/opf:package/opf:metadata/dc:date", namespaces=namespaces)
        if res:
            metadata["docdate"] = res[0].text

        # Authors
        res = tree.xpath(
            '/opf:package/opf:metadata/dc:creator[@role="aut"]', namespaces=namespaces
        )
        if not res:
            res = tree.xpath(
                "/opf:package/opf:metadata/dc:creator", namespaces=namespaces
            )
        metadata["authors"] = [node.text for node in res]

        # Language
        res = tree.xpath("/opf:package/opf:metadata/dc:language", namespaces=namespaces)
        if res and res[0].text:
            metadata["language_code"] = res[0].text.strip()

        # Tags
        res = tree.xpath("/opf:package/opf:metadata/dc:subject", namespaces=namespaces)
        metadata["tags"] = [node.text for node in res]

        # Series
        res = tree.xpath(
            '/opf:package/opf:metadata/opf:meta[@name="calibre:series"]',
            namespaces=namespaces,
        )
        if res:
            series = normalize_string(res[0].get("content"))
            if series:
                res_index = tree.xpath(
                    '/opf:package/opf:metadata/opf:meta[@name="calibre:series_index"]',
                    namespaces=namespaces,
                )
                index = (
                    normalize_string(res_index[0].get("content")) if res_index else None
                )
                metadata["series_info"] = {"title": series, "index": index}

        # Description
        res = tree.xpath(
            "/opf:package/opf:metadata/dc:description", namespaces=namespaces
        )
        if res and res[0].text:
            metadata["description"] = res[0].text.strip()

        return metadata
