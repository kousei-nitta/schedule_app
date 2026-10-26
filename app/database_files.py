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

# バックアップを置くフォルダの名前（DBのファイルと同じフォルダの中）
BACKUP_DIRECTORY_NAME = "backups"


def real_database_path(app: Flask) -> Path:
    """実データのDB（instance/app.db）のパスを返す。"""
    return Path(app.instance_path) / REAL_DATABASE_FILE_NAME


def real_backup_directory(app: Flask) -> Path:
    """実データのDBのバックアップのフォルダ（instance/backups/）を返す。"""
    return real_database_path(app).parent / BACKUP_DIRECTORY_NAME


def is_same_existing_directory(first: Path, second: Path) -> bool:
    """2つのフォルダが、どちらもあり、同じフォルダかを返す。

    パスの文字が違っても（大文字・小文字の違い、別の場所へのマウント）、
    同じフォルダなら True（samefile で、フォルダそのものを比べる）。
    """
    return first.is_dir() and second.is_dir() and first.samefile(second)


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
    if path.exists() and real_path.exists() and path.samefile(real_path):
        return True
    # 実データのDBがまだないときは、ファイルで比べられない。同じフォルダの、
    # 大文字・小文字だけが違う名前（APP.db など）は、macOSでは同じファイル
    # になるため、実データのDBとして扱う（安全のため、ほかの環境でも同じ）
    same_name = path.name.casefold() == real_path.name.casefold()
    if same_name and is_same_existing_directory(
        path.resolve().parent, real_path.parent
    ):
        return True
    return False


def is_in_real_backup_directory(path: Path, app: Flask) -> bool:
    """path が、実データのDBのバックアップのフォルダの中かを返す。

    instance/backups/ の下のフォルダの中も含む。大文字・小文字の違いや、
    別の場所にマウントしたフォルダでも、同じフォルダなら True。
    """
    backups = real_backup_directory(app)
    resolved_path = path.resolve()
    if resolved_path.is_relative_to(backups.resolve()):
        return True
    for parent in resolved_path.parents:
        if is_same_existing_directory(parent, backups):
            return True
    return False


def describe_database(app: Flask) -> str:
    """起動のときに表示する、使っているDBの説明を返す。"""
    path = database_file_path(app)
    if path is None:
        # URLにパスワードが含まれていても、表示しない
        url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
        location = url.render_as_string(hide_password=True)
        return (
            f"DB：{location}"
            "（SQLiteのファイルではないため、実データのDBかどうかは"
            "判定しません。自動のバックアップは作りません）"
        )
    if is_real_database(path, app):
        return f"DB：{path}（実データのDB）"
    return f"DB：{path}（実データのDBではありません。DATABASE_URL で指定）"
