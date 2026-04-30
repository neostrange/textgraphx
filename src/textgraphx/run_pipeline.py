"""Compatibility shim — canonical runner lives at ``textgraphx.orchestration.runner``.

This module exists so that the ``textgraphx-run`` console script declared in
``pyproject.toml`` and shell scripts that invoke ``python -m textgraphx.run_pipeline``
keep working. New code should import from :mod:`textgraphx.orchestration.runner`.
"""

from textgraphx.orchestration.runner import main


if __name__ == "__main__":
    main()
