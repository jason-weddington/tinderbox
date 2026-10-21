# tinderbox

Python generator (stdlib only, Python 3.13+) that scaffolds Rust + Tauri 2 + Svelte 5 macOS apps by copying a live template app and renaming a sentinel. `docs/design.md` is the spec; change it in the same commit when reality disagrees.

## Layout

- `src/tinderbox/cli.py`: everything: name derivation and sentinel replacement (`Names`), template copy, prerequisite check, setup steps, `main`.
- `hatch_build.py`: ships `template/` inside the wheel, using `iter_template_files` so the wheel and the CLI share one exclusion rule.
- `template/`: the live app "Emberly". It builds, tests and passes its own gate as checked in. Owned separately from the generator.
- `tests/`: pytest. `tests/fixtures/template` is a tiny template using every sentinel form; the real template is only touched by the opt-in slow test.
- `scripts/test-template.sh`: scaffold the real template under a hyphenated name and run its `gate.sh full`.

## Commands

```sh
uv sync
uv run ruff check && uv run ruff format --check
uv run mypy --strict
uv run pytest                                      # 100% coverage floor, slow test deselected
TINDERBOX_SLOW=1 uv run pytest -m slow --no-cov    # real template, full gate
```

`lefthook install` once per clone; `lefthook.yml` is the gate list. `./release.sh` cuts a release (cocogitto bumps `pyproject.toml` and `src/tinderbox/__init__.py`, tags, pushes to origin).

## Rules

- **The template is a live app: keep it green.** Never turn it into `.tpl` files or add template syntax.
- **Sentinel authors:** a bare lowercase `emberly` only where a kebab name is valid; Rust identifiers use `emberly_`; `Emberly` only in user-visible text; the sentinel never appears inside another word. The replacement order is in `docs/design.md`.
- **This repo is public.** No host names, internal domains, LAN IPs, private git URLs or references to personal tooling, in files, commit messages or branch names. Maintainer-local files are named `*.local.*` and are gitignored.
- **Hooks check, never fix.** When `ruff format --check` fails, run `uv run ruff format` and re-commit. Never `--no-verify`.
- **Tests that assert a tool is absent replace PATH** (see `empty_path` and `stub_tools` in `tests/conftest.py`); prepending would let the real tool through.
- Ratchet the coverage floor (`--cov-fail-under` in `pyproject.toml`) up, never down.
- Markdown prose: one line per paragraph, no hard-wrapping.
