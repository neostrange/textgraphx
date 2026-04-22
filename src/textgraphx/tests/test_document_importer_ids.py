from xml.etree import ElementTree as ET

from textgraphx.text_processing_components.DocumentImporter import resolve_document_id_from_naf_root


def test_resolve_document_id_from_naf_root_prefers_numeric_public_id():
    root = ET.fromstring(
        """<NAF>
        <nafHeader>
          <public publicId="76437" uri="http://example.test/doc" />
        </nafHeader>
        </NAF>"""
    )

    assert resolve_document_id_from_naf_root(root, 1) == 76437


def test_resolve_document_id_from_naf_root_falls_back_when_public_id_missing():
    root = ET.fromstring("<NAF><nafHeader /></NAF>")

    assert resolve_document_id_from_naf_root(root, 9) == 9


def test_resolve_document_id_from_naf_root_falls_back_when_public_id_non_numeric():
    root = ET.fromstring(
        """<NAF>
        <nafHeader>
          <public publicId="doc-A12" uri="http://example.test/doc" />
        </nafHeader>
        </NAF>"""
    )

    assert resolve_document_id_from_naf_root(root, 11) == 11