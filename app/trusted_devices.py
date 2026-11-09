"""一度ログインした端末の印（device cookie）。

仕様は docs/architecture/security.md の「ログインの試行の制限」の
「端末の印」（OWASP の「Slow Down Online Guessing Attacks with Device
Cookies」の方式。理由は ADR 0005）。

ログインIDごとの制限は、だれの失敗でも始まるため、IDを知っている人は、
本人を締め出し続けられる。そこで、ログインに成功した端末に、乱数の印を
Cookie で渡し、印のある端末からの試行は、IDごと・接続元ごとの制限を
受けない「印のある道」で扱う。印のある道は、印ごとの失敗の数で守る
（5回で、その印を使えなくする）。

- 印は、32バイトの乱数。DBには、SHA-256 だけを置く（DBが漏れても、
  印を作れない。SECRET_KEY が漏れても、作れない）
- 期限は、印を作ってから180日（サーバーの created_at で判定する）。
  ログインに成功するたびに、作り替える
- 利用者ごとに10個まで（古いものから消す）
- 印は、打ち込まれたログインIDが、印の持ち主のIDと完全に一致するときだけ
  使う（ほかの人の印を持ち込んでも、ほかのIDには効かない）。違うIDと
  一緒に届いたときも、その印の失敗に数える（盗まれた印で、ログインIDを
  探らせない）
"""
import secrets
from datetime import datetime, timedelta
from typing import NamedTuple

from flask import Response, current_app

from app.extensions import db
from app.models.trusted_device import TrustedDevice
from app.models.user import User
from app.user_sessions import TOKEN_BYTES, TOKEN_PATTERN, token_digest

# 印の期限（作ってから）
DEVICE_LIFETIME = timedelta(days=180)
# 印ごとに、続けて失敗してよい数（この数で、印を使えなくする）
MAX_DEVICE_FAILURES = 5
# 利用者ごとの印の数の上限（多ければ、古いものから消す）
MAX_DEVICES_PER_USER = 10


class TrustedDeviceMatch(NamedTuple):
    """有効な印（行の id、印の持ち主の利用者の id、打ち込まれたIDが、
    持ち主のIDと一致したか）。一致したときだけ、印のある道で扱う。"""

    device_id: int
    user_id: int
    login_id_matches: bool


def find_trusted_device(
    token: str | None, login_id: str, now: datetime
) -> TrustedDeviceMatch | None:
    """この端末の、有効な印を返す（なければ None）。

    有効でないもの：印がない・形が違う・見つからない・期限切れ・失敗が
    上限に達した・印の持ち主がいない・パスワードのない利用者。
    持ち主のログインIDが、打ち込まれたIDと違うとき（大文字・空白の違いも、
    違うとする）は、login_id_matches を False にして返す。
    行は、ORM のオブジェクトとしてでなく、列の値だけで読む（このあと、
    行を消して作り直すとき、古いオブジェクトが残らないように）。
    """
    if token is None or TOKEN_PATTERN.fullmatch(token) is None:
        return None
    device = db.session.execute(
        db.select(
            TrustedDevice.id,
            TrustedDevice.user_id,
            TrustedDevice.created_at,
            TrustedDevice.failure_count,
        ).where(TrustedDevice.token_digest == token_digest(token))
    ).first()
    if (
        device is None
        or now - device.created_at >= DEVICE_LIFETIME
        or device.failure_count >= MAX_DEVICE_FAILURES
    ):
        return None
    user = db.session.get(User, device.user_id)
    if user is None or user.password_hash is None:
        return None
    return TrustedDeviceMatch(
        device.id, device.user_id, user.username == login_id
    )


def reserve_device_attempt(device_id: int, now: datetime) -> bool:
    """パスワードを確かめる前に、その印の失敗の数を、先に1つ増やす（commit）。

    数が上限より少なく、期限内のときだけ増やし、True を返す。1つの文
    （UPDATE … WHERE 数 < 上限）で行うため、同時に送られた試行でも、
    上限を超えて試せない。合っていたら、呼び出し側が、印を作り替える
    （数は、新しい印で0から）。
    """
    result = db.session.execute(
        db.update(TrustedDevice)
        .where(
            TrustedDevice.id == device_id,
            TrustedDevice.failure_count < MAX_DEVICE_FAILURES,
            TrustedDevice.created_at > now - DEVICE_LIFETIME,
        )
        .values(failure_count=TrustedDevice.failure_count + 1)
    )
    db.session.commit()
    return result.rowcount == 1


