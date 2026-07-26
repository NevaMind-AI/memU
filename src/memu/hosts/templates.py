"""Self-updating instruction templates: server first, last-good next, embedded last.

Every template the SDK feeds an agent — the three self-evolve job templates and
the retrieval skill — ships embedded in the SDK as a Python string. Embedded text
is a floor, not a ceiling: it is frozen at release time, so a wording fix or a
better mining prompt cannot reach an install until that install upgrades. This
module lets the SDK *try* the server's current copy at
``https://memu.pro/sdk/instructions/<name>.txt`` and use it when it is reachable
and well-formed, falling back otherwise.

Two fallback shapes, because the two kinds of template are consumed differently:

* :func:`resolve` — server, then a local **last-good cache**, then embedded. For
  the job templates, which are read on the low-frequency, latency-tolerant
  ``prepare`` run and can be pulled every time. The cache is what makes a
  *transient* server outage a non-event: once an install has seen ``v1``, a day
  where the pull fails still runs ``v1`` rather than regressing to the embedded
  ``v0``.
* :func:`fetch` — server only, no cache. For the retrieval skill, whose durable
  copy is not a cache but the file already installed on disk
  (``…/memu-retrieve/SKILL.md`` or the managed instruction block). Its caller
  refreshes that file *only* on a successful fetch, so the installed copy is the
  de-facto last-good and there is nothing extra to cache.

Everything here is **fail-open and never raises**: a missing network, a non-200,
an oversize body, or a malformed template all collapse to "fall back". The
embedded template is always a correct answer, so the server is pure upside and
never a dependency.

One deliberate limitation, without version numbers (see ADR 0013): the cache
holds *the last text seen*, not *the newest by version*. If the SDK is upgraded
while the server is unreachable, a cached older-remote could momentarily win over
a newer embedded template. It self-heals on the next successful pull — which is
imminent, since a release publishes the matching server copy — and touches at
most a handful of low-frequency jobs. Adding a version field to arbitrate this is
tracked as the open issue in ADR 0013.
"""

from __future__ import annotations

import os
import urllib.request
from collections.abc import Iterable
from pathlib import Path

from memu.hosts.bridging.layout import BASE_DIR

DEFAULT_BASE_URL = "https://memu.pro/sdk/instructions"
"""Where the server keeps the current templates. Override with
``MEMU_TEMPLATE_BASE_URL``; set it empty to switch remote refresh off entirely
(air-gapped installs, offline CI, tests)."""

# Each template's stable id: both the URL stem (``<base>/<name>.txt``) and the
# cache-file stem. Kept next to the `{placeholder}` contract each one must honour,
# so a caller names the template and the required keys are looked up here.
MEMORY_JOB = "memory-job"
SKILL_JOB = "skill-job"
RESOURCE_JOB = "resource-job"
RETRIEVAL_SKILL = "retrieval-skill"

REQUIRED_KEYS: dict[str, frozenset[str]] = {
    MEMORY_JOB: frozenset({"input_path", "track_dir"}),
    SKILL_JOB: frozenset({"input_path", "track_dir", "resource_log"}),
    RESOURCE_JOB: frozenset({"verify_command", "resource_file"}),
    RETRIEVAL_SKILL: frozenset({"binary"}),
}

_TIMEOUT_SECONDS = 4.0
_MAX_BYTES = 64 * 1024


def _base_url() -> str | None:
    """The server root, or ``None`` when remote refresh is switched off.

    Read live rather than captured at import, so a test or an air-gapped install
    can steer it per process; an empty value disables the fetch.
    """
    value = os.environ.get("MEMU_TEMPLATE_BASE_URL", DEFAULT_BASE_URL)
    return value or None


def _cache_dir() -> Path:
    """Where last-good templates live — shared across hosts, since the templates
    are host-agnostic (only ``{binary}`` differs, and it is filled after fetch)."""
    return Path(os.path.expanduser(BASE_DIR)) / "cache" / "instructions"


def _valid(text: str, required_keys: Iterable[str]) -> bool:
    """True only if the template is non-empty, keeps its placeholder contract,
    and ``.format()``-s cleanly.

    The last two are the load-bearing guard: a server-side typo — a dropped
    ``{input_path}``, a stray ``{``, an ``{unknown}`` field — must be rejected
    here, never carried into a job file where ``.format()`` would raise mid-run.
    """
    if not text.strip():
        return False
    if any(("{" + key) not in text for key in required_keys):
        return False
    try:
        text.format(**dict.fromkeys(required_keys, ""))
    except (KeyError, IndexError, ValueError):
        return False
    return True


def _get(url: str) -> str | None:
    """Raw GET of one small UTF-8 asset, fail-open — the shared transport for
    both templates and docs. ``None`` on offline, non-200, oversize, or
    undecodable; content trust is the *caller's* job, applied to what this returns.

    Never raises.
    """
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as resp:  # noqa: S310
            if getattr(resp, "status", 200) != 200:
                return None
            # Read one byte past the cap so an exactly-cap body is still accepted
            # while anything larger is rejected without buffering the whole thing.
            raw: bytes = resp.read(_MAX_BYTES + 1)
    except Exception:
        return None
    if len(raw) > _MAX_BYTES:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def fetch(name: str) -> str | None:
    """The server's current ``name`` template, validated — or ``None``.

    Never raises: offline, non-200, oversize, or malformed all return ``None``,
    which every caller treats as "fall back". A successful, valid fetch also
    refreshes the on-disk last-good cache as a side effect.
    """
    base = _base_url()
    if base is None:
        return None
    text = _get(f"{base}/{name}.txt")
    if text is None or not _valid(text, REQUIRED_KEYS[name]):
        return None
    _write_cache(name, text)
    return text


