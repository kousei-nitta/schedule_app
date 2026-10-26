"""デモ用の架空のデータ（コマンド flask --app app create-demo-db）。

実データに触れずに、画面を確かめたり、見せたりするためのDBを作る。
使い方と守り（実データのDBには作らない、など）は、
docs/development/database.md の「デモ用の架空のデータ」。

データは、画面から登録したときと同じ検査と予定の自動生成を通すため、
アプリのAPIを、Flaskの test_client で呼んで登録する（HTTPのサーバーは
起動しない）。日付は、すべて今日からの相対で決める（いつ作っても、
今日を含む学期・直近の締切・期限切れが表示されるように）。
登場する授業・教室・派遣会社などは、すべて架空のもの。
"""
from datetime import date, timedelta
from pathlib import Path

from flask import Flask
from flask.testing import FlaskClient
from flask_migrate import upgrade

from app.database_files import (
    database_file_path,
    is_in_real_backup_directory,
    is_real_database,
)
from app.extensions import db
from app.models import Closure, Event, Semester, Subject, Task

# デモのDBの印。SQLiteのファイルの見出しの application_id（ファイルの
# 69〜72バイト目。アプリは使わない欄）に書く値。「DEMO」の4文字を、
# 数にしたもの。--replace は、この印のあるファイル（このコマンドで
# 作ったデモのDB）だけを作り直す（ほかのDBを、うっかり消さないため）
DEMO_APPLICATION_ID = 0x44454D4F

# migrationのフォルダ（リポジトリの migrations/）。コマンドを動かした
# 場所によらず、同じフォルダを使うため、このファイルからの位置で決める
MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"

# 架空の授業（weekday：0=月曜〜6=日曜。授業APIと同じ）
DEMO_SUBJECTS = [
    {
        "subject_name": "プログラミング演習",
        "room": "A棟201",
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "11:00",
        "notes": "ノートPCを持参する",
    },
    {
        "subject_name": "線形代数",
        "room": "B棟105",
        "weekday": 1,
        "start_time": "11:00",
        "end_time": "12:00",
    },
    {
        "subject_name": "英語コミュニケーション",
        "room": "C棟302",
        "weekday": 2,
        "start_time": "13:00",
        "end_time": "15:00",
    },
    {
        "subject_name": "データベース入門",
        "room": "A棟303",
        "weekday": 3,
        "start_time": "09:00",
        "end_time": "10:00",
    },
    {
        "subject_name": "情報倫理",
        "room": "B棟210",
        "weekday": 3,
        "start_time": "15:00",
        "end_time": "17:00",
    },
    {
        "subject_name": "統計学",
        "room": "C棟101",
        "weekday": 4,
        "start_time": "10:00",
        "end_time": "12:00",
    },
]


class DemoDataError(Exception):
    """デモデータを作れなかったときの例外。理由を、日本語の文で持つ。"""


def monday_of(day: date) -> date:
    """day を含む週の月曜日を返す。"""
    return day - timedelta(days=day.weekday())


def semester_name(today: date) -> str:
    """今日を含む学期の名前（例：2026年度 後期）。

    年度は4月始まり（1〜3月は前年度）。4〜8月を前期、9〜3月を後期にする
    （画面の学期の登録の初期値と同じ区切り。docs/ui_ux.md の「学期」）。
    """
    fiscal_year = today.year if today.month >= 4 else today.year - 1
    term = "前期" if 4 <= today.month <= 8 else "後期"
    return f"{fiscal_year}年度 {term}"


def semester_period(today: date) -> tuple[date, date]:
    """学期の期間：今日が6週目に入る、15週間（月曜日から日曜日まで）。"""
    start_date = monday_of(today) - timedelta(weeks=5)
    end_date = start_date + timedelta(weeks=15) - timedelta(days=1)
    return start_date, end_date


def is_demo_database_file(path: Path) -> bool:
    """path が、このコマンドで作ったデモのDB（印のあるSQLiteのファイル）か。

    SQLiteのファイルの先頭100バイト（見出し）を読んで確かめる。DBとして
    開かないので、ファイルを変えない。見出しの形は、SQLiteの資料の
    「Database File Format」のとおり（先頭16バイトが決まった文字、
    69〜72バイト目が application_id）。
    """
    with path.open("rb") as file:
        header = file.read(100)
    if len(header) < 100 or not header.startswith(b"SQLite format 3\x00"):
        return False
    application_id = int.from_bytes(header[68:72], "big")
    return application_id == DEMO_APPLICATION_ID


