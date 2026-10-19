from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_date,
    format_time,
    parse_date,
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_choice,
    validate_required_date,
    validate_required_integer,
    validate_required_string,
    validate_required_time,
)
from app.categories import (
    EVENT_CATEGORIES,
    EVENT_CATEGORY_CLASS,
    EVENT_CATEGORY_OTHER,
    EVENT_CATEGORY_PART_TIME,
)
from app.extensions import db
from app.models.event import Event
from app.models.subject import Subject


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/api/events",
)

# 予定の編集（PATCH）で受け付ける項目。カテゴリ（category）と授業
# （subject_id）は、登録のあとで変えられない（誤った場合は、削除して
# 登録し直す）。
UPDATE_FIELDS = {
    "date",
    "start_time",
    "end_time",
    "title",
    "room",
    "employer",
    "notes",
}
# 予定の登録（POST）で受け付ける項目。is_generated は受け付けない
# （登録した予定は、常に単発の予定）。
CREATE_FIELDS = UPDATE_FIELDS | {"category", "subject_id"}

# カテゴリごとの、そのカテゴリにない項目（項目がないか、null だけを
# 受け付ける）。
NOT_APPLICABLE_FIELDS = {
    EVENT_CATEGORY_CLASS: ("title", "employer"),
    EVENT_CATEGORY_PART_TIME: ("subject_id", "room"),
    EVENT_CATEGORY_OTHER: ("subject_id", "room", "employer"),
}
# そのカテゴリにない項目に、null 以外の値を指定したときのメッセージ。
NOT_APPLICABLE_MESSAGES = {
    "subject_id": "授業IDは、授業の予定にだけ指定できます",
    "title": (
        "授業の予定には、タイトルを指定できません（授業の科目名になります）"
    ),
    "room": "教室は、授業の予定にだけ指定できます",
    "employer": "派遣会社は、アルバイトの予定にだけ指定できます",
}

CATEGORY_MESSAGE = (
    "カテゴリは「class」「part_time」「other」のどれかで指定してください"
)
END_TIME_ORDER_MESSAGE = "終了時刻は開始時刻より後にしてください"
GENERATED_DATE_MESSAGE = (
    "自動生成の授業の予定は、日付を変えられません（別の日に移すときは、"
    "この予定を削除して、移す先の日に単発の授業を追加してください）"
)
SUBJECT_NOT_FOUND_MESSAGE = "指定された授業が存在しません"


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


