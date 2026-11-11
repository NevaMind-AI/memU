"""Ask Hermes to reload the active profile's plugins in its running gateway."""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path


def main() -> None:
    with contextlib.redirect_stdout(sys.stderr):
        import hermes_cli  # type: ignore[import-not-found]

        sys.path.insert(0, str(Path(hermes_cli.__file__).resolve().parent.parent))
        # Hermes owns source/dependency activation and any managed-Python relaunch.
        import hermes_bootstrap  # type: ignore[import-not-found]  # noqa: F401
        from hermes_cli.plugins_activation import reload_running_gateway  # type: ignore[import-not-found]

        answer = reload_running_gateway()
    print(json.dumps(answer))


if __name__ == "__main__":
    main()
