import re
from datetime import date
from typing import Any

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException, InternalServerError


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

        if request.endpoint == "semesters.get_semester":
            message = "学期が見つかりません"
        else:
            message = "URLが見つかりません"
        return api_error_response("not_found", message)

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
) -> tuple[str | None, str | None]:
    """必須文字列の欠落と型を検査し、値またはエラーメッセージを返す。"""
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, type_message
    return value, None


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
