"""Shared fixtures: the sentinel template and a PATH of stub tools."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from tinderbox import cli

FIXTURE_TEMPLATE = Path(__file__).parent / "fixtures" / "template"

STUB = """#!/bin/sh
printf '%s|%s|%s\\n' "${0##*/}" "$*" "$(pwd)" >> "$STUB_LOG"
if [ "$STUB_FAIL" = "${0##*/}" ]; then
    echo "boom from ${0##*/}" >&2
    exit 3
fi
"""


@pytest.fixture
def template() -> Path:
    return FIXTURE_TEMPLATE


@pytest.fixture
def empty_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Replace PATH with an empty directory, so no tool is found."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    return empty


@pytest.fixture
def stub_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Replace PATH with stub scripts for every prerequisite, git and pnpm; return the log."""
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    log = tmp_path / "stub.log"
    log.touch()
    for name in {*(tool.executable for tool in cli.PREREQUISITES), "git"}:
        script = bin_dir / name
        script.write_text(STUB)
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("STUB_LOG", str(log))
    monkeypatch.delenv("STUB_FAIL", raising=False)
    return log


@pytest.fixture
def use_fixture_template(monkeypatch: pytest.MonkeyPatch, template: Path) -> None:
    monkeypatch.setattr(cli, "find_template", lambda: template)
