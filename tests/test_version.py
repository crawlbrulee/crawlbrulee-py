"""``__version__`` must match the version pyproject publishes.

The version is declared twice — ``pyproject.toml`` for the wheel, ``_config.py``
for ``__version__`` and the user-agent built from it — with nothing comparing them.
0.8.0 shipped announcing 0.7.0 for exactly this reason. The mismatch is invisible
from inside: every test passes, the wheel builds, and the only evidence is in our
own request logs, attributing traffic to a version that was never released.
"""

from __future__ import annotations

from pathlib import Path

import tomllib

from crawlbrulee import __version__
from crawlbrulee._config import USER_AGENT

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _declared_version() -> str:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def test_dunder_version_matches_pyproject() -> None:
    assert __version__ == _declared_version()


def test_user_agent_reports_the_released_version() -> None:
    assert f"crawlbrulee-python/{_declared_version()} (httpx)" == USER_AGENT
