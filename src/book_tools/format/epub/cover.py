"""
Логика поиска обложки в EPUB.
"""

import os
import urllib.parse

from lxml import etree

from book_tools.format.epub.constants import Namespace


class EPubCoverFinder:
    def __init__(self, epub):
        self.epub = epub

    def find_cover(self, tree, prefix):
        namespaces = {"opf": Namespace.OPF, "dc": Namespace.DUBLIN_CORE}

        def xpath(query):
            res = tree.xpath(query, namespaces=namespaces)
            if not res:
                raise Exception("Not found")
            return res[0]

        def item_for_href(ref):
            return xpath('/opf:package/opf:manifest/opf:item[@href="%s"]' % ref)

        def image_infos(node):
            path = os.path.normpath(prefix + node.get("href")).replace("\\", "/")
            try:
                fileinfo = self.epub._zip_file.getinfo(path)
            except Exception:
                fileinfo = self.epub._zip_file.getinfo(urllib.parse.unquote(path))

            mime = node.get("media-type")
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
                img = img_nodes[0]
                return [
                    info,
                    {
                        "filename": os.path.normpath(xhtml_prefix + img.get("src")),
                        "mime": "image/auto",
                    },
                ]
            else:
                raise Exception("unknown mimetype %s" % mime)

        search_strategies = [
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
                )
            ),
            # 6. Guide reference (general type)
            lambda: image_infos(
                item_for_href(
                    xpath(
                        '/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"]'
                    ).get("href")
                )
            ),
            # 7. Manifest ID "cover"
            lambda: image_infos(
                xpath('/opf:package/opf:manifest/opf:item[@id="cover"]')
            ),
        ]

        for strategy in search_strategies:
            try:
                return strategy()
            except Exception:
                continue

        return []
