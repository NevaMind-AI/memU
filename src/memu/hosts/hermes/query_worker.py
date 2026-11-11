"""Executed by Hermes's Python, not imported by the memU service."""

from __future__ import annotations

import contextlib
import json
import sys


def main() -> None:
    instruction = sys.stdin.buffer.read().decode("utf-8")
    # Keep host startup diagnostics off the JSON response channel.
    with contextlib.redirect_stdout(sys.stderr):
        from agent.auxiliary_client import call_llm  # type: ignore[import-not-found]
        from hermes_cli.config import load_config  # type: ignore[import-not-found]
        from hermes_cli.runtime_provider import resolve_runtime_provider  # type: ignore[import-not-found]

        config = load_config()
        settings = config.get("model") or {}
        model = settings if isinstance(settings, str) else settings.get("default") or settings.get("model")
        provider = settings.get("provider") if isinstance(settings, dict) else None
        runtime = resolve_runtime_provider(requested=provider, target_model=model)
        response = call_llm(
            provider=runtime.get("provider"),
            model=model,
            base_url=runtime.get("base_url"),
            api_key=runtime.get("api_key"),
            api_mode=runtime.get("api_mode"),
            main_runtime=runtime,
            messages=[{"role": "user", "content": instruction}],
            tools=None,
            max_tokens=256,
            timeout=12,
        )
        value = json.loads(response.choices[0].message.content)
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
