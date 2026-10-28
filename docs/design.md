# tinderbox design

tinderbox scaffolds a Rust + Tauri 2 + Svelte 5 desktop app that an AI coding agent can work in from the first minute: a working example feature, the strictest deterministic quality gates we know how to run, and a `CLAUDE.md` that tells the agent how the project works. It is macOS-first (signing, install and the platform notes assume a Mac); the Rust core and the frontend are portable.

```sh
uvx --from git+https://github.com/jason-weddington/tinderbox@v0.1.0 tinderbox photo-sorter
```

This file is the spec. Change it in the same commit when reality disagrees.

## Repository layout

```
pyproject.toml            the generator package (hatchling, zero runtime dependencies)
hatch_build.py            build hook: ships template/ as tinderbox/template/, minus build output
src/tinderbox/            the CLI: copy the template, rename the sentinel, run setup
tests/                    generator tests (pytest); tests/fixtures/template exercises every sentinel form
template/                 the template: a complete, working app named "Emberly"
scripts/test-template.sh  scaffold the real template and run its full gate
lefthook.yml, cog.toml, release.sh, _typos.toml, .github/workflows/ci.yml   tinderbox's own tooling
docs/design.md            this file
```

### The template is a live app

`template/` is not a set of `.tpl` files. It is a real app, named with a sentinel, that builds, tests and passes its own gate exactly as checked in. The generator copies it and renames the sentinel. This means the template is always provably green (CI runs its full gate), an agent can work on it like any other app, and there is no template language to learn.

The wheel ships the template as package data (`tinderbox/template/`), built from `template/` with hatch `force-include`. Build output must never ship: no `target/`, `node_modules/`, `test-results/`, coverage output or `.DS_Store`. A test builds the wheel and asserts this.

### The sentinel

The template app is called **Emberly**. The generator replaces these forms, in this order, in file contents and in path names:

| Sentinel | Replaced with | Example for `photo-sorter` |
|---|---|---|
| `com.example.emberly` | the bundle identifier (`--identifier`, default `com.example.<name without hyphens>`) | `com.example.photosorter` |
| `EMBERLY_` | upper snake prefix | `PHOTO_SORTER_` |
| `emberly_` | snake prefix (Rust identifiers) | `photo_sorter_` |
| `Emberly` | the display title (`--title`, default title-cased name) | `Photo Sorter` |
| `emberly` | the kebab name | `photo-sorter` |

Rules for template authors, enforced by a generator test that scaffolds a hyphenated name and runs the generated app's gate:

- A bare lowercase `emberly` appears only where a kebab name is valid (package names, binary names, file names, CSS classes).
- A Rust identifier always uses the snake prefix form (`emberly_core`, `emberly_app_lib`), never a bare `emberly`.
- `Emberly` appears only in user-visible text.
- The sentinel never appears inside another word, and no other word in the template contains it.
- Anything sorted by name keeps the sentinel in a group of its own, so the order holds whatever the app is called: the core dependency in `src-tauri/Cargo.toml` sits in its own blank-line group (the gate runs `cargo sort --grouped`), and Rust `use` lines for the core crate form their own import group (rustfmt sorts within a group only).

The project name must match `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`. The title may not contain quotes, backslashes, `<`, `>`, `&` or control characters (it lands in JSON, TOML, HTML and Rust strings); the identifier must be dotted reverse-DNS (`[A-Za-z0-9-]` segments). The replacement is a single pass, so replacement text is never rescanned for the sentinel.

## The generated app

```
Cargo.toml                    root workspace: crates/* (logic only, no Tauri)
crates/emberly-core/          the logic: model, engine, ports (traits for every effect)
apps/desktop/                 its OWN cargo workspace (own Cargo.lock): Tauri's tree stays out of the core gates
  src-tauri/                  thin adapter: one #[tauri::command] per contract entry, forwarding to the core
  src/                        Svelte 5 + Vite + TypeScript; src/lib/bridge.ts is the only file that imports @tauri-apps
  tests/unit, tests/e2e       Playwright: unit (pure TS) and e2e (the app against the mock bridge)
scripts/gate.sh               the ONE definition of the quality gate (modes: pre-commit, pre-push, full)
scripts/check-*.sh            custom checks, each proven by scripts/selftest-checks.sh
scripts/install.sh            release build, verify signature, install to /Applications
lefthook.yml                  calls gate.sh, nothing else
release.sh, cog.toml          conventional-commit releases; the version is synced across every manifest
docs/design.md                the app's spec and bridge contract (command names, JSON shapes)
docs/quality-gates.md         what each gate catches and why it exists
docs/tauri-design-notes.md    lessons from shipping Tauri 2 apps on macOS
CLAUDE.md, README.md
```

