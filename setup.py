#!/usr/bin/env python3
"""Backwards-compatibility shim.  All packaging configuration has moved to pyproject.toml.
This file exists only for tooling that still invokes `python setup.py …` directly.
"""
from setuptools import setup

setup()
