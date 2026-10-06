import re
from datetime import date
from typing import Any

from flask import Blueprint, abort, jsonify

from app.api_helpers import (
    api_error_response,
    format_date,
    parse_date,
    read_json_object,
    validate_allowed_fields,
    validate_required_string,
)
from app.extensions import db
from app.models.semester import Semester


semesters_bp = Blueprint(
    "semesters",
    __name__,
    url_prefix="/api/semesters",
)


def semester_to_dict(semester: Semester) -> dict[str, Any]:
    """学期をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": semester.id,
        "name": semester.name,
        "start_date": format_date(semester.start_date),
        "end_date": format_date(semester.end_date),
    }


@semesters_bp.get("")
def get_semesters():
    semesters = Semester.query.order_by(
        Semester.start_date.desc(),
        Semester.id.desc(),
    ).all()
    return jsonify([semester_to_dict(semester) for semester in semesters])


@semesters_bp.get("/<int:semester_id>")
def get_semester(semester_id: int):
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        abort(404)
    return jsonify(semester_to_dict(semester))


@semesters_bp.post("")
def create_semester():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response
    assert payload is not None

    fields: dict[str, str] = {}

    name, name_error = validate_required_string(
        payload,
        "name",
        "学期名は必須です",
        "学期名は文字列で指定してください",
    )
    if name_error is not None:
        fields["name"] = name_error
    else:
        assert name is not None
        if len(name) > 50:
            fields["name"] = "学期名は50文字以内にしてください"
        elif re.fullmatch(r"[0-9]{4}年度 (前期|後期)", name) is None:
            # fullmatchにより、前後の改行や余分な文字も含めて形式違反にできる。
            fields["name"] = "学期名は「2026年度 前期」の形式で指定してください"
        elif Semester.query.filter_by(name=name).first() is not None:
            fields["name"] = "同じ名前の学期がすでに登録されています"

    start_date_text, start_date_error = validate_required_string(
        payload,
        "start_date",
        "開始日は必須です",
        "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    start_date_value: date | None = None
    if start_date_error is not None:
        fields["start_date"] = start_date_error
    else:
        assert start_date_text is not None
        start_date_value = parse_date(start_date_text)
        if start_date_value is None:
            fields["start_date"] = (
                "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
            )

    end_date_text, end_date_error = validate_required_string(
        payload,
        "end_date",
        "終了日は必須です",
        "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    end_date_value: date | None = None
    if end_date_error is not None:
        fields["end_date"] = end_date_error
    else:
        assert end_date_text is not None
        end_date_value = parse_date(end_date_text)
        if end_date_value is None:
            fields["end_date"] = (
                "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
            )

    if (
        start_date_value is not None
        and end_date_value is not None
        and end_date_value <= start_date_value
    ):
        fields["end_date"] = "終了日は開始日より後にしてください"

    fields.update(
        validate_allowed_fields(
            payload,
            {"name", "start_date", "end_date"},
        )
    )

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    assert name is not None
    assert start_date_value is not None
    assert end_date_value is not None
    semester = Semester(
        name=name,
        start_date=start_date_value,
        end_date=end_date_value,
    )
    db.session.add(semester)
    db.session.commit()
    return jsonify(semester_to_dict(semester)), 201
