from datetime import date, time, timedelta

import pytest

from app.class_events import (
    EVENT_CATEGORY_CLASS,
    build_class_event,
    build_class_events,
    class_event_dates,
)
from app.models.semester import Semester
from app.models.subject import Subject


# docs/architecture.md の例：2026-04-01（水）〜2026-07-31（金）の月曜日。
MONDAYS_FROM_APRIL_1 = [
    date(2026, 4, 6),
    date(2026, 4, 13),
    date(2026, 4, 20),
    date(2026, 4, 27),
    date(2026, 5, 4),
    date(2026, 5, 11),
    date(2026, 5, 18),
    date(2026, 5, 25),
    date(2026, 6, 1),
    date(2026, 6, 8),
    date(2026, 6, 15),
    date(2026, 6, 22),
    date(2026, 6, 29),
    date(2026, 7, 6),
    date(2026, 7, 13),
    date(2026, 7, 20),
    date(2026, 7, 27),
]


def make_subject(**overrides):
    values = {
        "semester_id": 1,
        "subject_name": "プログラミング基礎",
        "room": "3号館201",
        "weekday": 0,
        "start_time": time(9, 0),
        "end_time": time(10, 0),
        "notes": "前期の授業",
    }
    values.update(overrides)
    return Subject(**values)


def make_semester():
    return Semester(
        id=1,
        name="2026年度 前期",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 7, 31),
    )


def test_dates_match_the_documented_example():
    dates = class_event_dates(date(2026, 4, 1), date(2026, 7, 31), 0, set())

    assert dates == MONDAYS_FROM_APRIL_1


@pytest.mark.parametrize(
    ("weekday", "count", "first", "last"),
    [
        (0, 17, date(2026, 4, 6), date(2026, 7, 27)),
        (1, 17, date(2026, 4, 7), date(2026, 7, 28)),
        (2, 18, date(2026, 4, 1), date(2026, 7, 29)),
        (3, 18, date(2026, 4, 2), date(2026, 7, 30)),
        (4, 18, date(2026, 4, 3), date(2026, 7, 31)),
        (5, 17, date(2026, 4, 4), date(2026, 7, 25)),
        (6, 17, date(2026, 4, 5), date(2026, 7, 26)),
    ],
)
def test_dates_for_each_weekday_are_weekly_and_ascending(
    weekday, count, first, last
):
    dates = class_event_dates(
        date(2026, 4, 1), date(2026, 7, 31), weekday, set()
    )

    assert len(dates) == count
    assert dates[0] == first
    assert dates[-1] == last
    assert all(day.weekday() == weekday for day in dates)
    assert all(
        later - earlier == timedelta(days=7)
        for earlier, later in zip(dates, dates[1:])
    )


def test_start_and_end_dates_are_included():
    # 開始日・終了日とも月曜日。
    dates = class_event_dates(date(2026, 4, 6), date(2026, 4, 20), 0, set())

    assert dates == [date(2026, 4, 6), date(2026, 4, 13), date(2026, 4, 20)]


def test_single_day_period_returns_that_day_when_weekday_matches():
    dates = class_event_dates(date(2026, 4, 6), date(2026, 4, 6), 0, set())

    assert dates == [date(2026, 4, 6)]


def test_period_without_the_weekday_returns_empty_list():
    # 2026-04-01（水）〜2026-04-02（木）に、月曜日はない。
    dates = class_event_dates(date(2026, 4, 1), date(2026, 4, 2), 0, set())

    assert dates == []


def test_excluded_dates_are_removed():
    dates = class_event_dates(
        date(2026, 4, 1),
        date(2026, 7, 31),
        0,
        {date(2026, 5, 4), date(2026, 7, 20)},
    )

    assert len(dates) == 15
    assert date(2026, 5, 4) not in dates
    assert date(2026, 7, 20) not in dates


def test_excluded_dates_of_other_weekdays_or_outside_do_not_matter():
    dates = class_event_dates(
        date(2026, 4, 1),
        date(2026, 7, 31),
        0,
        {date(2026, 5, 5), date(2026, 3, 30), date(2026, 8, 3)},
    )

    assert dates == MONDAYS_FROM_APRIL_1


def test_all_days_excluded_returns_empty_list():
    dates = class_event_dates(
        date(2026, 4, 6),
        date(2026, 4, 12),
        0,
        {date(2026, 4, 6)},
    )

    assert dates == []


def test_excluded_dates_argument_is_required():
    with pytest.raises(TypeError):
        class_event_dates(date(2026, 4, 1), date(2026, 7, 31), 0)


def test_build_class_event_copies_subject_values():
    subject = make_subject()

    event = build_class_event(subject, date(2026, 4, 6))

    assert event.subject is subject
    assert event.category == EVENT_CATEGORY_CLASS == "class"
    assert event.date == date(2026, 4, 6)
    assert event.start_time == time(9, 0)
    assert event.end_time == time(10, 0)
    assert event.title == "プログラミング基礎"
    assert event.room == "3号館201"
    assert event.employer is None
    assert event.notes == "前期の授業"
    assert event.is_generated is True


def test_build_class_event_keeps_null_room_and_notes():
    subject = make_subject(room=None, notes=None)

    event = build_class_event(subject, date(2026, 4, 6))

    assert event.room is None
    assert event.notes is None


def test_build_class_events_uses_semester_period_and_excluded_dates():
    subject = make_subject()

    events = build_class_events(
        subject, make_semester(), {date(2026, 5, 4)}
    )

    assert [event.date for event in events] == [
        day for day in MONDAYS_FROM_APRIL_1 if day != date(2026, 5, 4)
    ]
    assert all(event.subject is subject for event in events)
    assert all(event.is_generated is True for event in events)


def test_build_class_events_returns_empty_list_without_matching_days():
    semester = Semester(
        id=1,
        name="2026年度 前期",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 2),
    )

    assert build_class_events(make_subject(), semester, set()) == []
