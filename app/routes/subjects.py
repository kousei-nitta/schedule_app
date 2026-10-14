from datetime import date
from typing import Any

from flask import Blueprint, jsonify

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_time,
    read_id_query,
    read_json_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_integer,
    validate_required_string,
    validate_required_time,
)
from app.class_events import build_class_events, build_class_events_from
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


subjects_bp = Blueprint(
    "subjects",
    __name__,
    url_prefix="/api/subjects",
)

# 授業の編集（PATCH）で受け付ける項目。学期（semester_id）は、変えられない
# （誤った場合は、授業を削除して、正しい学期に登録し直す）。
UPDATE_FIELDS = {
    "subject_name",
    "room",
    "weekday",
    "start_time",
    "end_time",
    "notes",
}
# 授業の登録（POST）で受け付ける項目。
CREATE_FIELDS = UPDATE_FIELDS | {"semester_id"}

END_TIME_ORDER_MESSAGE = "終了時刻は開始時刻より後にしてください"


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


def current_date() -> date:
    """授業全体の編集で、予定を作り直す基準の「今日」を返す。

    サーバー（Flaskを動かしているPC）のローカルの日付。テストで日付を
    固定できるように、関数にしておく（テストでは、monkeypatch で
    置き換える）。
    """
    return date.today()


def validate_subject_values(
    payload: dict[str, Any],
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """授業の項目（学期を除く）を検査し、（値、エラー）の組を返す。

    登録（POST）と編集（PATCH）で、同じ規則で検査するために使う。
    - partial=False（登録）：すべての項目を検査する。必須の項目が
      本文になければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する。含まれない
      項目は、値にもエラーにも入れない（今の値のまま変えない）
    値は、誤りのない項目だけを入れる（キーは、Subjectの列の名前と同じ）。
    開始時刻と終了時刻の前後の検査は、呼び出し側が行う（編集では、
    今の値と組み合わせて比べるため）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "subject_name" in payload:
        subject_name, error = validate_required_string(
            payload,
            "subject_name",
            "科目名は必須です",
            "科目名は文字列で指定してください",
            strip=True,
            max_length=100,
            length_message="科目名は100文字以内にしてください",
        )
        if error is None:
            values["subject_name"] = subject_name
        else:
            errors["subject_name"] = error

    if not partial or "room" in payload:
        room, error = validate_optional_string(
            payload,
            "room",
            "教室は文字列で指定してください",
            max_length=100,
            length_message="教室は100文字以内にしてください",
        )
        if error is None:
            values["room"] = room
        else:
            errors["room"] = error

    if not partial or "weekday" in payload:
        weekday, error = validate_required_integer(
            payload,
            "weekday",
            "曜日は必須です",
            "曜日は0（月曜）〜6（日曜）の整数で指定してください",
            min_value=0,
            max_value=6,
            range_message="曜日は0（月曜）〜6（日曜）の整数で指定してください",
        )
        if error is None:
            values["weekday"] = weekday
        else:
            errors["weekday"] = error

    if not partial or "start_time" in payload:
        start_time, error = validate_required_time(
            payload,
            "start_time",
            "開始時刻は必須です",
            "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください",
        )
        if error is None:
            values["start_time"] = start_time
        else:
            errors["start_time"] = error

    if not partial or "end_time" in payload:
        end_time, error = validate_required_time(
            payload,
            "end_time",
            "終了時刻は必須です",
            "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください",
        )
        if error is None:
            values["end_time"] = end_time
        else:
            errors["end_time"] = error

    if not partial or "notes" in payload:
        notes, error = validate_optional_string(
            payload,
            "notes",
            "詳細・メモは文字列で指定してください",
        )
        if error is None:
            values["notes"] = notes
        else:
            errors["notes"] = error

    return values, errors


def semester_closure_dates(semester_id: int) -> set[date]:
    """学期の休講日の日付を返す（予定を作らない日）。"""
    return set(
        db.session.scalars(
            db.select(Closure.date).where(Closure.semester_id == semester_id)
        )
    )


def delete_generated_events_from(subject_id: int, from_date: date) -> None:
    """授業の、from_date以降の自動生成の予定を削除する（commitしない）。

    授業全体の編集による作り直しで使う。単発の予定（is_generated=False）と、
    from_dateより前の予定は削除しない。
    """
    db.session.execute(
        db.delete(Event).where(
            Event.subject_id == subject_id,
            Event.is_generated.is_(True),
            Event.date >= from_date,
        )
    )


def count_subject_events(subject_id: int) -> int:
    """授業の予定（自動生成・単発とも、過去分を含む）の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Event)
        .where(Event.subject_id == subject_id)
    )


