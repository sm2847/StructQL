"""
Placeholder test so CI is green from the very first commit.

Delete this once real tests exist (Milestone M1 onwards) - a test suite
that never had a failing CI run is a good signal, but only if it's backed
by real tests, not just this file.
"""


def test_package_imports() -> None:
    import structql

    assert structql.__version__ == "0.1.0"
