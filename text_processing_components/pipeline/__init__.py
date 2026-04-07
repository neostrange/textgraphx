"""Pipeline component package namespace."""

from importlib import import_module

__all__ = ["component_factory"]


def __getattr__(name):
	if name == "component_factory":
		return import_module(f"{__name__}.component_factory")
	raise AttributeError(name)
