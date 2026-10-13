from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_date,
    format_time,
    parse_date,
)
from app.extensions import db
from app.models.event import Event


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/api/events",
)


def event_to_dict(event: Event) -> dict[str, Any]:
    """予定をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": event.id,
        "subject_id": event.subject_id,
        "category": event.category,
        "date": format_date(event.date),
        "start_time": format_time(event.start_time),
        "end_time": format_time(event.end_time),
        "title": event.title,
        "room": event.room,
        "employer": event.employer,
        "notes": event.notes,
        "is_generated": event.is_generated,
    }


def read_date_query(
    name: str,
    required_message: str,
    multiple_message: str,
    format_message: str,
) -> tuple[date | None, str | None]:
    """一覧のクエリで指定された、必須の日付を読み取る。

    戻り値は、（日付、エラーメッセージ）の組。
    - 指定がない：(None, required_message)
    - 2回以上の指定：(None, multiple_message)
    - YYYY-MM-DDの実在する日付でない（空文字・前後の空白を含む）：
      (None, format_message)
    - それ以外：(日付, None)
    使うのが予定の一覧だけのため、このファイルに置く。2つ目の利用者が
    出たときに、api_helpers.py へ移すかを決める。
    """
    values = request.args.getlist(name)
    if not values:
        return None, required_message
    if len(values) > 1:
        return None, multiple_message

    parsed_value = parse_date(values[0])
    if parsed_value is None:
        return None, format_message
    return parsed_value, None


@events_bp.get("")
def get_events():
    fields: dict[str, str] = {}

    start_date, start_date_error = read_date_query(
        "start_date",
        "開始日は必須です",
        "開始日は1つだけ指定してください",
        "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if start_date_error is not None:
        fields["start_date"] = start_date_error

    end_date, end_date_error = read_date_query(
        "end_date",
        "終了日は必須です",
        "終了日は1つだけ指定してください",
        "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if end_date_error is not None:
        fields["end_date"] = end_date_error

    # 期間の前後の検査は、開始日と終了日の両方に誤りがないときだけ行う。
    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        fields["end_date"] = "終了日は開始日以降の日付にしてください"

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 予定は、日付を1つだけ持つため、日付が期間内（両端を含む）の予定を返す。
    statement = (
        db.select(Event)
        .where(Event.date >= start_date, Event.date <= end_date)
        .order_by(
            Event.date.asc(),
            Event.start_time.asc(),
            Event.id.asc(),
        )
    )
    events = db.session.scalars(statement).all()
    return jsonify([event_to_dict(event) for event in events])


@events_bp.get(f"/<int(max={MAX_ID}):event_id>")
def get_event(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None:
        return api_error_response("not_found", "予定が見つかりません")
    return jsonify(event_to_dict(event))
