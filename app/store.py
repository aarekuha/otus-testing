import time
import pickle
from typing import Any
from redis import Redis


class Store:
    RETRY_PERIOD_SEC = 0.2
    RETRIES_COUNT = 5

    _host: str
    _port: int
    _database: int
    _storage: Redis | None
    _prefix: str
    _retries_left: int

    def __init__(self, host: str, port: int, database: int = 0, prefix: str = "") -> None:
        self._host = host
        self._port = port
        self._database = database
        self._prefix = prefix
        self._storage = None
        self._retries_left = self.RETRIES_COUNT

    def _connect(self) -> None:
        self._storage = Redis(
            host=self._host,
            port=self._port,
            db=self._database,
        )

    def _make_key(self, key: str) -> str:
        """ Обогащение ключа префиксом, для избежания перетирания данных не текущего сервиса """
        return f"{self._prefix}:{key}"

    def _check_connection(self) -> None:
        """
        Проверка установленного подключения
        :raises Exception: при ошибке подключения установленное количество раз (RETRIES_COUNT)
        """
        if not self._storage:
            self._connect()
            if not self._storage:
                raise Exception("Redis connection error...")

        while not self._storage.ping() and self._retries_left:
            time.sleep(self.RETRY_PERIOD_SEC)
            self._retries_left -= 1
            self._connect()

        if not self._retries_left:
            raise Exception("Redis connection retries expected...")

        self._retries_left = self.RETRIES_COUNT

    def cache_get(self, key: str) -> Any:
        """
        Получение данных из кэша без выбрасывания исключения
        :param key(str): ключ, по которому было ранее сохранено значение
        :returns Any: десериализованное значение, которое удалось получить из кэша
                      Если данные не были найдены, возвращается None
        """
        try:
            return self.get(key=key)
        except:
            return None

    def get(self, key: str) -> Any:
        """
        Получение данных из кэша (выбрасывает исключение, в случае ошибки подключения)
        :param key(str): ключ, по которому было ранее сохранено значение
        :returns Any: десериализованное значение, которое удалось получить из кэша
                      Если данные не были найдены, возвращается None
        """
        self._check_connection()
        prepared_key: str = self._make_key(key=key)
        finded_value: bytes | None = self._storage.get(name=prepared_key)  # type: ignore
        value: Any = None
        if finded_value and finded_value != bytes():
            value = pickle.loads(finded_value)
        else:
            raise Exception("Key not found")
        return value

    def cache_set(self, key: str, value: Any, ttl_sec: int) -> None:
        """
        Сохранение данных в кэш
        :param key(str): ключ, по которому необходимо сохранить значение
        :param value(Any):
        :param ttl(int): время хранения записи в кэше (секунды)
        """
        try:
            self._check_connection()
        except:
            return

        if not key or not value:
            return
        prepared_value: bytes = pickle.dumps(value)
        prepared_key: str = self._make_key(key=key)
        self._storage.set(name=prepared_key, value=prepared_value, ex=ttl_sec)  # type: ignore
