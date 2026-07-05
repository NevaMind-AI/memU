"""Allow ``python -m memu`` to invoke the CLI (used by the npm launcher)."""

import sys

from memu.cli import main

sys.exit(main())
