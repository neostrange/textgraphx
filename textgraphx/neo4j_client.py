"""neo4j_client

Centralized Neo4j connection helpers and a small compatibility shim that lets
existing code written for ``py2neo.Graph`` continue to work with the official
``neo4j`` bolt driver. The repository expects a simple ``.run(query, params).data()``
contract; the provided ``BoltGraphCompat`` implements that surface over the
bolt driver.

Configuration precedence (highest → lowest):

- `[py2neo]` section in ``textgraphx/config.ini`` (keeps backward compatibility)
- `[neo4j]` section in the same config file
- Environment variables: ``NEO4J_URI``, ``NEO4J_USER`` / ``NEO4J_USERNAME``, ``NEO4J_PASSWORD``

Examples
    >>> from textgraphx.neo4j_client import make_graph_from_config
    >>> graph = make_graph_from_config()
    >>> rows = graph.run('MATCH (n:TagOccurrence) RETURN count(n) AS cnt').data()

This module intentionally keeps a very small surface: callers should get an
object supporting ``.run(query, parameters).data()`` so the rest of the codebase
needs no changes when switching drivers.
"""
from __future__ import annotations

import os
from typing import Optional, Dict, Any
import atexit

from neo4j import GraphDatabase, Driver
from textgraphx.config import get_config


# Deprecated helper kept for backward compatibility with code that imported
# get_config_section from this module. New code should use `textgraphx.config`.
def get_config_section(path: Optional[str] = None, section: str = "py2neo") -> Dict[str, Any]:
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
    """Create and return an official neo4j bolt driver using the config file.

    The function tries the following sources, in this order:
    1. `[py2neo]` section in the provided config file (keeps backward comp.)
    2. `[neo4j]` section in the config
    3. Environment variables `NEO4J_URI`, `NEO4J_USER`/`NEO4J_USERNAME`, and
       `NEO4J_PASSWORD`.

    Returns:
        A `neo4j.Driver` instance connected using the provided credentials.

    Raises:
        RuntimeError: If no usable configuration is found.
    """
    # Use centralized config loader (supports env overrides and file-based
    # configs). Keep the previous error semantics.
    cfg = get_config()
    uri = cfg.neo4j.uri
    username = cfg.neo4j.user
    password = cfg.neo4j.password

    if not (uri and username and password):
        raise RuntimeError(
            "Missing Neo4j configuration. Provide a config file or set NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD environment variables.")

    return GraphDatabase.driver(uri, auth=(username, password))


def _safe_close_driver(driver: Optional[Driver]) -> None:
    """Try to close a neo4j driver without raising during interpreter shutdown.

    The neo4j Driver.__del__ may emit a warning if the driver is not closed
    explicitly before interpreter shutdown. Registering an atexit handler
    that calls ``close`` reduces the chance the driver's destructor runs
    during interpreter finalization (which can trigger the TypeError seen
    when some global state becomes None).
    """
    try:
        if driver is not None:
            driver.close()
    except Exception:
        # Be silent: atexit handlers run during shutdown where many objects
        # may already be torn down. We don't want to raise here.
        pass


class BoltGraphCompat:
    """Compatibility wrapper exposing a ``.run(query, parameters).data()`` API.

    This small shim opens a session for each ``run`` call, executes the query,
    eagerly collects results and returns an object with a ``.data()`` method that
    mirrors the list-of-mappings returned by ``py2neo.Graph.run(...).data()``.

    Notes:
    - Sessions are short-lived and closed immediately after collecting records.
    - This design matches the previous py2neo usage patterns in the codebase
      where callers do not manage transactions explicitly.
    """

    def __init__(self, driver: Driver):
        self._driver = driver

    def close(self) -> None:
        """Close the underlying driver immediately.

        Call this when your program is done with the graph. This avoids the
        driver destructor running during interpreter shutdown which can print
        noisy errors.
        """
        # Close and drop the reference so subsequent calls are safe.
        if getattr(self, "_driver", None) is not None:
            try:
                self._driver.close()
            except Exception:
                pass
            finally:
                self._driver = None

    def run(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a Cypher query and return a small wrapper exposing `.data()`.

        The method will open a short-lived session, execute the provided query
        with optional parameters, collect all records immediately and close the
        session. The returned object implements a ``data()`` method that
        returns a list of dictionaries (one per record), matching py2neo's
        ``Result.data()`` contract.
        """
        session = self._driver.session()
        try:
            result = session.run(query, parameters)
            # Collect records right away and close session to avoid leaving
            # open transactions when the caller iterates later.
            records = list(result)
        finally:
            session.close()

        class ResultWrapper:
            def __init__(self, records):
                self._records = records

            def data(self):
                return [r.data() for r in self._records]

        return ResultWrapper(records)


def make_graph_from_config(path: Optional[str] = None):
    """Create a compatibility graph object using the bolt driver. This returns
    a `BoltGraphCompat` instance which supports `.run(...).data()`.
    """
    driver = make_bolt_driver_from_config(path)
    # Register a best-effort atexit handler to close the driver. This keeps
    # the driver from relying on its __del__ during interpreter shutdown,
    # which can surface noisy TypeError messages in some environments.
    try:
        atexit.register(_safe_close_driver, driver)
    except Exception:
        # If registration fails for any reason, don't block creating the
        # graph object; we'll still return a wrapper that exposes `close()`.
        pass

    return BoltGraphCompat(driver)
