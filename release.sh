#!/usr/bin/env bash
# Release at a meaningful boundary. Derives the SemVer bump from conventional
# commits (cog), sets the version in pyproject.toml and src/tinderbox/__init__.py
# (cog.toml pre_bump_hooks), writes CHANGELOG.md, tags, and pushes to origin.
# GitHub is the only remote, so a release is public the moment it is pushed.
set -euo pipefail

git diff --quiet && git diff --cached --quiet || { echo "error: working tree is dirty"; exit 1; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "error: not on main"; exit 1; }
git fetch -q origin
git merge-base --is-ancestor origin/main HEAD || { echo "error: behind origin/main"; exit 1; }

# Optional maintainer-local leak scanner; absent for contributors and CI.
if [ -x ./release.guard.local.sh ]; then
    PUBLIC_GUARD_REMOTE=origin ./release.guard.local.sh || { echo "error: public guard failed"; exit 1; }
fi

cog bump --auto
git push origin main --tags
