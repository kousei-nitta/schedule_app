"""授業の予定（Event）の生成。

授業の登録、休講日の削除による予定の作成、授業全体の編集による
予定の作り直しから使う部品。
DBの読み書き（セッションへの追加・commit）は行わない。休講日の日付の
取得と、データの保存は、各routeが担当する。「今日」の日付も、この
ファイルでは求めない（作り直しの開始日は、routeが引数で渡す）。
"""

from datetime import date, timedelta

from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject


# 授業の予定のカテゴリの保存値。文字列 "class" を、ほかの場所に直接書かない。
EVENT_CATEGORY_CLASS = "class"


def class_event_dates(
    start_date: date,
    end_date: date,
    weekday: int,
    excluded_dates: set[date],
) -> list[date]:
    """期間の中で、曜日が一致する日を、昇順で返す。

    start_date・end_date は両端を含む。weekday は 0=月曜〜6=日曜
    （date.weekday() と同じ）。excluded_dates（学期の休講日の日付）に
    含まれる日は除く。休講日の渡し忘れを防ぐため、省略できない引数にする。
    該当する日がなければ、空の一覧を返す。
    """
    # 最初の該当日までの日数。Pythonの % は、負の数でも 0〜6 を返す。
    days_until_first = (weekday - start_date.weekday()) % 7
    current = start_date + timedelta(days=days_until_first)

    dates = []
    while current <= end_date:
        if current not in excluded_dates:
            dates.append(current)
        current += timedelta(days=7)
    return dates


def build_class_event(subject: Subject, event_date: date) -> Event:
    """授業と日付から、自動生成の予定を1件作る（セッションには追加しない）。

    授業の値を予定に写す方法は、この関数の1か所にまとめる。授業との関係は
    relationship で結ぶため、授業の id が採番される前でも作れる。
    """
    return Event(
        subject=subject,
        category=EVENT_CATEGORY_CLASS,
        date=event_date,
        start_time=subject.start_time,
        end_time=subject.end_time,
        title=subject.subject_name,
        room=subject.room,
        employer=None,
        notes=subject.notes,
        is_generated=True,
    )


def build_class_events(
    subject: Subject,
    semester: Semester,
    excluded_dates: set[date],
) -> list[Event]:
    """学期の期間全体の、授業の自動生成の予定を作る（セッションには追加しない）。

    学期は、routeが取得済みのものを受け取る（この関数の中で、DBを読まない）。
    """
    dates = class_event_dates(
        semester.start_date,
        semester.end_date,
        subject.weekday,
        excluded_dates,
    )
    return [build_class_event(subject, event_date) for event_date in dates]


def build_class_events_from(
    subject: Subject,
    semester: Semester,
    excluded_dates: set[date],
    from_date: date,
) -> list[Event]:
    """from_date以降の、授業の自動生成の予定を作る（セッションには追加しない）。

    授業全体の編集による作り直しで使う。対象の期間は、from_date（含む）と
    学期の開始日の遅いほうから、学期の終了日まで。from_dateが学期の
    終了日より後なら、空の一覧を返す。
    """
    start_date = max(from_date, semester.start_date)
    dates = class_event_dates(
        start_date,
        semester.end_date,
        subject.weekday,
        excluded_dates,
    )
    return [build_class_event(subject, event_date) for event_date in dates]
