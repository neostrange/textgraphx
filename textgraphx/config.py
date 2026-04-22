"""Central configuration loader for textgraphx.

run command temporary: /home/neo/environments/textgraphx/.venv/bin/python /home/neo/environments/textgraphx/textgraphx/run_pipeline.py

Supports INI and optional TOML configs and environment variable overrides.

Usage:
    from textgraphx.config import load_config, get_config
    cfg = load_config()  # searches for repo/user config and env vars
    neo = cfg.neo4j
"""
from __future__ import annotations
import os
import configparser
from dataclasses import dataclass
from typing import Optional


@dataclass
class Neo4jConfig:
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: Optional[str] = None


@dataclass
class LoggingConfig:
    level: str = "INFO"
    json: bool = False
    file: Optional[str] = None


@dataclass
class SpaCyConfig:
    model: str = "en_core_web_trf"
    use_gpu: bool = False


@dataclass
class PathsConfig:
    data_dir: str = "data"
    output_dir: str = "out"
    tmp_dir: str = "/tmp"


@dataclass
class ServicesConfig:
    service_timeout_sec: int = 20
    wsd_url: str = "http://localhost:81/api/model"
    coref_url: str = "http://localhost:9999/coreference_resolution"
    temporal_url: str = "http://localhost:5050/annotate"
    heideltime_url: str = "http://localhost:5000/annotate"
    srl_url: str = "http://localhost:8000/predict"
    llm_url: str = "http://localhost:11434/api/generate"
    dbpedia_sparql_url: str = "https://dbpedia.org/sparql"
    dbpedia_spotlight_url: str = "https://api.dbpedia-spotlight.org/en/annotate"
    dbpedia_timeout_sec: int = 8
    dbpedia_max_entities_per_run: int = 500
    dbpedia_spotlight_confidence: float = 0.5
    dbpedia_spotlight_support: int = 20
    dbpedia_spotlight_min_similarity: float = 0.8


@dataclass
class RuntimeConfig:
    mode: str = "production"
    strict_transition_gate: Optional[bool] = None
    naf_sentence_mode: str = "auto"
    tlink_shadow_mode: bool = False
    enable_tlink_xml_seed: bool = False
    enable_cross_document_fusion: bool = False


@dataclass
class FeatureFlags:
    create_refinement_run: bool = True
    compute_token_ids: bool = False
    enable_dbpedia_enrichment: bool = False
    # When False (default) the transitional :NUMERIC/:VALUE label-writing passes
    # are skipped. Enable only when running legacy pipelines that still rely on
    # the dynamic label reads.
    fill_numeric_labels: bool = False


@dataclass
class Config:
    neo4j: Neo4jConfig
    logging: LoggingConfig
    spacy: SpaCyConfig
    paths: PathsConfig
    features: FeatureFlags
    runtime: RuntimeConfig
    services: ServicesConfig = None

    def __post_init__(self):
        if self.services is None:
            self.services = ServicesConfig()


_CACHED: Optional[Config] = None


def _read_ini(path: str) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    cp.read(path)
    return cp


def _read_toml(path: str) -> dict:
    # try tomllib (py3.11+) or toml package
    try:
        import tomllib as _t
        with open(path, 'rb') as f:
            return _t.load(f)
    except Exception:
        try:
            import toml as _t
            return _t.load(path)
        except Exception:
            return {}


def _coerce_bool(val: Optional[str]) -> bool:
    if val is None:
        return False
    v = str(val).lower()
    return v in ("1", "true", "yes", "on")


def _coerce_optional_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    v = str(val).strip().lower()
    if v in ("", "auto", "default"):
        return None
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    raise ValueError(
        "runtime.strict_transition_gate must be one of: "
        "auto/default/true/false/1/0/yes/no/on/off"
    )


def _coerce_naf_sentence_mode(val: Optional[str]) -> str:
    mode = ("auto" if val is None else str(val)).strip().lower()
    allowed = {"auto", "preserve", "meantime", "legacy"}
    if mode not in allowed:
        raise ValueError(
            "runtime.naf_sentence_mode must be one of: auto/preserve/meantime/legacy"
        )
    return mode


