#!/usr/bin/env python3
"""Setup configuration for textgraphx package."""

from setuptools import setup, find_packages

setup(
    name="textgraphx",
    version="0.1.0",
    description="Text-to-Knowledge-Graph pipeline with multi-phase NLP processing",
    author="neostrange",
    packages=find_packages(),
    python_requires=">=3.7",
    include_package_data=True,
    zip_safe=False,
)
