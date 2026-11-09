"""日本時間の「今日」（app/clock.py。Task 026）。

クラウドのサーバーのタイムゾーンは、日本でないことがある。UTC の0時〜9時
（日本の9時〜18時）と、UTC の15時〜24時（日本の翌日の0時〜9時）で、
日付がずれないことを確かめる。時刻は、app/clock.py の utc_now を差し替える。
"""
import ast
from datetime import date, datetime
from pathlib import Path

import pytest

from app import clock
from app.routes.subjects import current_date

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("utc", "japan_date"),
    [
        # UTC の 14:59 は、日本の 23:59（同じ日）
        (datetime(2026, 11, 1, 14, 59), date(2026, 11, 1)),
        # UTC の 15:00 は、日本の翌日の 0:00
        (datetime(2026, 11, 1, 15, 0), date(2026, 11, 2)),
        # UTC の 0:00 は、日本の 9:00（同じ日）
        (datetime(2026, 11, 2, 0, 0), date(2026, 11, 2)),
        # 年をまたぐ
        (datetime(2026, 12, 31, 15, 0), date(2027, 1, 1)),
    ],
)
def test_japan_today(monkeypatch, utc, japan_date):
    monkeypatch.setattr(clock, "utc_now", lambda: utc)

    assert clock.japan_today() == japan_date
    # 授業の編集の基準の「今日」も、日本時間
    assert current_date() == japan_date


def test_japan_now_is_utc_plus_nine(monkeypatch):
    utc = datetime(2026, 11, 1, 15, 30)
    monkeypatch.setattr(clock, "utc_now", lambda: utc)

    assert clock.japan_now() == datetime(2026, 11, 2, 0, 30)


def test_manual_backup_name_uses_japan_time(app, monkeypatch):
    # UTC の 2026-11-01 15:30 は、日本の 2026-11-02 0:30
    utc = datetime(2026, 11, 1, 15, 30)
    monkeypatch.setattr(clock, "utc_now", lambda: utc)

    result = app.test_cli_runner().invoke(
        args=["backup-db", "--label", "jst"]
    )

    assert result.exit_code == 0, result.output
    assert "-20261102-003000-jst.db" in result.output


# 日付・時刻を、サーバーのタイムゾーンで求める呼び出し。app/clock.py の
# ほかでは使わない（クラウドでは、日本の日付と違いうるため）
LOCAL_TIME_CALLS = {
    ("date", "today"),
    ("datetime", "now"),
    ("datetime", "today"),
    ("time", "localtime"),
}


def local_time_calls(path: Path) -> list[str]:
    """ファイルの中の、上の呼び出しの場所（行番号）。"""
    found = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and (function.value.id, function.attr) in LOCAL_TIME_CALLS
        ):
            found.append(f"{path.name}:{node.lineno}")
    return found


def test_only_clock_uses_the_server_time():
    paths = [
        *sorted((PROJECT_ROOT / "app").rglob("*.py")),
        PROJECT_ROOT / "run.py",
        PROJECT_ROOT / "wsgi.py",
    ]
    found = []
    for path in paths:
        if path.name == "clock.py":
            continue
        found.extend(local_time_calls(path))

    assert found == []


def test_the_check_finds_local_time_calls(tmp_path):
    # 上の確かめが、見つけるべきものを見つけること
    path = tmp_path / "sample.py"
    path.write_text(
        "from datetime import date, datetime\n"
        "a = date.today()\n"
        "b = datetime.now()\n"
        "c = datetime.now(UTC)\n",
        encoding="utf-8",
    )

    assert local_time_calls(path) == [
        "sample.py:2",
        "sample.py:3",
        "sample.py:4",
    ]
