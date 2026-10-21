"""The tinderbox CLI: copy the template, rename the sentinel, run setup."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from tinderbox import __version__

if TYPE_CHECKING:
    from collections.abc import Iterator

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
# The title lands in JSON, TOML, HTML and Rust strings, so refuse anything
# that needs escaping in any of them.
TITLE_PATTERN = re.compile(r'^[^\x00-\x1f"\\<>&\x7f]+$')

# The sentinel forms, in replacement order. One alternation pass gives the
# same result as replacing them one after another, without rescanning text
# a previous replacement produced (a custom identifier may contain "emberly").
SENTINEL = re.compile(r"com\.example\.emberly|EMBERLY_|emberly_|Emberly|emberly")

# Build output that must never be copied or shipped. Names match at any depth;
# the anchored globs match from the template root, because the template has a
# source directory (tests/coverage) that shares the name of coverage output.
EXCLUDED_NAMES = ("target", "node_modules", "test-results", "playwright-report", ".DS_Store")
EXCLUDED_ANCHORED = ("coverage", "apps/*/coverage")
LOCAL_FILE = "*.local.*"

CARGO_INSTALL = "cargo install --locked {}"


@dataclass(frozen=True)
class Prerequisite:
    """A tool the scaffolded app's gates need, and how to install it."""

    executable: str
    hint: str


PREREQUISITES = (
    Prerequisite("rustup", "brew install rustup && rustup-init"),
    Prerequisite("node", "brew install node"),
    Prerequisite("pnpm", "brew install pnpm"),
    Prerequisite("lefthook", "brew install lefthook"),
    Prerequisite("cog", "brew install cocogitto"),
    Prerequisite("typos", "brew install typos-cli"),
    Prerequisite("gitleaks", "brew install gitleaks"),
    Prerequisite("cargo-nextest", CARGO_INSTALL.format("cargo-nextest")),
    Prerequisite("cargo-llvm-cov", CARGO_INSTALL.format("cargo-llvm-cov")),
    Prerequisite("cargo-deny", CARGO_INSTALL.format("cargo-deny")),
    Prerequisite("cargo-machete", CARGO_INSTALL.format("cargo-machete")),
    Prerequisite("cargo-sort", CARGO_INSTALL.format("cargo-sort")),
    Prerequisite("cargo-mutants", CARGO_INSTALL.format("cargo-mutants")),
)


class TinderboxError(Exception):
    """A user-facing failure: the message is printed and the exit code is 1."""


@dataclass(frozen=True)
class Names:
    """Every spelling of the new app's name the sentinel table needs."""

    kebab: str
    snake: str
    upper: str
    title: str
    identifier: str

    @classmethod
    def derive(
        cls,
        name: str,
        title: str | None = None,
        identifier: str | None = None,
    ) -> Names:
        """Validate ``name`` (and the overrides) and derive the other spellings."""
        if not NAME_PATTERN.fullmatch(name):
            msg = (
                f"invalid name {name!r}: use lowercase letters, digits and single hyphens, "
                "starting with a letter (for example photo-sorter)"
            )
            raise TinderboxError(msg)
        if title is None:
            title = " ".join(word.capitalize() for word in name.split("-"))
        elif not TITLE_PATTERN.fullmatch(title):
            msg = f"invalid title {title!r}: no quotes, backslashes, <, >, & or control characters"
            raise TinderboxError(msg)
        if identifier is None:
            identifier = f"com.example.{name.replace('-', '')}"
        elif not IDENTIFIER_PATTERN.fullmatch(identifier):
            msg = f"invalid identifier {identifier!r}: use reverse-DNS form such as com.acme.app"
            raise TinderboxError(msg)
        snake = name.replace("-", "_")
        return cls(kebab=name, snake=snake, upper=snake.upper(), title=title, identifier=identifier)

    def rename(self, text: str) -> str:
        """Replace every sentinel form in ``text``, in the design's order."""
        replacements = {
            "com.example.emberly": self.identifier,
            "EMBERLY_": f"{self.upper}_",
            "emberly_": f"{self.snake}_",
            "Emberly": self.title,
            "emberly": self.kebab,
        }
        return SENTINEL.sub(lambda match: replacements[match.group(0)], text)


def _packaged_template() -> Path:
    return Path(str(resources.files("tinderbox") / "template"))


def _checkout_template() -> Path:
    return Path(__file__).resolve().parents[2] / "template"


def find_template() -> Path:
    """Locate the template: the installed package data, else a source checkout's."""
    for candidate in (_packaged_template(), _checkout_template()):
        if candidate.is_dir():
            return candidate
    msg = "the template was not found (neither packaged nor in a source checkout)"
    raise TinderboxError(msg)


