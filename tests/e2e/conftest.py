"""E2Eテスト（Playwright）の共通の準備。

- live_server：一時ディレクトリのDB（migrationで作った雛形のコピー）で、
  アプリを別のスレッドで起動し、URLを返す（実データのDBに触れない）
- app_url：ブラウザで開くアプリのURL。環境変数 E2E_CDN_FROM_NPM=1 の
  ときは、CDN（jsDelivr）への読み込みに、node_modules の同じ版の
  ファイルで答える（CDNに届かない、Claudeの作業環境のため。CIは、
  CDNから読む）。ブラウザが integrity（SRI）を確かめるので、違う
  ファイルなら読み込まれない
- page_errors：ページで起きたJavaScriptの例外の一覧

page（ブラウザのページ）は、pytest-playwright のfixture。
実行のしかたは docs/development/testing.md の「E2Eテスト」。
"""
import json
import os
import shutil
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route
from werkzeug.serving import make_server

from app import create_app
from app.extensions import db


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NODE_MODULES = PROJECT_ROOT / "node_modules"
CDN_PREFIX = "https://cdn.jsdelivr.net/npm/"
CONTENT_TYPES = {".css": "text/css", ".js": "text/javascript"}


@pytest.fixture
def live_server(template_db: Path, tmp_path: Path):
    database_path = tmp_path / "e2e.db"
    shutil.copy2(template_db, database_path)
    server_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )
    # 番号0：空いているポートを、OSに選んでもらう
    server = make_server("127.0.0.1", 0, server_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}"

    server.shutdown()
    thread.join()
    with server_app.app_context():
        db.session.remove()
        db.engine.dispose()


def answer_from_node_modules(route: Route) -> None:
    """CDNへの読み込みに、node_modules の同じ版のファイルで答える。

    例：…/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css は、
    node_modules/bootstrap/dist/css/bootstrap.min.css（版が5.3.8のとき）。
    版が違う・ファイルがないときは、読み込みを失敗させる。
    """
    path_in_cdn = route.request.url.removeprefix(CDN_PREFIX)
    package_and_version, _, file_path = path_in_cdn.partition("/")
    package_name, _, version = package_and_version.partition("@")
    package_directory = NODE_MODULES / package_name
    package_json = package_directory / "package.json"
    file = (package_directory / file_path).resolve()

    if (
        not package_json.is_file()
        or json.loads(package_json.read_text())["version"] != version
        or not file.is_relative_to(package_directory.resolve())
        or not file.is_file()
        or file.suffix not in CONTENT_TYPES
    ):
        route.abort()
        return

    route.fulfill(
        path=file,
        content_type=CONTENT_TYPES[file.suffix],
        # crossorigin="anonymous" の読み込みのため、CDNと同じく許可する
        headers={"Access-Control-Allow-Origin": "*"},
    )


@pytest.fixture
def app_url(page: Page, live_server: str) -> str:
    if os.environ.get("E2E_CDN_FROM_NPM") == "1":
        page.route(CDN_PREFIX + "**", answer_from_node_modules)
    return live_server


@pytest.fixture
def page_errors(page: Page) -> list[str]:
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return errors
