#!/usr/bin/env python3
"""Sandbox helpers for executing runnable code blocks."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass

try:
    import resource
except ImportError:  # pragma: no cover - non-POSIX fallback
    resource = None


PYTHON_LANGUAGES = {"python", "py", "python3"}
SHELL_LANGUAGES = {"bash", "sh", "shell", "zsh"}


class SandboxUnavailableError(RuntimeError):
    """Raised when the requested sandbox backend cannot be used."""


class UnsafeCodeError(RuntimeError):
    """Raised when runnable code violates local execution safety rules."""


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration for runnable code execution."""

    mode: str = "auto"
    timeout_seconds: int = 30
    memory_mb: int = 256
    tmpfs_mb: int = 64
    pids_limit: int = 64
    allow_unsafe_process: bool = False
    docker_python_image: str = "python:3.12-alpine"
    docker_shell_image: str = "bash:5.2"


def docker_available() -> bool:
    """Return True when the Docker CLI is available."""
    return shutil.which("docker") is not None


PYTHON_NETWORK_PATTERNS = [
    ("requests", re.compile(r"^\s*(?:import\s+requests\b|from\s+requests\s+import\b)")),
    ("urllib", re.compile(r"^\s*(?:import\s+urllib\b|from\s+urllib\b)")),
    ("socket", re.compile(r"^\s*(?:import\s+socket\b|from\s+socket\s+import\b)")),
    ("http.client", re.compile(r"^\s*(?:import\s+http\.client\b|from\s+http\s+import\s+client\b)")),
]
SHELL_NETWORK_PATTERNS = [
    ("curl", re.compile(r"(^|[;&|]\s*)curl\b")),
    ("wget", re.compile(r"(^|[;&|]\s*)wget\b")),
    ("nc", re.compile(r"(^|[;&|]\s*)nc\b")),
    ("ssh", re.compile(r"(^|[;&|]\s*)ssh\b")),
]


def select_backend(mode: str, allow_unsafe_process: bool = False) -> str:
    """Resolve a sandbox backend from the requested mode."""
    if mode == "process":
        if not allow_unsafe_process:
            raise SandboxUnavailableError(
                "--sandbox process requires --allow-unsafe-process because it uses host process isolation"
            )
        return "process"
    if mode == "docker":
        if not docker_available():
            raise SandboxUnavailableError("Docker CLI not available for --sandbox docker")
        return "docker"
    if mode == "auto" and docker_available():
        return "docker"
    if mode == "auto" and allow_unsafe_process:
        return "process"
    if mode == "auto":
        raise SandboxUnavailableError(
            "Docker CLI not available for --sandbox auto; use --sandbox docker in CI/production "
            "or add --sandbox process --allow-unsafe-process for trusted local examples"
        )
    raise SandboxUnavailableError(f"Unknown sandbox mode: {mode}")


def resolve_executor(language: str) -> dict | None:
    """Return executor commands for the given language."""
    normalized = language.lower()
    if normalized in PYTHON_LANGUAGES:
        return {
            "local_command": [sys.executable, "-I", "-B", "-"],
            "docker_command": ["python3", "-I", "-B", "-"],
            "docker_image_type": "python",
        }
    if normalized in SHELL_LANGUAGES:
        return {
            "local_command": ["bash", "-s"],
            "docker_command": ["bash", "-s"],
            "docker_image_type": "shell",
        }
    return None


def build_docker_command(language: str, config: SandboxConfig) -> list[str]:
    """Build a Docker command with network/filesystem isolation."""
    executor = resolve_executor(language)
    if executor is None:
        raise SandboxUnavailableError(f"No sandbox executor for {language}")

    if executor["docker_image_type"] == "python":
        image = config.docker_python_image
    else:
        image = config.docker_shell_image

    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(config.pids_limit),
        "--memory",
        f"{config.memory_mb}m",
        "--user",
        "65534:65534",
        "--workdir",
        "/workspace",
        "--tmpfs",
        f"/workspace:rw,nosuid,nodev,size={config.tmpfs_mb}m",
        "--tmpfs",
        f"/tmp:rw,noexec,nosuid,nodev,size={config.tmpfs_mb}m",
        "--env",
        "HOME=/tmp",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTHONNOUSERSITE=1",
        image,
        *executor["docker_command"],
    ]


def sandbox_metadata(backend: str) -> dict:
    """Return structured metadata for the selected sandbox backend."""
    if backend == "docker":
        return {
            "backend": "docker",
            "network_access": "disabled",
            "filesystem_access": "tmpfs_only",
            "isolation_level": "strong",
        }
    return {
        "backend": "process",
        "network_access": "host",
        "filesystem_access": "tempdir_only",
        "isolation_level": "best_effort",
        "warning": "Process sandbox is not suitable for untrusted code. Use Docker for untrusted examples.",
    }


def detect_network_usage(code: str, language: str) -> list[dict]:
    """Detect obvious network access in runnable examples before execution."""
    normalized = language.lower()
    patterns = []
    if normalized in PYTHON_LANGUAGES:
        patterns = PYTHON_NETWORK_PATTERNS
    elif normalized in SHELL_LANGUAGES:
        patterns = SHELL_NETWORK_PATTERNS

    findings: list[dict] = []
    for line_number, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for name, pattern in patterns:
            if pattern.search(line):
                findings.append(
                    {
                        "line": line_number,
                        "pattern": name,
                        "issue": "Network access is not allowed in runnable examples.",
                    }
                )
    return findings


def build_process_env(workspace: str) -> dict[str, str]:
    """Construct a minimal environment for local fallback execution."""
    env = {
        "HOME": workspace,
        "TMPDIR": workspace,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", os.environ.get("LANG", "C.UTF-8")),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }
    return env


def build_preexec_fn() -> Callable[[], None] | None:
    """Return a POSIX-only pre-exec hook with conservative rlimits."""
    if resource is None or os.name != "posix":
        return None

    def _apply_limits():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if hasattr(resource, "RLIMIT_FSIZE"):
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        if hasattr(resource, "RLIMIT_NOFILE"):
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        if hasattr(resource, "RLIMIT_NPROC"):
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))

    return _apply_limits


def run_code_in_sandbox(code: str, language: str, config: SandboxConfig) -> dict:
    """Execute code in the requested sandbox backend."""
    executor = resolve_executor(language)
    if executor is None:
        raise SandboxUnavailableError(f"No sandbox executor for {language}")

    network_findings = detect_network_usage(code, language)
    if network_findings:
        summary = ", ".join(
            f"line {finding['line']} uses {finding['pattern']}" for finding in network_findings
        )
        raise UnsafeCodeError(f"Network usage is not allowed in runnable examples: {summary}")

    backend = select_backend(config.mode, allow_unsafe_process=config.allow_unsafe_process)

    try:
        if backend == "docker":
            command = build_docker_command(language, config)
            result = subprocess.run(
                command,
                input=code,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout.rstrip("\n"),
                "stderr": result.stderr.strip()[:500],
                "sandbox": sandbox_metadata("docker"),
            }

        with tempfile.TemporaryDirectory(prefix="ebook-writer-sandbox-") as workspace:
            result = subprocess.run(
                executor["local_command"],
                input=code,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                cwd=workspace,
                env=build_process_env(workspace),
                preexec_fn=build_preexec_fn(),
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout.rstrip("\n"),
                "stderr": result.stderr.strip()[:500],
                "sandbox": sandbox_metadata("process"),
            }
    except FileNotFoundError as exc:
        raise SandboxUnavailableError(str(exc)) from exc
