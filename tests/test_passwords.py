"""ログインIDとパスワードの決まり、ハッシュ、漏えいの確認のテスト
（app/passwords.py。docs/architecture/security.md の「パスワード」）。

漏えいの確認は、インターネットにつながず、通信を差し替えて確かめる。
"""
import hashlib
import io
import urllib.error

import pytest

from app import passwords
from app.passwords import (
    PASSWORD_HASH_METHOD,
    BreachCheckError,
    hash_password,
    is_breached_password,
    is_valid_username,
    password_rule_errors,
    verify_password,
)

GOOD_PASSWORD = "kumo sakura densha 2099"


@pytest.mark.parametrize(
    "username", ["abc", "owner", "a-b_c9", "x" * 32]
)
def test_valid_usernames(username):
    assert is_valid_username(username)


@pytest.mark.parametrize(
    "username",
    ["ab", "x" * 33, "Owner", "own er", " owner", "ｏｗｎｅｒ", "own.er", ""],
)
def test_invalid_usernames(username):
    assert not is_valid_username(username)


def test_good_password_has_no_errors():
    assert password_rule_errors(GOOD_PASSWORD, "owner") == []


def test_fourteen_characters_are_too_short():
    errors = password_rule_errors("kumo sakura 12", "owner")

    assert errors == [
        "パスワードは15文字以上にしてください"
        "（単語をいくつかつなげると、覚えやすく、強くなります）"
    ]


def test_fifteen_characters_are_enough():
    assert password_rule_errors("kumo sakura 123", "owner") == []


def test_length_is_counted_after_normalization():
    # 全角の英数字・空白は、半角にしてから数える（15文字のまま）
    full_width = "ｋｕｍｏ　ｓａｋｕｒａ　１２３"
    assert password_rule_errors(full_width, "owner") == []
    assert password_rule_errors(full_width[:-1], "owner") != []


def test_too_long_password():
    errors = password_rule_errors(("kumo sakura densha " * 7)[:129], "owner")

    assert errors == ["パスワードは128文字以内にしてください"]


def test_very_long_input_is_rejected_before_normalization():
    assert password_rule_errors("a" * 513, "owner") == [
        "パスワードは128文字以内にしてください"
    ]


@pytest.mark.parametrize(
    "password", ["my owner password 2099", "MY-OWNER-PASSWORD-2099"]
)
def test_password_must_not_contain_username(password):
    errors = password_rule_errors(password, "owner")

    assert "パスワードに、ログインIDを含めないでください" in errors


def test_repeated_single_character_is_rejected():
    errors = password_rule_errors("z" * 20, "owner")

    assert errors == ["同じ文字の繰り返しだけのパスワードは使えません"]


@pytest.mark.parametrize(
    "password",
    ["midori no tokei 42", "kumo sakura densha 2099", "9876 5432 10 abc"],
)
def test_varied_passwords_are_accepted(password):
    # 文字の種類が5つ以上で、連番だけでないもの
    assert password_rule_errors(password, "owner") == []


@pytest.mark.parametrize(
    "password, message",
    [
        ("abababababababab", "使われている文字の種類が少なすぎます"),
        ("1212 1212 1212 1212", "使われている文字の種類が少なすぎます"),
        ("123456789012345", "連続した文字"),
        ("ZYXWVUTSRQPONMLK", "連続した文字"),
        ("9876 5432 1098 7654", "連続した文字"),
    ],
)
def test_weak_patterns_are_rejected(password, message):
    [error] = password_rule_errors(password, "owner")
    assert error.startswith(message)


def test_control_characters_are_rejected():
    errors = password_rule_errors(GOOD_PASSWORD + "\x00", "owner")

    assert errors == ["パスワードに、制御文字は使えません"]


def test_hash_uses_strong_scrypt_and_verifies():
    password_hash = hash_password(GOOD_PASSWORD)

    assert password_hash.startswith(PASSWORD_HASH_METHOD + "$")
    assert PASSWORD_HASH_METHOD == "scrypt:32768:8:3"
    assert GOOD_PASSWORD not in password_hash
    assert verify_password(password_hash, GOOD_PASSWORD)
    assert not verify_password(password_hash, GOOD_PASSWORD + "x")


def test_verify_normalizes_the_typed_password():
    password_hash = hash_password("ＡＢＣdefghijklmnop")

    assert verify_password(password_hash, "ABCdefghijklmnop")


# --- 漏えいの確認 ---


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def sha1_upper(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest().upper()


@pytest.fixture
def requests_sent(monkeypatch):
    """送った要求を記録し、決めた本文を返すように、通信を差し替える。"""
    sent = []
    body = {"text": ""}

    def fake_urlopen(request, timeout):
        sent.append((request, timeout))
        return FakeResponse(body["text"].encode())

    monkeypatch.setattr(passwords.urllib.request, "urlopen", fake_urlopen)
    return sent, body


def test_breach_check_sends_only_five_characters(requests_sent):
    sent, body = requests_sent
    digest = sha1_upper(GOOD_PASSWORD)
    body["text"] = "0000000000000000000000000000000000A:3\r\n"

    is_breached_password(GOOD_PASSWORD)

    [(request, timeout)] = sent
    assert request.full_url == (
        "https://api.pwnedpasswords.com/range/" + digest[:5]
    )
    assert digest[5:] not in request.full_url
    assert request.get_header("Add-padding") == "true"
    assert timeout == 10


def test_breached_password_is_found(requests_sent):
    _, body = requests_sent
    suffix = sha1_upper(GOOD_PASSWORD)[5:]
    body["text"] = f"0123456789ABCDEF0123456789ABCDEF012:1\r\n{suffix}:42\r\n"

    assert is_breached_password(GOOD_PASSWORD)


def test_padding_entries_are_not_counted(requests_sent):
    # 件数が 0 の行は、応答の大きさを隠すための詰め物
    _, body = requests_sent
    suffix = sha1_upper(GOOD_PASSWORD)[5:]
    body["text"] = f"{suffix}:0\r\n"

    assert not is_breached_password(GOOD_PASSWORD)


def test_password_not_in_list(requests_sent):
    _, body = requests_sent
    body["text"] = "0123456789ABCDEF0123456789ABCDEF012:5\r\n"

    assert not is_breached_password(GOOD_PASSWORD)


def test_breach_check_uses_normalized_password(requests_sent):
    sent, body = requests_sent
    body["text"] = "0123456789ABCDEF0123456789ABCDEF012:5\r\n"

    is_breached_password("ＡＢＣdefghijklmnop")

    [(request, _timeout)] = sent
    assert request.full_url.endswith(sha1_upper("ABCdefghijklmnop")[:5])


@pytest.mark.parametrize(
    "text",
    [
        "",
        "<html><body>Wi-Fi にログインしてください</body></html>",
        "0123456789ABCDEF0123456789ABCDEF012:5\r\nnot a hash line\r\n",
    ],
    ids=["空", "HTML", "形の違う行"],
)
def test_unexpected_response_is_not_treated_as_safe(requests_sent, text):
    # このサービスの形でない応答（途中の機器が返した Wi-Fi のログインの
    # 画面など）を、「漏えいなし」にしない
    _, body = requests_sent
    body["text"] = text

    with pytest.raises(BreachCheckError):
        is_breached_password(GOOD_PASSWORD)


def test_breach_check_failure_is_reported(monkeypatch):
    def unreachable(request, timeout):
        raise urllib.error.URLError("network is unreachable")

    monkeypatch.setattr(passwords.urllib.request, "urlopen", unreachable)

    with pytest.raises(BreachCheckError):
        is_breached_password(GOOD_PASSWORD)
