from __future__ import annotations

import os
import runpy
from pathlib import Path

import pytest

from tinderbox import __version__, cli

pytestmark = pytest.mark.usefixtures("use_fixture_template")

NO_SETUP_NOTE = "git init -b main"


def run(*args: str) -> int:
    return cli.main(list(args))


def log_lines(log: Path) -> list[list[str]]:
    return [line.split("|") for line in log.read_text().splitlines()]


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        run("--version")
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"tinderbox {__version__}\n"


def test_version_matches_pyproject() -> None:
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    assert f'version = "{__version__}"' in pyproject


def test_module_entry_point(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["tinderbox", "--version"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("tinderbox", run_name="__main__")
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_invalid_name_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run("Bad_Name", "--dest", str(tmp_path / "x"), "--no-setup") == 1
    assert "invalid name" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()


def test_non_empty_destination_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "taken"
    dest.mkdir()
    (dest / "file").write_text("keep")
    assert run("photo-sorter", "--dest", str(dest), "--no-setup") == 1
    assert "not empty" in capsys.readouterr().err
    assert (dest / "file").read_text() == "keep"


def test_destination_that_is_a_file_is_refused(tmp_path: Path) -> None:
    dest = tmp_path / "file"
    dest.write_text("x")
    assert run("photo-sorter", "--dest", str(dest), "--no-setup") == 1


def test_empty_existing_destination_is_accepted(tmp_path: Path, empty_path: Path) -> None:
    dest = tmp_path / "empty"
    dest.mkdir()
    assert run("photo-sorter", "--dest", str(dest), "--no-setup") == 0
    assert (dest / "Cargo.toml").is_file()


def test_default_destination_is_the_name_under_the_cwd(
    tmp_path: Path, empty_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run("photo-sorter", "--no-setup") == 0
    assert (tmp_path / "photo-sorter" / "Cargo.toml").is_file()


def test_title_and_identifier_flags(tmp_path: Path, empty_path: Path) -> None:
    dest = tmp_path / "out"
    assert (
        run(
            "photo-sorter",
            "--title",
            "PS Pro",
            "--identifier",
            "org.acme.ps",
            "--dest",
            str(dest),
            "--no-setup",
        )
        == 0
    )
    conf = (dest / "apps/desktop/src-tauri/tauri.conf.json").read_text()
    assert '"productName": "PS Pro"' in conf
    assert '"identifier": "org.acme.ps"' in conf


def test_missing_prerequisites_are_an_error_without_no_setup(
    tmp_path: Path, empty_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "out"
    assert run("photo-sorter", "--dest", str(dest)) == 1
    err = capsys.readouterr().err
    for tool in cli.PREREQUISITES:
        assert f"missing {tool.executable}: {tool.hint}" in err
    assert "brew install pnpm" in err
    assert "cargo install --locked cargo-nextest" in err
    assert not dest.exists()


def test_missing_prerequisites_are_a_warning_with_no_setup(
    tmp_path: Path, empty_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "out"
    assert run("photo-sorter", "--dest", str(dest), "--no-setup") == 0
    captured = capsys.readouterr()
    assert "missing rustup" in captured.err
    assert (dest / "Cargo.toml").is_file()
    assert NO_SETUP_NOTE in captured.out


def test_one_missing_prerequisite_is_named(
    tmp_path: Path, stub_tools: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (stub_tools.parent / "stub-bin" / "cargo-mutants").unlink()
    assert run("photo-sorter", "--dest", str(tmp_path / "out")) == 1
    err = capsys.readouterr().err
    assert [line for line in err.splitlines() if line.startswith("missing ")] == [
        "missing cargo-mutants: cargo install --locked cargo-mutants"
    ]
    assert "missing cargo-mutants: cargo install --locked cargo-mutants" in err


def test_no_setup_runs_no_commands(tmp_path: Path, stub_tools: Path) -> None:
    assert run("photo-sorter", "--dest", str(tmp_path / "out"), "--no-setup") == 0
    assert stub_tools.read_text() == ""


def test_setup_runs_each_step_in_order(
    tmp_path: Path, stub_tools: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "out"
    assert run("photo-sorter", "--dest", str(dest)) == 0
    steps = [(name, args, Path(cwd)) for name, args, cwd in log_lines(stub_tools)]
    resolved = dest.resolve()
    assert steps == [
        ("git", "init -b main", resolved),
        ("pnpm", "install --frozen-lockfile", resolved / "apps" / "desktop"),
        ("lefthook", "install", resolved),
        ("git", "add -A", resolved),
        ("git", f"commit -m chore: scaffold from tinderbox {__version__}", resolved),
    ]
    out = capsys.readouterr().out
    assert "scripts/gate.sh full" in out
    assert NO_SETUP_NOTE not in out


def test_the_initial_commit_never_skips_hooks(tmp_path: Path, stub_tools: Path) -> None:
    assert run("photo-sorter", "--dest", str(tmp_path / "out")) == 0
    assert "--no-verify" not in stub_tools.read_text()
    assert " -n" not in stub_tools.read_text()


LAST_STEP = {"git": "git init", "pnpm": "pnpm install", "lefthook": "lefthook install"}


@pytest.mark.parametrize("failing", list(LAST_STEP))
def test_a_failing_step_stops_setup(
    tmp_path: Path,
    stub_tools: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failing: str,
) -> None:
    monkeypatch.setenv("STUB_FAIL", failing)
    assert run("photo-sorter", "--dest", str(tmp_path / "out")) == 1
    captured = capsys.readouterr()
    assert f"boom from {failing}" in captured.err
    assert "(exit 3)" in captured.err
    assert LAST_STEP[failing] in captured.out
    assert "initial commit" not in captured.out
    assert "Next steps" not in captured.out


def test_a_failing_commit_reports_the_hook_output(
    tmp_path: Path,
    stub_tools: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # git succeeds for init and add but fails for the commit: use a git stub that checks its argv.
    git = stub_tools.parent / "stub-bin" / "git"
    git.write_text('#!/bin/sh\nif [ "$1" = commit ]; then echo "gate failed" >&2; exit 1; fi\n')
    assert run("photo-sorter", "--dest", str(tmp_path / "out")) == 1
    captured = capsys.readouterr()
    assert "gate failed" in captured.err
    assert "commit -m chore: scaffold from tinderbox" in captured.err
    assert "Next steps" not in captured.out


def test_a_tool_that_vanishes_after_the_check_is_reported(
    tmp_path: Path, stub_tools: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (stub_tools.parent / "stub-bin" / "git").unlink()
    assert run("photo-sorter", "--dest", str(tmp_path / "out")) == 1
    assert "could not run" in capsys.readouterr().err


def test_template_is_found_from_the_package_then_the_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packaged = tmp_path / "packaged"
    checkout = tmp_path / "checkout"
    monkeypatch.undo()
    monkeypatch.setattr(cli, "_packaged_template", lambda: packaged)
    monkeypatch.setattr(cli, "_checkout_template", lambda: checkout)
    with pytest.raises(cli.TinderboxError, match="template was not found"):
        cli.find_template()
    checkout.mkdir()
    assert cli.find_template() == checkout
    packaged.mkdir()
    assert cli.find_template() == packaged


def test_the_real_locators_point_at_template_directories() -> None:
    assert cli._packaged_template().name == "template"  # noqa: SLF001
    assert cli._checkout_template() == Path(cli.__file__).resolve().parents[2] / "template"  # noqa: SLF001


def test_missing_template_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.undo()
    monkeypatch.setattr(cli, "_packaged_template", lambda: tmp_path / "no")
    monkeypatch.setattr(cli, "_checkout_template", lambda: tmp_path / "no")
    assert run("photo-sorter", "--dest", str(tmp_path / "out"), "--no-setup") == 1
    assert "template was not found" in capsys.readouterr().err


def test_stub_path_is_replaced_not_prepended(stub_tools: Path) -> None:
    assert os.environ["PATH"] == str(stub_tools.parent / "stub-bin")
