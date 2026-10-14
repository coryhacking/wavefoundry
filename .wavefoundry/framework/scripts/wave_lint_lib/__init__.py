"""Public lint entry point; importing constants does not load the CLI graph."""


def main() -> int:
    from .cli import main as cli_main

    return cli_main()


__all__ = ["main"]
