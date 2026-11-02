"""クラウドへ移すための、実データのDBの写し（移行の写し）を作る。

コマンド flask --app app make-transfer-copy（app/cli.py）が、Mac で使う。
手順は docs/development/deploy.md の「実データの移行」。

写しに持ち込まないもの：
- ログイン中の端末（user_sessions）・ログインの失敗（login_failures）・
  端末の印（trusted_devices）の行。Mac の Cookie は、同じ Mac の別の
  サーバーにも送られうるため、その値で本番に入れないように。失敗の記録は、
  本番では鍵（SECRET_KEY）が違い、意味がないため
- DBのファイルの空き領域（消した行の中身が残っていることがある）。
  VACUUM INTO で、使っているページだけの新しいファイルを作る

流れ：読み取り専用で写す（app/backup.py の copy_and_verify。元のDBは
変えない）→ secure_delete をオンにして、3つの表の行を消す → VACUUM INTO →
確かめる → 持ち主だけが読める（0600）正式な名前にする。途中のファイルは、
成功しても失敗しても消す。
"""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app.backup import (
    BackupError,
    copy_and_verify,
    integrity_check_result,
    remove_partial_files,
    table_row_counts,
)
from app.demo_data import DEMO_USERNAME

# 写しで空にする表（上の説明）
TRANSIENT_TABLES = ("user_sessions", "login_failures", "trusted_devices")
# 公開のリポジトリに書かれたログインID（推測されやすい。ADR 0004）
PUBLIC_USERNAME = "owner"


def existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {name for (name,) in rows}


def clear_transient_tables(path: Path) -> dict[str, int]:
    """写し（途中のファイル）の3つの表の行を、中身を0で消して消す。

    消した件数を返す（表がないDB（Task 026 より前の版）では、その表を
    飛ばす）。
    """
    removed = {}
    with closing(sqlite3.connect(path)) as connection:
        # 消した行の中身を、ファイルの中で0で上書きする（このあとの
        # VACUUM INTO で、空き領域ごと捨てるが、念のため）
        connection.execute("PRAGMA secure_delete = ON")
        tables = existing_tables(connection)
        for table in TRANSIENT_TABLES:
            if table not in tables:
                continue
            cursor = connection.execute(f'DELETE FROM "{table}"')
            removed[table] = cursor.rowcount
        connection.commit()
    return removed


def vacuum_into(source: Path, destination: Path) -> None:
    """空き領域のない、新しいDBのファイルを作る（VACUUM INTO）。"""
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("VACUUM INTO ?", (str(destination),))


def read_only_connection(path: Path) -> sqlite3.Connection:
    """DBを、読み取り専用で開く（確かめるだけで、ファイルを変えない）。"""
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def check_transfer_copy(
    path: Path, source_counts: dict[str, int]
) -> tuple[dict[str, int], str | None]:
    """できた写しを確かめ、各表の件数と、migration の版を返す。"""
    with closing(read_only_connection(path)) as connection:
        check_result = integrity_check_result(connection)
        if check_result != "ok":
            raise BackupError(
                f"写しの検査で、問題が見つかりました：{check_result}"
            )
        free_pages = connection.execute(
            "PRAGMA freelist_count"
        ).fetchone()[0]
        if free_pages != 0:
            raise BackupError(
                f"写しに、空き領域が残っています（{free_pages}ページ）"
            )
        counts = table_row_counts(connection)
        for table, count in source_counts.items():
            expected = 0 if table in TRANSIENT_TABLES else count
            if counts.get(table) != expected:
                raise BackupError(
                    f"写しの {table} の件数が、思ったものと違います"
                    f"（{counts.get(table)}。思ったもの：{expected}）"
                )
        version = None
        if "alembic_version" in counts:
            row = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
            version = None if row is None else row[0]
    return counts, version


def has_user(connection: sqlite3.Connection, username: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM users WHERE username = ?", (username,)
    ).fetchone()
    return row is not None


def check_no_public_username(path: Path) -> None:
    """公開のリポジトリに書かれたID（owner・demo）の利用者がいれば止める。"""
    with closing(read_only_connection(path)) as connection:
        if "users" not in existing_tables(connection):
            return
        has_owner = has_user(connection, PUBLIC_USERNAME)
        has_demo = has_user(connection, DEMO_USERNAME)
    if has_owner:
        raise BackupError(
            f"ログインIDが {PUBLIC_USERNAME} のままの利用者がいます。"
            "公開のリポジトリに書かれたIDのため、先に rename-user で、"
            "推測されにくいIDに変えてください"
        )
    if has_demo:
        # 本番のDBには、デモの利用者を置かない（ADR 0005）。デモのDBを
        # 選んでいる（DATABASE_URL）おそれもある
        raise BackupError(
            f"デモの利用者（{DEMO_USERNAME}）がいます。本番には、デモの"
            "利用者を持ち込みません（実データのDBを選んでいるか、"
            "確かめてください）"
        )


def make_transfer_copy(source: Path, output: Path) -> dict:
    """source のDBから、移行の写しを output に作る。

    返り値：{"counts": 各表の件数、"removed": 消した行の件数、
    "version": migration の版}。作れなければ BackupError（output は
    作らない）。
    """
    if not source.is_file():
        raise BackupError(f"写すDBが見つかりません：{source}")
    if output.exists():
        raise BackupError(f"出力先に、すでにファイルがあります：{output}")
    if not output.parent.is_dir():
        raise BackupError(f"出力先のフォルダがありません：{output.parent}")

    process = os.getpid()
    work_path = output.with_name(f"{output.name}.{process}.work")
    partial_path = output.with_name(f"{output.name}.{process}.partial")
    # 途中のファイル（ログイン中の端末なども入っている）も、最初から、
    # 持ち主だけが読み書きできる権限で作る（umask。終わったら元に戻す）
    previous_umask = os.umask(0o077)
    try:
        source_counts = copy_and_verify(source, work_path)
        check_no_public_username(work_path)
        removed = clear_transient_tables(work_path)
        vacuum_into(work_path, partial_path)
        counts, version = check_transfer_copy(partial_path, source_counts)
        # 持ち主だけが読み書きできる権限にしてから、正式な名前を付ける
        partial_path.chmod(0o600)
        try:
            os.link(partial_path, output)
        except FileExistsError as error:
            raise BackupError(
                f"出力先に、すでにファイルがあります：{output}"
            ) from error
    except (sqlite3.Error, OSError) as error:
        raise BackupError(f"移行の写しを作れませんでした：{error}") from error
    finally:
        remove_partial_files(work_path)
        remove_partial_files(partial_path)
        os.umask(previous_umask)
    return {"counts": counts, "removed": removed, "version": version}
