from app.extensions import db


class User(db.Model):
    """ログインする利用者。

    データ（学期・授業・休講日・予定・課題）は、user_id で、どれかの
    利用者のものになる（docs/architecture/data_model.md の「User」）。
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # ログインID（半角英小文字・数字・_・-、3〜32文字。app/passwords.py）。
    # 同じIDの利用者を2人作らないよう、DBでも一意にする
    username = db.Column(db.String(32), nullable=False, unique=True)
    # パスワードのハッシュ（Werkzeug の scrypt。パスワードそのものは
    # 保存しない）。NULL の利用者は、ログインできない（パスワードを
    # 決める前の owner など）
    password_hash = db.Column(db.String(255), nullable=True)
    # 作った日時（UTC。タイムゾーンなしで保存）
    created_at = db.Column(db.DateTime, nullable=False)
