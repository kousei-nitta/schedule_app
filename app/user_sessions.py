"""ログイン中の端末（サーバー側のセッション）。

仕様は docs/architecture/security.md の「ログインの状態（セッション）」。
- ログインすると、32バイトの乱数（トークン）を作り、Cookie に入れる。
  DBには、トークンの SHA-256 だけを置く（DBが漏れても、Cookieを
  作れない。SECRET_KEY が漏れても、ログインを偽造できない）
- 最後に使ってから14日、またはログインから30日で、切れる
- ログアウトでは、DBの行を消す（盗まれたCookieも、すぐに使えなくなる）
"""
import hashlib
import re
import secrets
from datetime import datetime, timedelta

from flask import Response, current_app

from app import clock
from app.extensions import db
from app.models.user_session import UserSession

# 最後に使ってから、この時間がたつと切れる（使うたびに延びる）
SESSION_IDLE_TIMEOUT = timedelta(days=14)
# ログインから、この時間がたつと、使っていても切れる（入れ直す）
SESSION_ABSOLUTE_TIMEOUT = timedelta(days=30)
# 最後に使った時刻を更新する間隔（読み取りのたびに、DBへ書かないため）
LAST_USED_UPDATE_INTERVAL = timedelta(hours=1)

# トークン：32バイトの乱数を、URLで使える文字にしたもの（43文字）
TOKEN_BYTES = 32
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")


def token_digest(token: str) -> str:
    """トークンの SHA-256（16進数の64文字）。DBには、これだけを置く。"""
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def is_expired(session: UserSession, now: datetime) -> bool:
    """ログイン中の端末の期限が切れているか。"""
    return (
        now - session.last_used_at >= SESSION_IDLE_TIMEOUT
        or now - session.created_at >= SESSION_ABSOLUTE_TIMEOUT
    )


def start_session(user_id: int) -> str:
    """ログインした端末の行を作り、トークンを返す（commitしない）。

    同じ利用者の、期限の切れた行は、ここで消す。
    """
    now = clock.utc_now()
    delete_expired_sessions(user_id, now)
    token = secrets.token_urlsafe(TOKEN_BYTES)
    db.session.add(
        UserSession(
            user_id=user_id,
            token_digest=token_digest(token),
            created_at=now,
            last_used_at=now,
        )
    )
    return token


def find_session(token: str | None) -> UserSession | None:
    """Cookie のトークンから、ログイン中の端末の行を探す。

    形式が違う・見つからない・期限が切れている（行を消す）ときは None。
    使ったので、最後に使った時刻を、1時間に1回だけ更新する。
    """
    if token is None or TOKEN_PATTERN.fullmatch(token) is None:
        return None
    session = db.session.scalar(
        db.select(UserSession).where(
            UserSession.token_digest == token_digest(token)
        )
    )
    if session is None:
        return None
    now = clock.utc_now()
    if is_expired(session, now):
        db.session.delete(session)
        db.session.commit()
        return None
    if now - session.last_used_at >= LAST_USED_UPDATE_INTERVAL:
        session.last_used_at = now
        db.session.commit()
    return session


def delete_expired_sessions(user_id: int, now: datetime) -> None:
    """利用者の、期限の切れた行を消す（commitしない）。"""
    db.session.execute(
        db.delete(UserSession).where(
            UserSession.user_id == user_id,
            db.or_(
                UserSession.last_used_at <= now - SESSION_IDLE_TIMEOUT,
                UserSession.created_at <= now - SESSION_ABSOLUTE_TIMEOUT,
            ),
        )
    )


def end_all_sessions(user_id: int) -> int:
    """利用者の、すべての端末のログインを終える（commitしない）。件数。"""
    result = db.session.execute(
        db.delete(UserSession).where(UserSession.user_id == user_id)
    )
    return result.rowcount


def count_active_sessions(user_id: int) -> int:
    """利用者の、期限の切れていないログイン中の端末の数。"""
    now = clock.utc_now()
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.last_used_at > now - SESSION_IDLE_TIMEOUT,
            UserSession.created_at > now - SESSION_ABSOLUTE_TIMEOUT,
        )
    )


def set_session_cookie(response: Response, token: str) -> None:
    """ログインのトークンを、Cookie に入れる。

    - HttpOnly：JavaScript から読めない（XSSで盗まれにくい）
    - SameSite=Strict：ほかのサイトから始まった要求には付けない（CSRF）
    - Secure：HTTPS のときだけ送る（設定。公開のとき（Task 026）にオン）
    - 期限：ログインから30日（サーバー側でも、14日・30日を確かめる）
    """
    response.set_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        token,
        max_age=int(SESSION_ABSOLUTE_TIMEOUT.total_seconds()),
        path="/",
        secure=current_app.config["AUTH_COOKIE_SECURE"],
        httponly=True,
        samesite="Strict",
    )


def clear_session_cookie(response: Response) -> None:
    """ログインの Cookie を、ブラウザから消す。"""
    response.delete_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        path="/",
        secure=current_app.config["AUTH_COOKIE_SECURE"],
        httponly=True,
        samesite="Strict",
    )
