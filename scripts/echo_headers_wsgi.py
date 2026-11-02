"""下見の道具：受け取った接続元とヘッダーを、JSON で返すだけの WSGI のアプリ。

本番のアプリ（app/）とは別のもの。alwaysdata の下見（docs/development/
deploy.md の「下見」）で、サイトの「Application path」を、一時的に
このファイルにして使う。確かめたら、すぐにサイトの設定を戻す（このアプリ
は、ログインなしで、サーバーの様子を表示するため）。

確かめること（Mac から、python scripts/check_public.py --probe URL）：
- プロキシが、利用者の送った X-Real-IP・X-Forwarded-For などを、上書き
  するか（上書きするヘッダーだけを、本番の CLIENT_ADDRESS_HEADER にする）
- X-Forwarded-Proto が付くか
- uWSGI のワーカーの数、Python と SQLite の版、ホームのフォルダの
  ファイルシステムの種類（SQLite は、ネットワークのファイルシステムで
  壊れうる）
Cookie と Authorization の値は、返さない。
"""
import json
import os
import platform
import sqlite3

# 値を返さないヘッダー（秘密を含みうる）
HIDDEN_HEADERS = {"HTTP_COOKIE", "HTTP_AUTHORIZATION"}


def filesystem_type(path: str) -> str:
    """path があるファイルシステムの種類（例：ext4、nfs4）。分からなければ ?。

    /proc/mounts の中から、path を含む、いちばん長いマウントの場所を探す。
    """
    try:
        with open("/proc/mounts", encoding="utf-8") as mounts:
            entries = [line.split() for line in mounts]
    except OSError:
        return "?"
    real_path = os.path.realpath(path)
    best_point = ""
    best_type = "?"
    for entry in entries:
        if len(entry) < 3:
            continue
        mount_point, kind = entry[1], entry[2]
        inside = real_path == mount_point or real_path.startswith(
            mount_point.rstrip("/") + "/"
        )
        if inside and len(mount_point) > len(best_point):
            best_point, best_type = mount_point, kind
    return best_type


def worker_count() -> int | None:
    """uWSGI のワーカーの数（uWSGI の外では None）。"""
    try:
        import uwsgi
    except ImportError:
        return None
    return uwsgi.numproc


def application(environ, start_response):
    headers = {
        key: ("（表示しません）" if key in HIDDEN_HEADERS else value)
        for key, value in environ.items()
        if key.startswith("HTTP_")
    }
    home = os.path.expanduser("~")
    report = {
        "REMOTE_ADDR": environ.get("REMOTE_ADDR"),
        "wsgi.url_scheme": environ.get("wsgi.url_scheme"),
        "headers": headers,
        "workers": worker_count(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "home_filesystem": filesystem_type(home),
    }
    body = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Robots-Tag", "noindex, nofollow"),
        ],
    )
    return [body]
