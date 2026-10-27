import os
from datetime import date

from app import create_app
from app.backup import backup_real_database_on_startup
from app.database_files import describe_database


app = create_app()


if __name__ == "__main__":
    # debug=True では、Flaskが、コードの変更を見張るプロセスと、アプリを
    # 動かすプロセス（コードを変えるたびに起動し直す）の2つで動く。
    # 起動のときの処理は、見張るほう（最初の起動）でだけ、1回行う。
    # アプリを動かすほうには、環境変数 WERKZEUG_RUN_MAIN が付く。
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print(describe_database(app))
        # 実データのDBの、その日の自動バックアップ
        # （その日の分があれば作らない）
        backup_real_database_on_startup(app, date.today())
    app.run(host="127.0.0.1", port=5001, debug=True)
