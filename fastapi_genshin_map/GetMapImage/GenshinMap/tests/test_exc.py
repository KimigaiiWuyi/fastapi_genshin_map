import pytest


def test_exc() -> None:
    from genshinmap.exc import StatusError

    def _raise() -> None:
        raise StatusError(1, "error")

    with pytest.raises(StatusError) as exc_info:
        _raise()
        exc = exc_info.value
        assert exc.status == 1
        assert exc.message == "err"

        assert str(exc) == "miHoYo API 1:1 err"
        assert repr(exc) == "<StatusError status=1, message=err>"
