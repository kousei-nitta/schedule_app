from datetime import date, time

import pytest
from flask import Flask

from app.api_helpers import (
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
    contains_unusable_character,
    format_time,
    parse_time,
    read_id_query,
    validate_optional_string,
    validate_required_integer,
    validate_required_date,
    validate_required_string,
    validate_required_time,
)


def test_unusable_character_message_constant():
    assert UNUSABLE_CHARACTER_MESSAGE == "使用できない文字が含まれています"


@pytest.mark.parametrize(
    "value",
    ["\ud800", "\udbff", "\udc00", "\udfff", "a\ud800b"],
)
def test_contains_unusable_character_detects_lone_surrogates(value):
    assert contains_unusable_character(value) is True


@pytest.mark.parametrize(
    "value",
    ["", "abc", "日本語", "😀", "\ud7ff", "\ue000"],
)
def test_contains_unusable_character_accepts_other_text(value):
    assert contains_unusable_character(value) is False


@pytest.mark.parametrize(
    "value",
    ["\ud800", "科目\udc00", " \ud800 "],
)
def test_validate_required_string_rejects_unusable_characters(value):
    assert validate_required_string(
        {"value": value},
        "value",
        "必須",
        "型",
        strip=True,
        max_length=100,
        length_message="長さ",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


def test_validate_required_string_rejects_unusable_characters_by_default():
    assert validate_required_string(
        {"value": "\ud800"},
        "value",
        "必須",
        "型",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


@pytest.mark.parametrize(
    "value",
    ["\ud800", "  \udfff  ", "メモ\ud800"],
)
def test_validate_optional_string_rejects_unusable_characters(value):
    assert validate_optional_string(
        {"value": value},
        "value",
        "型",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


@pytest.mark.parametrize("value", ["\ud800", "09:00\udc00"])
def test_validate_required_time_rejects_unusable_characters(value):
    assert validate_required_time(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


def test_surrogate_pairs_count_as_one_character():
    assert validate_required_string(
        {"value": "😀😀"},
        "value",
        "必須",
        "型",
        max_length=2,
        length_message="長さ",
    ) == ("😀😀", None)


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


@pytest.mark.parametrize("value", [900, True])
def test_validate_required_time_reports_non_string_as_format_error(value):
    assert validate_required_time(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


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


@pytest.mark.parametrize(
    "payload",
    [{}, {"value": None}, {"value": ""}],
)
def test_validate_required_string_checks_required(payload):
    assert validate_required_string(
        payload,
        "value",
        "必須",
        "型",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [123, True, []])
def test_validate_required_string_reports_type_error(value):
    assert validate_required_string(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (None, "型")


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


@pytest.mark.parametrize(
    "payload",
    [{}, {"value": None}, {"value": ""}, {"value": "  "}, {"value": "　"}],
)
def test_validate_optional_string_normalizes_empty_values(payload):
    assert validate_optional_string(
        payload,
        "value",
        "型",
    ) == (None, None)


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-04-01", date(2026, 4, 1)),
        ("2028-02-29", date(2028, 2, 29)),
    ],
)
def test_validate_required_date_converts_value(value, expected):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (expected, None)


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_date_reports_required(payload):
    assert validate_required_date(
        payload,
        "value",
        "必須",
        "形式",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [20260401, True])
def test_validate_required_date_reports_non_string_as_format_error(value):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


@pytest.mark.parametrize(
    "value",
    [
        "2026-4-1",
        "2026/04/01",
        "20260401",
        "2026-02-30",
        " 2026-04-01",
        "2026-04-01 ",
        "２０２６-04-01",
    ],
)
def test_validate_required_date_reports_format_error(value):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


@pytest.mark.parametrize("value", ["\ud800", "2026-04-01\udc00"])
def test_validate_required_date_rejects_unusable_characters(value):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


def read_semester_id_query(query_string):
    # read_id_queryは、要求のクエリを読むため、DBを使わない最小の
    # Flaskアプリで、要求の中の状態を作って呼ぶ。
    request_app = Flask(__name__)
    with request_app.test_request_context(query_string=query_string):
        return read_id_query("semester_id", "複数", "形式")


@pytest.mark.parametrize(
    "query_string",
    [{}, {"foo": "bar"}],
)
def test_read_id_query_without_value_is_not_specified(query_string):
    assert read_semester_id_query(query_string) == (False, None, None)


def test_read_id_query_rejects_repeated_values():
    assert read_semester_id_query(
        {"semester_id": ["1", "2"]}
    ) == (True, None, "複数")


@pytest.mark.parametrize(
    "value",
    ["", "abc", "-1", "1.5", "１", " 1", "1 "],
)
def test_read_id_query_rejects_non_digit_text(value):
    assert read_semester_id_query(
        {"semester_id": value}
    ) == (True, None, "形式")


@pytest.mark.parametrize(
    "value",
    ["0", "000", str(MAX_ID + 1), "9" * 5000],
)
def test_read_id_query_out_of_range_matches_nothing(value):
    assert read_semester_id_query(
        {"semester_id": value}
    ) == (True, None, None)


@pytest.mark.parametrize(
    ("value", "expected_id"),
    [("1", 1), ("001", 1), (str(MAX_ID), MAX_ID)],
)
def test_read_id_query_returns_id(value, expected_id):
    assert read_semester_id_query(
        {"semester_id": value}
    ) == (True, expected_id, None)
