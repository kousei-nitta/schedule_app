from datetime import date
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
from app.auth import current_user_id
from app.class_events import build_class_event
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.ownership import get_owned


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


def delete_generated_class_events(semester_id: int, event_date: date) -> None:
    """学期の授業の、その日付の自動生成の予定を削除する（commitしない）。

    休講日の追加で使う。単発の予定（is_generated=False）は削除しない。
    """
    user_id = current_user_id()
    semester_subject_ids = db.select(Subject.id).where(
        Subject.user_id == user_id,
        Subject.semester_id == semester_id,
    )
    db.session.execute(
        db.delete(Event).where(
            Event.user_id == user_id,
            Event.subject_id.in_(semester_subject_ids),
            Event.date == event_date,
            Event.is_generated.is_(True),
        )
    )


def build_missing_class_events(
    semester_id: int,
    event_date: date,
) -> list[Event]:
    """その日付の自動生成の予定がない授業の分だけ、予定を作る（追加しない）。

    休講日の削除で使う。対象は、学期の授業のうち、曜日がその日付の曜日と
    同じ授業。同じ授業・同じ日付の自動生成の予定を2件にしないため、
    すでにある授業は除く。単発の予定（is_generated=False）の有無は見ない。
    """
    user_id = current_user_id()
    subjects = db.session.scalars(
        db.select(Subject)
        .where(
            Subject.user_id == user_id,
            Subject.semester_id == semester_id,
            Subject.weekday == event_date.weekday(),
        )
        .order_by(Subject.id.asc())
    ).all()
    subject_ids_with_event = set(
        db.session.scalars(
            db.select(Event.subject_id).where(
                Event.user_id == user_id,
                Event.subject_id.in_([subject.id for subject in subjects]),
                Event.date == event_date,
                Event.is_generated.is_(True),
            )
        )
    )
    return [
        build_class_event(subject, event_date)
        for subject in subjects
        if subject.id not in subject_ids_with_event
    ]


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

    statement = db.select(Closure).where(
        Closure.user_id == current_user_id()
    )
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
            semester = get_owned(Semester, semester_id)
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
                    Closure.user_id == semester.user_id,
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
        # 休講日の持ち主は、学期の持ち主と同じ（子の行は、親の user_id を
        # 写す）
        user_id=semester.user_id,
        semester_id=semester_id,
        date=closure_date,
        name=name,
    )
    db.session.add(closure)
    # 休講日には授業の予定を作らないため、その日の自動生成の予定を消す。
    delete_generated_class_events(semester_id, closure_date)
    # 休講日の追加と予定の削除を、1回のcommitで保存する。
    db.session.commit()
    return jsonify(closure_to_dict(closure)), 201


@closures_bp.delete(f"/<int(max={MAX_ID}):closure_id>")
def delete_closure(closure_id: int):
    closure = get_owned(Closure, closure_id)
    if closure is None:
        return api_error_response("not_found", "休講日が見つかりません")

    semester_id = closure.semester_id
    closure_date = closure.date
    db.session.delete(closure)
    # 休講日でなくなった日に、その曜日の授業の自動生成の予定を作る。
    events = build_missing_class_events(semester_id, closure_date)
    # 予定は、明示的に追加する（授業との関係だけでは、セッションに入らない）。
    db.session.add_all(events)
    # 休講日の削除と予定の作成を、1回のcommitで保存する。
    db.session.commit()
    return "", 204
