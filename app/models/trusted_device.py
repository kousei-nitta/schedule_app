from app.extensions import db


class TrustedDevice(db.Model):
    """一度ログインした端末の印（device cookie）。1つの印につき1行。

    ログインに成功した端末に、乱数の印を Cookie で渡す。印のある端末は、
    ログインIDごと・接続元ごとの試行の制限を受けず、印ごとの失敗の数で
    守る（app/trusted_devices.py。docs/architecture/security.md の
    「ログインの試行の制限」）。DBには、印の SHA-256 だけを置く（DBが
    漏れても、印を作れない）。
    """

    __tablename__ = "trusted_devices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    # 印の SHA-256（16進数の64文字）。同じ値の行は作らない
    token_digest = db.Column(db.String(64), nullable=False, unique=True)
    # 印を作った日時（UTC。タイムゾーンなしで保存）。期限は、ここから決める
    # （Cookie の Max-Age には頼らない）。ログインに成功するたびに、
    # 印を作り替える
    created_at = db.Column(db.DateTime, nullable=False)
    # この印で、続けて失敗した数。決まった数で、印を使えなくする
    failure_count = db.Column(db.Integer, nullable=False)
