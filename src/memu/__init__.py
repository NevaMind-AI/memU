from memu._core import hello_from_bin


def _rust_entry() -> str:
    return hello_from_bin()
