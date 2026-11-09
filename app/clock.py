"""アプリが使う「今」の時刻と「今日」。時刻を求める処理を、この1か所にまとめる。

- ログインの処理（ログイン中の端末の期限、試行の制限、端末の印）は、UTCの
  時刻で決める（utc_now。サーバーのタイムゾーンや、Macとクラウドの違いに
  左右されないため）
- 予定・授業の「今日」と、バックアップの名前の日時は、日本時間で決める
  （japan_today・japan_now）。サーバー（クラウド）のタイムゾーンは、日本で
  ないことがあり、そのままでは、日本の朝（UTCの前の日）に、前の日を
  「今日」としてしまう。日本には夏時間がないため、UTC+9 の固定でよい
DBには、どちらも、タイムゾーンなし（naive）で保存する
（docs/architecture/data_model.md の「共通の約束」）。

ほかの場所で date.today()・datetime.now() を使わない（サーバーの
タイムゾーンになるため。tests/test_clock.py が確かめる）。テストでは、
この関数を差し替えて、時刻を進める（例：monkeypatch.setattr(clock,
"utc_now", ...)）。そのため、使う側は from app import clock として、
clock.utc_now() のように呼ぶ。
"""
from datetime import UTC, date, datetime, timedelta, timezone

# 日本時間（UTC+9。夏時間なし）
JAPAN_TIMEZONE = timezone(timedelta(hours=9), "JST")


def utc_now() -> datetime:
    """今のUTCの日時を、タイムゾーンなし（DBに保存する形）で返す。"""
    return datetime.now(UTC).replace(tzinfo=None)


def japan_now() -> datetime:
    """今の日本時間の日時を、タイムゾーンなしで返す。

    utc_now から求める（テストで utc_now を差し替えると、これも動く）。
    """
    return (utc_now() + timedelta(hours=9)).replace(tzinfo=None)


def japan_today() -> date:
    """日本時間の「今日」。"""
    return japan_now().date()
