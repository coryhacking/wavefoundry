from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LintContext:
    root: Path

    @property
    def docs_root(self) -> Path:
        return self.root / "docs"


def build_context() -> LintContext:
    env_root = os.environ.get("PROJECT_ROOT")
    root = Path(env_root).resolve() if env_root else Path.cwd().resolve()
    return LintContext(root=root)