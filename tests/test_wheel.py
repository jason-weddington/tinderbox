"""Build a wheel from a temp copy of the repo with a fake template and inspect it."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

SHIPPED = [
    "Cargo.toml",
    "apps/desktop/src-tauri/src/main.rs",
    "apps/desktop/tests/coverage/options.ts",
    "scripts/gate.sh",
]
BUILD_OUTPUT = [
    "target/debug/app",
    "apps/desktop/src-tauri/target/release/app",
    "apps/desktop/node_modules/svelte/index.js",
    "apps/desktop/test-results/result.json",
    "apps/desktop/playwright-report/index.html",
    "apps/desktop/coverage/lcov.info",
    "coverage/lcov.info",
    ".DS_Store",
    "docs/.DS_Store",
    "settings.local.json",
]


@pytest.fixture(scope="module")
def wheel_names(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[str], zipfile.ZipFile]:
    root = tmp_path_factory.mktemp("wheel-repo")
    for name in ("pyproject.toml", "hatch_build.py", "README.md", "LICENSE"):
        shutil.copy(REPO / name, root / name)
    shutil.copytree(REPO / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    template = root / "template"
    for rel in [*SHIPPED, *BUILD_OUTPUT]:
        path = template / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    (template / "scripts/gate.sh").chmod(0o755)
    out = root / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = zipfile.ZipFile(next(out.glob("tinderbox-*.whl")))
    return wheel.namelist(), wheel


def test_wheel_contains_the_package_and_the_template(
    wheel_names: tuple[list[str], zipfile.ZipFile],
) -> None:
    names, _ = wheel_names
    assert "tinderbox/cli.py" in names
    assert "tinderbox/py.typed" in names
    for rel in SHIPPED:
        assert f"tinderbox/template/{rel}" in names


def test_wheel_excludes_build_output(wheel_names: tuple[list[str], zipfile.ZipFile]) -> None:
    names, _ = wheel_names
    leaked = [
        n
        for n in names
        if n.startswith("tinderbox/template/")
        and n.removeprefix("tinderbox/template/") in BUILD_OUTPUT
    ]
    assert leaked == []
    for fragment in (
        "/target/",
        "node_modules",
        "test-results",
        "playwright-report",
        ".DS_Store",
        ".local.",
    ):
        assert not [n for n in names if fragment in n], fragment
    assert not [n for n in names if n.startswith("tinderbox/template/coverage/")]
    assert not [n for n in names if n.startswith("tinderbox/template/apps/desktop/coverage/")]


def test_wheel_preserves_the_executable_bit(wheel_names: tuple[list[str], zipfile.ZipFile]) -> None:
    _, wheel = wheel_names
    mode = wheel.getinfo("tinderbox/template/scripts/gate.sh").external_attr >> 16
    assert mode & 0o111
