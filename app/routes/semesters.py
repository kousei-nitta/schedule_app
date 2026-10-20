import re
from datetime import date
from typing import Any

from flask import Blueprint, jsonify

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_date,
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_required_date,
    validate_required_string,
)
from app.class_events import build_class_event, class_event_dates
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject


semesters_bp = Blueprint(
    "semesters",
    __name__,
    url_prefix="/api/semesters",
)

# 学期の登録（POST）と編集（PATCH）で受け付ける項目。
SEMESTER_FIELDS = {"name", "start_date", "end_date"}

END_DATE_ORDER_MESSAGE = "終了日は開始日より後にしてください"
SEMESTER_HAS_SUBJECTS_MESSAGE = (
    "授業が登録されている学期は削除できません。"
    "先に、授業をすべて削除してください"
)


def semester_to_dict(semester: Semester) -> dict[str, Any]:
    """学期をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": semester.id,
        "name": semester.name,
        "start_date": format_date(semester.start_date),
        "end_date": format_date(semester.end_date),
    }


def is_duplicate_name(name: str, current_id: int | None) -> bool:
    """同じ名前の、ほかの学期があるか（完全一致で比べる）。

    current_id は、編集する学期のID（自分自身は除く）。登録では None。
    """
    statement = db.select(Semester.id).where(Semester.name == name)
    if current_id is not None:
        statement = statement.where(Semester.id != current_id)
    return db.session.scalar(statement) is not None


def validate_semester_values(
    payload: dict[str, Any],
    *,
    partial: bool,
    current_id: int | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """学期の項目を検査し、（値、エラー）の組を返す。

    登録（POST）と編集（PATCH）で、同じ規則で検査するために使う。
    - partial=False（登録）：すべての項目を検査する。必須の項目が
      本文になければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する。含まれない
      項目は、値にもエラーにも入れない（今の値のまま変えない）
    current_id は、同じ名前の検査で除く学期のID（編集する学期。登録では
    None）。値は、誤りのない項目だけを入れる（キーは、Semesterの列の名前と
    同じ）。開始日と終了日の前後の検査は、呼び出し側が行う（編集では、
    今の値と組み合わせて比べるため）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "name" in payload:
        name, error = validate_required_string(
            payload,
            "name",
            "学期名は必須です",
            "学期名は文字列で指定してください",
            max_length=50,
            length_message="学期名は50文字以内にしてください",
        )
        if error is None and re.fullmatch(
            r"[0-9]{4}年度 (前期|後期)", name
        ) is None:
            # fullmatchにより、前後の改行や余分な文字も含めて形式違反にできる。
            error = "学期名は「2026年度 前期」の形式で指定してください"
        if error is None and is_duplicate_name(name, current_id):
            error = "同じ名前の学期がすでに登録されています"
        if error is None:
            values["name"] = name
        else:
            errors["name"] = error

    if not partial or "start_date" in payload:
        start_date, error = validate_required_date(
            payload,
            "start_date",
            "開始日は必須です",
            "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
        )
        if error is None:
            values["start_date"] = start_date
        else:
            errors["start_date"] = error

    if not partial or "end_date" in payload:
        end_date, error = validate_required_date(
            payload,
            "end_date",
            "終了日は必須です",
            "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
        )
        if error is None:
            values["end_date"] = end_date
        else:
            errors["end_date"] = error

    return values, errors


def count_semester_subjects(semester_id: int) -> int:
    """学期の授業の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Subject)
        .where(Subject.semester_id == semester_id)
    )


def count_semester_closures(semester_id: int) -> int:
    """学期の休講日の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Closure)
        .where(Closure.semester_id == semester_id)
    )


def sync_period_change(
    semester: Semester,
    previous_start_date: date,
    previous_end_date: date,
) -> None:
    """学期の期間の変更を、授業の予定と休講日に反映する（commitしない）。

    期間の変更は、「どの日が学期か」の訂正のため、休講日の同期と同じく、
    今日より前の日にも適用する。
    - 新しい期間の外になった日の、自動生成の予定（is_generated=True）と、
      休講日を削除する
    - 新しく期間に入った日（前の期間の外の日）に、学期の授業の予定を作る
      （休講日を除く）。自動生成の予定は、学期の期間の中にだけあるため、
      作る日には、同じ授業の自動生成の予定はない
    両方の期間に入る日の予定（個別に変更・削除したものを含む）と、単発の
    予定（is_generated=False）は、変えない。
    """
    start_date = semester.start_date
    end_date = semester.end_date

    # 新しい期間の外になった日の、自動生成の予定と休講日を削除する。
    semester_subject_ids = db.select(Subject.id).where(
        Subject.semester_id == semester.id
    )
    db.session.execute(
        db.delete(Event).where(
            Event.subject_id.in_(semester_subject_ids),
            Event.is_generated.is_(True),
            db.or_(Event.date < start_date, Event.date > end_date),
        )
    )
    db.session.execute(
        db.delete(Closure).where(
            Closure.semester_id == semester.id,
            db.or_(Closure.date < start_date, Closure.date > end_date),
        )
    )

    # 新しく期間に入った日に、学期の授業の予定を作る。
    # 予定を作らない日は、新しい期間の中に残った休講日。
    excluded_dates = set(
        db.session.scalars(
            db.select(Closure.date).where(Closure.semester_id == semester.id)
        )
    )
    subjects = db.session.scalars(
        db.select(Subject)
        .where(Subject.semester_id == semester.id)
        .order_by(Subject.id.asc())
    ).all()
    events = []
    for subject in subjects:
        dates = class_event_dates(
            start_date,
            end_date,
            subject.weekday,
            excluded_dates,
        )
        for event_date in dates:
            # 前の期間の中の日は、予定がすでにある（または、個別に削除
            # した）ため、作らない。
            if previous_start_date <= event_date <= previous_end_date:
                continue
            events.append(build_class_event(subject, event_date))
    # 予定は、明示的に追加する（授業との関係だけでは、セッションに入らない）。
    db.session.add_all(events)


