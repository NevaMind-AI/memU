"""Generic lazy client pool keyed by profile name.

``MemoryService`` needs three structurally identical caches: one each for the
chat (LLM), vision (VLM) and embedding clients. Each maps a profile name to a
lazily-built, cached client. This pool factors out that duplicated bookkeeping
so adding a fourth capability (e.g. rerank/STT) is a single instantiation rather
than another copy of the get/cache/build dance.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping


class ClientPool[TConfig, TClient]:
    """Lazily build and cache one client per named profile.

    Args:
        profiles: Mapping of profile name -> config object.
        builder: Factory turning a config into a concrete client.
        label: Human-readable capability name used in error messages
            (e.g. ``"llm"``, ``"vlm"``, ``"embedding"``).
        default_profile: Profile name used when ``get()`` is called with ``None``.
    """

    def __init__(
        self,
        *,
        profiles: Mapping[str, TConfig],
        builder: Callable[[TConfig], TClient],
        label: str,
        default_profile: str = "default",
    ) -> None:
        self._profiles = profiles
        self._builder = builder
        self._label = label
        self._default_profile = default_profile
        self._cache: dict[str, TClient] = {}

    def config(self, profile: str | None = None) -> TConfig | None:
        """Return the config for ``profile`` (or the default), if present."""
        return self._profiles.get(profile or self._default_profile)

    def get(self, profile: str | None = None) -> TClient:
        """Return the cached client for ``profile``, building it on first use.

        Raises:
            KeyError: if no profile with that name is configured.
        """
        name = profile or self._default_profile
        cached = self._cache.get(name)
        if cached is not None:
            return cached
        cfg = self._profiles.get(name)
        if cfg is None:
            msg = f"Unknown {self._label} profile '{name}'"
            raise KeyError(msg)
        client = self._builder(cfg)
        self._cache[name] = client
        return client


__all__ = ["ClientPool"]
