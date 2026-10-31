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
# ログインで受け付ける入力の長さ（正規化の前）。これより長いものは、
# 正規化もハッシュもせずに、失敗にする（NFKCは文字数を増やすことがあり、
# 長い入力で計算させないため）
MAX_PASSWORD_INPUT_LENGTH = 512

# 使われている文字の種類が、これより少ないパスワードは断る
# （abababab… のような、短い並びの繰り返し。漏えいの確認を省いたときも
# 断るため、手元で確かめる）
MIN_DISTINCT_CHARACTERS = 5

# ハッシュの方式：scrypt（N=2^15、r=8、p=3）。OWASPの推奨の1つで、
# 1回に32MiBのメモリーを使う（小さなクラウドのサーバーでも動くように、
# メモリーの代わりに、計算の回数（p）で強さを出す組み合わせ）
PASSWORD_HASH_METHOD = "scrypt:32768:8:3"

# 漏えいしたパスワードの確認（Have I Been Pwned の Pwned Passwords）。
# パスワードのSHA-1の、先頭5文字だけを送り、同じ先頭を持つハッシュの
# 一覧を受け取って、手元で照らす（パスワードそのものは送らない）。
# 応答の1行は「SHA-1の残りの35文字:件数」の形
BREACH_CHECK_URL = "https://api.pwnedpasswords.com/range/"
BREACH_CHECK_TIMEOUT_SECONDS = 10
BREACH_LINE_PATTERN = re.compile(r"([0-9A-F]{35}):([0-9]+)")


class BreachCheckError(Exception):
    """漏えいの確認のサービスに、つながらない・応答が読めない。"""


def is_valid_username(username: str) -> bool:
    """ログインIDの形式が正しいか。"""
    return USERNAME_PATTERN.fullmatch(username) is not None


def normalize_password(password: str) -> str:
    """パスワードを、NFKCで正規化する（設定とログインで、同じ処理）。"""
    return unicodedata.normalize("NFKC", password)


def is_simple_sequence(text: str) -> bool:
    """1つずつ増える・減る文字だけの並びか（123…・abc…・987… など）。

    空白は除き、大文字・小文字は区別しない。数字は、9の次の0（と、0の
    次の9）も続きとみなす（1234567890123… を断るため）。
    """
    characters = text.replace(" ", "").lower()
    if len(characters) < 2:
        return False
    for current, following in zip(characters, characters[1:]):
        step = ord(following) - ord(current)
        wraps = (current, following) in (("9", "0"), ("0", "9"))
        if abs(step) != 1 and not wraps:
            return False
    return True


def password_rule_errors(password: str, username: str) -> list[str]:
    """パスワードの決まりに合わない点を、文の一覧で返す（合えば空）。

    漏えいの確認（通信が要る）は、別の関数（is_breached_password）。
    """
    if len(password) > MAX_PASSWORD_INPUT_LENGTH:
        return [
            f"パスワードは{MAX_PASSWORD_LENGTH}文字以内にしてください"
        ]
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
    distinct_count = len(set(normalized))
    if distinct_count == 1:
        errors.append("同じ文字の繰り返しだけのパスワードは使えません")
    elif 1 < distinct_count < MIN_DISTINCT_CHARACTERS:
        errors.append(
            "使われている文字の種類が少なすぎます"
            "（同じ並びの繰り返しなど）"
        )
    if distinct_count >= MIN_DISTINCT_CHARACTERS and is_simple_sequence(
        normalized
    ):
        errors.append(
            "連続した文字（123… や abc… など）だけのパスワードは使えません"
        )
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
    行なので、数えない。つながらないとき・応答がこのサービスの形でない
    とき（Wi-Fi のログインの画面など、途中の機器が返した応答）は、
    BreachCheckError（確かめられなかったものを「漏えいなし」にしない）。
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

    entries = {}
    for line in body.splitlines():
        match = BREACH_LINE_PATTERN.fullmatch(line.strip().upper())
        if match is None:
            raise BreachCheckError(
                "漏えいしたパスワードの確認の応答が、読めませんでした"
                "（途中の機器が、別の応答を返したかもしれません）"
            )
        entries[match.group(1)] = int(match.group(2))
    if not entries:
        # 本物の応答は、詰め物があるため、いつも数百行ある
        raise BreachCheckError(
            "漏えいしたパスワードの確認の応答が、空でした"
        )
    # 件数が 0 の行は、大きさを隠すための詰め物
    return entries.get(suffix, 0) > 0