def load_config(path: Optional[str] = None, allow_env: bool = True) -> Config:
    """Load configuration using precedence:
      1. explicit path
      2. env TEXTGRAPHX_CONFIG
      3. package config.ini at textgraphx/config.ini
      4. user config at ~/.textgraphx/config.ini
      5. defaults

    Environment variables override file values when allow_env is True.
    """
    global _CACHED
    if _CACHED is not None and path is None:
        return _CACHED

    # discover config file
    candidates = []
    if path:
        candidates.append(path)
    env_path = os.getenv('TEXTGRAPHX_CONFIG')
    if env_path:
        candidates.append(env_path)
    # repo-local
    repo_cfg = os.path.join(os.path.dirname(__file__), 'config.ini')
    candidates.append(repo_cfg)
    # user
    home_cfg = os.path.join(os.path.expanduser('~'), '.textgraphx', 'config.ini')
    candidates.append(home_cfg)

    file_cfg = None
    for p in candidates:
        try:
            if p and os.path.exists(p):
                file_cfg = p
                break
        except Exception:
            continue

    # start with defaults
    neo = Neo4jConfig()
    log = LoggingConfig()
    spacy = SpaCyConfig()
    paths = PathsConfig()
    features = FeatureFlags()
    runtime = RuntimeConfig()
    services = ServicesConfig()

    if file_cfg:
        ext = os.path.splitext(file_cfg)[1].lower()
        if ext in ('.ini', ''):
            cp = _read_ini(file_cfg)
            if cp.has_section('neo4j'):
                neo.uri = cp.get('neo4j', 'uri', fallback=neo.uri)
                neo.user = cp.get('neo4j', 'user', fallback=neo.user)
                neo.password = cp.get('neo4j', 'password', fallback=neo.password)
                neo.database = cp.get('neo4j', 'database', fallback=neo.database)
            if cp.has_section('logging'):
                log.level = cp.get('logging', 'level', fallback=log.level)
                log.json = _coerce_bool(cp.get('logging', 'json', fallback=str(log.json)))
                log.file = cp.get('logging', 'file', fallback=log.file)
            if cp.has_section('spacy'):
                spacy.model = cp.get('spacy', 'model', fallback=spacy.model)
                spacy.use_gpu = _coerce_bool(cp.get('spacy', 'use_gpu', fallback=str(spacy.use_gpu)))
            if cp.has_section('paths'):
                paths.data_dir = cp.get('paths', 'data_dir', fallback=paths.data_dir)
                paths.output_dir = cp.get('paths', 'output_dir', fallback=paths.output_dir)
                paths.tmp_dir = cp.get('paths', 'tmp_dir', fallback=paths.tmp_dir)
            if cp.has_section('features'):
                features.create_refinement_run = _coerce_bool(cp.get('features', 'create_refinement_run', fallback=str(features.create_refinement_run)))
                features.compute_token_ids = _coerce_bool(cp.get('features', 'compute_token_ids', fallback=str(features.compute_token_ids)))
                features.enable_dbpedia_enrichment = _coerce_bool(
                    cp.get('features', 'enable_dbpedia_enrichment', fallback=str(features.enable_dbpedia_enrichment))
                )
                features.fill_numeric_labels = _coerce_bool(
                    cp.get('features', 'fill_numeric_labels', fallback=str(features.fill_numeric_labels))
                )
            if cp.has_section('runtime'):
                runtime.mode = cp.get('runtime', 'mode', fallback=runtime.mode).strip().lower()
                runtime.strict_transition_gate = _coerce_optional_bool(
                    cp.get('runtime', 'strict_transition_gate', fallback=None)
                )
                runtime.naf_sentence_mode = _coerce_naf_sentence_mode(
                    cp.get('runtime', 'naf_sentence_mode', fallback=runtime.naf_sentence_mode)
                )
                runtime.tlink_shadow_mode = _coerce_bool(
                    cp.get('runtime', 'tlink_shadow_mode', fallback=str(runtime.tlink_shadow_mode))
                )
                runtime.enable_cross_document_fusion = _coerce_bool(
                    cp.get(
                        'runtime',
                        'enable_cross_document_fusion',
                        fallback=str(runtime.enable_cross_document_fusion),
                    )
                )
            if cp.has_section('services'):
                try:
                    services.service_timeout_sec = int(
                        cp.get('services', 'service_timeout_sec', fallback=str(services.service_timeout_sec))
                    )
                except Exception:
                    pass
                services.wsd_url = cp.get('services', 'wsd_url', fallback=services.wsd_url)
                services.coref_url = cp.get('services', 'coref_url', fallback=services.coref_url)
                services.temporal_url = cp.get('services', 'temporal_url', fallback=services.temporal_url)
                services.heideltime_url = cp.get('services', 'heideltime_url', fallback=services.heideltime_url)
                services.srl_url = cp.get('services', 'srl_url', fallback=services.srl_url)
                services.llm_url = cp.get('services', 'llm_url', fallback=services.llm_url)
                services.dbpedia_sparql_url = cp.get('services', 'dbpedia_sparql_url', fallback=services.dbpedia_sparql_url)
                services.dbpedia_spotlight_url = cp.get('services', 'dbpedia_spotlight_url', fallback=services.dbpedia_spotlight_url)
                try:
                    services.dbpedia_timeout_sec = int(
                        cp.get('services', 'dbpedia_timeout_sec', fallback=str(services.dbpedia_timeout_sec))
                    )
                except Exception:
                    pass
                try:
                    services.dbpedia_max_entities_per_run = int(
                        cp.get('services', 'dbpedia_max_entities_per_run', fallback=str(services.dbpedia_max_entities_per_run))
                    )
                except Exception:
                    pass
                try:
                    services.dbpedia_spotlight_support = int(
                        cp.get('services', 'dbpedia_spotlight_support', fallback=str(services.dbpedia_spotlight_support))
                    )
                except Exception:
                    pass
                try:
                    services.dbpedia_spotlight_confidence = float(
                        cp.get(
                            'services',
                            'dbpedia_spotlight_confidence',
                            fallback=str(services.dbpedia_spotlight_confidence),
                        )
                    )
                except Exception:
                    pass
                try:
                    services.dbpedia_spotlight_min_similarity = float(
                        cp.get(
                            'services',
                            'dbpedia_spotlight_min_similarity',
                            fallback=str(services.dbpedia_spotlight_min_similarity),
                        )
                    )
                except Exception:
                    pass
        else:
            tom = _read_toml(file_cfg)
            neo_map = tom.get('neo4j', {})
            neo.uri = neo_map.get('uri', neo.uri)
            neo.user = neo_map.get('user', neo.user)
            neo.password = neo_map.get('password', neo.password)
            neo.database = neo_map.get('database', neo.database)
            log_map = tom.get('logging', {})
            log.level = log_map.get('level', log.level)
            log.json = bool(log_map.get('json', log.json))
            log.file = log_map.get('file', log.file)
            sp_map = tom.get('spacy', {})
            spacy.model = sp_map.get('model', spacy.model)
            spacy.use_gpu = bool(sp_map.get('use_gpu', spacy.use_gpu))
            paths_map = tom.get('paths', {})
            paths.data_dir = paths_map.get('data_dir', paths.data_dir)
            paths.output_dir = paths_map.get('output_dir', paths.output_dir)
            paths.tmp_dir = paths_map.get('tmp_dir', paths.tmp_dir)
            feat_map = tom.get('features', {})
            features.create_refinement_run = bool(feat_map.get('create_refinement_run', features.create_refinement_run))
            features.compute_token_ids = bool(feat_map.get('compute_token_ids', features.compute_token_ids))
            features.enable_dbpedia_enrichment = bool(
                feat_map.get('enable_dbpedia_enrichment', features.enable_dbpedia_enrichment)
            )
            features.fill_numeric_labels = bool(
                feat_map.get('fill_numeric_labels', features.fill_numeric_labels)
            )
            runtime_map = tom.get('runtime', {})
            runtime.mode = str(runtime_map.get('mode', runtime.mode)).strip().lower()
            if 'strict_transition_gate' in runtime_map:
                v = runtime_map.get('strict_transition_gate')
                if v is None:
                    runtime.strict_transition_gate = None
                elif isinstance(v, bool):
                    runtime.strict_transition_gate = v
                else:
                    runtime.strict_transition_gate = _coerce_optional_bool(str(v))
            if 'naf_sentence_mode' in runtime_map:
                runtime.naf_sentence_mode = _coerce_naf_sentence_mode(
                    str(runtime_map.get('naf_sentence_mode'))
                )
            if 'tlink_shadow_mode' in runtime_map:
                runtime.tlink_shadow_mode = bool(runtime_map.get('tlink_shadow_mode', runtime.tlink_shadow_mode))
            if 'enable_cross_document_fusion' in runtime_map:
                runtime.enable_cross_document_fusion = bool(
                    runtime_map.get('enable_cross_document_fusion', runtime.enable_cross_document_fusion)
                )
            svc_map = tom.get('services', {})
            services.service_timeout_sec = int(
                svc_map.get('service_timeout_sec', services.service_timeout_sec)
            )
            services.wsd_url = svc_map.get('wsd_url', services.wsd_url)
            services.coref_url = svc_map.get('coref_url', services.coref_url)
            services.temporal_url = svc_map.get('temporal_url', services.temporal_url)
            services.heideltime_url = svc_map.get('heideltime_url', services.heideltime_url)
            services.srl_url = svc_map.get('srl_url', services.srl_url)
            services.llm_url = svc_map.get('llm_url', services.llm_url)
            services.dbpedia_sparql_url = svc_map.get('dbpedia_sparql_url', services.dbpedia_sparql_url)
            services.dbpedia_spotlight_url = svc_map.get('dbpedia_spotlight_url', services.dbpedia_spotlight_url)
            services.dbpedia_timeout_sec = int(
                svc_map.get('dbpedia_timeout_sec', services.dbpedia_timeout_sec)
            )
            services.dbpedia_max_entities_per_run = int(
                svc_map.get('dbpedia_max_entities_per_run', services.dbpedia_max_entities_per_run)
            )
            services.dbpedia_spotlight_support = int(
                svc_map.get('dbpedia_spotlight_support', services.dbpedia_spotlight_support)
            )
            services.dbpedia_spotlight_confidence = float(
                svc_map.get('dbpedia_spotlight_confidence', services.dbpedia_spotlight_confidence)
            )
            services.dbpedia_spotlight_min_similarity = float(
                svc_map.get('dbpedia_spotlight_min_similarity', services.dbpedia_spotlight_min_similarity)
            )

    # environment overrides
    if allow_env:
        neo.uri = os.getenv('NEO4J_URI') or os.getenv('GRAPHDB_URI') or neo.uri
        neo.user = os.getenv('NEO4J_USER') or os.getenv('NEO4J_USERNAME') or neo.user
        neo.password = os.getenv('NEO4J_PASSWORD') or neo.password
        db = os.getenv('NEO4J_DATABASE')
        if db:
            neo.database = db

        log.level = os.getenv('TEXTGRAPHX_LOG_LEVEL') or log.level
        if os.getenv('TEXTGRAPHX_LOG_JSON') is not None:
            log.json = _coerce_bool(os.getenv('TEXTGRAPHX_LOG_JSON'))
        log.file = os.getenv('TEXTGRAPHX_LOG_FILE') or log.file

        spacy.model = os.getenv('SPACY_MODEL') or spacy.model
        if os.getenv('SPACY_USE_GPU') is not None:
            spacy.use_gpu = _coerce_bool(os.getenv('SPACY_USE_GPU'))

        paths.data_dir = os.getenv('TEXTGRAPHX_DATA_DIR') or paths.data_dir
        paths.output_dir = os.getenv('TEXTGRAPHX_OUTPUT_DIR') or paths.output_dir
        paths.tmp_dir = os.getenv('TEXTGRAPHX_TMP_DIR') or paths.tmp_dir

        if os.getenv('TEXTGRAPHX_CREATE_REFINEMENT_RUN') is not None:
            features.create_refinement_run = _coerce_bool(os.getenv('TEXTGRAPHX_CREATE_REFINEMENT_RUN'))
        if os.getenv('TEXTGRAPHX_COMPUTE_TOKEN_IDS') is not None:
            features.compute_token_ids = _coerce_bool(os.getenv('TEXTGRAPHX_COMPUTE_TOKEN_IDS'))
        if os.getenv('TEXTGRAPHX_ENABLE_DBPEDIA_ENRICHMENT') is not None:
            features.enable_dbpedia_enrichment = _coerce_bool(
                os.getenv('TEXTGRAPHX_ENABLE_DBPEDIA_ENRICHMENT')
            )
        if os.getenv('TEXTGRAPHX_FILL_NUMERIC_LABELS') is not None:
            features.fill_numeric_labels = _coerce_bool(
                os.getenv('TEXTGRAPHX_FILL_NUMERIC_LABELS')
            )

        runtime.mode = (os.getenv('TEXTGRAPHX_RUNTIME_MODE') or runtime.mode).strip().lower()
        env_strict = os.getenv('TEXTGRAPHX_STRICT_TRANSITION_GATE')
        if env_strict is not None:
            runtime.strict_transition_gate = _coerce_optional_bool(env_strict)
        env_naf_mode = os.getenv('TEXTGRAPHX_NAF_SENTENCE_MODE')
        if env_naf_mode is not None:
            runtime.naf_sentence_mode = _coerce_naf_sentence_mode(env_naf_mode)
        env_enable_tlink_xml_seed = os.getenv("TEXTGRAPHX_ENABLE_TLINK_XML_SEED")
        if env_enable_tlink_xml_seed is not None:
            runtime.enable_tlink_xml_seed = _coerce_bool(env_enable_tlink_xml_seed)
        env_tlink_shadow = os.getenv('TEXTGRAPHX_TLINK_SHADOW_MODE')
        if env_tlink_shadow is not None:
            runtime.tlink_shadow_mode = _coerce_bool(env_tlink_shadow)
        env_cross_doc_fusion = os.getenv('TEXTGRAPHX_ENABLE_CROSS_DOCUMENT_FUSION')
        if env_cross_doc_fusion is not None:
            runtime.enable_cross_document_fusion = _coerce_bool(env_cross_doc_fusion)

        # Standardised TEXTGRAPHX_* env vars (preferred); legacy names kept for
        # backward compatibility with existing deployments.
        services.wsd_url = (
            os.getenv('TEXTGRAPHX_WSD_URL')
            or os.getenv('WSD_API_URL')
            or services.wsd_url
        )
        service_timeout = os.getenv('TEXTGRAPHX_SERVICE_TIMEOUT_SEC') or os.getenv('SERVICE_TIMEOUT_SEC')
        if service_timeout is not None:
            try:
                services.service_timeout_sec = int(service_timeout)
            except Exception:
                pass
        services.coref_url = (
            os.getenv('TEXTGRAPHX_COREF_URL')
            or os.getenv('COREF_SERVICE_URL')
            or services.coref_url
        )
        services.temporal_url = (
            os.getenv('TEXTGRAPHX_TEMPORAL_URL')
            or os.getenv('TEMPORAL_SERVICE_URL')
            or services.temporal_url
        )
        services.heideltime_url = (
            os.getenv('TEXTGRAPHX_HEIDELTIME_URL')
            or os.getenv('HEIDELTIME_SERVICE_URL')
            or services.heideltime_url
        )
        services.srl_url = (
            os.getenv('TEXTGRAPHX_SRL_URL')
            or os.getenv('SRL_SERVICE_URL')
            or services.srl_url
        )
        services.llm_url = (
            os.getenv('TEXTGRAPHX_LLM_URL')
            or os.getenv('LLM_API_URL')
            or services.llm_url
        )
        services.dbpedia_sparql_url = os.getenv('DBPEDIA_SPARQL_URL') or services.dbpedia_sparql_url
        services.dbpedia_spotlight_url = os.getenv('DBPEDIA_SPOTLIGHT_URL') or services.dbpedia_spotlight_url

        dbpedia_timeout = os.getenv('DBPEDIA_TIMEOUT_SEC')
        if dbpedia_timeout is not None:
            try:
                services.dbpedia_timeout_sec = int(dbpedia_timeout)
            except Exception:
                pass

        dbpedia_limit = os.getenv('DBPEDIA_MAX_ENTITIES_PER_RUN')
        if dbpedia_limit is not None:
            try:
                services.dbpedia_max_entities_per_run = int(dbpedia_limit)
            except Exception:
                pass

        dbpedia_support = os.getenv('DBPEDIA_SPOTLIGHT_SUPPORT')
        if dbpedia_support is not None:
            try:
                services.dbpedia_spotlight_support = int(dbpedia_support)
            except Exception:
                pass

        dbpedia_confidence = os.getenv('DBPEDIA_SPOTLIGHT_CONFIDENCE')
        if dbpedia_confidence is not None:
            try:
                services.dbpedia_spotlight_confidence = float(dbpedia_confidence)
            except Exception:
                pass

        dbpedia_min_similarity = os.getenv('DBPEDIA_SPOTLIGHT_MIN_SIMILARITY')
        if dbpedia_min_similarity is not None:
            try:
                services.dbpedia_spotlight_min_similarity = float(dbpedia_min_similarity)
            except Exception:
                pass

    if runtime.mode not in {"production", "testing"}:
        raise ValueError("runtime.mode must be either 'production' or 'testing'")
    runtime.naf_sentence_mode = _coerce_naf_sentence_mode(runtime.naf_sentence_mode)

    cfg = Config(
        neo4j=neo,
        logging=log,
        spacy=spacy,
        paths=paths,
        features=features,
        runtime=runtime,
        services=services,
    )
    if path is None:
        _CACHED = cfg
    return cfg


