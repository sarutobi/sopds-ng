"""
Анализ шифрования EPUB.
"""

from typing import Any

from lxml import etree

from book_tools.format.epub.constants import Entry, Namespace


class EPubEncryptionHandler:
    def __init__(self, epub: Any) -> None:
        self.epub = epub

    def get_encryption_info(self) -> dict[str, str | list[str] | None]:
        UNKNOWN_ENCRYPTION: dict[str, str | list[str] | None] = {"method": "unknown"}
        algo: str | None = None

        if self._contains_entry(Entry.ENCRYPTION):
            try:
                tree = self.epub._etree_from_entry(Entry.ENCRYPTION)
                namespaces = {
                    "c": Namespace.CONTAINER,
                    "e": Namespace.ENCRYPTION,
                }
                res = tree.xpath(
                    "/c:encryption/e:EncryptedData/e:EncryptionMethod",
                    namespaces=namespaces,
                )
                algorithms = list(
                    set([r.get("Algorithm") for r in res if r.get("Algorithm")])
                )
                if len(algorithms) != 1:
                    return {"method": "multi", "ids": algorithms}
                if algorithms[0] == self.epub.ALGORITHM_EMBEDDING:
                    return {"method": "embedding"}
                elif algorithms[0] == self.epub.ALGORITHM_AES128:
                    algo = algorithms[0]
                else:
                    return UNKNOWN_ENCRYPTION
            except Exception:
                return UNKNOWN_ENCRYPTION

        if self._contains_entry(Entry.RIGHTS):
            if algo == self.epub.ALGORITHM_AES128:
                try:
                    tree = self.epub._etree_from_entry(Entry.RIGHTS)
                    namespaces = {"m": Namespace.MARLIN}
                    res = tree.xpath(
                        "/m:Marlin/m:RightsURL/m:RightsIssuer/m:URL",
                        namespaces=namespaces,
                    )
                    if res:
                        token_url = res[0].text
                        content_ids = (
                            self._extract_content_ids()
                            if token_url == self.epub.TOKEN_URL
                            else []
                        )
                        return {
                            "method": "marlin",
                            "token_url": token_url,
                            "content_ids": content_ids,
                        }
                except Exception:
                    pass
            return UNKNOWN_ENCRYPTION

        if self._contains_entry(Entry.SIGNATURES):
            return UNKNOWN_ENCRYPTION

        return {}

    def _contains_entry(self, name: str) -> bool:
        try:
            self.epub._zip_file.getinfo(name)
            return True
        except KeyError:
            return False

    def _extract_content_ids(self) -> list[str]:
        content_ids: set[str] = set()
        try:
            tree = self.epub._etree_from_entry(Entry.ENCRYPTION)
            ns = {
                "c": Namespace.CONTAINER,
                "e": Namespace.ENCRYPTION,
                "d": Namespace.DIGITAL_SIGNATURE,
            }
            res = tree.xpath(
                "/c:encryption/e:EncryptedData/d:KeyInfo/d:KeyName", namespaces=ns
            )
            for node in res:
                key_name = node.text
                if key_name and key_name.startswith(self.epub.CONTENT_ID_PREFIX):
                    content_ids.add(key_name[len(self.epub.CONTENT_ID_PREFIX) :])
        except Exception:
            pass
        return list(content_ids)
