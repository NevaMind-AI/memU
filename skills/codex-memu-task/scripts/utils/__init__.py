"""Helpers for the prepare_* entry scripts.

Kept as a sibling package of the entry scripts so the whole `skills/` folder is
self-contained: running `python .../skills/scripts/prepare_jobs.py` puts that
script's directory on `sys.path`, which makes `import lib.*` resolve no matter
where the folder is placed. No install step, no PYTHONPATH tweaking.
"""
