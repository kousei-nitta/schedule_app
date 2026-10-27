import os
from datetime import date

from app import create_app
from app.backup import backup_real_database_on_startup
from app.database_files import describe_database


app = create_app()


if __name__ == "__main__":
    # デバッグモードは、環境変数 FLASK_DEBUG が 1 のときだけ使う
    # （例：FLASK_DEBUG=1 python run.py）。デバッグモードでは、エラーの
    # 画面から、サーバーの中でコードを実行できる道具（デバッガー）が動く
    # ため、ふだん（実データで使うとき）はオフにする。1 だけにするのは、
    # Flaskの決まり（0・false・no 以外はオン）では、FLASK_DEBUG=off の
    # ような書き方でもオンになってしまうため。
    # docs/architecture/security.md の「debug（デバッグモード）」。
    debug = os.environ.get("FLASK_DEBUG") == "1"

    # デバッグモードでは、Flaskが、コードの変更を見張るプロセスと、アプリを
    # 動かすプロセス（コードを変えるたびに起動し直す）の2つで動く。
    # 起動のときの処理は、見張るほう（最初の起動）でだけ、1回行う。
    # アプリを動かすほうには、環境変数 WERKZEUG_RUN_MAIN が付く。
    # デバッグモードでないときは、プロセスは1つで、この値は付かない。
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print(describe_database(app))
        if debug:
            print(
                "デバッグモード：オン（FLASK_DEBUG）。開発のときだけ"
                "使ってください"
            )
        # 実データのDBの、その日の自動バックアップ
        # （その日の分があれば作らない）
        backup_real_database_on_startup(app, date.today())
    app.run(host="127.0.0.1", port=5001, debug=debug)
