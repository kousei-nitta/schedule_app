from typing import Any

from flask import Blueprint, jsonify, request

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_datetime,
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_boolean,
    validate_required_choice,
    validate_required_datetime,
    validate_required_integer,
    validate_required_string,
)
from app.categories import TASK_CATEGORIES, TASK_CATEGORY_OTHER
from app.extensions import db
from app.models.subject import Subject
from app.models.task import Task


tasks_bp = Blueprint(
    "tasks",
    __name__,
    url_prefix="/api/tasks",
)

# 課題・タスクの登録（POST）で受け付ける項目。完了の状態（is_completed）は
# 受け付けない（登録した課題・タスクは、常に未完了）。
CREATE_FIELDS = {
    "category",
    "subject_id",
    "title",
    "due_datetime",
    "notes",
}
# 課題・タスクの編集（PATCH）で受け付ける項目。カテゴリ（category）は、
# 変えられない（誤った場合は、削除して登録し直す）。
UPDATE_FIELDS = {
    "subject_id",
    "title",
    "due_datetime",
    "notes",
    "is_completed",
}

CATEGORY_MESSAGE = "カテゴリは「assignment」か「other」で指定してください"
COMPLETED_MESSAGE = "完了の状態は「true」か「false」で指定してください"
OTHER_SUBJECT_MESSAGE = "その他（締切のみ）には、授業を指定できません"


def task_to_dict(task: Task) -> dict[str, Any]:
    """課題・タスクをAPIレスポンス用の辞書に変換する。

    subject_name は、対象授業の今の科目名（付加情報。DBには保存しない）。
    対象授業がない場合（その他）は、None。
    """
    return {
        "id": task.id,
        "subject_id": task.subject_id,
        "subject_name": (
            task.subject.subject_name if task.subject is not None else None
        ),
        "category": task.category,
        "title": task.title,
        "due_datetime": format_datetime(task.due_datetime),
        "notes": task.notes,
        "is_completed": task.is_completed,
    }


def read_completed_query() -> tuple[bool, bool | None, str | None]:
    """一覧の絞り込みのクエリ is_completed を読み取る。

    戻り値は、（指定の有無、値、エラーメッセージ）の組。
    - 指定がない：(False, None, None)
    - 2回以上の指定：(True, None, 1つだけ指定するメッセージ)
    - 「true」「false」（小文字）以外（空文字・大文字・数字・空白を含む）：
      (True, None, COMPLETED_MESSAGE)
    - それ以外：(True, True または False, None)
    使うのが課題・タスクの一覧だけのため、このファイルに置く。
    """
    values = request.args.getlist("is_completed")
    if not values:
        return False, None, None
    if len(values) > 1:
        return True, None, "完了の状態は1つだけ指定してください"
    if values[0] == "true":
        return True, True, None
    if values[0] == "false":
        return True, False, None
    return True, None, COMPLETED_MESSAGE