@semesters_bp.get("")
def get_semesters():
    semesters = db.session.scalars(
        db.select(Semester).order_by(
            Semester.start_date.desc(),
            Semester.id.desc(),
        )
    ).all()
    return jsonify([semester_to_dict(semester) for semester in semesters])


@semesters_bp.get(f"/<int(max={MAX_ID}):semester_id>")
def get_semester(semester_id: int):
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        return api_error_response("not_found", "学期が見つかりません")

    response = semester_to_dict(semester)
    # 1件取得のレスポンスにだけ付ける付加情報（DBには保存しない）。
    # 学期の削除の確認に使う（授業があれば削除できない。休講日は、
    # 学期と一緒に削除される）。
    response["subject_count"] = count_semester_subjects(semester.id)
    response["closure_count"] = count_semester_closures(semester.id)
    return jsonify(response)


@semesters_bp.post("")
def create_semester():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    values, fields = validate_semester_values(
        payload,
        partial=False,
        current_id=None,
    )

    start_date = values.get("start_date")
    end_date = values.get("end_date")
    # 前後の検査は、開始日と終了日の両方に誤りがないときだけ行う。
    if (
        start_date is not None
        and end_date is not None
        and end_date <= start_date
    ):
        fields["end_date"] = END_DATE_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, SEMESTER_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    semester = Semester(
        name=values["name"],
        start_date=start_date,
        end_date=end_date,
    )
    db.session.add(semester)
    db.session.commit()
    return jsonify(semester_to_dict(semester)), 201


@semesters_bp.patch(f"/<int(max={MAX_ID}):semester_id>")
def update_semester(semester_id: int):
    # 対象の学期がなければ、本文を読む前に404にする。
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        return api_error_response("not_found", "学期が見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_semester_values(
        payload,
        partial=True,
        current_id=semester.id,
    )

    # 前後の検査は、変更後の値どうしで行う。本文に含まれない日付は、
    # 今の値を使う。本文の日付に誤りがあれば、検査しない。
    if "start_date" not in fields and "end_date" not in fields:
        start_date = values.get("start_date", semester.start_date)
        end_date = values.get("end_date", semester.end_date)
        if end_date <= start_date:
            fields["end_date"] = END_DATE_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, SEMESTER_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    previous_start_date = semester.start_date
    previous_end_date = semester.end_date
    # 本文に含まれていた項目だけを、学期に書き込む
    # （values のキーは、Semesterの列の名前と同じ）。
    for field_name, value in values.items():
        setattr(semester, field_name, value)

    # 期間が変わったときだけ、授業の予定と休講日に反映する（名前だけの
    # 変更では、予定も休講日も変えない）。
    if (semester.start_date, semester.end_date) != (
        previous_start_date,
        previous_end_date,
    ):
        sync_period_change(semester, previous_start_date, previous_end_date)
    # 学期の更新と、予定・休講日の削除・作成を、1回のcommitで保存する。
    db.session.commit()
    return jsonify(semester_to_dict(semester))


@semesters_bp.delete(f"/<int(max={MAX_ID}):semester_id>")
def delete_semester(semester_id: int):
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        return api_error_response("not_found", "学期が見つかりません")

    # 授業がある学期は、削除できない（授業の予定・課題を、まとめて消さない
    # ため。先に、授業を1件ずつ削除してもらう）。
    if count_semester_subjects(semester.id) > 0:
        return api_error_response("conflict", SEMESTER_HAS_SUBJECTS_MESSAGE)

    # 学期の休講日を、学期より先に、明示的に削除する（「データ設計」の
    # 「共通の約束」）。学期だけを削除すると、休講日が、semester_id が
    # NULL の行として残る。
    db.session.execute(
        db.delete(Closure).where(Closure.semester_id == semester.id)
    )
    db.session.delete(semester)
    # 休講日と学期の削除を、1回のcommitで保存する。
    db.session.commit()
    return "", 204