def get_config() -> Config:
    return load_config()


def write_example(path: str, fmt: str = 'toml') -> None:
    fmt = fmt.lower()
    example_ini = """[neo4j]
uri = bolt://localhost:7687
user = neo4j
password = password

[logging]
level = INFO
json = false

[spacy]
model = en_core_web_trf

[paths]
data_dir = data
output_dir = out

[features]
create_refinement_run = true
compute_token_ids = false
enable_dbpedia_enrichment = false
fill_numeric_labels = false

[runtime]
mode = production
strict_transition_gate = auto
naf_sentence_mode = auto
tlink_shadow_mode = false
enable_cross_document_fusion = false

[services]
service_timeout_sec = 20
dbpedia_sparql_url = https://dbpedia.org/sparql
dbpedia_spotlight_url = https://api.dbpedia-spotlight.org/en/annotate
dbpedia_timeout_sec = 8
dbpedia_max_entities_per_run = 500
dbpedia_spotlight_confidence = 0.5
dbpedia_spotlight_support = 20
dbpedia_spotlight_min_similarity = 0.8
"""

    example_toml = """[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "password"

[logging]
level = "INFO"
json = false

[spacy]
model = "en_core_web_trf"

[paths]
data_dir = "data"
output_dir = "out"

[features]
create_refinement_run = true
compute_token_ids = false
enable_dbpedia_enrichment = false
fill_numeric_labels = false

[runtime]
mode = "production"
strict_transition_gate = "auto"
naf_sentence_mode = "auto"
tlink_shadow_mode = false
enable_cross_document_fusion = false

[services]
service_timeout_sec = 20
dbpedia_sparql_url = "https://dbpedia.org/sparql"
dbpedia_spotlight_url = "https://api.dbpedia-spotlight.org/en/annotate"
dbpedia_timeout_sec = 8
dbpedia_max_entities_per_run = 500
dbpedia_spotlight_confidence = 0.5
dbpedia_spotlight_support = 20
dbpedia_spotlight_min_similarity = 0.8
"""

    if fmt == 'ini':
        with open(path, 'w') as f:
            f.write(example_ini)
    else:
        with open(path, 'w') as f:
            f.write(example_toml)
