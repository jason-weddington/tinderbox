"""Opt-in: scaffold the real template and run the generated app's full gate."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent


@pytest.mark.slow
def test_real_template_scaffolds_and_passes_its_full_gate() -> None:
    if os.environ.get("TINDERBOX_SLOW") != "1":
        pytest.skip("set TINDERBOX_SLOW=1 to scaffold the real template and run its full gate")
    if not (REPO / "template").is_dir():
        pytest.skip("template/ is not present on this branch")
    result = subprocess.run(
        [str(REPO / "scripts" / "test-template.sh")],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
