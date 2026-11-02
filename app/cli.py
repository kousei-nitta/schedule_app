"""このアプリの自作のコマンド（flask --app app <コマンド> で動かす）。

- backup-db：使っているDBのバックアップを取る（手動）
- create-demo-db：デモ用の架空のデータのDBを作る
- create-user・set-password・rename-user・unlock-login：利用者の管理
  （docs/development/database.md の「利用者の管理」）
- show-settings：今の設定（ローカルか本番か、使うDBなど）を表示する
  （秘密の値は表示しない）
- daily-backup：実データのDBの、その日のバックアップ（本番の定期実行の
  タスクから。新しい30個を残す）
- make-transfer-copy：クラウドへ移すための、実データのDBの写し（Mac で）

どのコマンドも、最初に、ローカルか本番か、と使うDBを表示する（本番の
SSH で、設定のファイルを読み忘れて、別のDBを変えてしまわないため）。

使うDBは、アプリと同じ設定（環境変数 DATABASE_URL）で決まる。
パスワードは、引数でなく、表示しない入力で受け取る（コマンドの履歴に
残さないため）。
"""
import os
import platform
import sqlite3
import stat
from pathlib import Path
import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app import clock
from app.auth import auth_logger
from app.backup import (
    AUTO_BACKUP_KEEP_COUNT,
    BackupError,
    backup_directory,
    create_backup,
    create_daily_backup,
    manual_backup_path,
    remove_old_auto_backups,
)
from app.config import PROJECT_ROOT
from app.database_files import (
    database_file_path,
    describe_database,
    is_real_database,
)
from app.demo_data import (
    DEMO_USERNAME,
    DemoDataError,
    check_demo_target,
    create_demo_database,
)
from app.env_file import ENV_FILE_VARIABLE
from app.extensions import db
from app.login_limits import keyed_digest, unlock_login_id
from app.models.user import User
from app.transfer import make_transfer_copy
from app.passwords import (
    MIN_PASSWORD_LENGTH,
    BreachCheckError,
    hash_password,
    is_breached_password,
    is_valid_username,
    password_rule_errors,
)
from app.trusted_devices import end_all_devices
from app.user_sessions import end_all_sessions

SKIP_BREACH_CHECK_HELP = (
    "漏えいしたパスワードの確認（Have I Been Pwned。インターネットに"
    "つなぐ）を省く。つながらないときだけ使う"
)
USERNAME_RULE = (
    "ログインIDは、半角英小文字・数字・_・- の3〜32文字にしてください"
)


def echo_environment() -> None:
    """ローカルか本番か、と使うDBを表示する（どのコマンドも、最初に呼ぶ）。"""
    if current_app.config["PRODUCTION"]:
        mode = "本番（APP_ENV=production）"
    else:
        mode = "ローカル"
    click.echo(f"環境：{mode}。{describe_database(current_app)}")


