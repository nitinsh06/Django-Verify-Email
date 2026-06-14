#!/usr/bin/env python
"""Bump the patch component of the project version in pyproject.toml.

Prints the new version to stdout. Used by the PyPI publish workflow to advance
the version after each release, so the next merge to main publishes a new one.
A minor/major release is still done by editing the version in pyproject.toml by
hand; this script only ever increments the patch number.
"""

import pathlib
import re

PYPROJECT = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
VERSION_RE = r'^(version\s*=\s*")(\d+)\.(\d+)\.(\d+)(")'


def main() -> str:
    text = PYPROJECT.read_text()
    match = re.search(VERSION_RE, text, flags=re.MULTILINE)
    if not match:
        raise SystemExit('Could not find a version = "X.Y.Z" line in pyproject.toml')

    major, minor, patch = (int(match.group(i)) for i in (2, 3, 4))
    new_version = f"{major}.{minor}.{patch + 1}"

    text = re.sub(
        VERSION_RE,
        rf"\g<1>{new_version}\g<5>",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(text)
    return new_version


if __name__ == "__main__":
    print(main())
