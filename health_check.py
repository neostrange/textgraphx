"""
Health check utilities for TextGraphX pipeline.
Verifies system setup before executing pipeline phases.
"""

import sys
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Raised when a health check fails."""
    pass


def check_neo4j_connection(
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "neo4j",
) -> Tuple[bool, str]:
    """
    Check if Neo4j database is accessible.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        from neo4j import GraphDatabase
        
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                result = session.run("RETURN 1")
                result.consume()
            driver.close()
            return True, f"✓ Neo4j connected ({uri})"
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "Could not connect" in error_msg:
                return False, f"✗ Neo4j not running on {uri}\n  Fix: Start Neo4j server"
            return False, f"✗ Neo4j connection failed: {error_msg}"
    except ImportError:
        return False, "✗ neo4j package not installed"


def check_spacy_model(model_name: str) -> Tuple[bool, str]:
    """
    Check if spaCy model is available.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        import spacy
        try:
            spacy.load(model_name)
            return True, f"✓ spaCy model '{model_name}' available"
        except OSError:
            return False, (
                f"✗ spaCy model '{model_name}' not found\n"
                f"  Fix: python -m spacy download {model_name}"
            )
    except ImportError:
        return False, "✗ spacy package not installed"


def check_dataset_directory(dataset_path: str) -> Tuple[bool, str]:
    """
    Check if dataset directory exists and is readable.
    
    Returns:
        (success: bool, message: str)
    """
    import os
    path = Path(dataset_path)
    
    if not path.exists():
        return False, f"✗ Dataset directory not found: {path.resolve()}"
    
    if not path.is_dir():
        return False, f"✗ Path is not a directory: {path.resolve()}"
    
    if not os.access(path, os.R_OK):
        return False, f"✗ Dataset directory not readable: {path.resolve()}"
    
    # Count files
    try:
        files = list(path.iterdir())
        file_count = len([f for f in files if f.is_file()])
        return True, f"✓ Dataset directory valid: {path.resolve()} ({file_count} files)"
    except Exception as e:
        return False, f"✗ Error reading dataset: {e}"


def check_required_modules() -> Tuple[bool, str]:
    """
    Check if all required Python packages are installed.
    
    Returns:
        (success: bool, message: str)
    """
    required = ["spacy", "neo4j", "logging"]
    missing = []
    
    for module_name in required:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
    
    if missing:
        return False, (
            f"✗ Missing required modules: {', '.join(missing)}\n"
            f"  Fix: pip install {' '.join(missing)}"
        )
    
    return True, "✓ All required Python packages installed"


def check_http_service(name: str, url: str, timeout: int = 3) -> Tuple[bool, str]:
    """
    Check if an HTTP service is reachable.

    Returns:
        (success: bool, message: str)
    """
    try:
        import requests
        requests.get(url, timeout=timeout)
        return True, f"✓ {name} reachable ({url})"
    except ImportError:
        return False, "✗ requests package not installed"
    except Exception:
        return False, f"✗ {name} not reachable: {url}\n  Service may not be running"


def check_external_services(cfg=None, fail_fast: bool = False) -> Tuple[bool, List[str]]:
    """
    Check all configured external NLP services.

    Args:
        cfg: Config object (loads from default config if None)
        fail_fast: If True, raise HealthCheckError on first failure

    Returns:
        (all_reachable: bool, messages: List[str])
    """
    if cfg is None:
        from textgraphx.config import get_config
        cfg = get_config()

    services = [
        ("WSD (AMUSE)", cfg.services.wsd_url),
        ("Coreference", cfg.services.coref_url),
        ("Temporal (TTK)", cfg.services.temporal_url),
        ("HeidelTime", cfg.services.heideltime_url),
        ("SRL (AllenNLP)", cfg.services.srl_url),
        ("LLM (Ollama)", cfg.services.llm_url),
    ]

    results = []
    all_reachable = True

    for name, url in services:
        passed, message = check_http_service(name, url)
        results.append(message)
        if not passed:
            all_reachable = False
            logger.warning(message)
            if fail_fast:
                raise HealthCheckError(message)

    return all_reachable, results


def run_health_checks(
    dataset_path: str,
    model_name: str = "en_core_web_sm",
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "neo4j",
    verbose: bool = False,
    check_services: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Run all health checks and return results.
    
    Args:
        dataset_path: Path to dataset directory
        model_name: spaCy model name
        neo4j_uri: Neo4j connection URI
        verbose: Print detailed results
        check_services: If True, also check external NLP service URLs
    
    Returns:
        (all_passed: bool, messages: List[str])
    """
    checks = [
        ("Python modules", lambda: check_required_modules()),
        ("Dataset directory", lambda: check_dataset_directory(dataset_path)),
        ("spaCy model", lambda: check_spacy_model(model_name)),
        ("Neo4j database", lambda: check_neo4j_connection(neo4j_uri, neo4j_user, neo4j_password)),
    ]
    
    results = []
    all_passed = True
    
    for check_name, check_fn in checks:
        try:
            passed, message = check_fn()
            results.append(message)
            if not passed:
                all_passed = False
                if verbose:
                    logger.warning(message)
        except Exception as e:
            result_msg = f"✗ {check_name} check failed: {e}"
            results.append(result_msg)
            all_passed = False
            logger.error(result_msg)

    if check_services:
        svc_passed, svc_messages = check_external_services()
        results.extend(svc_messages)
        if not svc_passed:
            all_passed = False
    
    return all_passed, results


def print_health_check_report(all_passed: bool, messages: List[str]) -> None:
    """Print formatted health check report."""
    print("\n" + "=" * 70)
    print("TextGraphX Health Check Report")
    print("=" * 70)
    
    for message in messages:
        print(message)
    
    print("=" * 70)
    if all_passed:
        print("✓ All checks passed. Ready to run pipeline.")
    else:
        print("✗ Some checks failed. Please fix issues above before running.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Simple test
    all_passed, messages = run_health_checks("./datastore/dataset", verbose=True)
    print_health_check_report(all_passed, messages)
    sys.exit(0 if all_passed else 1)
