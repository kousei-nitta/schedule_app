"""本番（APP_ENV=production）で、起動のときに確かめること・整えること。

仕様は docs/architecture/security.md の「本番の設定」。create_app が、
本番のときだけ呼ぶ。確かめられなければ、起動しない（ConfigError）。
"""
import os
import stat

from flask import Flask

from app.config import ConfigError
from app.database_files import database_file_path


def check_not_debug(app: Flask) -> None:
    """デバッグモードなら起動しない。

    デバッグモードのエラーの画面には、サーバーの中でコードを動かせる
    道具（Werkzeug のデバッガー）が出る。ログインの確かめより前に動く
    ため、本番では、どんな形でも動かさない。
    """
    if app.debug:
        raise ConfigError(
            "本番では、デバッグモード（FLASK_DEBUG）を使えません"
        )


def check_single_worker() -> None:
    """uWSGI の中で動くとき、ワーカー（プロセス）が1つでなければ起動しない。

    ログインの試行の制限の「判断と記録を1つずつ行う」仕組みと、
    パスワードの確かめの数の上限は、1つのプロセスの中の鍵で守っている
    （app/login_limits.py・app/routes/auth.py）。プロセスが2つ以上だと、
    同時の試行で、数え漏れや、上限を超える計算が起きうる。
    uwsgi は、uWSGI の中でだけ読み込めるモジュール（SSH のコマンドなど、
    uWSGI の外では、確かめない）。
    """
    try:
        import uwsgi
    except ImportError:
        return
    if uwsgi.numproc != 1:
        raise ConfigError(
            "本番では、uWSGI のワーカーを1つにしてください"
            f"（今は {uwsgi.numproc}。processes = 1。"
            "docs/development/deploy.md）"
        )


def check_database_directory(app: Flask) -> None:
    """DBのフォルダが、あって、持ち主だけが使える（700）ことを確かめる。

    同じサーバーのほかの利用者に、DBとバックアップ（同じフォルダの
    backups/）を読まれないため。
    """
    database_path = database_file_path(app)
    if database_path is None:
        raise ConfigError("本番のDBは、SQLite のファイルにしてください")
    directory = database_path.parent
    try:
        directory_stat = directory.stat()
    except OSError as error:
        raise ConfigError(
            f"本番のDBのフォルダがありません：{directory}"
            f"（mkdir -m 700 {directory}）"
        ) from error
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ConfigError(
            f"本番のDBのフォルダが、フォルダでありません：{directory}"
        )
    if stat.S_IMODE(directory_stat.st_mode) & 0o077:
        raise ConfigError(
            "本番のDBのフォルダを、持ち主だけが使える権限にしてください"
            f"（chmod 700 {directory}）"
        )


def prepare_production(app: Flask) -> None:
    """本番の起動のときに、確かめる・整える（create_app から呼ぶ）。"""
    check_not_debug(app)
    check_single_worker()
    check_database_directory(app)
    # これから作るファイル（DBの記録・バックアップ）を、持ち主だけが
    # 読み書きできる権限で作る（ほかの利用者と同じサーバーのため）
    os.umask(0o077)
