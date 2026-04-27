#!/usr/bin/env python3
"""Resolve domain plugin selection without implicit auto-activation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def available_plugins(plugins_root: str | Path = ".claude/plugins") -> list[str]:
    """Return plugin directory names that contain a PLUGIN.md file."""
    root = Path(plugins_root)
    if not root.is_dir():
        return []
    return sorted(
        child.name
        for child in root.iterdir()
        if child.is_dir() and (child / "PLUGIN.md").is_file()
    )


def resolve_plugin(
    requested_plugin: str | None,
    plugins_root: str | Path = ".claude/plugins",
) -> dict[str, Any]:
    """Resolve the explicitly requested plugin, or general-purpose mode.

    Domain plugins are never auto-detected. Available plugins are returned as
    advisory metadata so callers can show suggestions without changing state.
    """
    plugins = available_plugins(plugins_root)

    if not requested_plugin:
        return {
            "status": "ok",
            "plugin": None,
            "mode": "general-purpose",
            "available_plugins": plugins,
            "message": "No plugin requested; running in general-purpose mode.",
        }

    if requested_plugin not in plugins:
        return {
            "status": "failed",
            "plugin": None,
            "mode": "general-purpose",
            "available_plugins": plugins,
            "error": f"Plugin not found: {requested_plugin}",
        }

    return {
        "status": "ok",
        "plugin": requested_plugin,
        "mode": "domain-plugin",
        "available_plugins": plugins,
        "plugin_path": str(Path(plugins_root) / requested_plugin / "PLUGIN.md"),
        "message": f"Using explicitly requested plugin: {requested_plugin}",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve explicit ebook plugin selection.")
    parser.add_argument("--plugin", default=None, help="Explicit plugin domain to activate.")
    parser.add_argument("--plugins-root", default=".claude/plugins")
    args = parser.parse_args(argv)

    payload = resolve_plugin(args.plugin, args.plugins_root)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
