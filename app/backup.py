"""DB（SQLiteのファイル）のバックアップ。

- 自動：run.py の起動のとき、実データのDB（instance/app.db）の、その日の
  バックアップを1つ作る（backup_real_database_on_startup）
- 手動：コマンド flask --app app backup-db（app/cli.py）

仕様は docs/architecture/overview.md の「データの保護（バックアップ）」。
元のDBは、読み取り専用で開く（バックアップの処理で、元のDBを変えないため）。
"""
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from flask import Flask

from app.database_files import database_file_path, is_real_database

# バックアップを置くフォルダの名前（DBのファイルと同じフォルダの中）
BACKUP_DIRECTORY_NAME = "backups"

# 自動のバックアップを残す数（新しいものから）。手動のものは数えず、消さない
AUTO_BACKUP_KEEP_COUNT = 30

# 手動のバックアップの名前に入れるラベル。ファイル名に使うため、
# 英数字・「-」・「_」だけにする
LABEL_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,40}")


class BackupError(Exception):
    """バックアップを作れなかったときの例外。理由を、日本語の文で持つ。"""


def backup_directory(database_path: Path) -> Path:
    """バックアップを置くフォルダ（DBのファイルと同じフォルダの backups/）。

    実データのDB（instance/app.db）なら、instance/backups/ になる。
    """
    return database_path.parent / BACKUP_DIRECTORY_NAME


def auto_backup_path(database_path: Path, today: date) -> Path:
    """自動のバックアップのパス（例：backups/app-20261025-auto.db）。"""
    file_name = f"{database_path.stem}-{today:%Y%m%d}-auto.db"
    return backup_directory(database_path) / file_name


def manual_backup_path(
    database_path: Path, now: datetime, label: str
) -> Path:
    """手動のバックアップのパス。

    例：backups/app-20261025-153012-before-024.db
    """
    if LABEL_PATTERN.fullmatch(label) is None:
        raise BackupError(
            "ラベルは、英数字・「-」・「_」で、1〜40文字にしてください"
        )
    file_name = f"{database_path.stem}-{now:%Y%m%d-%H%M%S}-{label}.db"
    return backup_directory(database_path) / file_name


def table_row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """DBの各テーブルの件数を、テーブルの名前の順で返す。"""
    rows = connection.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        " ORDER BY name"
    ).fetchall()
    counts = {}
    for (table_name,) in rows:
        # テーブルの名前は、このDBのもの。念のため、"" で囲んで使う
        quoted_name = '"' + table_name.replace('"', '""') + '"'
        count = connection.execute(
            f"SELECT COUNT(*) FROM {quoted_name}"
        ).fetchone()[0]
        counts[table_name] = count
    return counts


def integrity_check_result(connection: sqlite3.Connection) -> str:
    """SQLiteの検査（PRAGMA integrity_check）の結果を返す。

    問題がなければ ok。
    """
    rows = connection.execute("PRAGMA integrity_check").fetchall()
    return "\n".join(row[0] for row in rows)


def copy_and_verify(database_path: Path, copy_path: Path) -> dict[str, int]:
    """DBを copy_path にコピーし、壊れていないことと、件数を確かめる。

    返り値は、各テーブルの件数。確かめられなければ、BackupError。
    """
    # mode=ro：元のDBを、読み取り専用で開く
    source_uri = database_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(source_uri, uri=True)) as source:
        with closing(sqlite3.connect(copy_path)) as copy:
            # 件数を数えてからコピーが終わるまで、読み取りのトランザクションの
            # 中で行う。その間、ほかの接続（動いているアプリ）の書き込みは
            # 待たされるので、数えた件数とコピーの中身がずれない。
            source.execute("BEGIN")
            source_counts = table_row_counts(source)
            source.backup(copy)
            source.execute("ROLLBACK")

            check_result = integrity_check_result(copy)
            if check_result != "ok":
                raise BackupError(
                    f"コピーしたDBの検査で、問題が見つかりました：{check_result}"
                )
            copy_counts = table_row_counts(copy)
            if copy_counts != source_counts:
                raise BackupError(
                    "コピーしたDBの件数が、元のDBと違います"
                    f"（元：{source_counts}、コピー：{copy_counts}）"
                )
    return source_counts


