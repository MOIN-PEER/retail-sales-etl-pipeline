import pytest

from retail_etl.utils import retry


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    @retry(attempts=3, backoff_seconds=0, exceptions=(OSError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("temporary")
        return "ok"

    assert flaky() == "ok" and calls["n"] == 3


def test_retry_gives_up():
    @retry(attempts=2, backoff_seconds=0, exceptions=(OSError,))
    def always_fails():
        raise OSError("down")

    with pytest.raises(OSError):
        always_fails()
