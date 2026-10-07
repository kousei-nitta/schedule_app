from datetime import time

import pytest

from app.api_helpers import (
    format_time,
    parse_time,
    validate_optional_string,
    validate_required_integer,
    validate_required_string,
    validate_required_time,
)


@pytest.mark.parametrize(
    "value",
    ["00:00", "09:00", "23:59"],
)
def test_parse_time_accepts_valid_times(value):
    assert parse_time(value) == time.fromisoformat(value)


@pytest.mark.parametrize(
    "value",
    [
        "24:00",
        "09:60",
        "9:00",
        "09:0",
        "0900",
        "09:00:00",
        " 09:00",
        "09:00 ",
        "09:00\n",
        "０９：００",
        "ab:cd",
        "",
        900,
        None,
    ],
)
def test_parse_time_rejects_invalid_values(value):
    assert parse_time(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [(time(9, 0), "09:00"), (time(23, 59), "23:59")],
)
def test_format_time(value, expected):
    assert format_time(value) == expected


@pytest.mark.parametrize(
    "payload",
    [{}, {"value": None}, {"value": ""}],
)
def test_validate_required_time_reports_required(payload):
    assert validate_required_time(
        payload,
        "value",
        "必須",
        "形式",
    ) == (None, "必須")


def test_validate_required_time_reports_format_and_converts_value():
    assert validate_required_time(
        {"value": "9:00"},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")
    assert validate_required_time(
        {"value": "09:00"},
        "value",
        "必須",
        "形式",
    ) == (time(9, 0), None)


def test_validate_required_string_keeps_legacy_behavior_by_default():
    assert validate_required_string(
        {"value": "  "},
        "value",
        "必須",
        "型",
    ) == ("  ", None)
    assert validate_required_string(
        {"value": " x "},
        "value",
        "必須",
        "型",
    ) == (" x ", None)


@pytest.mark.parametrize("value", ["", None])
def test_validate_required_string_checks_required(value):
    assert validate_required_string(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (None, "必須")
    assert validate_required_string(
        {},
        "value",
        "必須",
        "型",
    ) == (None, "必須")


def test_validate_required_string_strip_and_length():
    assert validate_required_string(
        {"value": "　x　"},
        "value",
        "必須",
        "型",
        strip=True,
        max_length=1,
        length_message="長さ",
    ) == ("x", None)
    assert validate_required_string(
        {"value": "x" * 100},
        "value",
        "必須",
        "型",
        strip=True,
        max_length=100,
        length_message="長さ",
    ) == ("x" * 100, None)
    assert validate_required_string(
        {"value": "x" * 101},
        "value",
        "必須",
        "型",
        max_length=100,
        length_message="長さ",
    ) == (None, "長さ")
    assert validate_required_string(
        {"value": "　"},
        "value",
        "必須",
        "型",
        strip=True,
    ) == (None, "必須")


def test_validate_required_string_requires_length_message():
    with pytest.raises(ValueError):
        validate_required_string(
            {"value": "x"},
            "value",
            "必須",
            "型",
            max_length=1,
        )


@pytest.mark.parametrize("value", [None, "", "  ", "　"])
def test_validate_optional_string_normalizes_empty_values(value):
    assert validate_optional_string(
        {"value": value},
        "value",
        "型",
    ) == (None, None)
    assert validate_optional_string({}, "value", "型") == (None, None)


def test_validate_optional_string_checks_type_and_length():
    assert validate_optional_string(
        {"value": 123},
        "value",
        "型",
    ) == (None, "型")
    assert validate_optional_string(
        {"value": "　教室　"},
        "value",
        "型",
        max_length=2,
        length_message="長さ",
    ) == ("教室", None)
    assert validate_optional_string(
        {"value": "x" * 101},
        "value",
        "型",
        max_length=100,
        length_message="長さ",
    ) == (None, "長さ")


@pytest.mark.parametrize("value", [True, False, 1.0, "1", [1], {}])
def test_validate_required_integer_rejects_non_integer_types(value):
    assert validate_required_integer(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (None, "型")


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_integer_checks_required(payload):
    assert validate_required_integer(
        payload,
        "value",
        "必須",
        "型",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [-1, 0, 1, 2])
def test_validate_required_integer_checks_inclusive_range(value):
    expected = (value, None) if 0 <= value <= 1 else (None, "範囲")
    assert validate_required_integer(
        {"value": value},
        "value",
        "必須",
        "型",
        min_value=0,
        max_value=1,
        range_message="範囲",
    ) == expected


def test_validate_required_integer_defaults_range_message_to_type_message():
    assert validate_required_integer(
        {"value": -1},
        "value",
        "必須",
        "型",
        min_value=0,
    ) == (None, "型")


@pytest.mark.parametrize("value", [-10, 0, 10])
def test_validate_required_integer_accepts_integers_without_range(value):
    assert validate_required_integer(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (value, None)
