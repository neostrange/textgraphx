"""Canonical Neo4j client helpers for the database package.

Centralized Neo4j connection helpers and a small compatibility shim that lets
existing code written for ``py2neo.Graph`` continue to work with the official
``neo4j`` bolt driver. The repository expects a simple ``.run(query, params).data()``
contract; the provided ``BoltGraphCompat`` implements that surface over the
bolt driver.

Configuration precedence (highest -> lowest):

- `[py2neo]` section in ``textgraphx/config.ini`` (keeps backward compatibility)
- `[neo4j]` section in the same config file
- Environment variables: ``NEO4J_URI``, ``NEO4J_USER`` / ``NEO4J_USERNAME``, ``NEO4J_PASSWORD``

Examples
    >>> from textgraphx.database.client import make_graph_from_config
    >>> graph = make_graph_from_config()
    >>> rows = graph.run('MATCH (n:TagOccurrence) RETURN count(n) AS cnt').data()

This module intentionally keeps a very small surface: callers should get an
object supporting ``.run(query, parameters).data()`` so the rest of the codebase
needs no changes when switching drivers.
"""

from __future__ import annotations

import atexit
from typing import Any, Dict, Optional

from neo4j import Driver, GraphDatabase

from textgraphx.infrastructure.config import get_config


def get_config_section(path: Optional[str] = None, section: str = "py2neo") -> Dict[str, Any]:
    """Return Neo4j configuration for legacy callers importing this helper."""
    cfg = get_config()
    if section.lower() in ("py2neo", "neo4j"):
        return {
            "uri": cfg.neo4j.uri,
            "user": cfg.neo4j.user,
            "password": cfg.neo4j.password,
            "database": cfg.neo4j.database,
        }
    return {}


def make_bolt_driver_from_config(path: Optional[str] = None) -> Driver:
    """Create and return an official neo4j bolt driver using the configured credentials."""
    cfg = get_config()
    uri = cfg.neo4j.uri
    username = cfg.neo4j.user
    password = cfg.neo4j.password

    if not (uri and username and password):
        raise RuntimeError(
            "Missing Neo4j configuration. Provide a config file or set NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD environment variables."
        )

    return GraphDatabase.driver(uri, auth=(username, password))


def _safe_close_driver(driver: Optional[Driver]) -> None:
    """Try to close a neo4j driver without raising during interpreter shutdown."""
    try:
        if driver is not None:
            driver.close()
    except Exception:
        pass


class BoltGraphCompat:
    """Compatibility wrapper exposing a ``.run(query, parameters).data()`` API.

    A single Neo4j session is opened lazily on the first ``.run()`` call and
    reused for all subsequent calls on the same instance.  This eliminates the
    per-query session-creation overhead that appeared as N+1 round-trips during
    pipeline phases.  The session is closed (and the driver released) when
    ``.close()`` is called or the object is garbage-collected.

    The pipeline phases are single-threaded; sessions are **not** shared across
    threads, so reuse is safe here.
    """

    def __init__(self, driver: Driver):
        self._driver = driver
        self._session = None  # opened lazily; reused across .run() calls

    def _open_session(self):
        """Return the live session, opening one if needed."""
        if self._session is None:
            self._session = self._driver.session()
        return self._session

    def close(self) -> None:
        """Close the session and the underlying driver."""
        if getattr(self, "_session", None) is not None:
            try:
                self._session.close()
            except Exception:
                pass
            finally:
                self._session = None
        if getattr(self, "_driver", None) is not None:
            try:
                self._driver.close()
            except Exception:
                pass
            finally:
                self._driver = None

    def run(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a Cypher query and return a small wrapper exposing ``data()``."""
        session = self._open_session()
        try:
            result = session.run(query, parameters)
            records = list(result)
        except Exception:
            # Session may be broken (e.g. connection reset). Reset it and retry
            # once with a fresh session before propagating the error.
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
            session = self._open_session()
            result = session.run(query, parameters)
            records = list(result)

        class ResultWrapper:
            def __init__(self, records):
                self._records = records

            def data(self):
                return [record.data() for record in self._records]

        return ResultWrapper(records)


def make_graph_from_config(path: Optional[str] = None):
    """Create a compatibility graph object using the bolt driver."""
    driver = make_bolt_driver_from_config(path)
    try:
        atexit.register(_safe_close_driver, driver)
    except Exception:
        pass

    return BoltGraphCompat(driver)


__all__ = [
    "BoltGraphCompat",
    "get_config_section",
    "make_bolt_driver_from_config",
    "make_graph_from_config",
]