def check_demo_target(app: Flask, replace: bool) -> Path:
    """デモデータを作るDBのファイルを確かめ、そのパスを返す。

    実データのDB、実データのDBのバックアップのフォルダ（instance/backups/）
    の中のファイル、SQLite以外のDB、すでにあるファイル（replace でないとき）
    、このコマンドで作ったデモのDBでないファイル（replace のとき）では、
    DemoDataError（何も変えない）。
    """
    database_path = database_file_path(app)
    if database_path is None:
        raise DemoDataError(
            "デモデータを作れるのは、SQLiteのファイルのDBだけです"
        )
    if is_real_database(database_path, app):
        raise DemoDataError(
            "実データのDB（instance/app.db）には、デモデータを作れません。"
            "環境変数 DATABASE_URL で、別のファイルを指定してください"
            "（例：DATABASE_URL=sqlite:///demo.db）"
        )
    if is_in_real_backup_directory(database_path, app):
        # バックアップは、実データを守る最後の手段のため、置き換えない
        raise DemoDataError(
            "実データのDBのバックアップのフォルダ（instance/backups/）の"
            "中には、デモデータを作れません。別のファイルを指定してください"
        )
    if database_path.exists() and not replace:
        raise DemoDataError(
            f"DBのファイルが、すでにあります：{database_path}"
            "（作り直すときは、--replace を付けてください）"
        )
    if database_path.exists() and not is_demo_database_file(database_path):
        raise DemoDataError(
            f"このファイルは、create-demo-db で作ったデモのDBではないため、"
            f"作り直せません：{database_path}（消してよいファイルなら、"
            "自分で消してから、もう一度実行してください）"
        )
    return database_path


def call_api(
    client: FlaskClient,
    method: str,
    url: str,
    body: dict,
    expected_status: int,
) -> dict:
    """APIを呼び、期待した状態コードでなければ、DemoDataError にする。"""
    response = client.open(url, method=method, json=body)
    if response.status_code != expected_status:
        raise DemoDataError(
            f"{method} {url} が失敗しました"
            f"（{response.status_code}：{response.get_json()}）"
        )
    return response.get_json()


