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
    # ログインの試行のたびに、この3つで探す・消すため、索引を付ける
    # （行が増えても、表の全部を読まないように。接続元を変えながら行を
    # 増やされても、ログインが遅くならないように）
    login_id_digest = db.Column(db.String(64), nullable=False, index=True)
    client_digest = db.Column(db.String(64), nullable=False, index=True)
    # 失敗した日時（UTC。タイムゾーンなしで保存）
    failed_at = db.Column(db.DateTime, nullable=False, index=True)
    # この失敗で始まった、ログインを断る期限（ログインIDごと・接続元
    # ごと）。断らないときは、failed_at と同じ。記録するときに決めて残す
    # （古い失敗が数えなくなっても、始まった制限が早く解けないように）
    login_id_locked_until = db.Column(db.DateTime, nullable=False)
    client_locked_until = db.Column(db.DateTime, nullable=False)