def create_backup(database_path: Path, backup_path: Path) -> dict[str, int]:
    """database_path のDBのバックアップを、backup_path に作る。

    途中のファイルは「名前.partial」で作り、確かめてから、正式な名前に
    変える（失敗したときに、確かめていないファイルが、バックアップの
    名前で残らないため）。返り値は、各テーブルの件数。
    """
    if not database_path.is_file():
        raise BackupError(
            f"バックアップするDBが見つかりません：{database_path}"
        )
    if backup_path.exists():
        raise BackupError(
            f"同じ名前のバックアップが、すでにあります：{backup_path}"
        )

    partial_path = backup_path.with_name(backup_path.name + ".partial")
    try:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        # 前に失敗したときの途中のファイルが残っていれば、消してから作る
        partial_path.unlink(missing_ok=True)
        counts = copy_and_verify(database_path, partial_path)
        partial_path.rename(backup_path)
    except BackupError:
        partial_path.unlink(missing_ok=True)
        raise
    except (sqlite3.Error, OSError) as error:
        partial_path.unlink(missing_ok=True)
        raise BackupError(
            f"バックアップを作れませんでした：{error}"
        ) from error
    return counts


def create_daily_backup(database_path: Path, today: date) -> Path | None:
    """その日の自動のバックアップを作り、そのパスを返す。

    その日の分がすでにあれば、作らずに None を返す。
    """
    backup_path = auto_backup_path(database_path, today)
    if backup_path.exists():
        return None
    create_backup(database_path, backup_path)
    return backup_path


def remove_old_auto_backups(
    database_path: Path, keep_count: int = AUTO_BACKUP_KEEP_COUNT
) -> list[Path]:
    """自動のバックアップを、新しいものから keep_count 個だけ残して消す。

    消すのは、「DBの名前-YYYYMMDD-auto.db」の形のファイルだけ。手動の
    バックアップや、ほかのファイルは消さない。消したファイルを返す。
    """
    directory = backup_directory(database_path)
    if not directory.is_dir():
        return []
    name_pattern = re.compile(
        re.escape(database_path.stem) + r"-[0-9]{8}-auto\.db"
    )
    auto_backups = [
        path
        for path in directory.iterdir()
        if path.is_file() and name_pattern.fullmatch(path.name)
    ]
    # 名前に日付（YYYYMMDD）が入っているので、名前の順が、日付の順になる
    auto_backups.sort(key=lambda path: path.name, reverse=True)
    old_backups = auto_backups[keep_count:]
    for path in old_backups:
        path.unlink()
    return old_backups


def backup_real_database_on_startup(app: Flask, today: date) -> None:
    """起動のとき（run.py）に、実データのDBの、その日の自動バックアップを作る。

    結果を表示する。失敗しても、例外を外に出さない（バックアップの失敗で、
    アプリを使えなくしないため。警告を見て、手動で取り直す）。
    """
    database_path = database_file_path(app)
    if database_path is None or not is_real_database(database_path, app):
        print("自動のバックアップ：実データのDBではないため、作りません")
        return
    if not database_path.exists():
        print("自動のバックアップ：実データのDBがまだないため、作りません")
        return

    # どんな失敗でも、起動は続ける（上の説明）
    try:
        backup_path = create_daily_backup(database_path, today)
        if backup_path is None:
            print("自動のバックアップ：今日の分は、作成済みです")
            return
        print(f"自動のバックアップを作りました：{backup_path}")
        removed_paths = remove_old_auto_backups(database_path)
    except Exception as error:
        print(
            "警告：自動のバックアップを作れませんでした。"
            "アプリは起動しますが、早めに、flask --app app backup-db で、"
            f"手動のバックアップを取ってください（理由：{error}）"
        )
        return
    if removed_paths:
        print(
            f"古い自動のバックアップを{len(removed_paths)}個消しました"
            f"（新しい{AUTO_BACKUP_KEEP_COUNT}個を残します）"
        )
