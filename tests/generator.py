"""Utility to generate baseline unit tests for changed files using an LLM."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Iterable, List

from api.providers import OpenAICompatibleProvider, get_provider

__all__ = ["get_changed_files", "write_tests", "main"]


def get_changed_files(base: str) -> List[Path]:
    """Return python files changed relative to ``base``.

    Parameters
    ----------
    base: str
        Git revision to diff against.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", base],
        check=False,
        capture_output=True,
        text=True,
    )
    files = []
    for line in result.stdout.splitlines():
        p = Path(line)
        if p.suffix == ".py" and not str(p).startswith("tests/"):
            files.append(p)

    # include untracked python files
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        check=False,
        capture_output=True,
        text=True,
    )
    for line in untracked.stdout.splitlines():
        p = Path(line)
        if p.suffix == ".py" and not str(p).startswith("tests/"):
            files.append(p)

    # remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in files:
        if f not in seen:
            unique_files.append(f)
            seen.add(f)
    return unique_files


def generate_test_content(path: Path, model: str) -> str:
    """Use the configured LLM provider to generate tests for ``path``."""
    provider = get_provider()
    if isinstance(provider, OpenAICompatibleProvider):  # allow overriding model
        provider.model = model
    content = path.read_text()
    prompt = (
        "You are a coding assistant tasked with writing pytest-style unit tests."
        f"\nGiven the following file located at {path}, write minimal tests that exercise"
        "\nits main behaviour. Ensure the tests are valid Python code.\n\n" + content
    )
    return provider.chat([{"role": "user", "content": prompt}], temperature=0.0)


def write_tests(files: Iterable[Path], output_dir: Path, model: str) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for f in files:
        test_name = output_dir / f"test_{f.stem}.py"
        try:
            content = generate_test_content(f, model)
        except SystemExit as exc:  # missing openai or key
            print(f"Skipping {f}: {exc}")
            continue
        test_name.write_text(content)
        written.append(test_name)
        print(f"Generated {test_name}")
    return written


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base", default="HEAD", help="Git revision to diff against (default: HEAD)"
    )
    parser.add_argument(
        "--output", default="tests/generated", help="Directory to place generated tests"
    )
    parser.add_argument(
        "--model", default="gpt-3.5-turbo", help="OpenAI model to use"
    )
    args = parser.parse_args(argv)

    files = get_changed_files(args.base)
    if not files:
        print("No changed Python files detected.")
        return 0
    write_tests(files, Path(args.output), args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
