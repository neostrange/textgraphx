#!/usr/bin/env python3
"""
Smoke-test MCP servers configured in .vscode/mcp.json.

Speaks MCP over stdio (JSON-RPC 2.0, line-delimited):
  1. initialize
  2. notifications/initialized
  3. tools/list

Exits 0 on success, 1 on failure. Prints the tool list per server.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from typing import Any


def _read_message(proc: subprocess.Popen, timeout: float = 15.0) -> dict[str, Any] | None:
    """Read one JSON-RPC message (line-delimited or LSP-framed)."""
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        # Plain line-delimited JSON path
        line_str = line.decode("utf-8", errors="replace").strip()
        if line_str.startswith("{"):
            try:
                return json.loads(line_str)
            except json.JSONDecodeError:
                buf += line
                continue
        # LSP-style framing: Content-Length: N\r\n\r\n<json>
        if line_str.lower().startswith("content-length:"):
            length = int(line_str.split(":", 1)[1].strip())
            # consume blank line
            proc.stdout.readline()
            payload = proc.stdout.read(length)
            return json.loads(payload.decode("utf-8"))
    return None


def _send(proc: subprocess.Popen, msg: dict[str, Any]) -> None:
    data = (json.dumps(msg) + "\n").encode("utf-8")
    proc.stdin.write(data)
    proc.stdin.flush()


def _drain_stderr(proc: subprocess.Popen, label: str) -> None:
    """Background reader so stderr doesn't block on the pipe."""
    def _run():
        for line in iter(proc.stderr.readline, b""):
            sys.stderr.write(f"[{label}/stderr] {line.decode(errors='replace')}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def test_server(label: str, command: list[str], env: dict[str, str] | None = None) -> bool:
    print(f"\n=== {label} ===")
    print(f"command: {' '.join(command)}")
    full_env = {**os.environ}
    if env:
        full_env.update(env)
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            bufsize=0,
        )
    except FileNotFoundError as e:
        print(f"  FAIL: {e}")
        return False

    _drain_stderr(proc, label)

    try:
        # 1) initialize
        _send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "0.1.0"},
            },
        })
        init_resp = _read_message(proc, timeout=60.0)
        if not init_resp or "result" not in init_resp:
            print(f"  FAIL: no/invalid initialize response: {init_resp!r}")
            return False
        server_info = init_resp["result"].get("serverInfo", {})
        print(f"  initialize OK: {server_info}")

        # 2) initialized notification
        _send(proc, {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })

        # 3) tools/list
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = _read_message(proc, timeout=15.0)
        if not tools_resp or "result" not in tools_resp:
            print(f"  FAIL: no/invalid tools/list response: {tools_resp!r}")
            return False
        tools = tools_resp["result"].get("tools", [])
        print(f"  tools/list OK ({len(tools)} tools):")
        for t in tools:
            print(f"    - {t.get('name')}: {t.get('description', '')[:80]}")
        return True
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def main() -> int:
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    datastore = os.path.join(workspace, "src", "textgraphx", "datastore")

    results = {}

    # Filesystem MCP server (no external deps)
    results["datastore-fs"] = test_server(
        "datastore-fs",
        ["npx", "-y", "@modelcontextprotocol/server-filesystem", datastore],
    )

    # Neo4j Cypher MCP server — uses NEO4J_* env vars if set
    neo4j_env = {
        "NEO4J_URI": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "NEO4J_USERNAME": os.environ.get("NEO4J_USERNAME", "neo4j"),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "password"),
        "NEO4J_DATABASE": os.environ.get("NEO4J_DATABASE", "neo4j"),
    }
    results["neo4j-cypher"] = test_server(
        "neo4j-cypher",
        ["uvx", "--python", "3.12", "mcp-neo4j-cypher@latest", "--transport", "stdio"],
        env=neo4j_env,
    )

    print("\n=== summary ===")
    for name, ok in results.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
