import pytest
from typing import Generator

from app.store import Store
from .mocked_redis import MockedRedis


@pytest.fixture(scope="function")
def mocked_redis() -> Generator[MockedRedis, None, None]:
    _redis: MockedRedis = MockedRedis()
    yield _redis
    _redis._clear_storage()


@pytest.fixture
def patched_store(monkeypatch: pytest.MonkeyPatch, mocked_redis: MockedRedis) -> Store:
    storage: Store = Store(host="", port=0)
    monkeypatch.setattr(storage, "_storage", mocked_redis)
    return storage