def validate_event_values(
    payload: dict[str, Any],
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """予定の項目（日付・開始時刻・終了時刻・詳細／メモ）を検査する。

    どのカテゴリにもある項目で、登録（POST）と編集（PATCH）で、同じ規則で
    検査するために使う。
    - partial=False（登録）：4つの項目を検査する。必須の項目が本文に
      なければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する
    戻り値は、（値、エラー）の組。値は、誤りのない項目だけを入れる
    （キーは、Eventの列の名前と同じ）。開始時刻と終了時刻の前後の検査は、
    呼び出し側が行う（編集では、今の値と組み合わせて比べるため）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "date" in payload:
        event_date, error = validate_required_date(
            payload,
            "date",
            "日付は必須です",
            "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください",
        )
        if error is None:
            values["date"] = event_date
        else:
            errors["date"] = error

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


def validate_event_subject_id(
    payload: dict[str, Any],
) -> tuple[int | None, str | None]:
    """授業の予定の授業ID（subject_id）を検査する（登録のときだけ）。

    必須。整数で、その授業が存在すること。規則とメッセージは、課題の
    対象授業（routes/tasks.py）と同じ。DBを読むため、api_helpers.py には
    置かない。
    """
    subject_id, error = validate_required_integer(
        payload,
        "subject_id",
        "授業IDは必須です",
        "授業IDは整数で指定してください",
    )
    if error is not None:
        return None, error
    # 範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。
    if not 1 <= subject_id <= MAX_ID:
        return None, SUBJECT_NOT_FOUND_MESSAGE
    if db.session.get(Subject, subject_id) is None:
        return None, SUBJECT_NOT_FOUND_MESSAGE
    return subject_id, None


def validate_category_fields(
    payload: dict[str, Any],
    category: str,
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """カテゴリによって規則が変わる項目を、そのカテゴリの規則で検査する。

    対象は、授業ID（subject_id）・タイトル（title）・教室（room）・
    派遣会社（employer）。
    - 授業：授業IDは必須、教室は任意。タイトル・派遣会社は指定できない
    - アルバイト：タイトルは必須、派遣会社は任意。授業ID・教室は
      指定できない
    - その他：タイトルは必須。授業ID・教室・派遣会社は指定できない
    指定できない項目は、項目がないか、null だけを受け付ける。
    - partial=False（登録）：上の項目を、すべて検査する
    - partial=True（編集）：本文に含まれる項目だけを検査する。授業IDは
      検査しない（編集では、値によらず受け付けないため。呼び出し側の
      validate_allowed_fields が誤りにする）
    戻り値は、（値、エラー）の組（validate_event_values と同じ形）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if category == EVENT_CATEGORY_CLASS:
        if not partial:
            subject_id, error = validate_event_subject_id(payload)
            if error is None:
                values["subject_id"] = subject_id
            else:
                errors["subject_id"] = error

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
    else:
        if not partial or "title" in payload:
            title, error = validate_required_string(
                payload,
                "title",
                "タイトルは必須です",
                "タイトルは文字列で指定してください",
                strip=True,
                max_length=200,
                length_message="タイトルは200文字以内にしてください",
            )
            if error is None:
                values["title"] = title
            else:
                errors["title"] = error

    if category == EVENT_CATEGORY_PART_TIME and (
        not partial or "employer" in payload
    ):
        employer, error = validate_optional_string(
            payload,
            "employer",
            "派遣会社は文字列で指定してください",
            max_length=100,
            length_message="派遣会社は100文字以内にしてください",
        )
        if error is None:
            values["employer"] = employer
        else:
            errors["employer"] = error

    # そのカテゴリにない項目は、項目がないか、null だけを受け付ける
    # （null は、値を変えない）。値の中身は見ない。
    for field_name in NOT_APPLICABLE_FIELDS[category]:
        if partial and field_name == "subject_id":
            continue
        if payload.get(field_name) is not None:
            errors[field_name] = NOT_APPLICABLE_MESSAGES[field_name]

    return values, errors


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


@events_bp.get("/employers")
def get_employers():
    """アルバイトの派遣会社の入力候補を、新しく使った順に返す。

    派遣会社ごとに、その派遣会社を持つ予定の最も大きいid（最も新しく
    登録した予定）で並べる。重複は、文字列の完全一致で除く。
    """
    statement = (
        db.select(Event.employer)
        .where(
            Event.category == EVENT_CATEGORY_PART_TIME,
            Event.employer.is_not(None),
        )
        .group_by(Event.employer)
        .order_by(db.func.max(Event.id).desc())
    )
    employers = db.session.scalars(statement).all()
    return jsonify(list(employers))


@events_bp.post("")
def create_event():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    fields: dict[str, str] = {}

    category, category_error = validate_required_choice(
        payload,
        "category",
        EVENT_CATEGORIES,
        "カテゴリは必須です",
        CATEGORY_MESSAGE,
    )
    if category_error is not None:
        fields["category"] = category_error

    values, value_errors = validate_event_values(payload, partial=False)
    fields.update(value_errors)

    start_time = values.get("start_time")
    end_time = values.get("end_time")
    # 前後の検査は、開始時刻と終了時刻の両方に誤りがないときだけ行う。
    # 日付をまたぐ予定（終了が開始より前）は、1件では登録できない。
    if (
        start_time is not None
        and end_time is not None
        and end_time <= start_time
    ):
        fields["end_time"] = END_TIME_ORDER_MESSAGE

    # カテゴリによって規則が変わる項目は、カテゴリに誤りがないときだけ
    # 検査する。
    if category is not None:
        category_values, category_errors = validate_category_fields(
            payload, category, partial=False
        )
        values.update(category_values)
        fields.update(category_errors)

    fields.update(validate_allowed_fields(payload, CREATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    if category == EVENT_CATEGORY_CLASS:
        # 授業の予定のタイトルは、授業の科目名の控え（指定できない）。
        subject = db.session.get(Subject, values["subject_id"])
        values["title"] = subject.subject_name

    # values のキーは、Eventの列の名前と同じ。そのカテゴリにない項目
    # （授業ID・教室・派遣会社）は、values になく、None のまま。
    event = Event(category=category, is_generated=False, **values)
    db.session.add(event)
    db.session.commit()
    return jsonify(event_to_dict(event)), 201


@events_bp.patch(f"/<int(max={MAX_ID}):event_id>")
def update_event(event_id: int):
    # 対象の予定がなければ、本文を読む前に404にする。
    event = db.session.get(Event, event_id)
    if event is None:
        return api_error_response("not_found", "予定が見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_event_values(payload, partial=True)

    # 自動生成の授業の予定は、日付を変えられない（値によらず誤り）。
    # 休講日の同期と、授業全体の編集による作り直しが、自動生成の予定は
    # 授業の曜日の日にあることを前提にしているため。
    if event.is_generated and "date" in payload:
        values.pop("date", None)
        fields["date"] = GENERATED_DATE_MESSAGE

    # 前後の検査は、変更後の値どうしで行う。本文に含まれない時刻は、
    # 今の値を使う。本文の時刻に誤りがあれば、検査しない。
    if "start_time" not in fields and "end_time" not in fields:
        start_time = values.get("start_time", event.start_time)
        end_time = values.get("end_time", event.end_time)
        if end_time <= start_time:
            fields["end_time"] = END_TIME_ORDER_MESSAGE

    # カテゴリによって規則が変わる項目は、今のカテゴリ（変えられない）の
    # 規則で検査する。
    category_values, category_errors = validate_category_fields(
        payload, event.category, partial=True
    )
    values.update(category_values)
    fields.update(category_errors)

    fields.update(validate_allowed_fields(payload, UPDATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 本文に含まれていた項目だけを、予定に書き込む（values のキーは、
    # Eventの列の名前と同じ）。is_generated は変えない。
    for field_name, value in values.items():
        setattr(event, field_name, value)
    db.session.commit()
    return jsonify(event_to_dict(event))


@events_bp.delete(f"/<int(max={MAX_ID}):event_id>")
def delete_event(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None:
        return api_error_response("not_found", "予定が見つかりません")

    # 予定は、子の行を持たないため、この行だけを削除する。自動生成の
    # 予定も削除できる（削除したことは記録しない）。
    db.session.delete(event)
    db.session.commit()
    return "", 204
