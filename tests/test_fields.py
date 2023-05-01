import pytest
import datetime
from typing import Any

from app.api import (
    Field,
    CharField,
    EmailField,
    PhoneField,
    DateField,
    BirthDayField,
    GenderField,
)


@pytest.fixture
def default_field_settings() -> dict:
    return {
        "required": True,
        "nullable": True,
    }


@pytest.mark.parametrize(
    argnames="required,nullable,value,expected",
    argvalues=[
        (True, False, "Value", "Value"),
        (True, False, 123, 123),
        (True, False, 123.0, 123.0),
        (False, False, "Another", "Another"),
        (False, True, None, None),
    ],
)
def test_Field_valid(required: bool, nullable: bool, value: str, expected: Any) -> None:
    assert Field(required=required, nullable=nullable).from_value(value=value) == expected


@pytest.mark.parametrize(
    argnames="required,nullable,value,contains",
    argvalues=[
        (True, False, None, "Not nullable"),
        (True, False, "", ""),
        (False, False, "", ""),
    ],
)
def test_Field_invalid(required: bool, nullable: bool, value: str, contains: str) -> None:
    with pytest.raises(Exception, match=f"{contains}"):
        Field(required=required, nullable=nullable).from_value(value=value)


@pytest.mark.parametrize(
    argnames="FieldClass,value,expected",
    argvalues=[
        (EmailField, "test@mail.ru", "test@mail.ru"),
        (PhoneField, "71234567890", "71234567890"),
        (PhoneField, "+71234567890", "+71234567890"),
        (PhoneField, 71234567890, 71234567890),
        (DateField, "10.10.2000", datetime.datetime(2000, 10, 10)),
        (DateField, "01.01.1900", datetime.datetime(1900, 1, 1)),
        (BirthDayField, "01.01.1990", datetime.datetime(1990, 1, 1)),
        (GenderField, "0", "0"),
        (GenderField, "1", "1"),
    ]
)
def test_CustomField_valid(FieldClass: type, value: str, expected: Any, default_field_settings: dict) -> None:
    assert FieldClass(**default_field_settings).from_value(value=value) == expected


@pytest.mark.parametrize(
    argnames="FieldClass,value,contains",
    argvalues=[
        (CharField, 123, "Invalid.*type"),
        (EmailField, "test@mail.1ru", "Validator"),  # Неправильный домен 1ого уровня (нельзя цифры)
        (PhoneField, "", "Validator"),
        (PhoneField, "7123456789", "Validator"),  # Не хватает одной цифры
        (PhoneField, "-71234567890", "Validator"),  # Первым знаком допускается только плюс
        (DateField, "011.01.1900", "Invalid value"),
        (BirthDayField, "01.01.1950", "Invalid.*age"),
        (GenderField, "3", "Validator"),
    ],
)
def test_CustomField_invalid(FieldClass: type, value: str, contains: str, default_field_settings: dict) -> None:
    with pytest.raises(Exception, match=f"{contains}"):
        FieldClass(**default_field_settings).from_value(value=value)

