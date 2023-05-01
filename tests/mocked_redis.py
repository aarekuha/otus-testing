from typing import Union


_Value = Union[bytes, float, int, str]
_Key = Union[str, bytes]
_STORAGE: dict[_Key, _Value] = {}


class MockedRedis:
    def __init__(self, *args, **kwargs) -> None:
        args, kwargs

    def set(self, name: _Key, value: _Value, *args, **kwargs) -> None:
        args, kwargs
        _STORAGE[name] = value

    def get(self, name: str, *args, **kwargs) -> _Value:
        args, kwargs
        return _STORAGE.get(name, bytes())

    def ping(self) -> bool:
        return True

    def _clear_storage(self) -> None:
        _STORAGE.clear()
