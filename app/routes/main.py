from flask import Blueprint, render_template

from app.auth import current_user
from app.user_sessions import count_active_sessions


main = Blueprint("main", __name__)


@main.route("/")
def index():
    # 利用者のメニュー（右上）に、ログインIDと、ログイン中の端末の数を
    # 出す（ほかの端末で、知らないログインがないかに気づけるように）。
    # 値は、Jinja が自動でエスケープする
    user = current_user()
    return render_template(
        "index.html",
        current_username=user.username,
        session_count=count_active_sessions(user.id),
    )
