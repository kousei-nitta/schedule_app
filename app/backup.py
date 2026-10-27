"""DB（SQLiteのファイル）のバックアップ。

- 自動：run.py の起動のとき、実データのDB（instance/app.db）の、その日の
  バックアップを1つ作る（backup_real_database_on_startup）
- 手動：コマンド flask --app app backup-db（app/cli.py）

仕様は docs/architecture/overview.md の「データの保護（バックアップ）」。
元のDBは、読み取り専用で開く（バックアップの処理で、元のDBを変えないため）。
"""
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from flask import Flask

from app.database_files import (
    BACKUP_DIRECTORY_NAME,
    database_file_path,
    is_real_database,
)

# 自動のバックアップを残す数（新しいものから）。手動のものは数えず、消さない
AUTO_BACKUP_KEEP_COUNT = 30

# 手動のバックアップの名前に入れるラベル。ファイル名に使うため、
# 英数字・「-」・「_」だけにする
LABEL_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,40}")

# 元のDBを開くとき、ほかの接続（動いているアプリ）が書き込み中なら、
# 終わるまで最大で何秒待つか（超えると「database is locked」で失敗する）
SQLITE_WAIT_SECONDS = 5

# SQLiteが、DBのファイルの横に作ることがあるファイルの名前の終わり
# （-journal：書きかけの記録、-wal・-shm：WALのモードのときの記録）
SQLITE_COMPANION_SUFFIXES = ("-journal", "-wal", "-shm")


class BackupError(Exception):
    """バックアップを作れなかったときの例外。理由を、日本語の文で持つ。"""


class BackupExistsError(BackupError):
    """同じ名前のバックアップが、すでにあるときの例外。"""


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

    例：backups/app-20261025-153012-before-025.db
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


def companion_paths(path: Path) -> list[Path]:
    """SQLiteが、path の横に作ることがあるファイル（-journal など）を返す。"""
    return [
        path.with_name(path.name + suffix)
        for suffix in SQLITE_COMPANION_SUFFIXES
    ]


def copy_and_verify(database_path: Path, copy_path: Path) -> dict[str, int]:
    """DBを copy_path にコピーし、壊れていないことと、件数を確かめる。

    返り値は、各テーブルの件数。確かめられなければ、BackupError。
    """
    # mode=ro：元のDBを、読み取り専用で開く
    source_uri = database_path.resolve().as_uri() + "?mode=ro"
    source_connection = sqlite3.connect(
        source_uri, uri=True, timeout=SQLITE_WAIT_SECONDS
    )
    with closing(source_connection) as source:
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


def remove_partial_files(partial_path: Path) -> None:
    """途中のファイルと、SQLiteがその横に作ったファイルを消す。

    消せなくても、例外を出さない（後片付けの失敗で、バックアップを
    作れなかった本当の理由が、隠れないようにするため）。
    """
    for path in [partial_path, *companion_paths(partial_path)]:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def failure_message(database_path: Path, error: Exception) -> str:
    """バックアップを作れなかったときの、日本語の説明を返す。"""
    message = f"バックアップを作れませんでした：{error}"
    journal_path = database_path.with_name(database_path.name + "-journal")
    # 書きかけの記録（印のある -journal）があると、読み取り専用では開けず、
    # SQLiteは SQLITE_READONLY_ROLLBACK で失敗する（取り消すために、DBに
    # 書き込む必要があるため）。そのときだけ、次の操作を案内する（-journal
    # は、書き込み中のアプリや、取り消しの要らない古い記録でもあるため、
    # ファイルがあるだけでは、書きかけとは限らない）
    error_name = getattr(error, "sqlite_errorname", None)
    if error_name == "SQLITE_READONLY_ROLLBACK":
        message += (
            f"。書きかけの記録（{journal_path.name}）があります。アプリが"
            "書き込みの途中で止まった可能性があります。アプリを起動して"
            "画面を一度開くと、SQLiteが書きかけを取り消します。そのあとで、"
            "もう一度バックアップを取ってください"
            "（docs/development/database.md の「実データのDBの扱い」）。"
            "ただし、バックアップから戻す作業の途中（cp で戻したあと）なら、"
            "画面を開かないでください（起動のときにこの表示が出たら、画面を"
            "開かずに Ctrl+C でサーバーを止める）。記録は戻す前のDBのもので、"
            "画面を開くと、戻したDBに書き戻されます。記録を instance/backups/"
            " へ移し、戻すところからやり直します（同じ資料の"
            "「バックアップから戻す」）"
        )
    return message


