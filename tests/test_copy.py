from __future__ import annotations

import os
from pathlib import Path

import pytest

from tinderbox.cli import Names, copy_template, is_excluded


@pytest.fixture
def scaffold(tmp_path: Path, template: Path) -> Path:
    dest = tmp_path / "photo-sorter"
    copy_template(template, dest, Names.derive("photo-sorter"))
    return dest


def test_contents_use_every_sentinel_form(scaffold: Path) -> None:
    lib = (scaffold / "crates/photo-sorter-core/src/lib.rs").read_text()
    assert "//! Photo Sorter core." in lib
    assert "use photo_sorter_core::run;" in lib
    assert '"PHOTO_SORTER_HOME"' in lib
    assert 'ID: &str = "com.example.photosorter"' in lib
    assert '"com.example.photosorter.helper"' in lib
    assert 'PRODUCT: &str = "photo-sorter"' in lib
    assert "mberly" not in lib


def test_no_sentinel_survives_in_any_path(scaffold: Path) -> None:
    for path in scaffold.rglob("*"):
        assert "mberly" not in path.relative_to(scaffold).as_posix().lower()


def test_paths_are_renamed(scaffold: Path) -> None:
    expected = {
        "Cargo.toml",
        "crates/photo-sorter-core/Cargo.toml",
        "crates/photo-sorter-core/src/lib.rs",
        "apps/desktop/src-tauri/tauri.conf.json",
        "apps/desktop/tests/coverage/options.ts",
        "scripts/run.sh",
        "docs/Photo Sorter.md",
        "PHOTO_SORTER_NOTES.md",
        "photo_sorter_helpers.rs",
        "com.example.photosorter.plist",
        "assets/icon.bin",
        "assets/legacy.txt",
        "assets/crlf.txt",
        "plain.txt",
    }
    found = {p.relative_to(scaffold).as_posix() for p in scaffold.rglob("*") if p.is_file()}
    assert found == expected


def test_text_files_have_no_sentinel_left(scaffold: Path) -> None:
    for path in scaffold.rglob("*"):
        if path.is_file() and path.suffix not in {".bin", ".txt"}:
            assert "mberly" not in path.read_text(), path


def test_json_identifier_and_title(scaffold: Path) -> None:
    conf = (scaffold / "apps/desktop/src-tauri/tauri.conf.json").read_text()
    assert '"productName": "Photo Sorter"' in conf
    assert '"identifier": "com.example.photosorter"' in conf
    assert '"mainBinaryName": "photo-sorter"' in conf


def test_binary_files_are_copied_unchanged(scaffold: Path, template: Path) -> None:
    for rel in ("assets/icon.bin", "assets/legacy.txt"):
        original = template / rel
        assert (scaffold / rel).read_bytes() == original.read_bytes()
    assert b"emberly" in (scaffold / "assets/icon.bin").read_bytes()


def test_line_endings_are_preserved(scaffold: Path) -> None:
    assert (scaffold / "assets/crlf.txt").read_bytes() == b"CRLF photo-sorter\r\nline two\r\n"


def test_executable_bit_is_preserved(scaffold: Path) -> None:
    assert os.access(scaffold / "scripts/run.sh", os.X_OK)
    assert not os.access(scaffold / "plain.txt", os.X_OK)
    assert (scaffold / "scripts/run.sh").read_text() == '#!/bin/sh\necho "starting photo-sorter"\n'


def test_returns_the_file_count(tmp_path: Path, template: Path) -> None:
    assert copy_template(template, tmp_path / "out", Names.derive("photo-sorter")) == 14


def test_build_output_is_not_copied(tmp_path: Path, template: Path) -> None:
    source = tmp_path / "template"
    source.mkdir()
    (source / "keep.txt").write_text("keep")
    junk = [
        "target/debug/x",
        "apps/desktop/src-tauri/target/x",
        "apps/desktop/node_modules/pkg/index.js",
        "apps/desktop/test-results/r.json",
        "apps/desktop/playwright-report/index.html",
        "apps/desktop/coverage/lcov.info",
        "coverage/lcov.info",
        ".DS_Store",
        "docs/.DS_Store",
        "config.local.toml",
        "apps/desktop/tests/coverage/options.ts",
    ]
    for rel in junk:
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    copy_template(source, tmp_path / "out", Names.derive("photo-sorter"))
    found = {
        p.relative_to(tmp_path / "out").as_posix()
        for p in (tmp_path / "out").rglob("*")
        if p.is_file()
    }
    assert found == {"keep.txt", "apps/desktop/tests/coverage/options.ts"}


@pytest.mark.parametrize(
    ("relative", "excluded"),
    [
        ("target/x", True),
        ("crates/a/target", True),
        ("node_modules", True),
        ("coverage", True),
        ("apps/desktop/coverage/index.html", True),
        ("apps/desktop/tests/coverage/options.ts", False),
        ("tests/coverage/options.ts", False),
        ("src/coverage.rs", False),
        ("a.local.sh", True),
        ("dir/.DS_Store", True),
        ("Cargo.lock", False),
    ],
)
def test_is_excluded(relative: str, excluded: bool) -> None:  # noqa: FBT001
    assert is_excluded(Path(relative)) is excluded
