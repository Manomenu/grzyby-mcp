"""Every part of the server has a place in the import contracts.

import-linter checks only the modules a contract names, so a new feature left out of
pyproject.toml would escape the layering unnoticed. This test closes that gap.
"""

import pkgutil
import tomllib
from pathlib import Path

import grzyby_server

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def layered_modules() -> set[str]:
    contracts = tomllib.loads(PYPROJECT.read_text())["tool"]["importlinter"]["contracts"]
    top = next(contract for contract in contracts if contract["type"] == "layers" and "containers" not in contract)
    # "a | b" are siblings on one level; "(a)" marks an optional layer.
    return {name.strip(" ()") for layer in top["layers"] for name in layer.split("|")}


def test_every_server_module_has_a_layer() -> None:
    modules = {f"grzyby_server.{module.name}" for module in pkgutil.iter_modules(grzyby_server.__path__)} - {"grzyby_server.__main__"}

    missing = modules - layered_modules()

    assert not missing, f"add to the first [[tool.importlinter.contracts]] in pyproject.toml: {sorted(missing)}"
