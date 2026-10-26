"""このアプリの自作のコマンド（flask --app app <コマンド> で動かす）。

- backup-db：使っているDBのバックアップを取る（手動）
- create-demo-db：デモ用の架空のデータのDBを作る

使うDBは、アプリと同じ設定（環境変数 DATABASE_URL）で決まる。
"""
from datetime import date, datetime

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app.backup import BackupError, create_backup, manual_backup_path
from app.database_files import database_file_path
from app.demo_data import DemoDataError, create_demo_database


@click.command("backup-db")
@click.option(
    "--label",
    default="manual",
    show_default=True,
    help="バックアップの名前に入れる言葉（英数字・-・_）。例：before-025",
)
@with_appcontext
def backup_db_command(label: str) -> None:
    """使っているDB（SQLiteのファイル）のバックアップを取る。"""
    database_path = database_file_path(current_app)
    if database_path is None:
        raise click.ClickException(
            "バックアップできるのは、SQLiteのファイルのDBだけです"
        )

    try:
        backup_path = manual_backup_path(database_path, datetime.now(), label)
        counts = create_backup(database_path, backup_path)
    except BackupError as error:
        # ClickException は、メッセージを表示して、終了コード1で終わる
        raise click.ClickException(str(error)) from error

    click.echo(f"バックアップを作りました：{backup_path}")
    counts_text = "、".join(
        f"{table_name} {count}件" for table_name, count in counts.items()
    )
    click.echo(f"各テーブルの件数（元のDBと同じことを確かめました）：{counts_text}")


@click.command("create-demo-db")
@click.option(
    "--replace",
    is_flag=True,
    help=(
        "このコマンドで作ったデモのDBがすでにあれば、消して作り直す"
        "（ほかのDB・実データのDB・バックアップは、作り直さない）"
    ),
)
@with_appcontext
def create_demo_db_command(replace: bool) -> None:
    """使っているDBのファイルに、デモ用の架空のデータを作る。

    実データのDBには作らない。例：
    DATABASE_URL=sqlite:///demo.db flask --app app create-demo-db
    """
    try:
        counts = create_demo_database(current_app, date.today(), replace)
    except DemoDataError as error:
        raise click.ClickException(str(error)) from error

    database_path = database_file_path(current_app)
    click.echo(f"デモデータのDBを作りました：{database_path}")
    counts_text = "、".join(
        f"{name} {count}件" for name, count in counts.items()
    )
    click.echo(f"件数：{counts_text}")
    click.echo(
        "このDBで起動するときは、同じ DATABASE_URL を付けて、"
        "python run.py を実行してください"
    )


def register_commands(app: Flask) -> None:
    """自作のコマンドを、アプリに登録する（create_app から呼ぶ）。"""
    app.cli.add_command(backup_db_command)
    app.cli.add_command(create_demo_db_command)
