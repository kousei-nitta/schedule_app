"""使っているDBのファイルの場所と、実データのDBかどうかの判定。

自動のバックアップ（app/backup.py）、デモデータ（app/demo_data.py）、
起動のときの表示（run.py）で使う。
"""
from pathlib import Path

from flask import Flask
from sqlalchemy.engine import make_url

# 実データのDBのファイル名（instance/ の中）。config.py の
# DEFAULT_DATABASE_URI（sqlite:///app.db）が指すファイル。
REAL_DATABASE_FILE_NAME = "app.db"


def real_database_path(app: Flask) -> Path:
    """実データのDB（instance/app.db）のパスを返す。"""
    return Path(app.instance_path) / REAL_DATABASE_FILE_NAME


def database_file_path(app: Flask) -> Path | None:
    """使っているDBが、SQLiteのファイルなら、そのパスを返す。

    SQLite以外のDB（将来のクラウドのDBなど）と、メモリ上のSQLiteでは、
    None を返す。相対パスは、Flask-SQLAlchemyと同じく、instance/ からの
    パスとして扱う（sqlite:///app.db → instance/app.db）。
    """
    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if url.get_backend_name() != "sqlite":
        return None
    if url.database in (None, "", ":memory:"):
        return None
    # 「file:…?uri=true」の形の指定は、このアプリでは扱わない
    if url.query.get("uri"):
        return None

    path = Path(url.database)
    if not path.is_absolute():
        path = Path(app.instance_path) / path
    return path


def is_real_database(path: Path, app: Flask) -> bool:
    """path が、実データのDB（instance/app.db）を指すかを返す。

    別の書き方（../ を含むパス、大文字・小文字の違いなど）でも、同じ
    ファイルなら True。
    """
    real_path = real_database_path(app)
    if path.resolve() == real_path.resolve():
        return True
    # パスの文字が違っても、同じファイルのことがある。macOSの既定の
    # ファイルシステムは大文字・小文字を区別しない（APP.db も app.db）。
    # ハードリンクや、別の場所にマウントしたフォルダも同じ。両方の
    # ファイルがあれば、ファイルそのもの（samefile）で比べる。
    if path.exists() and real_path.exists():
        return path.samefile(real_path)
    return False


def describe_database(app: Flask) -> str:
    """起動のときに表示する、使っているDBの説明を返す。"""
    path = database_file_path(app)
    if path is None:
        # URLにパスワードが含まれていても、表示しない
        url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
        location = url.render_as_string(hide_password=True)
        return f"DB：{location}（実データのDBではありません）"
    if is_real_database(path, app):
        return f"DB：{path}（実データのDB）"
    return f"DB：{path}（実データのDBではありません。DATABASE_URL で指定）"
