"""Executed by Hermes's Python, not imported by the memU service."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sys
from pathlib import Path


def main() -> None:
    # Keep host startup diagnostics off the JSON response channel.
    with contextlib.redirect_stdout(sys.stderr):
        import hermes_cli  # type: ignore[import-not-found]

        # Editable Hermes upgrades may leave top-level modules out of the venv finder.
        # Resolve its own package root, as the Hermes CLI bootstrap does.
        root = Path(hermes_cli.__file__).resolve().parent.parent
        sys.path.insert(0, str(root))
        if importlib.util.find_spec("pm") is not None:
            from pm.environments import activate_dependencies  # type: ignore[import-not-found]

            activate_dependencies(root)
        from agent.auxiliary_client import call_llm  # type: ignore[import-not-found]
        from hermes_cli.config import load_config  # type: ignore[import-not-found]
        from hermes_cli.runtime_provider import resolve_runtime_provider  # type: ignore[import-not-found]

        config = load_config()
        settings = config.get("model") or {}
        model = settings if isinstance(settings, str) else settings.get("default") or settings.get("model")
        provider = settings.get("provider") if isinstance(settings, dict) else None
        runtime = resolve_runtime_provider(requested=provider, target_model=model)
        # A file survives Hermes re-exec and import-time stdin handling.
        instruction = Path(sys.argv[1]).read_text(encoding="utf-8")
        response = call_llm(
            provider=runtime.get("provider"),
            model=model,
            base_url=runtime.get("base_url"),
            api_key=runtime.get("api_key"),
            api_mode=runtime.get("api_mode"),
            main_runtime=runtime,
            messages=[
                {
                    "role": "system",
                    "content": "Extract a memory search query. Return only a JSON object with a query string. Do not use tools.",
                },
                {"role": "user", "content": instruction},
            ],
            tools=None,
            max_tokens=256,
            timeout=12,
        )
        value = json.loads(response.choices[0].message.content)
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
