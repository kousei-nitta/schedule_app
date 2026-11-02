"""E2E：主な流れ（ログイン → 学期 → 休講日 → 授業 → カレンダー → 課題 →
完了 → ログアウト）。

画面を、利用者と同じようにブラウザで操作して確かめる。日付は、
すべて今日からの相対で決める（docs/development/testing.md の
「画面の確認」）。週の始まりは日曜日（カレンダーの週表示と同じ）。

- 学期：先週の日曜日から、4週間後の土曜日まで（5週間）
- 休講日：今週の水曜日
- 授業A：水曜日（今週の水曜日は休講日のため、予定がない）
- 授業B：木曜日（今週の予定があることで、今週の予定の読み込みが
  終わったことを確かめてから、授業Aの予定がないことを確かめる）

印 e2e は、tests/e2e/conftest.py が自動で付ける。
"""
import re
from datetime import date, datetime, time, timedelta

import pytest
from playwright.sync_api import Page, expect

from app import clock, security
from app.demo_data import semester_name
from tests.auth_support import E2E_USERNAME, TEST_PASSWORD

SUBJECT_A = "E2Eテストの授業A"
SUBJECT_B = "E2Eテストの授業B"
TASK_TITLE = "E2Eテストの課題"


def sunday_of(day: date) -> date:
    """day を含む週（日曜始まり）の日曜日を返す。"""
    # weekday()：月曜日が0、日曜日が6
    return day - timedelta(days=(day.weekday() + 1) % 7)


def timegrid_events(page: Page, day: date, title: str):
    """週表示の、その日の列の中の、タイトルを含む予定。"""
    column = page.locator(f'td.fc-timegrid-col[data-date="{day}"]')
    return column.locator(".fc-event").filter(has_text=title)


def register_semester(page: Page, today: date, start: date, end: date):
    page.locator("#subjects-tab").click()
    page.locator("#semester-empty-open-button").click()
    # 学期の名前（例：2026年度 後期）は、デモデータと同じ決め方にする
    name = semester_name(today)
    year_text, term = name.split(" ")
    page.locator("#semester-year").fill(year_text.removesuffix("年度"))
    page.locator("#semester-term").select_option(term)
    page.locator("#semester-start-date").fill(start.isoformat())
    page.locator("#semester-end-date").fill(end.isoformat())
    page.locator("#semester-submit-button").click()

    expect(page.locator("#semester-modal")).to_be_hidden()
    expect(page.locator("#semester-detail-name")).to_have_text(name)


def add_closure(page: Page, closure_date: date):
    page.locator("#closure-date").fill(closure_date.isoformat())
    page.locator("#closure-name").fill("E2Eテストの休講日")
    page.locator("#closure-submit-button").click()

    closure_items = page.locator("#closure-list li")
    expect(closure_items).to_have_count(1)
    expect(closure_items).to_contain_text("E2Eテストの休講日")


def log_in(page: Page, app_url: str) -> None:
    """ログインしていないと、ログインの画面に移る。ログインして、トップへ。"""
    page.goto(app_url + "/")
    expect(page).to_have_url(app_url + "/login")
    page.locator("#login-id").fill(E2E_USERNAME)
    page.locator("#login-password").fill(TEST_PASSWORD)
    page.locator("#login-submit-button").click()
    expect(page).to_have_url(app_url + "/")
    expect(page.locator("#user-menu-button")).to_have_text(E2E_USERNAME)


def log_out(page: Page, app_url: str) -> None:
    """利用者のメニューから、ログアウトする。ログインの画面に戻る。"""
    page.locator("#user-menu-button").click()
    page.locator("#logout-button").click()
    expect(page).to_have_url(app_url + "/login")
    # 「戻る」でも、ログイン中の画面（データ）は見えない（開き直して、
    # ログインの画面になる）。戻る・進むのキャッシュ（bfcache）から戻る
    # 場合は、下の test_back_after_logout_with_bfcache で確かめる
    page.go_back()
    expect(page).to_have_url(app_url + "/login")
    expect(page.locator("#user-menu-button")).to_have_count(0)
    # ログアウトのあとは、トップを開いても、ログインの画面になる
    page.goto(app_url + "/")
    expect(page).to_have_url(app_url + "/login")


