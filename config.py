"""Central configuration loader for textgraphx.

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
class FeatureFlags:
    create_refinement_run: bool = True
    compute_token_ids: bool = False


@dataclass
class Config:
    neo4j: Neo4jConfig
    logging: LoggingConfig
    spacy: SpaCyConfig
    paths: PathsConfig
    features: FeatureFlags


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

    cfg = Config(neo4j=neo, logging=log, spacy=spacy, paths=paths, features=features)
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
"""

    if fmt == 'ini':
        with open(path, 'w') as f:
            f.write(example_ini)
    else:
        with open(path, 'w') as f:
            f.write(example_toml)
