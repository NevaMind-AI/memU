"""TLS trust for the two stdlib HTTP call sites, and nothing else.

:mod:`memu.events` and :mod:`memu.hosts.templates` both reach a memU server with
``urllib`` rather than the ``httpx`` the rest of the package uses, because both
are fail-open paths that must not depend on the async stack to stay silent about
their own failures. That choice has one sharp edge, and this module is it.

``urllib`` verifies against whatever trust store OpenSSL was pointed at. A
python.org framework build whose bundled ``Install Certificates.command`` was
never run is pointed at *nothing* — ``ssl.get_default_verify_paths()`` reports no
``cafile`` and no ``capath`` — so every HTTPS call raises
``CERTIFICATE_VERIFY_FAILED``. On a fail-open path that is not an error a user
ever sees: events spool forever and never deliver, templates silently fall back
to their embedded copies, and the machine looks identical to one that simply has
nothing to report. ``httpx`` carries :mod:`certifi` and is unaffected, which is
why ``retrieve`` keeps working on exactly the machine where ``report flush``
delivers zero — the divergence that made this take an afternoon to find.

**Why a fallback and not a pin.** Handing ``certifi`` to these two call sites
unconditionally would fix that machine and break the opposite one: a corporate
root CA installed OS-wide is in the system store and is *not* in ``certifi``, so
every user behind a TLS-inspecting proxy would start failing exactly as silently
as this. So the system store still wins wherever one exists, and ``certifi`` only
fills a vacuum. A machine that works today is untouched by construction —
:func:`ssl_context` returns ``None`` there, and ``None`` means "pass no context
at all", which is literally the call these sites made before.
"""

from __future__ import annotations

import functools
import ssl


@functools.cache
def ssl_context() -> ssl.SSLContext | None:
    """A verifying context for ``urlopen``, or ``None`` to use urllib's default.

    Cached because the answer cannot change inside one process and the miss is
    not free: building the fallback parses ``certifi``'s whole PEM bundle, and a
    single :func:`memu.events.flush` may POST :data:`~memu.events.MAX_FLUSH_POSTS`
    times. Call ``ssl_context.cache_clear()`` in a test that steers the paths.

    Never raises. Every failure here returns ``None``, which is today's
    behaviour — this must not become the reason a fail-open path stops being one.
    """
    try:
        paths = ssl.get_default_verify_paths()
        if paths.cafile or paths.capath:
            # A trust store exists. Use it, MITM proxies and corporate CAs and
            # all — this function's job is a vacuum, not a preference.
            return None
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        # Includes `certifi` absent: it arrives as an httpx dependency rather
        # than one this module declares, so treat it as optional and degrade to
        # the unverifiable-but-unchanged behaviour rather than raising here.
        return None


def urlopen_kwargs() -> dict[str, ssl.SSLContext]:
    """``context=`` for ``urlopen``, or an empty dict when there is nothing to say.

    The empty case is the point. On every machine with a working trust store the
    call site passes no ``context`` argument whatsoever, so the fix cannot change
    the behaviour — or the signature every stub in the test suite matches — of
    the installs that were already fine.
    """
    context = ssl_context()
    return {"context": context} if context is not None else {}