def register_subject(
    page: Page, name: str, weekday: int, start_time: str, end_time: str
) -> None:
    """授業の登録のモーダルで、1件登録する（モーダルは開いたまま）。"""
    page.locator("#subject-name").fill(name)
    page.locator("#subject-room").fill("E2E教室")
    page.locator("#subject-weekday").select_option(str(weekday))
    page.locator("#subject-start-time").select_option(start_time)
    page.locator("#subject-end-time").select_option(end_time)
    page.locator("#subject-submit-button").click()


def test_main_flow(
    page: Page,
    app_url: str,
    page_errors: list[str],
    csp_violations: list[str],
):
    # 「今日」は、アプリと同じ日本時間（app/clock.py。ブラウザの時間帯も
    # 日本。tests/e2e/conftest.py の browser_context_args）
    today = clock.japan_today()
    this_sunday = sunday_of(today)
    semester_start = this_sunday - timedelta(weeks=1)
    semester_end = this_sunday + timedelta(weeks=4, days=-1)
    this_wednesday = this_sunday + timedelta(days=3)
    this_thursday = this_sunday + timedelta(days=4)
    next_wednesday = this_wednesday + timedelta(weeks=1)

    # ブラウザの「今」を、テストの「今日」の正午に固定する（テストの途中で
    # 日付をまたいでも、Pythonとブラウザの「今日」がずれないように）
    page.clock.set_fixed_time(
        datetime.combine(today, time(12, 0), tzinfo=clock.JAPAN_TIMEZONE)
    )

    # 0. ログインする
    log_in(page, app_url)

    # 1. 学期を登録する
    register_semester(page, today, semester_start, semester_end)

    # 2. 休講日（今週の水曜日）を追加する
    add_closure(page, this_wednesday)

    # 3. 授業を2つ、続けて登録する。水曜日の授業は、5回のうち休講日の
    #    1回を除いて4件、木曜日の授業は5件の予定ができる
    page.locator("#subject-add-button").click()
    success = page.locator("#subject-form-success")
    register_subject(page, SUBJECT_A, 2, "10:00", "12:00")
    expect(success).to_have_text(
        f"「{SUBJECT_A}」を登録しました（予定4件を作成）"
    )
    register_subject(page, SUBJECT_B, 3, "13:00", "15:00")
    expect(success).to_have_text(
        f"「{SUBJECT_B}」を登録しました（予定5件を作成）"
    )
    page.locator("#subject-modal .modal-footer button").filter(
        has_text="閉じる"
    ).click()
    expect(page.locator("#subject-modal")).to_be_hidden()
    expect(page.locator("#subject-table-body tr")).to_have_count(2)

    # 4. カレンダー（今週の週表示）で、授業の予定を確かめる
    page.locator("#calendar-tab").click()
    expect(timegrid_events(page, this_thursday, SUBJECT_B)).to_have_count(1)
    # 授業Bの予定が出た＝今週の予定の読み込みが終わった。休講日の
    # 水曜日には、授業Aの予定がない
    expect(timegrid_events(page, this_wednesday, SUBJECT_A)).to_have_count(0)
    page.locator(".fc-next-button").click()
    expect(timegrid_events(page, next_wednesday, SUBJECT_A)).to_have_count(1)
    page.locator(".fc-today-button").click()

    # 5. 課題を登録する（締切は2日後。「直近の締切」欄に出る）
    page.locator("#tasks-tab").click()
    page.locator("#task-add-button").click()
    page.locator("#task-title").fill(TASK_TITLE)
    page.locator("#task-subject").select_option(label=SUBJECT_A)
    due_date = today + timedelta(days=2)
    page.locator("#task-due-date").fill(due_date.isoformat())
    page.locator("#task-due-time").fill("18:00")
    page.locator("#task-submit-button").click()

    expect(page.locator("#task-modal")).to_be_hidden()
    expect(page.locator("#task-incomplete-body")).to_contain_text(TASK_TITLE)

    page.locator("#calendar-tab").click()
    deadline_list = page.locator("#calendar-deadline-list")
    expect(deadline_list).to_contain_text(TASK_TITLE)

    # 6. 課題を完了にする。完了の一覧に移り、「直近の締切」欄から消える
    page.locator("#tasks-tab").click()
    complete_checkbox = page.get_by_role(
        "checkbox", name=re.compile(f"「{TASK_TITLE}」.*の完了")
    )
    complete_checkbox.check()

    expect(page.locator("#task-completed-body")).to_contain_text(TASK_TITLE)
    expect(page.locator("#task-incomplete-empty")).to_be_visible()

    page.locator("#calendar-tab").click()
    expect(page.locator("#calendar-deadline-empty")).to_be_visible()
    expect(deadline_list).not_to_contain_text(TASK_TITLE)

    # 7. ログアウトする
    log_out(page, app_url)

    # 流れの全体で、JavaScriptの例外が起きていない
    assert page_errors == []
    # CSP（app/security.py）で、BootstrapやFullCalendar（差し込む <style>
    # を含む）の読み込み・実行が止められていない
    assert csp_violations == []