def create_backup(database_path: Path, backup_path: Path) -> dict[str, int]:
    """database_path のDBのバックアップを、backup_path に作る。

    途中のファイルは「名前.<プロセス番号>.partial」で作り、確かめてから、
    正式な名前を付ける（失敗したときに、確かめていないファイルが、
    バックアップの名前で残らないため）。返り値は、各テーブルの件数。
    """
    if not database_path.is_file():
        raise BackupError(
            f"バックアップするDBが見つかりません：{database_path}"
        )
    if backup_path.exists():
        raise BackupExistsError(
            f"同じ名前のバックアップが、すでにあります：{backup_path}"
        )
    directory = backup_path.parent
    if directory.is_symlink() and not directory.exists():
        raise BackupError(
            "バックアップのフォルダはリンクですが、リンク先がありません"
            f"（外部のディスクを外している、など）：{directory}"
        )
    if directory.exists() and not directory.is_dir():
        raise BackupError(
            f"バックアップのフォルダの場所に、フォルダでないものがあります："
            f"{directory}"
        )

    # 途中のファイルの名前に、プロセス番号を入れる（同時に2つの処理が
    # 同じ名前のバックアップを作っても、互いの途中のファイルを消さないため）
    partial_path = backup_path.with_name(
        f"{backup_path.name}.{os.getpid()}.partial"
    )
    try:
        directory.mkdir(parents=True, exist_ok=True)
        counts = copy_and_verify(database_path, partial_path)
        # 正式な名前を付ける。os.link は、同じ名前のファイルがあると失敗する
        # （rename は黙って上書きするため使わない。確かめたバックアップを、
        # ほかの処理が作ったファイルで上書きしないように）。途中のファイルは、
        # 下の finally で消す（正式な名前のファイルは残る）
        try:
            os.link(partial_path, backup_path)
        except FileExistsError as error:
            # この1行の FileExistsError だけを「すでにある」とする（フォルダ
            # を作るときなど、ほかの FileExistsError と取り違えないため）
            raise BackupExistsError(
                f"同じ名前のバックアップが、すでにあります：{backup_path}"
            ) from error
    except (sqlite3.Error, OSError) as error:
        raise BackupError(failure_message(database_path, error)) from error
    finally:
        remove_partial_files(partial_path)
    return counts


def create_daily_backup(database_path: Path, today: date) -> Path | None:
    """その日の自動のバックアップを作り、そのパスを返す。

    その日の分がすでにあれば（ほかの処理が、同時に作った場合を含む）、
    作らずに None を返す。
    """
    backup_path = auto_backup_path(database_path, today)
    if backup_path.exists():
        return None
    try:
        create_backup(database_path, backup_path)
    except BackupExistsError:
        # 本当にあるときだけ、作成済みとする（ないのに「作成済み」と
        # 表示して、バックアップが黙って作られなくなるのを防ぐため）
        if backup_path.is_file():
            return None
        raise
    return backup_path


def remove_old_auto_backups(
    database_path: Path,
    today: date,
    keep_count: int = AUTO_BACKUP_KEEP_COUNT,
) -> list[Path]:
    """自動のバックアップを、新しいものから keep_count 個だけ残して消す。

    消すのは、「DBの名前-YYYYMMDD-auto.db」の形のファイルだけ。手動の
    バックアップや、ほかのファイルは消さない。日付が今日より後の名前の
    ファイル（Macの時計が一時的にずれていた場合など）は、数えず、消さない
    （数えると、今日作ったものが、古いものとして消えてしまうため）。
    消したファイルを返す。
    """
    directory = backup_directory(database_path)
    if not directory.is_dir():
        return []
    name_pattern = re.compile(
        re.escape(database_path.stem) + r"-([0-9]{8})-auto\.db"
    )
    today_text = f"{today:%Y%m%d}"
    auto_backups = []
    for path in directory.iterdir():
        match = name_pattern.fullmatch(path.name)
        if match is None or not path.is_file():
            continue
        # YYYYMMDD は桁が決まっているので、文字列の大小で日付を比べられる
        if match.group(1) > today_text:
            continue
        auto_backups.append(path)
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
    if database_path is None:
        print("自動のバックアップ：SQLiteのファイルではないため、作りません")
        return
    if not is_real_database(database_path, app):
        print("自動のバックアップ：実データのDBではないため、作りません")
        return
    if not database_path.exists():
        print("自動のバックアップ：実データのDBがまだないため、作りません")
        return

    # どんな失敗でも、起動は続ける（上の説明）
    try:
        backup_path = create_daily_backup(database_path, today)
    except Exception as error:
        print(
            "警告：自動のバックアップを作れませんでした。"
            "アプリは起動しますが、早めに、flask --app app backup-db で、"
            f"手動のバックアップを取ってください（理由：{error}）"
        )
        return
    if backup_path is None:
        print("自動のバックアップ：今日の分は、作成済みです")
        return
    print(f"自動のバックアップを作りました：{backup_path}")

    # 古いものを消せなくても、今日のバックアップは作れている
    try:
        removed_paths = remove_old_auto_backups(database_path, today)
    except Exception as error:
        print(
            "警告：古い自動のバックアップを消せませんでした"
            f"（今日のバックアップは作れています。理由：{error}）"
        )
        return
    if removed_paths:
        print(
            f"古い自動のバックアップを{len(removed_paths)}個消しました"
            f"（新しい{AUTO_BACKUP_KEEP_COUNT}個を残します）"
        )