### The example feature

The template ships one small feature that exercises every seam, so an agent can see each pattern working before replacing it: the user picks a folder (dialog plugin); the core scans it through a `Host` port (filesystem reads) and returns a summary (file count and total size per extension, largest first); progress arrives as events from Rust; the result list scrolls. Behind it: a fake `Host` and fake `Clock` in core tests, the mock bridge for browser tests, the contract test between `bridge.ts` and the Rust command signatures, serde round-trip tests pinning the JSON shapes, and a CSP test. It must be small and easy to delete; `CLAUDE.md` says how to replace it.

### Architecture rules (checked, not just written)

- The core crate has no Tauri, no async runtime and no direct I/O: every effect goes through a trait in `ports.rs`, with the real implementation in the app crate and fakes in tests.
- `src-tauri` is a thin adapter: commands forward to the core and map errors; no logic.
- `bridge.ts` is the only frontend file that imports `@tauri-apps/*`. Outside Tauri it falls back to `mock.ts`, which identifies itself (`data-bridge="mock"`) so a test can prove the browser suite never talks to a real backend.
- No `#[allow(...)]` anywhere: exceptions use `#[expect(lint, reason = "...")]`.

`scripts/check-architecture.sh` enforces these (with `cargo tree` for the dependency direction), and `scripts/selftest-checks.sh` plants a violation of each rule in a scratch copy and asserts the check fails.

## Quality gates

`scripts/gate.sh <mode>` is the single definition. lefthook calls it (`pre-commit`, `pre-push`), and an agent harness or CI calls `gate.sh full`, so hooks and agents cannot drift. `gate.sh release` is `full` plus mutation testing over the whole core; the template's `release.sh` runs it before `cog bump`, so mutants run once per release rather than on every push. Hooks check and never fix. A docs-only change (`docs/**`, top-level `*.md`) skips the heavy steps, failing safe: any other file re-enables them.

| Step | pre-commit | pre-push | full | release |
|---|---|---|---|---|
| `cargo fmt --check` and `cargo sort --grouped --check` (both workspaces), `typos`, `gitleaks` | yes | yes | yes | yes |
| check-architecture, selftest-checks | yes | yes | yes | yes |
| `cargo clippy --all-targets --all-features --locked -D warnings` (both workspaces) | yes | yes | yes | yes |
| core tests: `cargo llvm-cov nextest --no-report` (one shared instrumented build) | yes | yes | yes | yes |
| core tests again under `TZ=Pacific/Chatham LANG=de_DE.UTF-8` | yes | yes | yes | yes |
| frontend: `pnpm install --frozen-lockfile`, `svelte-check --fail-on-warnings`, `eslint --max-warnings 0`, unit tests | yes | yes | yes | yes |
| Rust line coverage floor (starts at the measured value, at least 98) | | yes | yes | yes |
| doctests | | yes | yes | yes |
| `cargo mutants` over the whole core, zero survivors | | | | yes |
| `cargo machete`, `cargo deny check` (both workspaces), `pnpm audit --prod` | | yes | yes | yes |
| Playwright e2e with axe accessibility checks, frontend coverage floor, `vite build` | | yes | yes | yes |

Coverage floors only ratchet up; they are literals at the top of `gate.sh`. The frontend floor is whole-number line coverage of `src/` (unit and e2e merged, the mock excluded). `.config/nextest.toml` sets a hard timeout (`slow-timeout = { period = "30s", terminate-after = 4 }`); `.cargo/mutants.toml` names the files mutation testing examines (the whole core). `selftest-checks.sh` also proves the eslint Tauri-import ban and the docs-only skip.

### Lints

The core uses the strictest table we run: `unsafe_code = "forbid"`; `missing_docs`, `unreachable_pub`, `unused_results` deny; clippy `all` and `pedantic` deny, plus `allow_attributes`, `allow_attributes_without_reason`, `unwrap_used`, `expect_used`, `panic`, `todo`, `unimplemented`, `unreachable`, `indexing_slicing`, `string_slice`, `arithmetic_side_effects`, `as_conversions`, `wildcard_enum_match_arm`, `dbg_macro`, `print_stdout`, `print_stderr`, `let_underscore_must_use`, `shadow_unrelated`, `missing_assert_message` and `tests_outside_test_module` deny. The table in `Cargo.toml` is the source of truth and adds the rest of the strict set (`get_unwrap`, the `cast_*` family, `match_wildcard_for_single_variants`, `let_underscore_untyped`, `exit`, `unused_must_use`), with `overflow-checks` on in every profile. `clippy.toml` allows unwrap, expect, panic and indexing in tests and uses `disallowed-methods` to ban `std::process::exit` and `std::env::set_var` / `remove_var`. `src-tauri` is outside the root workspace, so it carries its own copy of the table; any lint that Tauri's generated code trips is relaxed there with a `reason`.

