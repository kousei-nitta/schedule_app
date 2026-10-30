"""ログインの処理が使う「今」の時刻。

ログイン中の端末の期限と、ログインの試行の制限は、UTCの時刻で決める
（サーバーのタイムゾーンや、Macとクラウドの違いに左右されないため）。
DBには、タイムゾーンなし（naive）で保存する（docs/architecture/data_model.md
の「時刻」）。

時刻を求める処理を、この1か所にまとめる。テストでは、この関数を
差し替えて、時刻を進める（例：monkeypatch.setattr(clock, "utc_now", ...)）。
そのため、使う側は from app import clock として、clock.utc_now() で呼ぶ。
"""
from datetime import UTC, datetime


def utc_now() -> datetime:
    """今のUTCの日時を、タイムゾーンなし（DBに保存する形）で返す。"""
    return datetime.now(UTC).replace(tzinfo=None)
