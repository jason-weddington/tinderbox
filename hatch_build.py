"""Hatch build hook: ship template/ as tinderbox/template/, minus build output."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class TemplateHook(BuildHookInterface[BuilderConfig]):
    """Add the template's files to the wheel with the generator's exclusion rules."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        """Force-include every non-excluded template file."""
        root = Path(self.root)
        sys.path.insert(0, str(root / "src"))
        from tinderbox.cli import iter_template_files  # noqa: PLC0415

        template = root / "template"
        for source in iter_template_files(template):
            relative = source.relative_to(template).as_posix()
            build_data["force_include"][str(source)] = f"tinderbox/template/{relative}"