## Versions

A new kit starts on the latest of everything; move to an older version only for a recorded problem (write the reason next to the pin). Checked 2026-10-21:

| Component | Version | Pin |
|---|---|---|
| Rust toolchain (`rust-toolchain.toml`, edition 2024, resolver 3) | 1.99.1 | exact |
| `tauri` / `tauri-build` | 2.12.4 / 2.7.3 | exact (`=`) |
| `@tauri-apps/cli` / `@tauri-apps/api` | 2.12.3 / 2.12.4 | exact; major.minor must match the crate |
| `tauri-plugin-dialog` / `@tauri-apps/plugin-dialog` | 2.8.3 / 2.8.3 | exact |
| `tauri-plugin-single-instance` | 2.5.4 | exact |
| svelte / @sveltejs/vite-plugin-svelte / vite | 5.57.2 / 7.3.1 / 8.3.5 | exact |
| typescript / svelte-check | 6.0.3 and 7.0.2 / 4.7.7 | exact. TypeScript 7's npm package ships no compiler API (its main export is the version string), so typescript-eslint 8.72 (peer `typescript <6.1`) cannot load it. 6.0.3 is `typescript` for eslint; 7.0.2 is installed as `@typescript/native` and svelte-check type-checks with it (`--tsgo`) |
| eslint / typescript-eslint / eslint-plugin-svelte / globals | 10.13.0 / 8.72.0 / 3.23.1 / 17.13.0 | exact |
| @playwright/test / @axe-core/playwright | 1.64.1 / 4.14.0 | exact |
| monocart-coverage-reports | 3.0.0 | exact |
| pnpm (`packageManager`) | 12.14.0 | exact |
| @types/node | 26.6.5 | exact |
| serde / serde_json / thiserror | latest at build time | caret + `Cargo.lock` (the example needs no tempfile or insta: its tests use fakes, and its JSON shapes are pinned by a shared fixture) |

Lockfiles (`Cargo.lock` in both workspaces, `pnpm-lock.yaml`) ship with the template, so a scaffold resolves exactly what CI tested.

## The generator

```
tinderbox <name> [--title TEXT] [--identifier REVERSE.DNS] [--dest DIR] [--no-setup]
```

1. Validate the name; refuse a non-empty destination (default `./<name>`).
2. Check prerequisites and print the install command for each one missing: `rustup`, `pnpm`, `node`, `lefthook`, `cog`, `typos`, `gitleaks`, `cargo-nextest`, `cargo-llvm-cov`, `cargo-deny`, `cargo-machete`, `cargo-sort`, `cargo-mutants`. Missing tools are a warning with `--no-setup` and an error (before anything is written) otherwise.
3. Copy the template, renaming the sentinel in contents and paths. Binary files are copied unchanged.
4. Unless `--no-setup`: `git init -b main`, `pnpm install --frozen-lockfile` (run in `apps/desktop`, where the frontend lives), `lefthook install`, `git add -A`, then an initial commit `chore: scaffold from tinderbox <version>` that runs the pre-commit gate (never `--no-verify`), so a scaffold is proven green on the user's machine before they start. Each step's failure stops setup with that command's output and a non-zero exit; the files stay on disk.
5. Print next steps.

The generator is Python 3.13+ with no runtime dependencies (the standard library only), so `uvx` installs it in seconds.

## tinderbox's own gates

- Python: `ruff check`, `ruff format --check`, `mypy --strict`, `pytest` with a coverage floor that only ratchets up.
- `typos`, `gitleaks`, `cog verify` on commit messages.
- The template: CI (GitHub Actions, macOS) scaffolds a hyphenated name and runs the generated app's `gate.sh full`. `scripts/test-template.sh` does the same locally.

## Publishing

GitHub is the only remote, so every push is public. Two rules follow.

- **No private infrastructure in the repo.** No host names, internal domains, LAN addresses, private URLs or personal-tool references, in files, commit messages or branch names. A maintainer may link a private leak scanner as `release.guard.local.sh` (gitignored, like every `*.local.*` file); when it exists, the pre-push hook runs it with `PUBLIC_GUARD_REMOTE=origin` and the push aborts on any non-zero exit. Without it the step prints a notice and is skipped, so contributors and CI are unaffected.
- **Users install tags, not `main`.** `release.sh` (cocogitto) bumps the version, tags and pushes; the README's install command names a tag.

The generated app inherits the same optional hook: its `release.sh` runs `./release.guard.local.sh` before pushing when the file exists.
