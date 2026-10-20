import re
from collections.abc import Collection
from datetime import date, datetime, time
from typing import Any

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    InternalServerError,
    MethodNotAllowed,
)


# IDの上限（SQLiteのINTEGERの最大値）。これを超える数をDBに渡すとエラーになるため、IDを受け取るURLでは、この値までに制限する
MAX_ID = 2**63 - 1

ERROR_STATUS_CODES = {
    "invalid_json": 400,
    "validation_error": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "conflict": 409,
    "server_error": 500,
}

INVALID_JSON_MESSAGE = (
    "リクエストの本文がJSONとして読めません。"
    "Content-Typeを application/json にして、JSONで送ってください"
)
UNUSABLE_CHARACTER_MESSAGE = "使用できない文字が含まれています"
EMPTY_PATCH_MESSAGE = "変更する項目を指定してください"


def contains_unusable_character(value: str) -> bool:
    """UTF-8に変換できない孤立サロゲートが含まれるか確認する。"""
    return any(
        0xD800 <= ord(character) <= 0xDFFF
        for character in value
    )


def api_error_response(
    code: str,
    message: str,
    fields: dict[str, str] | None = None,
) -> tuple[Response, int]:
    """共通形式のAPIエラーレスポンスを作る。"""
    error: dict[str, Any] = {"code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    return jsonify({"error": error}), ERROR_STATUS_CODES[code]


def is_api_path(path: str) -> bool:
    """APIのエラーだけをJSONにするため、パスの境界を確認する。"""
    return path == "/api" or path.startswith("/api/")


def register_api_error_handlers(app: Flask) -> None:
    """APIの404・405・500をJSON形式で返すハンドラーを登録する。"""

    @app.errorhandler(404)
    def handle_not_found(error: HTTPException):
        # API以外の画面には影響させず、Flask標準のHTMLエラーを維持する。
        if not is_api_path(request.path):
            return error

        # URLそのものが存在しない場合のメッセージ。データが存在しない場合は、各routeが返す。
        return api_error_response("not_found", "URLが見つかりません")

    @app.errorhandler(405)
    def handle_method_not_allowed(error: MethodNotAllowed):
        if not is_api_path(request.path):
            return error
        response, status = api_error_response(
            "method_not_allowed",
            "このURLでは、そのメソッドは使えません",
        )
        # そのURLで使えるメソッドを、Allow ヘッダーで知らせる（405の応答に
        # 付ける決まり）。Werkzeugが渡すメソッドの並びは、決まっていない
        # ため、名前の順に並べる。
        if error.valid_methods:
            response.headers["Allow"] = ", ".join(sorted(error.valid_methods))
        return response, status

    @app.errorhandler(InternalServerError)
    def handle_internal_server_error(error: InternalServerError):
        if not is_api_path(request.path):
            return error
        return api_error_response(
            "server_error",
            "サーバーでエラーが発生しました",
        )


def read_json_object() -> tuple[
    dict[str, Any] | None,
    tuple[Response, int] | None,
]:
    """application/jsonの本文を読み、JSONオブジェクトだけを受け付ける。"""
    if request.mimetype != "application/json":
        return None, api_error_response("invalid_json", INVALID_JSON_MESSAGE)

    try:
        # silent=TrueではJSONのnullと解析失敗が同じNoneになるため、例外で判別する。
        payload = request.get_json()
    except BadRequest:
        return None, api_error_response("invalid_json", INVALID_JSON_MESSAGE)

    if not isinstance(payload, dict):
        return None, api_error_response(
            "validation_error",
            "リクエストの本文は、JSONのオブジェクトにしてください",
        )
    return payload, None


def read_patch_object() -> tuple[
    dict[str, Any] | None,
    tuple[Response, int] | None,
]:
    """PATCHの本文を読み、項目が1つもないオブジェクト（{}）を誤りにする。

    本文の読み取りは、read_json_object と同じ。{} は、特定の項目に
    結びつかない誤りのため、fields を付けない。
    """
    payload, error_response = read_json_object()
    if error_response is not None:
        return None, error_response
    if not payload:
        return None, api_error_response(
            "validation_error",
            EMPTY_PATCH_MESSAGE,
        )
    return payload, None


def read_id_query(
    name: str,
    multiple_message: str,
    format_message: str,
) -> tuple[bool, int | None, str | None]:
    """一覧の絞り込みのクエリで指定されたIDを読み取る。

    戻り値は、（指定の有無、ID、エラーメッセージ）の組。
    - 指定がない：(False, None, None)
    - 2回以上の指定：(True, None, multiple_message)
    - 数字だけでない（空文字・符号・小数・全角数字・空白など）：
      (True, None, format_message)
    - 数字だけだが、1〜MAX_IDの外（0、MAX_IDより大きい数）：
      (True, None, None)。該当するデータがないため、呼び出し側は、
      DBに問い合わせずに、空の一覧を返す
    - それ以外：(True, ID, None)
    DBは読まない（IDのデータが存在するかは、確かめない）。
    """
    values = request.args.getlist(name)
    if not values:
        return False, None, None
    if len(values) > 1:
        return True, None, multiple_message

    text = values[0]
    if re.fullmatch(r"[0-9]+", text) is None:
        return True, None, format_message

    # MAX_IDより大きい数をDBに渡すとOverflowErrorになり、非常に長い
    # 数字の文字列をint()に渡すとValueErrorになるため、int()の前に、
    # 先頭の0を取り除いた桁数と値で、MAX_IDと比べる。
    normalized_text = text.lstrip("0")
    maximum_text = str(MAX_ID)
    if normalized_text == "" or len(normalized_text) > len(maximum_text):
        return True, None, None
    if (
        len(normalized_text) == len(maximum_text)
        and normalized_text > maximum_text
    ):
        return True, None, None
    return True, int(normalized_text), None


def validate_allowed_fields(
    payload: dict[str, Any],
    allowed_fields: set[str],
) -> dict[str, str]:
    """許可されていない項目や読み取り専用項目をエラーにする。"""
    return {
        field: "この項目は指定できません"
        for field in payload
        if field not in allowed_fields
    }


def validate_required_string(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    type_message: str,
    *,
    max_length: int | None = None,
    length_message: str | None = None,
    strip: bool = False,
) -> tuple[str | None, str | None]:
    """必須文字列を検査し、値またはエラーメッセージを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、引数の指定に関係なく、
    型の検査のあと、前後の空白の除去と長さの検査より前に、常に行う。
    """
    if max_length is not None and length_message is None:
        raise ValueError("max_lengthを指定する場合はlength_messageが必要です")

    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, type_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE
    if strip:
        value = value.strip()
        if value == "":
            return None, required_message
    if max_length is not None and len(value) > max_length:
        return None, length_message
    return value, None


def validate_optional_string(
    payload: dict[str, Any],
    field: str,
    type_message: str,
    *,
    max_length: int | None = None,
    length_message: str | None = None,
) -> tuple[str | None, str | None]:
    """任意文字列を検査して正規化し、値またはエラーを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、引数の指定に関係なく、
    型の検査のあと、前後の空白の除去と長さの検査より前に、常に行う。
    """
    if max_length is not None and length_message is None:
        raise ValueError("max_lengthを指定する場合はlength_messageが必要です")

    value = payload.get(field)
    if field not in payload or value is None:
        return None, None
    if not isinstance(value, str):
        return None, type_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    value = value.strip()
    if value == "":
        return None, None
    if max_length is not None and len(value) > max_length:
        return None, length_message
    return value, None


def validate_required_integer(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    type_message: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
    range_message: str | None = None,
) -> tuple[int | None, str | None]:
    """必須整数を検査し、必要に応じて範囲も確認する。"""
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if isinstance(value, bool) or not isinstance(value, int):
        return None, type_message
    if (
        (min_value is not None and value < min_value)
        or (max_value is not None and value > max_value)
    ):
        return None, range_message or type_message
    return value, None


def validate_required_boolean(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    type_message: str,
) -> tuple[bool | None, str | None]:
    """必須の真偽値を検査する。JSONの true・false だけを受け付ける。

    数値（0・1）や文字列（"true" など）は、型の誤りにする。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, bool):
        return None, type_message
    return value, None


def validate_required_choice(
    payload: dict[str, Any],
    field: str,
    choices: Collection[str],
    required_message: str,
    choice_message: str,
) -> tuple[str | None, str | None]:
    """決まった値（choices）の中から選ぶ、必須の文字列を検査する。

    カテゴリ（category）に使う。choices のどれかと完全に一致する文字列
    だけを受け付ける（前後の空白を取り除かない）。文字列でない値と、
    choices にない値は、どちらも choice_message を返す。使用できない
    文字（孤立サロゲート）を含む場合は、UNUSABLE_CHARACTER_MESSAGE を返す。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, choice_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE
    if value not in choices:
        return None, choice_message
    return value, None


def parse_time(value: Any) -> time | None:
    """HH:MMの厳密な形式と時刻の範囲を確認して変換する。"""
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"[0-9]{2}:[0-9]{2}", value) is None:
        return None

    hour, minute = (int(part) for part in value.split(":"))
    try:
        return time(hour, minute)
    except ValueError:
        return None