def register_demo_data(client: FlaskClient, today: date) -> None:
    """架空の学期・授業・休講日・予定・課題を、APIで登録する。"""
    this_monday = monday_of(today)
    next_monday = this_monday + timedelta(weeks=1)
    start_date, end_date = semester_period(today)

    semester = call_api(
        client,
        "POST",
        "/api/semesters",
        {
            "name": semester_name(today),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        201,
    )

    # 休講日：過去に1日（3週目の月曜日）、これからに1日（来週の水曜日）
    closures = [
        (start_date + timedelta(weeks=2), "大学の休業日"),
        (next_monday + timedelta(days=2), "創立記念日"),
    ]
    for closure_date, name in closures:
        call_api(
            client,
            "POST",
            "/api/closures",
            {
                "semester_id": semester["id"],
                "date": closure_date.isoformat(),
                "name": name,
            },
            201,
        )

    # 授業（登録すると、学期の毎週の予定が、休講日を除いて自動でできる）
    subject_ids = {}
    for subject_values in DEMO_SUBJECTS:
        subject = call_api(
            client,
            "POST",
            "/api/subjects",
            {"semester_id": semester["id"], **subject_values},
            201,
        )
        subject_ids[subject["subject_name"]] = subject["id"]

    # カレンダーから登録する予定（単発の授業・アルバイト・その他）
    events = [
        {
            "category": "class",
            "subject_id": subject_ids["プログラミング演習"],
            "date": (this_monday + timedelta(days=5)).isoformat(),
            "start_time": "10:00",
            "end_time": "12:00",
            "room": "A棟201",
            "notes": "補講",
        },
        {
            "category": "part_time",
            "title": "倉庫での軽作業",
            "employer": "派遣会社A",
            "date": (this_monday + timedelta(days=1)).isoformat(),
            "start_time": "17:00",
            "end_time": "21:00",
        },
        {
            "category": "part_time",
            "title": "イベントの設営",
            "employer": "派遣会社B",
            "date": (today + timedelta(days=3)).isoformat(),
            "start_time": "18:00",
            "end_time": "22:00",
        },
        {
            "category": "part_time",
            "title": "引っ越しの手伝い",
            "employer": "派遣会社A",
            "date": (next_monday + timedelta(days=5)).isoformat(),
            "start_time": "09:00",
            "end_time": "17:00",
        },
        {
            "category": "other",
            "title": "サークルの練習",
            "date": today.isoformat(),
            "start_time": "19:00",
            "end_time": "20:30",
        },
        {
            "category": "other",
            "title": "インターンシップの説明会",
            "date": (today + timedelta(days=6)).isoformat(),
            "start_time": "14:00",
            "end_time": "16:00",
            "notes": "オンライン",
        },
    ]
    for event in events:
        call_api(client, "POST", "/api/events", event, 201)

    # 課題・タスク：期限切れ・今週・来週・7日より先・完了・締切のみ
    def due(days: int, time_text: str) -> str:
        return f"{(today + timedelta(days=days)).isoformat()}T{time_text}"

    tasks = [
        ("線形代数", "演習問題 第5回", due(-2, "23:59")),
        ("プログラミング演習", "課題3：配列と繰り返し", due(2, "23:59")),
        ("英語コミュニケーション", "エッセイの下書き", due(5, "17:00")),
        ("データベース入門", "ER図のレポート", due(12, "23:59")),
    ]
    for subject_name, title, due_datetime in tasks:
        call_api(
            client,
            "POST",
            "/api/tasks",
            {
                "category": "assignment",
                "subject_id": subject_ids[subject_name],
                "title": title,
                "due_datetime": due_datetime,
            },
            201,
        )

    completed_task = call_api(
        client,
        "POST",
        "/api/tasks",
        {
            "category": "assignment",
            "subject_id": subject_ids["情報倫理"],
            "title": "小レポート 第1回",
            "due_datetime": due(-7, "23:59"),
        },
        201,
    )
    call_api(
        client,
        "PATCH",
        f"/api/tasks/{completed_task['id']}",
        {"is_completed": True},
        200,
    )

    call_api(
        client,
        "POST",
        "/api/tasks",
        {
            "category": "other",
            "title": "図書館の本の返却",
            "due_datetime": due(3, "12:00"),
        },
        201,
    )


def remove_database_files(database_path: Path) -> None:
    """DBのファイルと、SQLiteがその横に作るファイル（-journal など）を消す。

    前に途中で止まったときの、書きかけの記録も残さないため。
    """
    for suffix in ("", "-journal", "-wal", "-shm"):
        database_path.with_name(database_path.name + suffix).unlink(
            missing_ok=True
        )


def count_rows(model) -> int:
    """テーブルの件数を返す。"""
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def create_demo_database(
    app: Flask, today: date, replace: bool = False
) -> dict[str, int]:
    """使っているDBのファイルに、デモデータのDBを作る。各件数を返す。

    replace が True なら、すでにあるデモのDBを消して、作り直す
    （消してよいかは、check_demo_target で確かめる）。途中で失敗したら、
    作りかけのDBを消してから、例外を出し直す（半端なデモのDBを残さない）。
    """
    database_path = check_demo_target(app, replace)

    with app.app_context():
        # 開いている接続を閉じてから、ファイルを消す
        db.engine.dispose()
        remove_database_files(database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 最初に印を書く（途中で失敗して残っても、デモのDBと分かる）
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    f"PRAGMA application_id = {DEMO_APPLICATION_ID}"
                )
            # 空のDBに、migrationで、テーブルを作る
            upgrade(directory=str(MIGRATIONS_DIRECTORY))
            register_demo_data(app.test_client(), today)
        except BaseException:
            db.session.remove()
            db.engine.dispose()
            remove_database_files(database_path)
            raise

        return {
            "学期": count_rows(Semester),
            "授業": count_rows(Subject),
            "休講日": count_rows(Closure),
            "予定": count_rows(Event),
            "課題・タスク": count_rows(Task),
        }
