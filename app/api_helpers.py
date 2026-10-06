import re
from datetime import date, time
from typing import Any

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException, InternalServerError


# IDの上限（SQLiteのINTEGERの最大値）。これを超える数をDBに渡すとエラーになるため、IDを受け取るURLでは、この値までに制限する
MAX_ID = 2**63 - 1

ERROR_STATUS_CODES = {
    "invalid_json": 400,
    "validation_error": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "server_error": 500,
}

INVALID_JSON_MESSAGE = (
    "リクエストの本文がJSONとして読めません。"
    "Content-Typeを application/json にして、JSONで送ってください"
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
    def handle_method_not_allowed(error: HTTPException):
        if not is_api_path(request.path):
            return error
        return api_error_response(
            "method_not_allowed",
            "このURLでは、そのメソッドは使えません",
        )

    @app.errorhandler(InternalServerError)
    def handle_internal_server_error(error: InternalServerError):
        if not is_api_path(request.path):
            return error
        return api_error_response(
            "server_error",
            "サーバーでエラーが発生しました",
        )


def read_json_object() -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
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
    """必須文字列の欠落と型を検査し、値またはエラーメッセージを返す。"""
    if max_length is not None and length_message is None:
        raise ValueError("max_lengthを指定する場合はlength_messageが必要です")

    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, type_message
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
    """任意文字列を正規化し、型と長さを検査する。"""
    if max_length is not None and length_message is None:
        raise ValueError("max_lengthを指定する場合はlength_messageが必要です")

    value = payload.get(field)
    if field not in payload or value is None:
        return None, None
    if not isinstance(value, str):
        return None, type_message

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
    """必須時刻を検査し、Pythonのtimeに変換する。"""
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message

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
