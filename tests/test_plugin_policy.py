from __future__ import annotations

from helpers import load_module


plugin_policy = load_module("plugin_policy_module", "scripts/plugin_policy.py")


def make_plugin(root, name: str) -> None:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "PLUGIN.md").write_text(f"# {name}\n", encoding="utf-8")


def test_no_requested_plugin_does_not_auto_activate_available_plugin(tmp_path) -> None:
    plugins_root = tmp_path / "plugins"
    make_plugin(plugins_root, "legal")

    result = plugin_policy.resolve_plugin(None, plugins_root)

    assert result["status"] == "ok"
    assert result["plugin"] is None
    assert result["mode"] == "general-purpose"
    assert result["available_plugins"] == ["legal"]


def test_explicit_plugin_resolves_to_domain_mode(tmp_path) -> None:
    plugins_root = tmp_path / "plugins"
    make_plugin(plugins_root, "legal")

    result = plugin_policy.resolve_plugin("legal", plugins_root)

    assert result["status"] == "ok"
    assert result["plugin"] == "legal"
    assert result["mode"] == "domain-plugin"
    assert result["plugin_path"].endswith("legal/PLUGIN.md")


def test_missing_plugin_reports_error_without_fallback_activation(tmp_path) -> None:
    plugins_root = tmp_path / "plugins"
    make_plugin(plugins_root, "legal")

    result = plugin_policy.resolve_plugin("finance", plugins_root)

    assert result["status"] == "failed"
    assert result["plugin"] is None
    assert result["available_plugins"] == ["legal"]
