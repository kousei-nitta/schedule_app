from typing import Any

from flask import Blueprint, jsonify

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_date,
    read_id_query,
    read_json_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_date,
    validate_required_integer,
)
from app.extensions import db
from app.models.closure import Closure
from app.models.semester import Semester


closures_bp = Blueprint(
    "closures",
    __name__,
    url_prefix="/api/closures",
)


def closure_to_dict(closure: Closure) -> dict[str, Any]:
    """休講日をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": closure.id,
        "semester_id": closure.semester_id,
        "date": format_date(closure.date),
        "name": closure.name,
    }


@closures_bp.get("")
def get_closures():
    specified, semester_id, query_error = read_id_query(
        "semester_id",
        "学期IDは1つだけ指定してください",
        "学期IDは整数で指定してください",
    )
    if query_error is not None:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            {"semester_id": query_error},
        )

    statement = db.select(Closure)
    if specified:
        if semester_id is None:
            return jsonify([])
        statement = statement.where(Closure.semester_id == semester_id)

    statement = statement.order_by(Closure.date.asc(), Closure.id.asc())
    closures = db.session.scalars(statement).all()
    return jsonify([closure_to_dict(closure) for closure in closures])


@closures_bp.post("")
def create_closure():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    fields: dict[str, str] = {}
    semester: Semester | None = None
    semester_id, semester_id_error = validate_required_integer(
        payload,
        "semester_id",
        "学期IDは必須です",
        "学期IDは整数で指定してください",
    )
    if semester_id_error is not None:
        fields["semester_id"] = semester_id_error
    elif semester_id is not None:
        # 範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。
        if not 1 <= semester_id <= MAX_ID:
            fields["semester_id"] = "指定された学期が存在しません"
        else:
            semester = db.session.get(Semester, semester_id)
            if semester is None:
                fields["semester_id"] = "指定された学期が存在しません"

    closure_date, date_error = validate_required_date(
        payload,
        "date",
        "日付は必須です",
        "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if date_error is not None:
        fields["date"] = date_error
    elif semester is not None:
        # 学期の期間と重複の検査は、semester_idとdateの両方に
        # 誤りがないときだけ行う。
        if not semester.start_date <= closure_date <= semester.end_date:
            fields["date"] = "休講日は、学期の期間内の日付にしてください"
        else:
            duplicate = db.session.scalars(
                db.select(Closure).where(
                    Closure.semester_id == semester.id,
                    Closure.date == closure_date,
                )
            ).first()
            if duplicate is not None:
                fields["date"] = "同じ日付の休講日がすでに登録されています"

    name, name_error = validate_optional_string(
        payload,
        "name",
        "名前は文字列で指定してください",
        max_length=100,
        length_message="名前は100文字以内にしてください",
    )
    if name_error is not None:
        fields["name"] = name_error

    fields.update(
        validate_allowed_fields(payload, {"semester_id", "date", "name"})
    )

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    closure = Closure(
        semester_id=semester_id,
        date=closure_date,
        name=name,
    )
    db.session.add(closure)
    db.session.commit()
    return jsonify(closure_to_dict(closure)), 201


@closures_bp.delete(f"/<int(max={MAX_ID}):closure_id>")
def delete_closure(closure_id: int):
    closure = db.session.get(Closure, closure_id)
    if closure is None:
        return api_error_response("not_found", "休講日が見つかりません")

    db.session.delete(closure)
    db.session.commit()
    return "", 204
