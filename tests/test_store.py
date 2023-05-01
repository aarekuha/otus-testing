import pytest

from app.store import Store


@pytest.mark.parametrize(
    argnames="key,value",
    argvalues=[
        ("Any name", "any value"),
        ("Any name", "any value another"),
        ("Another name", "another value"),
        ("Bytes value", b"another value"),
        ("Int value", 17),
        ("Float value", 17.7),
    ]
)
def test_set_get(key: str, value: str, patched_store: Store) -> None:
    """Проверка записи и чтения значений. ttl_sec - не проверяется."""
    patched_store.cache_set(key=key, value=value, ttl_sec=0)
    assert patched_store.cache_get(key) == value


def test_exception_get(patched_store: Store) -> None:
    """
    Должно выбрасываться исключение, при попытке получить значение по ключу,
    который отсутствует в БД. Метод: get(key)
    """
    with pytest.raises(Exception, match=r"not found"):
        patched_store.get("Non existent key")


def test_non_exception_cache_get(patched_store: Store) -> None:
    """
    Должно возвращаться пустое значение, при попытке получить значение по ключу,
    который отсутствует в БД. Метод: cache_get(key)
    """
    empty_value: None = patched_store.cache_get("Non existent key")
    assert empty_value is None
