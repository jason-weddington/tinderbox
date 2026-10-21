# tinderbox

A macOS-first starter kit for Rust + Tauri 2 + Svelte 5 desktop apps, built so an AI coding agent can work in the project from the first minute: a small working example feature, strict deterministic quality gates, and a `CLAUDE.md` that explains how the project works.

The Rust core and the frontend are portable; signing, install and the platform notes assume a Mac.

## Quick start

```sh
uvx --from git+https://github.com/jason-weddington/tinderbox@v0.1.0 tinderbox photo-sorter
```

This creates `./photo-sorter`, initialises git, installs the frontend dependencies and git hooks, and makes an initial commit that runs the pre-commit gate, so you start from a scaffold that is proven green on your machine. Options:

```
tinderbox <name> [--title TEXT] [--identifier REVERSE.DNS] [--dest DIR] [--no-setup]
```

The name is kebab-case. The display title defaults to the title-cased name (`Photo Sorter`) and the bundle identifier to `com.example.<name without hyphens>`. `--no-setup` copies the files and stops.

## Prerequisites

The generator needs Python 3.13+ (via `uv`). The generated app's gates need these tools, and `tinderbox` prints an install command for each one that is missing:

```sh
brew install rustup && rustup-init
brew install node pnpm lefthook cocogitto typos-cli gitleaks
cargo install --locked cargo-nextest cargo-llvm-cov cargo-deny cargo-machete cargo-sort cargo-mutants
```

## What you get

- A Cargo workspace with a logic-only core crate (every effect behind a trait), a Tauri 2 adapter in its own workspace, and a Svelte 5 + TypeScript frontend that reaches Tauri through a single bridge file with a browser mock.
- One small example feature that exercises every seam, easy to delete.
- `scripts/gate.sh`, the single definition of the quality gate: formatting, clippy with a strict lint table, tests with coverage floors, mutation testing, dependency audits, accessibility checks and architecture checks. Git hooks and CI call the same script.
- Conventional-commit releases with cocogitto.
- `CLAUDE.md` and design docs written for agents.

`docs/design.md` is the full spec.

## Developing tinderbox

`template/` is a real, working app named "Emberly"; the generator copies it and renames the sentinel. Keep it green.

```sh
uv sync
uv run ruff check && uv run ruff format --check
uv run mypy --strict
uv run pytest                          # 100% coverage floor
TINDERBOX_SLOW=1 uv run pytest -m slow --no-cov   # scaffold the real template, run its full gate
scripts/test-template.sh               # the same, as a script
```

`lefthook install` once per clone. Hooks check and never fix.

## License

MIT, see `LICENSE`.