def cancel_device_attempt(device_id: int) -> None:
    """先に増やした数を戻す（パスワードを確かめなかったとき。commit）。"""
    db.session.execute(
        db.update(TrustedDevice)
        .where(TrustedDevice.id == device_id, TrustedDevice.failure_count > 0)
        .values(failure_count=TrustedDevice.failure_count - 1)
    )
    db.session.commit()


def remove_device_if_exhausted(device_id: int) -> bool:
    """失敗が上限に達した印の行を消す（commit）。消したら True。

    印が盗まれ、パスワードを試されているかもしれない（呼び出し側が、
    ログに残す）。
    """
    result = db.session.execute(
        db.delete(TrustedDevice).where(
            TrustedDevice.id == device_id,
            TrustedDevice.failure_count >= MAX_DEVICE_FAILURES,
        )
    )
    db.session.commit()
    return result.rowcount == 1


def forget_device_token(token: str | None, user_id: int) -> None:
    """その利用者の、この印の行を消す（作り替える前。commitしない）。

    期限切れ・失敗が上限の印でも、同じ利用者のものなら消す（古い印の行を
    残さない）。ほかの利用者の印は、消さない。
    """
    if token is None or TOKEN_PATTERN.fullmatch(token) is None:
        return
    db.session.execute(
        db.delete(TrustedDevice).where(
            TrustedDevice.token_digest == token_digest(token),
            TrustedDevice.user_id == user_id,
        )
    )


def issue_device_token(user_id: int, now: datetime) -> str:
    """新しい印を作り、トークンを返す（commitしない）。

    期限の切れた行（すべての利用者の分）を消し、この利用者の印が
    上限を超えたら、古いものから消す。
    """
    db.session.execute(
        db.delete(TrustedDevice).where(
            TrustedDevice.created_at <= now - DEVICE_LIFETIME
        )
    )
    token = secrets.token_urlsafe(TOKEN_BYTES)
    db.session.add(
        TrustedDevice(
            user_id=user_id,
            token_digest=token_digest(token),
            created_at=now,
            failure_count=0,
        )
    )
    db.session.flush()
    # 新しい順に並べ、上限より後ろ（古いもの）を消す
    old_ids = db.session.scalars(
        db.select(TrustedDevice.id)
        .where(TrustedDevice.user_id == user_id)
        .order_by(TrustedDevice.created_at.desc(), TrustedDevice.id.desc())
        .offset(MAX_DEVICES_PER_USER)
    ).all()
    if old_ids:
        db.session.execute(
            db.delete(TrustedDevice).where(TrustedDevice.id.in_(old_ids))
        )
    return token


def end_all_devices(user_id: int) -> int:
    """利用者の、すべての印を消す（commitしない）。件数。

    パスワードを変えたときと、「すべての端末からログアウト」（端末を
    なくしたとき）に使う。
    """
    result = db.session.execute(
        db.delete(TrustedDevice).where(TrustedDevice.user_id == user_id)
    )
    return result.rowcount


def set_device_cookie(response: Response, token: str) -> None:
    """印を、Cookie に入れる（ログインの Cookie と同じ属性。180日）。"""
    response.set_cookie(
        current_app.config["DEVICE_COOKIE_NAME"],
        token,
        max_age=int(DEVICE_LIFETIME.total_seconds()),
        path="/",
        secure=current_app.config["AUTH_COOKIE_SECURE"],
        httponly=True,
        samesite="Strict",
    )


def clear_device_cookie(response: Response) -> None:
    """印の Cookie を、ブラウザから消す。"""
    response.delete_cookie(
        current_app.config["DEVICE_COOKIE_NAME"],
        path="/",
        secure=current_app.config["AUTH_COOKIE_SECURE"],
        httponly=True,
        samesite="Strict",
    )
