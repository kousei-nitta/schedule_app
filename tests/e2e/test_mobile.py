"""スマホの幅での、最低限の表示（Task 026）。

仕様は docs/ui_ux.md の「スマホでの表示」。

画面の幅が390px（iPhone）のとき：
- どのモードでも、横にはみ出さない（横のスクロールが出ない）
- カレンダーは、一覧表示で始まる
- 課題・タスクの表で、課題名が1文字ずつ折り返されない
見た目の作り込みは、段階3。Safari での確認は、Koma が iPhone で行う。
"""
from datetime import timedelta

from playwright.sync_api import Page, expect

from app import clock
from tests.auth_support import E2E_USERNAME, TEST_PASSWORD

TASK_TITLE = "スマホで読める長さの課題の名前"


def log_in(page: Page, app_url: str) -> None:
    page.goto(app_url + "/login")
    page.locator("#login-id").fill(E2E_USERNAME)
    page.locator("#login-password").fill(TEST_PASSWORD)
    page.locator("#login-submit-button").click()
    expect(page).to_have_url(app_url + "/")


def add_task(page: Page, app_url: str) -> None:
    """課題を、APIで1件登録する（ログインした Cookie を使う）。"""
    due = clock.japan_today() + timedelta(days=2)
    response = page.request.post(
        app_url + "/api/tasks",
        data={
            "category": "other",
            "title": TASK_TITLE,
            "due_datetime": f"{due.isoformat()}T12:00",
        },
    )
    assert response.status == 201


def page_is_not_wider_than_screen(page: Page) -> bool:
    return page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )


def test_phone_width_screens(phone_page: Page, live_server: str):
    page = phone_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    log_in(page, live_server)
    add_task(page, live_server)
    page.reload()

    # カレンダー：一覧表示で始まる（週・月のボタンも使える）
    expect(page.locator(".fc-list")).to_be_visible()
    expect(page.locator(".fc-listFourWeeks-button")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert page_is_not_wider_than_screen(page)

    # 週表示に切り替えても、はみ出さない
    page.locator(".fc-timeGridWeek-button").click()
    expect(page.locator(".fc-timeGridWeek-view")).to_be_visible()
    assert page_is_not_wider_than_screen(page)

    # 授業モード
    page.locator("#subjects-tab").click()
    expect(page.locator("#subjects-pane")).to_be_visible()
    assert page_is_not_wider_than_screen(page)

    # 課題・タスクモード：課題名が、1行に十分な幅で表示される
    page.locator("#tasks-tab").click()
    title_cell = page.locator(
        "#task-incomplete-list tbody tr td", has_text=TASK_TITLE
    )
    expect(title_cell).to_be_visible()
    assert title_cell.bounding_box()["width"] >= 150
    assert page_is_not_wider_than_screen(page)

    assert errors == []
