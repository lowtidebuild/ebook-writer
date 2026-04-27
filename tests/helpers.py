from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    """Load a repo-local script module from an arbitrary path."""
    module_path = REPO_ROOT / relative_path
    module_dir = str(module_path.parent)
    inserted = False

    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        inserted = True

    try:
        spec = importlib.util.spec_from_file_location(name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted:
            sys.path.remove(module_dir)
