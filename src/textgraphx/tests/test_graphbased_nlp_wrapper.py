"""Compatibility tests for the moved GraphBasedNLP ingestion module."""

import importlib
import sys
import types
from types import SimpleNamespace


def _install_graphbased_nlp_stubs(monkeypatch):
    spacy_module = types.ModuleType("spacy")
    spacy_module.__path__ = []
    spacy_module.prefer_gpu = lambda: None
    spacy_module.load = lambda *args, **kwargs: SimpleNamespace(
        config=SimpleNamespace(to_str=lambda: ""),
    )
    monkeypatch.setitem(sys.modules, "spacy", spacy_module)

    spacy_tokens_module = types.ModuleType("spacy.tokens")

    class _FakeDoc:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    class _FakeToken:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    class _FakeSpan:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    spacy_tokens_module.Doc = _FakeDoc
    spacy_tokens_module.Token = _FakeToken
    spacy_tokens_module.Span = _FakeSpan
    monkeypatch.setitem(sys.modules, "spacy.tokens", spacy_tokens_module)

    spacy_lang_module = types.ModuleType("spacy.lang")
    spacy_lang_module.__path__ = []
    monkeypatch.setitem(sys.modules, "spacy.lang", spacy_lang_module)

    spacy_char_classes_module = types.ModuleType("spacy.lang.char_classes")
    spacy_char_classes_module.ALPHA = ""
    spacy_char_classes_module.ALPHA_LOWER = ""
    spacy_char_classes_module.ALPHA_UPPER = ""
    spacy_char_classes_module.CONCAT_QUOTES = []
    spacy_char_classes_module.LIST_ELLIPSES = []
    spacy_char_classes_module.LIST_ICONS = []
    monkeypatch.setitem(sys.modules, "spacy.lang.char_classes", spacy_char_classes_module)

    spacy_util_module = types.ModuleType("spacy.util")
    spacy_util_module.compile_infix_regex = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "spacy.util", spacy_util_module)

    neo4j_module = types.ModuleType("neo4j")
    neo4j_module.GraphDatabase = object
    monkeypatch.setitem(sys.modules, "neo4j", neo4j_module)

    semantic_role_labeler_module = types.ModuleType("textgraphx.util.SemanticRoleLabeler")
    semantic_role_labeler_module.SemanticRoleLabel = object
    monkeypatch.setitem(sys.modules, "textgraphx.util.SemanticRoleLabeler", semantic_role_labeler_module)

    entity_fishing_linker_module = types.ModuleType("textgraphx.util.EntityFishingLinker")
    entity_fishing_linker_module.EntityFishing = object
    monkeypatch.setitem(sys.modules, "textgraphx.util.EntityFishingLinker", entity_fishing_linker_module)

    rest_caller_module = types.ModuleType("textgraphx.util.RestCaller")
    rest_caller_module.callAllenNlpApi = lambda *args, **kwargs: {}
    monkeypatch.setitem(sys.modules, "textgraphx.util.RestCaller", rest_caller_module)

    graph_db_base_module = types.ModuleType("textgraphx.util.GraphDbBase")

    class _FakeGraphDBBase:
        pass

    graph_db_base_module.GraphDBBase = _FakeGraphDBBase
    monkeypatch.setitem(sys.modules, "textgraphx.util.GraphDbBase", graph_db_base_module)

    text_processor_module = types.ModuleType("textgraphx.pipeline.ingestion.text_processor")
    text_processor_module.TextProcessor = object
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.ingestion.text_processor", text_processor_module)

    document_importer_module = types.ModuleType("textgraphx.text_processing_components.DocumentImporter")
    document_importer_module.MeantimeXMLImporter = object
    document_importer_module.resolve_document_id_from_naf_root = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "textgraphx.text_processing_components.DocumentImporter", document_importer_module)

    text_normalization_module = types.ModuleType("textgraphx.text_normalization")
    text_normalization_module.normalize_naf_raw_text = lambda text: text
    monkeypatch.setitem(sys.modules, "textgraphx.text_normalization", text_normalization_module)

    config_module = types.ModuleType("textgraphx.config")
    config_module.get_config = lambda: SimpleNamespace(runtime=SimpleNamespace(naf_sentence_mode="split"))
    monkeypatch.setitem(sys.modules, "textgraphx.config", config_module)


def test_graphbased_nlp_module_aliases_canonical_module(monkeypatch):
    _install_graphbased_nlp_stubs(monkeypatch)

    sys.modules.pop("textgraphx.pipeline.ingestion.graph_based_nlp", None)
    sys.modules.pop("textgraphx.pipeline.ingestion.graph_based_nlp", None)

    canonical_module = importlib.import_module("textgraphx.pipeline.ingestion.graph_based_nlp")
    legacy_module = importlib.import_module("textgraphx.pipeline.ingestion.graph_based_nlp")

    assert legacy_module is canonical_module
    assert legacy_module.GraphBasedNLP is canonical_module.GraphBasedNLP
