"""本番の設定（APP_ENV=production）のアプリを、テストで作る補助。

本番のアプリは、production_settings で作った設定を、test_config で渡して
作る（環境変数を変えずに済むため）。DBは、一時ディレクトリの中の、
持ち主だけのフォルダ（700）に置く。fixture は tests/conftest.py
（production_app・keep_umask）。
"""

PUBLIC_HOST = "schedule.example"
PUBLIC_ORIGIN = f"https://{PUBLIC_HOST}"
SECRET = "s" * 40
OWNER_ADDRESS = "198.51.100.20"


def production_environment(tmp_path) -> dict[str, str]:
    """本番の環境変数（DBのフォルダは、持ち主だけの 700 で作る）。"""
    data_directory = tmp_path / "data"
    data_directory.mkdir(mode=0o700, exist_ok=True)
    return {
        "APP_ENV": "production",
        "PUBLIC_ORIGIN": PUBLIC_ORIGIN,
        "SECRET_KEY": SECRET,
        "DATABASE_URL": f"sqlite:///{data_directory / 'app.db'}",
        "CLIENT_ADDRESS_HEADER": "X-Real-IP",
    }