def refuse_demo_username_in_production(username: str) -> None:
    """本番で、デモの利用者のID（demo）を断る。

    demo は、公開のリポジトリに書かれたIDで、見せるためにパスワードを
    教えることがある。本番のDBに置くと、だれでもログインして、ログインの
    あとの機能を使えるようになる（ADR 0005）。
    """
    if current_app.config["PRODUCTION"] and username == DEMO_USERNAME:
        raise click.ClickException(
            f"本番では、デモの利用者のID（{DEMO_USERNAME}）を使えません"
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
    echo_environment()
    database_path = database_file_path(current_app)
    if database_path is None:
        raise click.ClickException(
            "バックアップできるのは、SQLiteのファイルのDBだけです"
        )

    try:
        backup_path = manual_backup_path(
            database_path, clock.japan_now(), label
        )
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
    echo_environment()
    try:
        # パスワードを入れてもらう前に、作れる場所かを確かめる
        check_demo_target(current_app, replace)
    except DemoDataError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"デモの利用者（ログインID：{DEMO_USERNAME}）のパスワード")
    password = prompt_new_password(DEMO_USERNAME, skip_breach_check)
    try:
        counts = create_demo_database(
            current_app, clock.japan_today(), replace, password=password
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
    echo_environment()
    refuse_demo_username_in_production(username)
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
    echo_environment()
    user = find_user(username)
    password = prompt_new_password(username, skip_breach_check)
    user.password_hash = hash_password(password)
    # 前のパスワードでログインした端末は、すべてログアウトさせ、端末の印も
    # 消す（パスワードが漏れて変えた場合に、他人のログインや印を残さない）
    count = end_all_sessions(user.id)
    end_all_devices(user.id)
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
    echo_environment()
    refuse_demo_username_in_production(new_username)
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
    echo_environment()
    count = unlock_login_id(keyed_digest("login_id", username))
    db.session.commit()
    click.echo(
        f"ログインID {username} の失敗の記録を、{count}件消しました"
    )


def permission_text(path) -> str:
    """ファイル・フォルダの権限（例：700）。ないときは「ありません」。"""
    try:
        return f"{stat.S_IMODE(path.stat().st_mode):o}"
    except OSError:
        return "ありません"


@click.command("show-settings")
@with_appcontext
def show_settings_command() -> None:
    """今の設定を表示する（秘密の値は表示しない）。

    本番の準備（下見）と、SSH で設定のファイルを読めているかの確かめに
    使う（docs/development/deploy.md）。
    """
    echo_environment()
    config = current_app.config
    database_path = database_file_path(current_app)
    lines = [
        f"PUBLIC_ORIGIN：{config['PUBLIC_ORIGIN'] or 'なし（ローカル）'}",
        f"受け付ける Host：{'・'.join(config['TRUSTED_HOSTS'])}",
        "接続元のヘッダー："
        f"{config['CLIENT_ADDRESS_HEADER'] or 'なし（ローカル）'}",
        f"ログインの Cookie：{config['AUTH_COOKIE_NAME']}"
        f"（Secure：{'オン' if config['AUTH_COOKIE_SECURE'] else 'オフ'}）",
        f"端末の印の Cookie：{config['DEVICE_COOKIE_NAME']}",
        # 秘密の鍵そのものは表示しない（長さだけ）
        f"SECRET_KEY：あり（{len(config['SECRET_KEY'])}文字）",
        "設定のファイル："
        + (os.environ.get(ENV_FILE_VARIABLE, "").strip() or "なし"),
        f"本文の上限：{config['MAX_CONTENT_LENGTH']}バイト",
        f"Python：{platform.python_version()}、SQLite：{sqlite3.sqlite_version}",
    ]
    if database_path is not None:
        lines.append(
            f"DBのファイルの権限：{permission_text(database_path)}、"
            f"DBのフォルダの権限：{permission_text(database_path.parent)}"
        )
    for line in lines:
        click.echo(line)


def folder_size_text(directory: Path) -> str:
    """フォルダの中のファイルの大きさの合計（MB）。"""
    if not directory.is_dir():
        return "0MB"
    total = sum(
        path.stat().st_size for path in directory.iterdir() if path.is_file()
    )
    return f"{total / 1024 / 1024:.1f}MB"


@click.command("daily-backup")
@with_appcontext
def daily_backup_command() -> None:
    """実データのDBの、その日（日本時間）のバックアップを作る。

    本番の定期実行のタスクから、毎日動かす（docs/development/deploy.md）。
    その日の分がなければ作り、自動のバックアップを、新しい30個だけ残す。
    作れなければ、終了コード1で終わる（定期実行のタスクの記録に残る）。
    """
    echo_environment()
    database_path = database_file_path(current_app)
    if database_path is None or not is_real_database(
        database_path, current_app
    ):
        raise click.ClickException(
            "毎日のバックアップを作れるのは、実データのDBだけです"
        )
    today = clock.japan_today()
    try:
        backup_path = create_daily_backup(database_path, today)
    except BackupError as error:
        raise click.ClickException(str(error)) from error
    if backup_path is None:
        click.echo("今日の分は、作成済みです")
    else:
        click.echo(f"バックアップを作りました：{backup_path}")
    removed_paths = remove_old_auto_backups(database_path, today)
    if removed_paths:
        click.echo(
            f"古い自動のバックアップを{len(removed_paths)}個消しました"
            f"（新しい{AUTO_BACKUP_KEEP_COUNT}個を残します）"
        )
    directory = backup_directory(database_path)
    click.echo(f"バックアップのフォルダの合計：{folder_size_text(directory)}")


@click.command("make-transfer-copy")
@click.argument("output", type=click.Path(path_type=Path))
@with_appcontext
def make_transfer_copy_command(output: Path) -> None:
    """クラウドへ移すための、実データのDBの写しを作る（Mac で使う）。

    元のDBは変えない。写しには、ログイン中の端末・ログインの失敗・端末の
    印の行と、ファイルの空き領域を持ち込まない（app/transfer.py）。
    OUTPUT は、リポジトリのフォルダの外のパス（例：~/Desktop/transfer.db）。
    """
    echo_environment()
    if current_app.config["PRODUCTION"]:
        raise click.ClickException(
            "移行の写しは、Mac（ローカル）で作ります"
        )
    source = database_file_path(current_app)
    if source is None:
        raise click.ClickException(
            "写せるのは、SQLiteのファイルのDBだけです"
        )
    output = output.expanduser().absolute()
    if output.resolve().is_relative_to(PROJECT_ROOT):
        raise click.ClickException(
            "写しは、リポジトリのフォルダの外に作ってください"
            "（Git に入れないため。例：~/Desktop/transfer.db）"
        )
    try:
        result = make_transfer_copy(source, output)
    except BackupError as error:
        raise click.ClickException(str(error)) from error

    click.echo(f"移行の写しを作りました：{output}（持ち主だけが読める600）")
    removed_text = "、".join(
        f"{table} {count}件" for table, count in result["removed"].items()
    )
    click.echo(f"消した行：{removed_text or 'なし'}")
    counts_text = "、".join(
        f"{table} {count}件" for table, count in result["counts"].items()
    )
    click.echo(f"写しの各テーブルの件数：{counts_text}")
    click.echo(f"migration の版：{result['version']}")
    click.echo(
        "送ったら、この写しを消してください（rm）。本番では、写しに "
        "flask db upgrade を当ててから使います（docs/development/deploy.md）"
    )


def register_commands(app: Flask) -> None:
    """自作のコマンドを、アプリに登録する（create_app から呼ぶ）。"""
    app.cli.add_command(backup_db_command)
    app.cli.add_command(create_demo_db_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(set_password_command)
    app.cli.add_command(rename_user_command)
    app.cli.add_command(unlock_login_command)
    app.cli.add_command(show_settings_command)
    app.cli.add_command(daily_backup_command)
    app.cli.add_command(make_transfer_copy_command)
