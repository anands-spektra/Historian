"""Provider registry. A provider is any module here exposing
`analyze(prompt: str, cfg: dict) -> str`. Selected by config key `provider`."""

import importlib


def get_provider(name):
    return importlib.import_module(f".{name}", __package__)
