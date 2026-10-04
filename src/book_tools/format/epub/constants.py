"""
Константы для формата EPUB.
"""


class Issue:
    FIRST_ITEM_NOT_MIMETYPE = 1
    MIMETYPE_ITEM_IS_DEFLATED = 2


class Namespace:
    XHTML = "http://www.w3.org/1999/xhtml"
    CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
    OPF = "http://www.idpf.org/2007/opf"
    DUBLIN_CORE = "http://purl.org/dc/elements/1.1/"
    ENCRYPTION = "http://www.w3.org/2001/04/xmlenc#"
    DIGITAL_SIGNATURE = "http://www.w3.org/2000/09/xmldsig#"
    MARLIN = "http://marlin-drm.com/epub"
    CALIBRE = "http://calibre.kovidgoyal.net/2009/metadata"


class Entry:
    MIMETYPE = "mimetype"
    MANIFEST = "META-INF/manifest.xml"
    METADATA = "META-INF/metadata.xml"
    CONTAINER = "META-INF/container.xml"
    ENCRYPTION = "META-INF/encryption.xml"
    RIGHTS = "META-INF/rights.xml"
    SIGNATURES = "META-INF/signatures.xml"
