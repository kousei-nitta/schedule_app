"""ログインIDとパスワードの決まり、パスワードのハッシュ、漏えいの確認。

仕様は docs/architecture/security.md の「ログイン」。
- パスワードは、NFKC（全角の英数字を半角にする、など）で正規化してから、
  長さを数え、ハッシュにする（入力の方法による違いで、ログインできなく
  ならないため）
- パスワードを設定するのは、コマンドだけ（app/cli.py）。画面では
  受け付けない
"""
import hashlib
import re
import unicodedata
import urllib.error
import urllib.request

from werkzeug.security import check_password_hash, generate_password_hash

# ログインID：半角英小文字・数字・_・-、3〜32文字
USERNAME_PATTERN = re.compile(r"[a-z0-9_-]{3,32}")

# パスワードの長さ（正規化したあとの文字数）。パスワードだけでログイン
# する場合は、15文字以上（NIST SP 800-63B-4。2025年）。上限は、長すぎる
# 入力で、ハッシュの計算に時間をかけさせないため
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128

# ハッシュの方式：scrypt（N=2^15、r=8、p=3）。OWASPの推奨の1つで、
# 1回に32MiBのメモリーを使う（小さなクラウドのサーバーでも動くように、
# メモリーの代わりに、計算の回数（p）で強さを出す組み合わせ）
PASSWORD_HASH_METHOD = "scrypt:32768:8:3"

# 漏えいしたパスワードの確認（Have I Been Pwned の Pwned Passwords）。
# パスワードのSHA-1の、先頭5文字だけを送り、同じ先頭を持つハッシュの
# 一覧を受け取って、手元で照らす（パスワードそのものは送らない）
BREACH_CHECK_URL = "https://api.pwnedpasswords.com/range/"
BREACH_CHECK_TIMEOUT_SECONDS = 10


class BreachCheckError(Exception):
    """漏えいの確認のサービスに、つながらない・応答が読めない。"""


def is_valid_username(username: str) -> bool:
    """ログインIDの形式が正しいか。"""
    return USERNAME_PATTERN.fullmatch(username) is not None


def normalize_password(password: str) -> str:
    """パスワードを、NFKCで正規化する（設定とログインで、同じ処理）。"""
    return unicodedata.normalize("NFKC", password)


def password_rule_errors(password: str, username: str) -> list[str]:
    """パスワードの決まりに合わない点を、文の一覧で返す（合えば空）。

    漏えいの確認（通信が要る）は、別の関数（is_breached_password）。
    """
    normalized = normalize_password(password)
    errors = []
    if len(normalized) < MIN_PASSWORD_LENGTH:
        errors.append(
            f"パスワードは{MIN_PASSWORD_LENGTH}文字以上にしてください"
            "（単語をいくつかつなげると、覚えやすく、強くなります）"
        )
    if len(normalized) > MAX_PASSWORD_LENGTH:
        errors.append(
            f"パスワードは{MAX_PASSWORD_LENGTH}文字以内にしてください"
        )
    if username and username.lower() in normalized.lower():
        errors.append("パスワードに、ログインIDを含めないでください")
    if normalized and len(set(normalized)) == 1:
        errors.append("同じ文字の繰り返しだけのパスワードは使えません")
    if any(unicodedata.category(character) == "Cc"
           for character in normalized):
        errors.append("パスワードに、制御文字は使えません")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in normalized):
        errors.append("パスワードに、使用できない文字が含まれています")
    return errors


def hash_password(password: str) -> str:
    """パスワードを、正規化してから、ハッシュにする。"""
    return generate_password_hash(
        normalize_password(password), method=PASSWORD_HASH_METHOD
    )


def verify_password(password_hash: str, password: str) -> bool:
    """パスワードが、ハッシュと合うか。"""
    return check_password_hash(password_hash, normalize_password(password))


def is_breached_password(password: str) -> bool:
    """漏えいしたパスワードの一覧に、このパスワードがあるか。

    SHA-1の先頭5文字だけを送る（k-匿名性。サービスは、どのパスワードかを
    知れない）。Add-Padding：応答の件数を、毎回ばらばらに増やしてもらい、
    応答の大きさからも推測されないようにする。増やした分は、件数が 0 の
    行なので、数えない。つながらないときは、BreachCheckError。
    """
    # SHA-1 は、サービスの決まり（照らし合わせのためで、パスワードを
    # 守るためのハッシュではない）
    digest = hashlib.sha1(
        normalize_password(password).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    request = urllib.request.Request(
        BREACH_CHECK_URL + prefix,
        headers={
            "Add-Padding": "true",
            "User-Agent": "schedule_app-password-check",
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=BREACH_CHECK_TIMEOUT_SECONDS
        ) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, OSError, UnicodeDecodeError) as error:
        raise BreachCheckError(
            f"漏えいしたパスワードの確認ができませんでした（{error}）"
        ) from error

    for line in body.splitlines():
        line_suffix, _, count_text = line.strip().partition(":")
        if line_suffix.upper() != suffix:
            continue
        # 件数が 0 の行は、大きさを隠すための詰め物
        return count_text.strip().isdigit() and int(count_text) > 0
    return False
