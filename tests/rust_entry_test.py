from memu import _rust_entry


def test_rust_entry():
    assert _rust_entry() == "Hello from memu!"