def is_excluded(relative: Path) -> bool:
    """Whether a template-relative path is build output that must not be copied."""
    parts = relative.parts
    if any(part in EXCLUDED_NAMES or fnmatch.fnmatchcase(part, LOCAL_FILE) for part in parts):
        return True
    return any(
        fnmatch.fnmatchcase("/".join(parts[: len(pattern.split("/"))]), pattern)
        for pattern in EXCLUDED_ANCHORED
    )


def iter_template_files(template: Path) -> Iterator[Path]:
    """Yield the template's files in a stable order, pruning excluded directories.

    Pruning keeps a source checkout's ``node_modules`` and ``target`` from being walked.
    """
    for directory, subdirs, files in os.walk(template):
        here = Path(directory)
        subdirs[:] = sorted(d for d in subdirs if not is_excluded((here / d).relative_to(template)))
        for name in sorted(files):
            path = here / name
            if not is_excluded(path.relative_to(template)):
                yield path


def _is_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def copy_template(template: Path, dest: Path, names: Names) -> int:
    """Copy ``template`` to ``dest``, renaming the sentinel in paths and text files.

    Returns the number of files written.
    """
    count = 0
    for source in iter_template_files(template):
        relative = source.relative_to(template)
        target = dest.joinpath(*(names.rename(part) for part in relative.parts))
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        if _is_binary(data):
            target.write_bytes(data)
        else:
            target.write_text(names.rename(data.decode("utf-8")), encoding="utf-8", newline="")
        shutil.copymode(source, target)
        count += 1
    return count


def missing_prerequisites() -> list[Prerequisite]:
    """Return the prerequisites not found on PATH."""
    return [tool for tool in PREREQUISITES if shutil.which(tool.executable) is None]


def _write(stream: str, text: str) -> None:
    out = sys.stdout if stream == "out" else sys.stderr
    out.write(f"{text}\n")


def _run(command: list[str], cwd: Path, label: str) -> None:
    """Run one setup step; any failure stops setup with the command's output."""
    _write("out", f"  {label}")
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        msg = f"`{' '.join(command)}` could not run: {error.filename} not found"
        raise TinderboxError(msg) from error
    if result.returncode != 0:
        tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-40:])
        msg = f"`{' '.join(command)}` failed (exit {result.returncode}) in {cwd}\n{tail}"
        raise TinderboxError(msg)


def run_setup(dest: Path) -> None:
    """Initialise git, install dependencies and hooks, and make the first commit."""
    frontend = dest / "apps" / "desktop"
    _run(["git", "init", "-b", "main"], dest, "git init")
    _run(["pnpm", "install", "--frozen-lockfile"], frontend, "pnpm install")
    _run(["lefthook", "install"], dest, "lefthook install")
    _run(["git", "add", "-A"], dest, "git add")
    _run(
        ["git", "commit", "-m", f"chore: scaffold from tinderbox {__version__}"],
        dest,
        "initial commit (runs the pre-commit gate; this can take several minutes)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tinderbox",
        description="Scaffold a Rust + Tauri 2 + Svelte 5 app with strict quality gates.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("name", help="project name, kebab-case (for example photo-sorter)")
    parser.add_argument("--title", help="display title (default: the title-cased name)")
    parser.add_argument(
        "--identifier",
        metavar="REVERSE.DNS",
        help="bundle identifier (default: com.example.<name without hyphens>)",
    )
    parser.add_argument("--dest", type=Path, help="destination directory (default: ./<name>)")
    parser.add_argument(
        "--no-setup",
        action="store_true",
        help="copy the files only: no git init, install, hooks or commit",
    )
    return parser


def _check_destination(dest: Path) -> None:
    if dest.is_file() or (dest.is_dir() and any(dest.iterdir())):
        msg = f"destination {dest} already exists and is not empty"
        raise TinderboxError(msg)


def _scaffold(args: argparse.Namespace) -> None:
    names = Names.derive(args.name, args.title, args.identifier)
    dest: Path = args.dest if args.dest is not None else Path.cwd() / names.kebab
    _check_destination(dest)
    template = find_template()

    missing = missing_prerequisites()
    for tool in missing:
        _write("err", f"missing {tool.executable}: {tool.hint}")
    if missing and not args.no_setup:
        msg = "install the missing tools above, or pass --no-setup to copy the files only"
        raise TinderboxError(msg)

    count = copy_template(template, dest, names)
    _write("out", f"Created {names.title} ({names.kebab}) at {dest} ({count} files)")
    if not args.no_setup:
        run_setup(dest)

    _write("out", "\nNext steps:")
    _write("out", f"  cd {dest}")
    if args.no_setup:
        _write("out", "  git init -b main && (cd apps/desktop && pnpm install) && lefthook install")
    _write("out", "  scripts/gate.sh full        # the whole quality gate")
    _write("out", "  claude                      # CLAUDE.md tells the agent how the project works")


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        _scaffold(args)
    except TinderboxError as error:
        _write("err", f"error: {error}")
        return 1
    return 0
