"""
Логика поиска обложки в EPUB.
"""

import os
import urllib.parse
from typing import Any

from lxml import etree

from book_tools.format.epub.constants import Namespace


class EPubCoverFinder:
    def __init__(self, epub: Any) -> None:
        self.epub = epub

    def find_cover(self, tree: etree._Element, prefix: str) -> list[dict[str, str]]:
        namespaces = {"opf": Namespace.OPF, "dc": Namespace.DUBLIN_CORE}

        def xpath(query: str) -> etree._Element:
            res = tree.xpath(query, namespaces=namespaces)
            if not res:
                raise Exception("Not found")
            return res[0]  # type: ignore

        def item_for_href(ref: str) -> etree._Element:
            return xpath('/opf:package/opf:manifest/opf:item[@href="%s"]' % ref)

        def image_infos(node: etree._Element) -> list[dict[str, str]]:
            path = os.path.normpath(prefix + (node.get("href") or "")).replace(
                "\\", "/"
            )
            try:
                fileinfo = self.epub._zip_file.getinfo(path)
            except Exception:
                fileinfo = self.epub._zip_file.getinfo(urllib.parse.unquote(path))

            mime = node.get("media-type") or ""
            info = {"filename": fileinfo.filename, "mime": mime}

            if mime.startswith("image/"):
                return [info]
            elif mime == "application/xhtml+xml":
                xhtml = self.epub._etree_from_entry(fileinfo)
                xhtml_prefix = os.path.dirname(fileinfo.filename) + "/"
                img_nodes = xhtml.xpath(
                    "//xhtml:img[@src]", namespaces={"xhtml": Namespace.XHTML}
                )
                if not img_nodes:
                    raise Exception("No img tag in XHTML")
                img = img_nodes[0]  # type: ignore
                return [
                    info,
                    {
                        "filename": os.path.normpath(
                            xhtml_prefix + (img.get("src") or "")
                        ),
                        "mime": "image/auto",
                    },
                ]
            else:
                raise Exception("unknown mimetype %s" % mime)

        # Используем Any для обхода проблем с типами lambda в strict моде, если они сложные
        search_strategies: list[Any] = [
            # 1. Manifest cover-image property
            lambda: image_infos(
                xpath('/opf:package/opf:manifest/opf:item[@properties="cover-image"]')
            ),
            # 2. Meta cover (opf:package/opf:metadata/opf:meta[@name="cover"])
            lambda: image_infos(
                xpath(
                    '/opf:package/opf:manifest/opf:item[@id="%s"]'
                    % xpath('/opf:package/opf:metadata/opf:meta[@name="cover"]').get(
                        "content"
                    )
                )
            ),
            # 3. Meta cover (opf:package/opf:metadata/meta[@name="cover"])
            lambda: image_infos(
                xpath(
                    '/opf:package/opf:manifest/opf:item[@id="%s"]'
                    % xpath('/opf:package/opf:metadata/meta[@name="cover"]').get(
                        "content"
                    )
                )
            ),
            # 4. Meta cover (without opf prefix)
            lambda: image_infos(
                xpath(
                    '/package/manifest/item[@id="%s"]'
                    % xpath('/package/metadata/meta[@name="cover"]').get("content")
                )
            ),
            # 5. Guide reference (specific type and title)
            lambda: image_infos(
                item_for_href(
                    xpath(
                        '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"][@title="Cover"]'
                    ).get("href")
                    or ""
                )
            ),
            # 6. Guide reference (general type)
            lambda: image_infos(
                item_for_href(
                    xpath(
                        '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"]'
                    ).get("href")
                    or ""
                )
            ),
            # 7. Manifest ID "cover"
            lambda: image_infos(
                xpath('/opf:package/opf:manifest/opf:item[@id="cover"]')
            ),
        ]

        for strategy in search_strategies:
            try:
                res = strategy()
                return res  # type: ignore
            except Exception:
                continue

        return []
