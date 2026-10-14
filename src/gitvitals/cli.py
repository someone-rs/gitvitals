"""Command-line interface for gitvitals."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .checks import analyze
from .git import GitError
from .render import render_json, render_markdown, render_terminal
from .scoring import score


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitvitals",
        description="Health check for any git repository: activity, "
                    "contributors, hygiene, and a 0-100 vitality score.",
    )
    parser.add_argument(
        "path", nargs="?", default=".",
        help="path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "--format", choices=["terminal", "json", "markdown"],
        default="terminal", help="output format (default: terminal)",
    )
    parser.add_argument(
        "--no-github", action="store_true",
        help="skip GitHub API lookup even when the remote is on github.com",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="disable colored output",
    )
    parser.add_argument(
        "--version", action="store_true", help="print the version and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    try:
        metrics = analyze(args.path, include_github=not args.no_github)
    except GitError as exc:
        print(f"gitvitals: error: {exc}", file=sys.stderr)
        return 2
    result = score(metrics)
    if args.format == "json":
        print(render_json(metrics, result))
    elif args.format == "markdown":
        print(render_markdown(metrics, result))
    else:
        render_terminal(metrics, result, no_color=args.no_color)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