def _write_cache(name: str, text: str) -> None:
    """Refresh the last-good copy, atomically. Best-effort: a cache we cannot
    write is not fatal, since the fetched text is already in hand for this run."""
    try:
        cache_dir = _cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cache_dir / f"{name}.txt.tmp"
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, cache_dir / f"{name}.txt")
    except OSError:
        pass


def _read_cache(name: str) -> str | None:
    """The last server template we saw and trusted, if it is still valid on disk.

    Re-validated on read: a truncated or hand-edited cache file is treated as
    absent, so a corrupt cache is never worse than no cache.
    """
    try:
        text = (_cache_dir() / f"{name}.txt").read_text(encoding="utf-8")
    except OSError:
        return None
    return text if _valid(text, REQUIRED_KEYS[name]) else None


def resolve(name: str, embedded: str) -> str:
    """The best template available: server, then last-good cache, then ``embedded``.

    For the job templates — low-frequency, latency-tolerant, so pulled on every
    ``prepare``. The embedded copy shipped with the SDK is the guaranteed floor,
    so a total outage degrades to it, never to nothing.
    """
    return fetch(name) or _read_cache(name) or embedded


# --------------------------------------------------------------------------- #
# Host-facing docs (``<binary> docs install|task|uninstall``)
#
# Same server-first / cache / embedded shape as the templates above, but for the
# per-host guides the SDK ships in each host package (``INSTALL.md`` etc). Two
# differences drive the separate code path:
#
#   * **Host-scoped, not host-agnostic.** Each host has its own copy, so the URL
#     and cache carry a ``<host>`` segment: ``<base>/<host>/<filename>`` and
#     ``~/.memu/cache/docs/<host>/<filename>``. (The templates share one flat
#     namespace precisely because they are host-agnostic.)
#   * **Printed, not executed.** ``docs`` prints the guide to a human's terminal;
#     the text is never ``.format()``-ed or fed to an agent. So there is no
#     ``{placeholder}`` contract to enforce — the trust check is just "non-empty,
#     decodes, under the size cap", which ``_get`` already covers. See
#     :func:`_valid_doc`.
#
# Duty cycle is interactive and one-off (like ``install-instruction``), and a user
# may re-run ``docs`` offline, so this keeps the cached :func:`resolve`-style
# fallback rather than the uncached :func:`fetch` shape.
# --------------------------------------------------------------------------- #

DEFAULT_DOCS_BASE_URL = "https://memu.pro/sdk/docs"
"""Server root for the host guides. Override with ``MEMU_DOCS_BASE_URL``; set it
empty to switch remote doc refresh off (air-gapped installs, offline CI, tests).
Kept distinct from ``MEMU_TEMPLATE_BASE_URL`` so the two can be steered — and
disabled — independently."""


def _docs_base_url() -> str | None:
    """The docs server root, or ``None`` when remote doc refresh is off. Read live
    (not captured at import) so a test or air-gapped install can steer it."""
    value = os.environ.get("MEMU_DOCS_BASE_URL", DEFAULT_DOCS_BASE_URL)
    return value or None


def _docs_cache_dir(host: str) -> Path:
    """Last-good docs for one host. Host-scoped, since the guides differ per host."""
    return Path(os.path.expanduser(BASE_DIR)) / "cache" / "docs" / host


def _valid_doc(text: str) -> bool:
    """True if the doc is worth trusting. Unlike a template it is only printed for
    a human, so there is no placeholder contract — non-empty is the whole check.

    TODO(review): consider a light sanity marker (e.g. a leading ``#`` heading) so
    an accidentally-served error page or redirect body is rejected as well.
    """
    return bool(text.strip())


def fetch_doc(host: str, filename: str) -> str | None:
    """The server's current ``<host>/<filename>`` guide, validated — or ``None``.

    Never raises; a valid fetch refreshes the host-scoped last-good cache.
    """
    base = _docs_base_url()
    if base is None:
        return None
    text = _get(f"{base}/{host}/{filename}")
    if text is None or not _valid_doc(text):
        return None
    _write_doc_cache(host, filename, text)
    return text


def _write_doc_cache(host: str, filename: str, text: str) -> None:
    """Refresh a host's last-good doc, atomically. Best-effort (see :func:`_write_cache`)."""
    try:
        cache_dir = _docs_cache_dir(host)
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cache_dir / f"{filename}.tmp"
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, cache_dir / filename)
    except OSError:
        pass


def _read_doc_cache(host: str, filename: str) -> str | None:
    """The last server doc we saw for this host, re-validated on read."""
    try:
        text = (_docs_cache_dir(host) / filename).read_text(encoding="utf-8")
    except OSError:
        return None
    return text if _valid_doc(text) else None


def resolve_doc(host: str, filename: str, embedded: str) -> str:
    """The best guide available: server, then host-scoped cache, then ``embedded``.

    ``embedded`` is the copy shipped in the host package — the guaranteed floor,
    so a total outage degrades to it, never to nothing.
    """
    return fetch_doc(host, filename) or _read_doc_cache(host, filename) or embedded