def count_subject_tasks(subject_id: int) -> int:
    """授業の課題の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Task)
        .where(Task.subject_id == subject_id)
    )


@subjects_bp.get("")
def get_subjects():
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

    statement = db.select(Subject)
    if specified:
        if semester_id is None:
            # 範囲外のIDに当たる学期はないため、空の一覧を返す。
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

    response = subject_to_dict(subject)
    # 1件取得のレスポンスにだけ付ける付加情報（DBには保存しない）。
    # 授業を削除すると一緒に削除される件数で、削除の確認に使う。
    response["event_count"] = count_subject_events(subject.id)
    response["task_count"] = count_subject_tasks(subject.id)
    return jsonify(response)


@subjects_bp.post("")
def create_subject():
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

    values, value_errors = validate_subject_values(payload, partial=False)
    fields.update(value_errors)

    start_time = values.get("start_time")
    end_time = values.get("end_time")
    # 前後の検査は、開始時刻と終了時刻の両方に誤りがないときだけ行う。
    if (
        start_time is not None
        and end_time is not None
        and end_time <= start_time
    ):
        fields["end_time"] = END_TIME_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, CREATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 予定を作らない日（学期の休講日）を、先に取得する。
    excluded_dates = semester_closure_dates(semester.id)

    subject = Subject(
        semester_id=semester_id,
        subject_name=values["subject_name"],
        room=values["room"],
        weekday=values["weekday"],
        start_time=start_time,
        end_time=end_time,
        notes=values["notes"],
    )
    db.session.add(subject)
    events = build_class_events(subject, semester, excluded_dates)
    # 予定も、明示的に追加する。授業を先に追加したあとで作った予定は、
    # 授業との関係だけではセッションに入らず、エラーにならないまま
    # 保存されないため。
    db.session.add_all(events)
    # 授業と予定を1回のcommitで保存する。commitの前に例外が起きた場合は、
    # どちらも保存されない。
    db.session.commit()

    response = subject_to_dict(subject)
    # 作成のレスポンスにだけ付ける付加情報（DBには保存しない）。
    response["generated_event_count"] = len(events)
    return jsonify(response), 201


@subjects_bp.patch(f"/<int(max={MAX_ID}):subject_id>")
def update_subject(subject_id: int):
    # 対象の授業がなければ、本文を読む前に404にする。
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return api_error_response("not_found", "授業が見つかりません")

    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response
    # 項目が1つもない本文（{}）は、誤りにする（API共通ルール）。
    if not payload:
        return api_error_response(
            "validation_error",
            "変更する項目を指定してください",
        )

    values, fields = validate_subject_values(payload, partial=True)

    # 前後の検査は、変更後の値どうしで行う。本文に含まれない時刻は、
    # 今の値を使う。本文の時刻に誤りがあれば、検査しない。
    if "start_time" not in fields and "end_time" not in fields:
        start_time = values.get("start_time", subject.start_time)
        end_time = values.get("end_time", subject.end_time)
        if end_time <= start_time:
            fields["end_time"] = END_TIME_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, UPDATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 本文に含まれていた項目だけを、授業に書き込む
    # （values のキーは、Subjectの列の名前と同じ）。
    for field_name, value in values.items():
        setattr(subject, field_name, value)

    # 今日以降の自動生成の予定を、授業の新しい値で作り直す。
    # 変わった項目によらず、毎回作り直す（個別に変更・削除した日も、
    # 設定どおりに戻すため）。単発の予定と、今日より前の予定は変えない。
    today = current_date()
    delete_generated_events_from(subject.id, today)
    events = build_class_events_from(
        subject,
        subject.semester,
        semester_closure_dates(subject.semester_id),
        today,
    )
    # 予定は、明示的に追加する（授業との関係だけでは、セッションに入らない）。
    db.session.add_all(events)
    # 授業の更新と、予定の削除・作成を、1回のcommitで保存する。
    db.session.commit()
    return jsonify(subject_to_dict(subject))


@subjects_bp.delete(f"/<int(max={MAX_ID}):subject_id>")
def delete_subject(subject_id: int):
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return api_error_response("not_found", "授業が見つかりません")

    # 授業に結びつく予定（自動生成・単発とも、過去分を含む）と課題を、
    # 授業より先に、明示的に削除する（「データ設計」の「共通の約束」）。
    # 授業だけを削除すると、予定と課題が、subject_id が NULL の行として残る。
    db.session.execute(db.delete(Event).where(Event.subject_id == subject.id))
    db.session.execute(db.delete(Task).where(Task.subject_id == subject.id))
    db.session.delete(subject)
    # 予定・課題・授業の削除を、1回のcommitで保存する。
    db.session.commit()
    return "", 204
