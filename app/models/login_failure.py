from app.extensions import db


class LoginFailure(db.Model):
    """ログインの失敗の記録（試行の制限に使う。app/login_limits.py）。

    打ち込まれたログインIDと、接続元（IPアドレス）は、そのまま保存せず、
    秘密の鍵（SECRET_KEY）を使ったハッシュ（HMAC-SHA256）でだけ残す。
    DBが漏れても、どんなIDが打ち込まれたか、どこから接続されたかは
    分からない。24時間より古い記録は消す。
    """

    __tablename__ = "login_failures"

    id = db.Column(db.Integer, primary_key=True)
    login_id_digest = db.Column(db.String(64), nullable=False)
    client_digest = db.Column(db.String(64), nullable=False)
    # 失敗した日時（UTC。タイムゾーンなしで保存）
    failed_at = db.Column(db.DateTime, nullable=False)