def test_expired_login_moves_to_login_page(
    page: Page,
    app_url: str,
    page_errors: list[str],
    csp_violations: list[str],
):
    # 画面を開いたまま、ログインが切れたら（ここでは、ほかのタブで
    # ログアウトする）、次のAPIの呼び出し（401）で、ログインの画面に移る
    # （app/static/js/api.js）
    log_in(page, app_url)
    other_tab = page.context.new_page()
    other_tab.goto(app_url + "/")
    other_tab.locator("#user-menu-button").click()
    other_tab.locator("#logout-button").click()
    expect(other_tab).to_have_url(app_url + "/login")

    page.locator("#tasks-tab").click()

    expect(page).to_have_url(app_url + "/login")
    assert page_errors == []
    assert csp_violations == []


def not_restored_reasons_of(page: Page) -> list[str]:
    """bfcache を使わなかった（「戻る」で開き直した）ときに、Chrome が
    知らせる理由の一覧（あとから増える）。"""
    reasons = []
    devtools = page.context.new_cdp_session(page)
    devtools.send("Page.enable")
    devtools.on(
        "Page.backForwardCacheNotUsed",
        lambda event: reasons.extend(
            explanation["reason"]
            for explanation in event["notRestoredExplanations"]
        ),
    )
    return reasons


# 画面が隠れていたかを、Pythonに知らせる。
# - フォームの送信（submit）：フォームの処理（app/static/js/
#   logout_protection.js）のあと。ログアウトを送る前に、隠したか
# - 画面が出るとき（pageshow）：bfcache から戻ったか（persisted）も。
#   ページのスクリプトより先に登録されるため、logout_protection.js が、
#   そのイベントで隠すより前の状態を記録する
# 画面を離れるとき（pagehide）の知らせは、移る途中で届かないことがある
# ため、記録しない
REPORT_PAGE_EVENTS = """
window.addEventListener("submit", () => {
  const hidden = document.body.classList.contains("d-none");
  window.reportPageEvent(`${location.pathname} submit hidden=${hidden}`);
});
window.addEventListener("pageshow", (event) => {
  const hidden = document.body.classList.contains("d-none");
  window.reportPageEvent(
    `${location.pathname} pageshow persisted=${event.persisted} ` +
    `hidden=${hidden}`
  );
});
"""


def page_events_of(page: Page) -> list[str]:
    """フォームの送信・画面が出るときの記録（あとから増える）。"""
    events = []
    page.expose_function("reportPageEvent", lambda text: events.append(text))
    page.add_init_script(REPORT_PAGE_EVENTS)
    return events


def log_out_and_go_back(page: Page, app_url: str) -> None:
    """ログインし、カレンダーを読み込んでから、ログアウトして「戻る」。"""
    log_in(page, app_url)
    # カレンダーの読み込み（APIの取得）が終わってから、ログアウトする
    expect(page.locator(".fc-timegrid")).to_be_visible()
    page.locator("#user-menu-button").click()
    page.locator("#logout-button").click()
    expect(page).to_have_url(app_url + "/login")
    # bfcache から戻ると、読み込み（load）が起きないため、commit まで待つ
    page.go_back(wait_until="commit")


