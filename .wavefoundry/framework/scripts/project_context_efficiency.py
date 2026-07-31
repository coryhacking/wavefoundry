#!/usr/bin/env python3
"""Project pending context-efficiency generations without recording tool cost.

This entry point is intentionally fail-safe.  Turn-end hooks launch it detached;
the MCP monitor provides the same operation as a quiet-period safety net.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", default=".")
    args, _unknown = parser.parse_known_args(argv)
    try:
        import server_impl

        server_impl.project_pending_context_efficiency_root(
            Path(args.root).resolve(), automatic=True
        )
    except Exception:
        # A turn-end hook must never block or fail the host. Pending durable
        # generations remain available for the MCP quiet-period monitor or the
        # next lifecycle hard boundary.
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
