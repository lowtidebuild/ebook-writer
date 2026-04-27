from __future__ import annotations

import pytest

from helpers import load_module


execution_sandbox = load_module(
    "test_execution_sandbox_module",
    ".claude/skills/code-example-validator/scripts/execution_sandbox.py",
)
validate_code = load_module(
    "test_validate_code_for_sandbox_module",
    ".claude/skills/code-example-validator/scripts/validate_code.py",
)


def test_select_backend_prefers_docker_when_available(monkeypatch):
    monkeypatch.setattr(execution_sandbox, "docker_available", lambda: True)

    assert execution_sandbox.select_backend("auto") == "docker"


def test_select_backend_requires_process_opt_in_when_docker_missing(monkeypatch):
    monkeypatch.setattr(execution_sandbox, "docker_available", lambda: False)

    with pytest.raises(execution_sandbox.SandboxUnavailableError):
        execution_sandbox.select_backend("auto")


def test_select_backend_allows_process_with_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(execution_sandbox, "docker_available", lambda: False)

    assert execution_sandbox.select_backend("auto", allow_unsafe_process=True) == "process"


def test_build_docker_command_includes_network_and_filesystem_guards():
    command = execution_sandbox.build_docker_command(
        "python",
        execution_sandbox.SandboxConfig(),
    )

    assert "--network" in command
    assert "none" in command
    assert "--read-only" in command
    assert "--tmpfs" in command
    assert "python:3.12-alpine" in command


def test_run_code_in_sandbox_process_mode_reports_process_metadata():
    result = execution_sandbox.run_code_in_sandbox(
        "import os\nprint(os.getcwd())\n",
        "python",
        execution_sandbox.SandboxConfig(mode="process", allow_unsafe_process=True),
    )

    assert result["returncode"] == 0
    assert "ebook-writer-sandbox-" in result["stdout"]
    assert result["sandbox"]["backend"] == "process"
    assert result["sandbox"]["filesystem_access"] == "tempdir_only"
    assert "warning" in result["sandbox"]


def test_network_usage_is_rejected_before_execution():
    findings = execution_sandbox.detect_network_usage("import requests\nprint('x')", "python")

    assert findings[0]["pattern"] == "requests"

    with pytest.raises(execution_sandbox.UnsafeCodeError):
        execution_sandbox.run_code_in_sandbox(
            "import socket\nprint('x')",
            "python",
            execution_sandbox.SandboxConfig(mode="process", allow_unsafe_process=True),
        )


def test_execute_block_fails_when_docker_mode_requested_without_docker(monkeypatch):
    monkeypatch.setattr(validate_code, "resolve_executor", lambda language: {"ok": True})
    monkeypatch.setattr(
        validate_code,
        "run_code_in_sandbox",
        lambda code, language, config: (_ for _ in ()).throw(
            validate_code.SandboxUnavailableError("Docker CLI not available for --sandbox docker")
        ),
    )

    result = validate_code.execute_block("print('x')", "python", sandbox_mode="docker")

    assert result["status"] == "failed"
    assert "Docker CLI not available" in result["error"]
    assert result["sandbox"]["backend"] == "docker"
