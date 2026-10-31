"""このアプリの自作のコマンド（flask --app app <コマンド> で動かす）。

- backup-db：使っているDBのバックアップを取る（手動）
- create-demo-db：デモ用の架空のデータのDBを作る
- create-user・set-password・rename-user・unlock-login：利用者の管理
  （docs/development/database.md の「利用者の管理」）

使うDBは、アプリと同じ設定（環境変数 DATABASE_URL）で決まる。
パスワードは、引数でなく、表示しない入力で受け取る（コマンドの履歴に
残さないため）。
"""
from datetime import date, datetime

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app import clock
from app.auth import auth_logger
from app.backup import BackupError, create_backup, manual_backup_path
from app.database_files import database_file_path
from app.demo_data import (
    DEMO_USERNAME,
    DemoDataError,
    check_demo_target,
    create_demo_database,
)
from app.extensions import db
from app.login_limits import keyed_digest, unlock_login_id
from app.models.user import User
from app.passwords import (
    MIN_PASSWORD_LENGTH,
    BreachCheckError,
    hash_password,
    is_breached_password,
    is_valid_username,
    password_rule_errors,
)
from app.user_sessions import end_all_sessions

SKIP_BREACH_CHECK_HELP = (
    "漏えいしたパスワードの確認（Have I Been Pwned。インターネットに"
    "つなぐ）を省く。つながらないときだけ使う"
)
USERNAME_RULE = (
    "ログインIDは、半角英小文字・数字・_・- の3〜32文字にしてください"
)


def prompt_new_password(username: str, skip_breach_check: bool) -> str:
    """新しいパスワードを、表示しない入力で2回受け取り、決まりを確かめる。"""
    password = click.prompt(
        f"パスワード（{MIN_PASSWORD_LENGTH}文字以上。入力は表示されません）",
        hide_input=True,
        confirmation_prompt="確認のため、もう一度入れてください",
    )
    errors = password_rule_errors(password, username)
    if errors:
        raise click.ClickException("\n".join(errors))
    if skip_breach_check:
        click.echo("漏えいしたパスワードの確認を省きました")
        return password
    try:
        breached = is_breached_password(password)
    except BreachCheckError as error:
        raise click.ClickException(
            f"{error}。ネットワークを確かめて、もう一度実行してください"
            "（どうしても確かめられないときは、--skip-breach-check）"
        ) from error
    if breached:
        raise click.ClickException(
            "このパスワードは、漏えいしたパスワードの一覧にあります"
            "（ほかのサイトから漏れて、攻撃に使われるもの）。"
            "別のパスワードにしてください"
        )
    return password


def find_user(username: str) -> User:
    """ログインIDの利用者。いなければ、エラーで終わる。"""
    user = db.session.scalar(db.select(User).where(User.username == username))
    if user is None:
        raise click.ClickException(f"利用者 {username} がいません")
    return user


def check_new_username(username: str) -> None:
    """新しいログインIDの形式と、重ならないことを確かめる。"""
    if not is_valid_username(username):
        raise click.ClickException(USERNAME_RULE)
    exists = db.session.scalar(
        db.select(User.id).where(User.username == username)
    )
    if exists is not None:
        raise click.ClickException(f"利用者 {username} は、すでにいます")


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
@click.option("--skip-breach-check", is_flag=True, help=SKIP_BREACH_CHECK_HELP)
@with_appcontext
def create_demo_db_command(replace: bool, skip_breach_check: bool) -> None:
    """使っているDBのファイルに、デモ用の架空のデータを作る。

    実データのDBには作らない。データは、利用者 demo のもの（パスワードの
    入力を求める）。例：
    DATABASE_URL=sqlite:///demo.db flask --app app create-demo-db
    """
    try:
        # パスワードを入れてもらう前に、作れる場所かを確かめる
        check_demo_target(current_app, replace)
    except DemoDataError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"デモの利用者（ログインID：{DEMO_USERNAME}）のパスワード")
    password = prompt_new_password(DEMO_USERNAME, skip_breach_check)
    try:
        counts = create_demo_database(
            current_app, date.today(), replace, password=password
        )
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


@click.command("create-user")
@click.argument("username")
@click.option("--skip-breach-check", is_flag=True, help=SKIP_BREACH_CHECK_HELP)
@with_appcontext
def create_user_command(username: str, skip_breach_check: bool) -> None:
    """利用者を作る（パスワードの入力を求める）。"""
    check_new_username(username)
    password = prompt_new_password(username, skip_breach_check)
    user = User(
        username=username,
        password_hash=hash_password(password),
        created_at=clock.utc_now(),
    )
    db.session.add(user)
    db.session.commit()
    auth_logger.info("利用者を作りました（利用者：%s）", user.id)
    click.echo(f"利用者 {username} を作りました")


@click.command("set-password")
@click.argument("username")
@click.option("--skip-breach-check", is_flag=True, help=SKIP_BREACH_CHECK_HELP)
@with_appcontext
def set_password_command(username: str, skip_breach_check: bool) -> None:
    """利用者のパスワードを決める・変える。すべての端末からログアウトする。"""
    user = find_user(username)
    password = prompt_new_password(username, skip_breach_check)
    user.password_hash = hash_password(password)
    # 前のパスワードでログインした端末は、すべてログアウトさせる
    # （パスワードが漏れて変えた場合に、他人のログインを残さない）
    count = end_all_sessions(user.id)
    db.session.commit()
    auth_logger.info(
        "パスワードを変えました（利用者：%s、ログアウトした端末：%s台）",
        user.id,
        count,
    )
    click.echo(
        f"利用者 {username} のパスワードを決めました"
        f"（ログイン中だった端末 {count}台を、ログアウトしました）"
    )


@click.command("rename-user")
@click.argument("username")
@click.argument("new_username")
@with_appcontext
def rename_user_command(username: str, new_username: str) -> None:
    """利用者のログインIDを変える（推測されにくいIDにするときなど）。"""
    user = find_user(username)
    check_new_username(new_username)
    user.username = new_username
    db.session.commit()
    auth_logger.info("ログインIDを変えました（利用者：%s）", user.id)
    click.echo(f"ログインIDを {username} から {new_username} に変えました")
    # パスワードは、ハッシュしかないため、新しいIDを含むかを確かめられない
    click.echo(
        "今のパスワードに、新しいIDが含まれているときは、"
        f"set-password {new_username} で変えてください"
    )


@click.command("unlock-login")
@click.argument("username")
@with_appcontext
def unlock_login_command(username: str) -> None:
    """ログインの試行の制限を解く（そのログインIDの失敗の記録を消す）。

    他人にわざと失敗され、締め出されたときに使う。何度も締め出される
    なら、rename-user で、推測されにくいIDに変える。
    """
    count = unlock_login_id(keyed_digest("login_id", username))
    db.session.commit()
    click.echo(
        f"ログインID {username} の失敗の記録を、{count}件消しました"
    )


def register_commands(app: Flask) -> None:
    """自作のコマンドを、アプリに登録する（create_app から呼ぶ）。"""
    app.cli.add_command(backup_db_command)
    app.cli.add_command(create_demo_db_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(set_password_command)
    app.cli.add_command(rename_user_command)
    app.cli.add_command(unlock_login_command)
