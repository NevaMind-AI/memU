"""Exercise the installed TypeScript extension's lifecycle using Node's native runner."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_pi_recall_extension_lifecycle():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the pi extension")
    version = subprocess.run([node, "--version"], capture_output=True, check=True, text=True)  # noqa: S603
    major, minor = map(int, version.stdout.strip().lstrip("v").split(".")[:2])
    if (major, minor) < (22, 13):
        pytest.skip("Node.js 22.13+ is required for native TypeScript test loading")
    result = subprocess.run(  # noqa: S603
        [node, "--test", str(Path(__file__).with_name("pi_recall_extension.test.mjs"))],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (result.stdout + result.stderr).decode("utf-8", errors="replace")
