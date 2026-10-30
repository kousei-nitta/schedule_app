"""ログインの試行の制限（総当たりで、パスワードを当てさせない）。

仕様は docs/architecture/security.md の「ログインの試行の制限」。
- 同じログインID（IDがなくても同じに扱う。IDの有無を知らせないため）：
  24時間の失敗が5回で15分、10回で1時間、20回で24時間、最後の失敗から
  ログインを断る
- 同じ接続元（IPv6は、同じ /64 の範囲をまとめる）：1時間の失敗が10回で、
  最後の失敗から1時間断る
- 断っている間は、正しいパスワードでも断る。断った試行は、失敗に数えない
- 記録は、ログインIDと接続元を、秘密の鍵（SECRET_KEY）を使ったハッシュ
  （HMAC-SHA256）でだけ残す。24時間より古い記録は消す

同時に送られた試行で、数え漏れが起きないよう、「断るかの判断」と
「失敗の記録」を、ひとまとめにして、1つずつ行う（reserve_attempt）。
パスワードを確かめる前に、先に失敗として記録し、合っていたら消す。
"""
import hashlib
import hmac
import ipaddress
import math
import threading
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models.login_failure import LoginFailure

# 同じログインIDの失敗の数と、断る時間（多いものから順に確かめる）
LOGIN_ID_LOCK_STEPS = [
    (20, timedelta(hours=24)),
    (10, timedelta(hours=1)),
    (5, timedelta(minutes=15)),
]
LOGIN_ID_WINDOW = timedelta(hours=24)

# 同じ接続元の失敗の数と、断る時間
CLIENT_FAILURE_LIMIT = 10
CLIENT_WINDOW = timedelta(hours=1)
CLIENT_LOCK_TIME = timedelta(hours=1)

# 記録を残す長さ（いちばん長い窓と同じ）
RECORD_RETENTION = timedelta(hours=24)

# 「断るかの判断」と「失敗の記録」を、1つずつ行うための鍵
# （同じプロセスの中の、同時の要求。クラウドで複数のプロセスで動かす
# ときは、Task 026 で、DBの側で1つずつにする）
ATTEMPT_LOCK = threading.Lock()


def keyed_digest(purpose: str, value: str) -> str:
    """値を、秘密の鍵で、HMAC-SHA256 にする（16進数の64文字）。

    purpose（"login_id"・"client"）を混ぜ、同じ文字の値でも、用途ごとに
    違うハッシュにする。
    """
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    message = f"{purpose}\0{value}".encode("utf-8", errors="replace")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def client_key(remote_address: str | None) -> str:
    """接続元を、数える単位の文字にする。

    IPv6 は、1つの契約で /64 の範囲（とても多くのアドレス）を持つことが
    多く、アドレスを変えながら試せるため、/64 でまとめる。IPv4 を IPv6 の
    形で表したもの（::ffff:192.0.2.1）は、IPv4 として扱う。
    """
    if not remote_address:
        return "unknown"
    try:
        address = ipaddress.ip_address(remote_address)
    except ValueError:
        return remote_address
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ipaddress.IPv6Network((address, 64), strict=False))
    return str(address)


def lock_until(
    failure_times: list[datetime],
    steps: list[tuple[int, timedelta]],
) -> datetime | None:
    """失敗の時刻の一覧から、いつまで断るかを返す（断らなければ None）。

    steps は、（失敗の数、断る時間）の一覧（多いものから順）。失敗の数が
    しきい値以上なら、最後の失敗から、その時間だけ断る。
    """
    if not failure_times:
        return None
    for limit, lock_time in steps:
        if len(failure_times) >= limit:
            return max(failure_times) + lock_time
    return None


def failure_times(column, digest: str, since: datetime) -> list[datetime]:
    """ある digest の、since より後の失敗の時刻の一覧。"""
    return list(
        db.session.scalars(
            db.select(LoginFailure.failed_at).where(
                column == digest,
                LoginFailure.failed_at > since,
            )
        )
    )


def locked_until(
    login_id_digest: str,
    client_digest: str,
    now: datetime,
) -> datetime | None:
    """今、ログインを断るなら、いつまでかを返す（断らなければ None）。"""
    candidates = [
        lock_until(
            failure_times(
                LoginFailure.login_id_digest,
                login_id_digest,
                now - LOGIN_ID_WINDOW,
            ),
            LOGIN_ID_LOCK_STEPS,
        ),
        lock_until(
            failure_times(
                LoginFailure.client_digest,
                client_digest,
                now - CLIENT_WINDOW,
            ),
            [(CLIENT_FAILURE_LIMIT, CLIENT_LOCK_TIME)],
        ),
    ]
    future = [until for until in candidates if until is not None]
    if not future:
        return None
    until = max(future)
    return until if until > now else None


def remaining_minutes(until: datetime, now: datetime) -> int:
    """断っている残りの時間を、分で返す（切り上げ。最低1分）。"""
    return max(1, math.ceil((until - now).total_seconds() / 60))


def reserve_attempt(
    login_id_digest: str,
    client_digest: str,
    now: datetime,
) -> tuple[LoginFailure | None, datetime | None]:
    """ログインの試行を受け付けるかを決め、受け付けるなら、先に失敗として
    記録する（commitする）。

    戻り値：（記録した失敗の行、断る期限）。断るときは（None、期限）。
    パスワードが合っていたら、呼び出し側が、記録した行を消す
    （forget_failures）。
    """
    with ATTEMPT_LOCK:
        # 古い記録を消す
        db.session.execute(
            db.delete(LoginFailure).where(
                LoginFailure.failed_at <= now - RECORD_RETENTION
            )
        )
        until = locked_until(login_id_digest, client_digest, now)
        if until is not None:
            db.session.commit()
            return None, until
        failure = LoginFailure(
            login_id_digest=login_id_digest,
            client_digest=client_digest,
            failed_at=now,
        )
        db.session.add(failure)
        db.session.commit()
        return failure, None


def forget_failures(login_id_digest: str, client_digest: str) -> None:
    """ログインに成功したとき、そのIDの、その接続元からの失敗を消す
    （commitしない）。

    ほかの接続元からの失敗（ほかの人の試行かもしれない）は、残す
    （本人のログインで、他人の試行の数が戻らないように）。
    """
    db.session.execute(
        db.delete(LoginFailure).where(
            LoginFailure.login_id_digest == login_id_digest,
            LoginFailure.client_digest == client_digest,
        )
    )


def unlock_login_id(login_id_digest: str) -> int:
    """そのログインIDの失敗を、すべて消す（commitしない）。消した件数。

    他人にわざと失敗され、締め出されたときに、コマンドで使う
    （flask --app app unlock-login）。
    """
    result = db.session.execute(
        db.delete(LoginFailure).where(
            LoginFailure.login_id_digest == login_id_digest
        )
    )
    return result.rowcount