def validate_task_values(
    payload: dict[str, Any],
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """課題・タスクの項目（タイトル・締切日時・詳細／メモ）を検査する。

    登録（POST）と編集（PATCH）で、同じ規則で検査するために使う。
    - partial=False（登録）：3つの項目を検査する。必須の項目が本文に
      なければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する
    戻り値は、（値、エラー）の組。値は、誤りのない項目だけを入れる
    （キーは、Taskの列の名前と同じ）。カテゴリ・対象授業・完了の状態は、
    呼び出し側が検査する。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

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

    if not partial or "due_datetime" in payload:
        due_datetime, error = validate_required_datetime(
            payload,
            "due_datetime",
            "締切日時は必須です",
            "締切日時は実在する日時を「YYYY-MM-DDTHH:MM」の形式で"
            "指定してください",
        )
        if error is None:
            values["due_datetime"] = due_datetime
        else:
            errors["due_datetime"] = error

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


def validate_task_subject_id(
    payload: dict[str, Any],
    category: str,
) -> tuple[int | None, str | None]:
    """対象授業（subject_id）を、カテゴリの規則で検査する。

    - 課題（assignment）：必須。整数で、その授業が存在すること
    - その他（other）：指定できない（項目がないか、null だけを受け付ける）
    戻り値は、（値、エラーメッセージ）の組。その他の値は、常に None。
    """
    if category == TASK_CATEGORY_OTHER:
        # その他（締切のみ）は、授業に結びつかない。
        if payload.get("subject_id") is not None:
            return None, OTHER_SUBJECT_MESSAGE
        return None, None

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
        return None, "指定された授業が存在しません"
    if db.session.get(Subject, subject_id) is None:
        return None, "指定された授業が存在しません"
    return subject_id, None


@tasks_bp.get("")
def get_tasks():
    specified, is_completed, query_error = read_completed_query()
    if query_error is not None:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            {"is_completed": query_error},
        )

    statement = db.select(Task)
    if specified:
        statement = statement.where(Task.is_completed.is_(is_completed))
    statement = statement.order_by(
        Task.due_datetime.asc(),
        Task.id.asc(),
    )
    tasks = db.session.scalars(statement).all()
    return jsonify([task_to_dict(task) for task in tasks])


@tasks_bp.get(f"/<int(max={MAX_ID}):task_id>")
def get_task(task_id: int):
    task = db.session.get(Task, task_id)
    if task is None:
        return api_error_response("not_found", "課題・タスクが見つかりません")
    return jsonify(task_to_dict(task))


@tasks_bp.post("")
def create_task():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    fields: dict[str, str] = {}

    category, category_error = validate_required_choice(
        payload,
        "category",
        TASK_CATEGORIES,
        "カテゴリは必須です",
        CATEGORY_MESSAGE,
    )
    if category_error is not None:
        fields["category"] = category_error

    values, value_errors = validate_task_values(payload, partial=False)
    fields.update(value_errors)

    # 対象授業の規則は、カテゴリによって変わるため、カテゴリに誤りが
    # ないときだけ検査する。
    subject_id = None
    if category is not None:
        subject_id, subject_id_error = validate_task_subject_id(
            payload, category
        )
        if subject_id_error is not None:
            fields["subject_id"] = subject_id_error

    fields.update(validate_allowed_fields(payload, CREATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    task = Task(
        category=category,
        subject_id=subject_id,
        title=values["title"],
        due_datetime=values["due_datetime"],
        notes=values["notes"],
        is_completed=False,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task_to_dict(task)), 201


@tasks_bp.patch(f"/<int(max={MAX_ID}):task_id>")
def update_task(task_id: int):
    # 対象の課題・タスクがなければ、本文を読む前に404にする。
    task = db.session.get(Task, task_id)
    if task is None:
        return api_error_response("not_found", "課題・タスクが見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_task_values(payload, partial=True)

    if "is_completed" in payload:
        is_completed, error = validate_required_boolean(
            payload,
            "is_completed",
            "完了の状態は必須です",
            COMPLETED_MESSAGE,
        )
        if error is None:
            values["is_completed"] = is_completed
        else:
            fields["is_completed"] = error

    # 対象授業は、今のカテゴリ（変えられない）の規則で検査する。
    if "subject_id" in payload:
        subject_id, error = validate_task_subject_id(payload, task.category)
        if error is None:
            values["subject_id"] = subject_id
        else:
            fields["subject_id"] = error

    fields.update(validate_allowed_fields(payload, UPDATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 本文に含まれていた項目だけを、課題・タスクに書き込む
    # （values のキーは、Taskの列の名前と同じ）。
    for field_name, value in values.items():
        setattr(task, field_name, value)
    db.session.commit()
    return jsonify(task_to_dict(task))


@tasks_bp.delete(f"/<int(max={MAX_ID}):task_id>")
def delete_task(task_id: int):
    task = db.session.get(Task, task_id)
    if task is None:
        return api_error_response("not_found", "課題・タスクが見つかりません")

    # 課題・タスクは、子の行を持たないため、この行だけを削除する。
    db.session.delete(task)
    db.session.commit()
    return "", 204