def format_time(value: time) -> str:
    """時刻をAPIのHH:MM形式にする。"""
    return value.strftime("%H:%M")


def validate_required_time(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[time | None, str | None]:
    """必須時刻を検査し、Pythonのtimeかエラーメッセージを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_time(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None


def parse_date(value: Any) -> date | None:
    """YYYY-MM-DDの形式と実在性を確認して日付に変換する。"""
    if not isinstance(value, str):
        return None

    # fromisoformatは区切りのない日付も受理するため、先に厳密な形式を確認する。
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_date(value: date) -> str:
    """日付をAPIのYYYY-MM-DD形式にする。"""
    return value.isoformat()


def validate_required_date(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[date | None, str | None]:
    """必須の日付を検査し、Pythonのdateかエラーメッセージを返す。

    文字列でない値は、時刻と同じく、format_messageを返す。
    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_date(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None


def parse_datetime(value: Any) -> datetime | None:
    """YYYY-MM-DDTHH:MMの形式と実在性を確認して日時に変換する。"""
    if not isinstance(value, str):
        return None

    # fromisoformatは秒や別の書式も受理するため、先に厳密な形式を確認する。
    if (
        re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", value)
        is None
    ):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_datetime(value: datetime) -> str:
    """日時をAPIのYYYY-MM-DDTHH:MM形式にする（秒は出さない）。"""
    return value.isoformat(timespec="minutes")


def validate_required_datetime(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[datetime | None, str | None]:
    """必須の日時を検査し、Pythonのdatetimeかエラーメッセージを返す。

    文字列でない値は、日付・時刻と同じく、format_messageを返す。
    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_datetime(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None
