#!/usr/bin/env bash
# Scaffold the real template into a temp dir under a hyphenated name and run
# the generated app's full gate. This is what proves the template is a live,
# green app and that the sentinel survives renaming. CI runs the same script.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -d "$repo/template" ] || { echo "error: $repo/template does not exist"; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
dest="$work/photo-sorter"

# Full setup: git init, pnpm install, lefthook install and the initial commit,
# which itself runs the generated app's pre-commit gate.
(cd "$repo" && uv run tinderbox photo-sorter --dest "$dest")

# No sentinel may survive in the scaffold (text files; build output excluded).
if leftovers="$(grep -rIil --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=target emberly "$dest")"; then
    echo "error: the sentinel survived in:"
    echo "$leftovers"
    exit 1
fi

(cd "$dest" && scripts/gate.sh full)
echo "template OK"
