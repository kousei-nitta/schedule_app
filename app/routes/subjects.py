import re
from datetime import time
from typing import Any

from flask import Blueprint, jsonify, request

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_time,
    read_json_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_integer,
    validate_required_string,
    validate_required_time,
)
from app.extensions import db
from app.models.semester import Semester
from app.models.subject import Subject


subjects_bp = Blueprint(
    "subjects",
    __name__,
    url_prefix="/api/subjects",
)


def subject_to_dict(subject: Subject) -> dict[str, Any]:
    """授業をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": subject.id,
        "semester_id": subject.semester_id,
        "subject_name": subject.subject_name,
        "room": subject.room,
        "weekday": subject.weekday,
        "start_time": format_time(subject.start_time),
        "end_time": format_time(subject.end_time),
        "notes": subject.notes,
    }


@subjects_bp.get("")
def get_subjects():
    semester_values = request.args.getlist("semester_id")
    if len(semester_values) > 1:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            {"semester_id": "学期IDは1つだけ指定してください"},
        )

    statement = db.select(Subject)
    if semester_values:
        semester_text = semester_values[0]
        if re.fullmatch(r"[0-9]+", semester_text) is None:
            return api_error_response(
                "validation_error",
                "入力内容に誤りがあります",
                {"semester_id": "学期IDは整数で指定してください"},
            )

        normalized_id = semester_text.lstrip("0")
        if not normalized_id:
            return jsonify([])

        maximum_id = str(MAX_ID)
        if len(normalized_id) > len(maximum_id) or (
            len(normalized_id) == len(maximum_id)
            and normalized_id > maximum_id
        ):
            return jsonify([])
        semester_id = int(normalized_id)
        if semester_id < 1:
            return jsonify([])
        statement = statement.where(Subject.semester_id == semester_id)

    statement = statement.order_by(
        Subject.weekday.asc(),
        Subject.start_time.asc(),
        Subject.id.asc(),
    )
    subjects = db.session.scalars(statement).all()
    return jsonify([subject_to_dict(subject) for subject in subjects])


@subjects_bp.get(f"/<int(max={MAX_ID}):subject_id>")
def get_subject(subject_id: int):
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return api_error_response("not_found", "授業が見つかりません")
    return jsonify(subject_to_dict(subject))


@subjects_bp.post("")
def create_subject():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response
    if payload is None:
        return api_error_response(
            "validation_error",
            "リクエストの本文は、JSONのオブジェクトにしてください",
        )

    fields: dict[str, str] = {}
    allowed_fields = {
        "semester_id",
        "subject_name",
        "room",
        "weekday",
        "start_time",
        "end_time",
        "notes",
    }

    semester_id, semester_id_error = validate_required_integer(
        payload,
        "semester_id",
        "学期IDは必須です",
        "学期IDは整数で指定してください",
    )
    if semester_id_error is not None:
        fields["semester_id"] = semester_id_error
    elif semester_id is not None:
        if not 1 <= semester_id <= MAX_ID:
            fields["semester_id"] = "指定された学期が存在しません"
        else:
            # 範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。
            if db.session.get(Semester, semester_id) is None:
                fields["semester_id"] = "指定された学期が存在しません"

    subject_name, subject_name_error = validate_required_string(
        payload,
        "subject_name",
        "科目名は必須です",
        "科目名は文字列で指定してください",
        strip=True,
        max_length=100,
        length_message="科目名は100文字以内にしてください",
    )
    if subject_name_error is not None:
        fields["subject_name"] = subject_name_error

    room, room_error = validate_optional_string(
        payload,
        "room",
        "教室は文字列で指定してください",
        max_length=100,
        length_message="教室は100文字以内にしてください",
    )
    if room_error is not None:
        fields["room"] = room_error

    weekday, weekday_error = validate_required_integer(
        payload,
        "weekday",
        "曜日は必須です",
        "曜日は0（月曜）〜6（日曜）の整数で指定してください",
        min_value=0,
        max_value=6,
        range_message="曜日は0（月曜）〜6（日曜）の整数で指定してください",
    )
    if weekday_error is not None:
        fields["weekday"] = weekday_error

    start_time, start_time_error = validate_required_time(
        payload,
        "start_time",
        "開始時刻は必須です",
        "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください",
    )
    if start_time_error is not None:
        fields["start_time"] = start_time_error

    end_time, end_time_error = validate_required_time(
        payload,
        "end_time",
        "終了時刻は必須です",
        "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください",
    )
    if end_time_error is not None:
        fields["end_time"] = end_time_error
    elif start_time is not None and end_time is not None and end_time <= start_time:
        fields["end_time"] = "終了時刻は開始時刻より後にしてください"

    notes, notes_error = validate_optional_string(
        payload,
        "notes",
        "詳細・メモは文字列で指定してください",
    )
    if notes_error is not None:
        fields["notes"] = notes_error

    fields.update(validate_allowed_fields(payload, allowed_fields))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    subject = Subject(
        semester_id=semester_id,
        subject_name=subject_name,
        room=room,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        notes=notes,
    )
    db.session.add(subject)
    db.session.commit()
    return jsonify(subject_to_dict(subject)), 201