def expect_login_page(page: Page, app_url: str) -> None:
    expect(page).to_have_url(app_url + "/login")
    expect(page.locator("#login-password")).to_be_visible()
    expect(page.locator("#user-menu-button")).to_have_count(0)


def test_back_after_logout_with_bfcache(bfcache_page: Page, live_server: str):
    """ログアウトのあとの「戻る」で、ログイン中の画面が bfcache から
    戻らない（共用のPCで、次の人に見られない）。

    守りの1つ目は、画面とAPIの Cache-Control: no-store（app/security.py）。
    Chrome は、no-store のページを bfcache に入れない（入れる機能が有効
    でも、HttpOnly の Cookie が変わると追い出す）。no-store を外すと、
    ログイン中の画面が、サーバーへの要求なしに、そのまま戻る（Task 025で
    確かめた）。
    """
    page = bfcache_page
    not_restored_reasons = not_restored_reasons_of(page)
    page_events = page_events_of(page)

    log_out_and_go_back(page, live_server)

    expect_login_page(page, live_server)
    # bfcache が使えないから（空振り）でなく、no-store のため、戻らなかった
    assert "MainResourceHasCacheControlNoStore" in not_restored_reasons
    # ログアウトのフォームを送る前に、画面を隠していた（Safari の、
    # スワイプで戻るときの画面の写しに、ログイン中の画面が残らないように）
    assert "/ submit hidden=true" in page_events


def test_page_restored_from_bfcache_after_logout_is_reloaded(
    bfcache_page: Page, live_server: str, monkeypatch: pytest.MonkeyPatch
):
    """bfcache から画面が戻っても、隠したまま読み込み直し、ログインの
    画面になる。

    守りの2つ目（app/static/js/logout_protection.js）。Safari は、HTTP の
    ページでは、no-store でも bfcache に残す（Task 025で、KomaのMacで
    見つけた）。ここでは、Chromium で同じ状況を作るため、no-store を
    no-cache に替える（bfcache に入る）。
    """
    monkeypatch.setattr(security, "NO_STORE", "no-cache")
    page = bfcache_page
    not_restored_reasons = not_restored_reasons_of(page)
    page_events = page_events_of(page)

    log_out_and_go_back(page, live_server)

    expect_login_page(page, live_server)
    # 画面は、bfcache から戻っていた（このテストが空振りしていない）。
    # 戻った時点で、画面は隠れていた
    assert not_restored_reasons == []
    assert "/ pageshow persisted=true hidden=true" in page_events


def test_page_restored_from_bfcache_while_logged_in_is_hidden_then_reloaded(
    bfcache_page: Page, live_server: str, monkeypatch: pytest.MonkeyPatch
):
    """ログイン中に、ほかの画面へ移ってから「戻る」：bfcache に入るときに
    隠し（pagehide）、戻ったら読み込み直して、ふだんの画面になる。
    読み込み直しは、1回だけ（繰り返さない）。
    """
    monkeypatch.setattr(security, "NO_STORE", "no-cache")
    page = bfcache_page
    not_restored_reasons = not_restored_reasons_of(page)
    page_events = page_events_of(page)
    log_in(page, live_server)
    expect(page.locator(".fc-timegrid")).to_be_visible()

    # このアプリの、ほかの画面（静的ファイル）へ移ってから、戻る
    page.goto(live_server + "/static/css/style.css")
    page.go_back(wait_until="commit")

    expect(page).to_have_url(live_server + "/")
    expect(page.locator(".fc-timegrid")).to_be_visible()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\bd-none\b"))
    assert not_restored_reasons == []
    # bfcache に入るときに隠し（pagehide）、隠れたまま戻った。読み込み
    # 直したあとは、普通の表示（persisted=false）で、もう読み込み直さない
    restored = "/ pageshow persisted=true hidden=true"
    assert restored in page_events
    assert page_events[page_events.index(restored) + 1:] == [
        "/ pageshow persisted=false hidden=false"
    ]
