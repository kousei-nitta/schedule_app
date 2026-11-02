from app.extensions import db


class UserSession(db.Model):
    """ログイン中の端末（1回のログインにつき1行）。

    Cookie には、乱数のトークンだけを入れ、DBには、そのSHA-256だけを
    置く（DBが漏れても、ログインを偽造できない）。ログアウトで行を消すと、
    その端末のCookieは、すぐに使えなくなる（app/user_sessions.py）。
    """

    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    # トークンの SHA-256（16進数の64文字）。同じ値の行は作らない
    token_digest = db.Column(db.String(64), nullable=False, unique=True)
    # ログインした日時と、最後に使った日時（どちらも UTC。タイムゾーン
    # なしで保存）。期限は、この2つから決める
    created_at = db.Column(db.DateTime, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=False)
