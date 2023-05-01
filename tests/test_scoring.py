import pytest
import pickle
from datetime import datetime

from app.store import Store
from app.scoring import (
    get_score,
    get_interests,
)


@pytest.mark.parametrize(
    argnames="phone,email,birthday,gender,first_name,last_name,expected",
    argvalues=[
        ("+79014377767", "aarekuha@gmail.com", "10.10.2000", 1, "Александр", "Рекуха", 5.0),
        ("+79014377767", "", "10.10.2000", 1, "Александр", "Рекуха", 3.5),
        ("+79014377767", "", "", 1, "Александр", "Рекуха", 2.0),
        ("+79014377767", "", "", 1, "", "Рекуха", 1.5),
        ("+79014377767", "", "", 1, "", "", 1.5),
        ("", "", "", None, "", "", 0),
    ]
)
def test_get_score(
    phone: str,
    email: str,
    birthday: str,
    gender: int,
    first_name: str,
    last_name: str,
    expected: float,
    patched_store: Store,
) -> None:
    dt_birthday: datetime | None = None
    if birthday:
         dt_birthday = datetime.strptime(birthday, "%d.%m.%Y")

    score: float = get_score(
        store=patched_store,
        phone=phone,
        email=email,
        birthday=dt_birthday,
        gender=gender,
        first_name=first_name,
        last_name=last_name,
    )
    assert score == expected


def test_get_interests_valid(monkeypatch: pytest.MonkeyPatch, patched_store: Store) -> None:
    with monkeypatch.context() as context:
        context.setattr(patched_store._storage, "get", lambda name: pickle.dumps("10"))
        get_interests(store=patched_store, cid=0)


def test_get_interests_exception(patched_store: Store) -> None:
    with pytest.raises(Exception, match=r"not found"):
        get_interests(store=patched_store, cid=0)
