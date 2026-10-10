# タスク007: API入力検証の整理（使用できない文字の検査とTask 005のLowの整理）

| 項目 | 内容 |
|---|---|
| Task ID | 007 |
| Task名 | API入力検証の整理（使用できない文字の検査とTask 005のLowの整理） |
| ブランチ | `feature/007-api-input-validation`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

## 目的
学期API・授業APIの文字列の入力で、UTF-8に変換できない文字（孤立サロゲート、U+D800〜U+DFFF）を400（`validation_error`）にする。あわせて、Task 005のレビューで持ち越した軽微な指摘（Low）を整理する。次の3段階で、この順に行う。

| 段階 | 内容 | APIの挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | コードの整理（不要なimport・死んだコード・コメント・PEP 8） | なし | **212件**（変わらない） |
| 2 | テストの整理（重複・名前・中身のない確認・ループと分岐） | なし（テストの書き方だけ） | **233件** |
| 3 | 使用できない文字の検査と、そのテスト | 孤立サロゲートを含む文字列が、その項目の「使用できない文字が含まれています」になる | **273件** |

## 前提（Task 006完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API（`GET`・`POST /api/semesters`）、授業API（`GET`・`POST /api/subjects`）、`app/api_helpers.py` の検証関数（`validate_required_string`・`validate_optional_string`・`validate_required_integer`・`validate_required_time` など）、pytest（**212件**）、学期UI・授業UI |
| 今の挙動（このタスクで直す） | 孤立サロゲートを含む文字列を送ると、授業の `subject_name`・`room`・`notes` は**500**（DBへの保存のときに `UnicodeEncodeError`）。学期の `name`・`start_date`・`end_date` と、授業の `start_time`・`end_time` は、形式の誤りの400 |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` の「API共通ルール」に、「使用できない文字」と「文字列の項目の検査の順序」があり、「API共通処理の補助モジュール」に、定数 `UNUSABLE_CHARACTER_MESSAGE` がある |
| DBの構造 | 変えない。**migrationは不要** |
| 開発用DB | `instance/app.db` には、実際の学期・授業が入っている場合がある。**このタスクで、書き込まない。** 読むのは、「Copilot確認手順」の1・5・6の読み取り（ハッシュ・件数・`GET`）だけ。Copilotは、`POST` を実行しない |
| 設計資料のほうが先の部分 | 設計資料には、予定（Event）の自動生成、`generated_event_count`、休講日が書かれているが、**このタスクでは実装しない**（後のタスク）。今のコードとテストが、これらを持たないこと（例：授業の登録で予定が作られない、既存のテスト `test_duplicate_subject_rows_are_allowed_and_do_not_create_events_or_tasks`）は、矛盾として扱わない |
| 検査の順序と文言 | 検査の順序は、`docs/architecture.md` の「文字列の項目の検査の順序」に従う。エラーメッセージの文言は、Task 003・005のMDのとおり（変えない）。Task 005のMDの検査の表と、順序の書き方が違って見える箇所があるが、今の入力に対する結果は同じなので、矛盾として扱わない |

## Source of Truth
- `docs/architecture.md`：「API共通ルール」の「リクエストとレスポンス（JSON）」（特に「**文字列**」の「使用できない文字」と「文字列の項目の検査の順序」）、「API共通処理の補助モジュール：`app/api_helpers.py`」、「学期API」、「授業API」、「自動テスト（pytest）」（特に「テストの書き方」）
- `docs/tasks/003_api_foundation_and_semesters_api.md`：学期APIの仕様と、エラーメッセージの文言
- `docs/tasks/005_subjects_api_and_pytest.md`：授業APIの仕様、エラーメッセージの文言、`routes/subjects.py` に書く理由のコメント（「実装の規則」の①②）
- `.github/copilot-instructions.md`：進め方、コーディング方針、「テスト」、「DBスキーマとmigration」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 変更 | `app/routes/subjects.py` | 1 | C1・C3・C4・C5・C6 |
| 変更 | `app/api_helpers.py` | 1・3 | C6（段階1）。使用できない文字の検査（段階3） |
| 変更 | `app/__init__.py` | 1 | C2（**コメントを足すだけ**） |
| 変更 | `tests/conftest.py` | 1 | C6（**折り返しだけ**。fixtureの挙動は変えない） |
| 変更 | `tests/test_api_helpers.py` | 2・3 | T1〜T4（段階2）。テストの追加（段階3） |
| 変更 | `tests/test_subjects_api.py` | 2・3 | T5〜T8（段階2）。テストの追加（段階3） |
| 変更 | `tests/test_semesters_api.py` | 3 | テストの追加だけ（既存のテストは変えない） |

上の7ファイル以外は、変更しない。

## 非対象（このタスクでは作らない・変更しない）
- `app/routes/semesters.py`（**変更しない**。学期APIの使用できない文字の検査は、`api_helpers.py` の検証関数を通じて入る）、`app/routes/main.py`
- `app/models/`、`app/config.py`、`app/extensions.py`、`run.py`
- `migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない。** DBの構造の変更が必要だと判断した場合は、作らず・適用せず、停止して報告する）
- `app/templates/`、`app/static/`（画面・JavaScript）。**Task 006で見つかった学期登録モーダルの不具合（登録に成功してもモーダルが閉じず、ボタンが無効のまま残る）は、Task 008で扱う。このタスクでは直さない**
- `docs/`、`.github/`、`.gitignore`、`pytest.ini`、`requirements.txt`（**ライブラリを追加しない**。`pycodestyle`・`flake8` なども入れない）、`tests/test_setup.py`
- Task 003で持ち越した項目（405の `Allow` ヘッダー、`assert` の整理、`Semester.query` と `db.session` の書き方の統一、学期APIの日付検証コードの共通化）
- 休講日、予定（Event）の自動生成、`generated_event_count`、`app/class_events.py`、授業の編集・削除、Task 006のLow（画面の持ち越し）
- JSONの項目名（キー）と、URLのクエリへの、使用できない文字の検査（設計資料で対象外。今の挙動を、テストで確かめるだけ）
- 整理の対象に見えても、変えないもの：`routes/semesters.py` の `assert`（Task 003の持ち越し）、`routes/subjects.py` の `elif semester_id is not None:`、テスト `test_duplicate_subject_rows_are_allowed_and_do_not_create_events_or_tasks`（予定の自動生成のタスクで変える）

## 段階1：コードの整理（APIの挙動を変えない）
Task 005のレビューの軽微な指摘（Low）の種類（不要なimport・死んだコード・コメント・PEP 8）を、今の `main` のコードで確かめ直した一覧。行番号は、`main`（このタスクを始める時点）のもの。

| 番号 | 種類 | 場所 | 変更 |
|---|---|---|---|
| C1 | 不要なimport | `app/routes/subjects.py` 2行目 `from datetime import time` | 削除する（使われていない） |
| C2 | 不要なimportに見えるもの | `app/__init__.py` 29行目 `from app import models` | **削除しない**（モデルをSQLAlchemyに登録するために必要で、migrationもこれに頼る）。直前に、理由のコメントを足す（下の例） |
| C3 | 死んだコード | `app/routes/subjects.py` の `create_subject` の `if payload is None:` のブロック（101〜105行目） | 削除する（`read_json_object` は、エラーがないとき、必ず辞書を返すため、通らない）。代わりの `assert` は書かない |
| C4 | 死んだコード | `app/routes/subjects.py` の `get_subjects` の `if semester_id < 1:` と、その `return jsonify([])`（75〜76行目） | 削除する（先頭の0を取り除いた、空でない数字は、必ず1以上のため、通らない） |
| C5 | コメント | `app/routes/subjects.py` | Task 005のMDの「実装の規則」で指示した、理由のコメント2つをそろえる。①「範囲外のIDをDBに渡すと…」のコメント（130行目。今は `else` の中）を、範囲を確かめる `if not 1 <= semester_id <= MAX_ID:` の直前に移す。②`get_subjects` の桁数の確認（68〜73行目）の直前に、理由のコメントを足す（今はない） |
| C6 | PEP 8（1行79文字まで） | `app/api_helpers.py` 74行目、`app/routes/subjects.py` 185行目、`tests/conftest.py` 33行目 | 79文字以内に折り返す（処理は変えない）。`tests/test_subjects_api.py` 335行目は、段階2のT8で解消する |

書き方の例（同じ意味なら、文言は多少違ってよい。1行は79文字以内）：

```python
# C2（app/__init__.py）
    # モデルをSQLAlchemyに登録するための読み込み。名前は使わないが、
    # migrationがテーブルを見つけるために必要なので、消さない。
    from app import models

# C5①（create_subject）
    elif semester_id is not None:
        # 範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。
        if not 1 <= semester_id <= MAX_ID:
            fields["semester_id"] = "指定された学期が存在しません"
        else:
            if db.session.get(Semester, semester_id) is None:
                fields["semester_id"] = "指定された学期が存在しません"

# C5②（get_subjects）
        # MAX_IDより大きい数をDBに渡すとOverflowErrorになり、非常に長い
        # 数字の文字列をint()に渡すとValueErrorになるため、int()の前に、
        # 桁数と値でMAX_IDと比べる。
        maximum_id = str(MAX_ID)

# C6（api_helpers.py の read_json_object）
def read_json_object() -> tuple[
    dict[str, Any] | None,
    tuple[Response, int] | None,
]:

# C6（subjects.py の時刻の前後の確認）
    elif (
        start_time is not None
        and end_time is not None
        and end_time <= start_time
    ):

# C6（conftest.py の template_db）
    template_directory = tmp_path_factory.mktemp("schedule-template")
    template_path = template_directory / "template.db"
```

段階1の終わりに、`python -m pytest -q` が **212件、すべて合格**すること。

## 段階2：テストの整理（APIの挙動を変えない）
Task 005のレビューのLowのうち、テストの改善に当たるもの。**変更してよいテストは、この表のものだけ**（ほかの既存のテストは変えない）。

| 番号 | ファイル | 対象のテスト | 変更 | 件数 |
|---|---|---|---|---|
| T1 | `test_api_helpers.py` | `test_validate_required_string_checks_required` | パラメータを `payload` にし、`[{}, {"value": None}, {"value": ""}]` の3つにする（今は、パラメータごとに `{}` を確かめ直している） | 2→3 |
| T2 | `test_api_helpers.py` | `test_validate_optional_string_normalizes_empty_values` | パラメータを `payload` にし、`[{}, {"value": None}, {"value": ""}, {"value": "  "}, {"value": "　"}]` の5つにする（同じ理由） | 4→5 |
| T3 | `test_api_helpers.py` | （新規）`test_validate_required_string_reports_type_error` | `123`・`True`・`[]` → `(None, "型")`（型の誤りの単体テストがないため） | +3 |
| T4 | `test_api_helpers.py` | （新規）`test_validate_required_time_reports_non_string_as_format_error` | `900`・`True` → `(None, "形式")`（時刻は、型の誤りも形式のメッセージ） | +2 |
| T5 | `test_subjects_api.py` | `test_optional_subject_fields_validate_types_and_length` | パラメータの `("room", "教" * 101, "教室は100文字以内にしてください")` を削除する（`test_subject_name_and_room_over_length_are_rejected` と同じ確認のため）。長さの確認がなくなるため、名前を `test_optional_subject_fields_validate_types` に変える | 5→4 |
| T6 | `test_subjects_api.py` | `test_subject_get_success_and_not_found`、`test_empty_subject_list_and_all_semester_listing` | 名前だけを、中身に合わせて変える：`test_subject_get_returns_created_subject`、`test_empty_subject_list_returns_empty_array`（中身は変えない） | 変わらない |
| T7 | `test_subjects_api.py` | `test_unsupported_subject_methods_do_not_change_rows` | 授業が0件のまま確かめているため、先に授業を1件、ORMで作り（`with app.app_context():` の中で `db.session.add`・`commit`。テストの準備は、APIを通さない）、URLの `1` を、作った授業のidにする（例：パラメータを `"/api/subjects/{subject_id}"` にして、テストの中で埋める）。要求の前と後に、その授業を `GET` し、応答が同じことと、授業の件数が同じことを確かめる（`POST` の応答とは比べない。のちのタスクで、`POST` の応答だけに項目が増えるため）。期待する状態コード（405）と `code` は変えない | 変わらない（6） |
| T8 | `test_subjects_api.py` | `test_invalid_subject_times_are_rejected_for_both_fields` | 1つのテストの中のループと分岐をなくすため、次の2つのテストに分け、元のテストは削除する。期待するメッセージは、モジュールの辞書（例：`TIME_MESSAGES[field]["required"]`・`["format"]`）から、`field` で引く（文言は、今と同じ）。①`test_missing_subject_times_are_required`：`field` × `[None, ""]` → 必須のメッセージ。②`test_malformed_subject_times_are_rejected`：`field` × 13の値（`900`・`True`・`"9:00"`・`"09:0"`・`"0900"`・`"09:00:00"`・`"24:00"`・`"09:60"`・`"ab:cd"`・`" 09:00"`・`"09:00 "`・`"09:00\n"`・`"０９：００"`）→ 形式のメッセージ。`field` は `"start_time"`・`"end_time"` の2つ（`pytest.mark.parametrize` を2つ重ねてよい） | 15→30 |

段階2の終わりに、`python -m pytest -q` が **233件、すべて合格**すること（段階1のコードのまま、テストだけを変えて合格する）。この時点で、79文字を超える行がないこと（「Copilot確認手順」の3）。

## 段階3：使用できない文字の検査

### 3-1. `app/api_helpers.py`
**DBの操作を持たせない**（`db` を `import` しない）。

| 追加・変更 | 内容 |
|---|---|
| 定数 `UNUSABLE_CHARACTER_MESSAGE`（新設） | 値は `"使用できない文字が含まれています"`。すべての項目で同じ文言。ファイルの上の方（`INVALID_JSON_MESSAGE` の近く）に置く |
| `contains_unusable_character(value: str) -> bool`（新設） | `value` に、U+D800〜U+DFFF の文字が1つでもあれば `True`。それ以外は `False`。正しい組（サロゲートペア）は、Pythonでは1つの文字（U+10000以上）になるため、`False` になる。日本語のdocstringを書く |
| `validate_required_string`（変更） | 下の表の順序で検査する |
| `validate_optional_string`（変更） | 下の表の順序で検査する |
| `validate_required_time`（変更） | 下の表の順序で検査する |

検査の順序（`docs/architecture.md` の「文字列の項目の検査の順序」のとおり。最初に見つかった誤りを返す）：

| 関数 | 順序 |
|---|---|
| `validate_required_string` | ①キーがない・`None`・`""` → `required_message` ②文字列でない → `type_message` ③使用できない文字 → `UNUSABLE_CHARACTER_MESSAGE` ④`strip=True` のとき、前後の空白を取り除き、空なら `required_message` ⑤`max_length` を超えたら `length_message` |
| `validate_optional_string` | ①キーがない・`None` → `(None, None)` ②文字列でない → `type_message` ③使用できない文字 → `UNUSABLE_CHARACTER_MESSAGE` ④前後の空白を取り除き、空なら `(None, None)` ⑤`max_length` を超えたら `length_message` |
| `validate_required_time` | ①キーがない・`None`・`""` → `required_message` ②文字列でない → `format_message`（**これまでどおり、型の誤りも形式のメッセージ**） ③使用できない文字 → `UNUSABLE_CHARACTER_MESSAGE` ④`parse_time` が `None` → `format_message` |

- 使用できない文字の検査は、**引数を指定しなくても、常に行う**（設計資料の「共通関数の追加・拡張で、すでにあるAPIの挙動を変えない」の例外）。新しい引数は足さない
- ほかの関数（`validate_required_integer`・`validate_allowed_fields`・`read_json_object`・`parse_time`・`parse_date`・`format_time`・`format_date`）は、段階1のC6の折り返しを除いて、変えない
- routeのファイルは、段階3では変更しない（学期の `name`・`start_date`・`end_date` は `validate_required_string` を、授業の `subject_name` は `validate_required_string`、`room`・`notes` は `validate_optional_string`、`start_time`・`end_time` は `validate_required_time` を通るため、すべての文字列の項目が対象になる）
- 3つの検証関数のdocstringを、使用できない文字の検査を含む内容に直す

### 3-2. 変わる挙動

| 入力 | 今 | 変更後 |
|---|---|---|
| 授業の `subject_name`・`room`・`notes` に、孤立サロゲートを含む文字列 | 500 | 400（`validation_error`）。その項目に「使用できない文字が含まれています」 |
| 授業の `start_time`・`end_time` に、孤立サロゲートを含む文字列 | 400（形式の誤り） | 400。その項目に「使用できない文字が含まれています」 |
| 学期の `name`・`start_date`・`end_date` に、孤立サロゲートを含む文字列 | 400（形式の誤り） | 400。その項目に「使用できない文字が含まれています」 |

この表の「孤立サロゲートを含む文字列」は、JSONの正しいエスケープ（`\ud800` など）を解析したあとの文字列のこと。全体の `message` は、これまでどおり「入力内容に誤りがあります」。ほかの項目の誤りも、これまでどおり、あわせて `fields` に入る。

### 3-3. 変わらない挙動
- キーがない・`null`・空文字 `""` は、これまでどおり必須のエラー（型の検査より先）。任意項目は `null`
- 型の誤りは、これまでどおり型のメッセージ（時刻の項目は、形式のメッセージ）
- 前後の空白を取り除く項目・取り除かない項目は、これまでどおり。前後の空白と孤立サロゲートの両方がある場合は、使用できない文字のエラー（空白の除去より先に検査するため）
- 正しい組（サロゲートペア。絵文字など）は、受け付け、1文字として数える
- JSONの項目名（キー）に孤立サロゲートがある場合：これまでどおり、未知の項目として400（「この項目は指定できません」）。500にならない
- URLのクエリ：授業の一覧の `semester_id` は、これまでどおり、整数の形式の検査で400。未知のクエリは無視する
- UTF-8として読めない本文（例：`\xff`）：これまでどおり、400（`invalid_json`）。`read_json_object` は変えない（A2・B2で確かめる）
- 参考：孤立サロゲートを表すバイト列（例：`\xed\xa0\x80`）も不正なUTF-8だが、今の実装（Flaskの `request.get_json()` が使う、Pythonの `json`）は、これを `invalid_json` にせず、`"\ud800"` と同じ文字列として読む。このタスクでは、この本文をテストで扱わない。この挙動のために、`read_json_object` やrouteを変更しない
- **孤立サロゲートを含まない入力の結果は、すべて今と同じ**（既存のテストが、期待値を変えずに合格すること）

### 3-4. 追加するテスト
孤立サロゲートは、ソースファイルに直接書かず、Pythonのエスケープ（`"\ud800"`）で書く（ファイルはUTF-8のまま保存できる）。S3の範囲の前後の文字（`"\ud7ff"`・`"\ue000"`）も、目に見えない文字のため、同じくエスケープで書く。孤立サロゲートの検査のテスト（A1・B1・B5など）は、`client.post(url, json=...)` で送る（`"\ud800"` は、JSONの正しいエスケープ `\ud800` として送られ、解析したあとの文字列に、孤立サロゲートが入る）。B6は、項目名にエスケープを書くため、文字列の `data` で送る（下の例）。不正なUTF-8の本文のテスト（A2・B2）だけは、バイト列を `data=b"..."` と `content_type="application/json"` で送る。期待するメッセージは、テストの中で文字列を書かず、`UNUSABLE_CHARACTER_MESSAGE` と、A2・B2では `INVALID_JSON_MESSAGE` を `import` して使う（定数そのもののテストS1を除く）。

`tests/test_api_helpers.py`（単体テスト。DBを使わない。合計22件）：

| 番号 | テスト | 入力 | 期待 |
|---|---|---|---|
| S1 | `test_unusable_character_message_constant` | なし | `UNUSABLE_CHARACTER_MESSAGE == "使用できない文字が含まれています"` |
| S2 | `test_contains_unusable_character_detects_lone_surrogates` | `"\ud800"`・`"\udbff"`・`"\udc00"`・`"\udfff"`・`"a\ud800b"`（5件） | `True` |
| S3 | `test_contains_unusable_character_accepts_other_text` | `""`・`"abc"`・`"日本語"`・`"😀"`・`"\ud7ff"`（範囲の直前）・`"\ue000"`（範囲の直後）（6件） | `False` |
| S4 | `test_validate_required_string_rejects_unusable_characters` | `"\ud800"`・`"科目\udc00"`・`" \ud800 "`（3件）。`strip=True`、`max_length=100`、`length_message="長さ"` | `(None, UNUSABLE_CHARACTER_MESSAGE)` |
| S5 | `test_validate_required_string_rejects_unusable_characters_by_default` | `"\ud800"`。キーワード引数なし | `(None, UNUSABLE_CHARACTER_MESSAGE)` |
| S6 | `test_validate_optional_string_rejects_unusable_characters` | `"\ud800"`・`"  \udfff  "`・`"メモ\ud800"`（3件） | `(None, UNUSABLE_CHARACTER_MESSAGE)` |
| S7 | `test_validate_required_time_rejects_unusable_characters` | `"\ud800"`・`"09:00\udc00"`（2件） | `(None, UNUSABLE_CHARACTER_MESSAGE)` |
| S8 | `test_surrogate_pairs_count_as_one_character` | `"😀😀"`。`max_length=2`、`length_message="長さ"` | `("😀😀", None)` |

`tests/test_semesters_api.py`（既存の補助関数 `create_semester`・`assert_api_error`・`semester_count` を使ってよい。合計6件）：

| 番号 | テスト | 入力 | 期待 |
|---|---|---|---|
| A1 | `test_unusable_characters_in_semester_fields_are_rejected` | 正しい本文（`"2026年度 前期"`・`"2026-04-01"`・`"2026-07-31"`）の1項目だけを替える：`name`＝`"2026年度 前期\ud800"`、`name`＝`"\ud800"`、`start_date`＝`"2026-04-01\ud800"`、`end_date`＝`"\udfff"`（4件） | 400、`validation_error`、「入力内容に誤りがあります」、`fields` は `{その項目: UNUSABLE_CHARACTER_MESSAGE}` だけ。学期の件数が0のまま |
| A2 | `test_invalid_utf8_semester_body_is_invalid_json` | バイト列 `b'{"name": "\xff", "start_date": "2026-04-01", "end_date": "2026-07-31"}'`（`\xff` は、UTF-8として読めないバイト） | 400、`invalid_json`、メッセージは `INVALID_JSON_MESSAGE`、`fields` はない（既存の `test_invalid_json_content` と同じく、`assert_api_error(response, 400, "invalid_json", INVALID_JSON_MESSAGE)` で確かめる）。学期の件数が0のまま。今の実装のままで合格する（変更の前後で結果が変わらないことを確かめるテスト） |
| A3 | `test_surrogate_pair_in_semester_name_is_format_error` | `name`＝`"2026年度 前期😀"` | 400、`fields` は `{"name": "学期名は「2026年度 前期」の形式で指定してください"}`（正しい組は、使用できない文字ではない） |

`tests/test_subjects_api.py`（既存の補助関数 `make_semester`・`subject_payload`・`assert_validation_error`・`subject_count` を使ってよい。合計12件）：

| 番号 | テスト | 入力 | 期待 |
|---|---|---|---|
| B1 | `test_unusable_characters_in_subject_fields_are_rejected` | 基本の本文の1項目だけを替える：`subject_name`＝`"\ud800"`、`subject_name`＝`"  \ud800  "`、`room`＝`"\udfff"`、`notes`＝`"メモ\ud800"`、`start_time`＝`"\ud800"`、`end_time`＝`"09:00\udc00"`（6件） | 400、`fields` は `{その項目: UNUSABLE_CHARACTER_MESSAGE}` だけ。授業の件数が変わらない |
| B2 | `test_invalid_utf8_subject_body_is_invalid_json` | 基本の本文を、バイト列で送る。`subject_name` の値を `b"\xff"`（UTF-8として読めないバイト）にする（下の例） | 400、`invalid_json`、メッセージは `INVALID_JSON_MESSAGE`、`fields` はない（既存の `test_invalid_json_or_content_type_is_rejected` と同じ `invalid_json` の扱い）。授業の件数が0のまま。今の実装のままで合格する |
| B3 | `test_surrogate_pairs_in_subject_strings_are_accepted` | `subject_name`＝`"😀" * 100`、`room`＝`"教室😀"`、`notes`＝`"メモ😀"` | 201。応答の3項目が、入力と同じ |
| B4 | `test_surrogate_pairs_count_as_one_character_for_subject_name` | `subject_name`＝`"😀" * 101` | 400、`{"subject_name": "科目名は100文字以内にしてください"}` |
| B5 | `test_unusable_character_and_other_errors_are_reported_together` | `subject_name`＝`"\ud800"`、`weekday`＝`7` | 400、`fields` は `subject_name`（使用できない文字）と `weekday`（「曜日は0（月曜）〜6（日曜）の整数で指定してください」）の2つ |
| B6 | `test_lone_surrogate_field_name_is_unknown_field` | 基本の本文に、項目名が孤立サロゲートの項目を足し、文字列の `data` で送る（下の例） | 400、`fields` は `{"\ud800": "この項目は指定できません"}`（500にならない） |
| B7 | `test_invalid_bytes_in_semester_id_query_are_validation_error` | `GET /api/subjects?semester_id=%ED%A0%80` | 400、`{"semester_id": "学期IDは整数で指定してください"}`（500にならない） |

B2・B6の本文の例：

```python
# B2：UTF-8として読めないバイト（\xff）を含む本文
body = (
    f'{{"semester_id": {semester_id}, "subject_name": "'.encode()
    + b"\xff"
    + b'", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}'
)
response = client.post(
    "/api/subjects", data=body, content_type="application/json"
)

# B6：JSONのエスケープ \ud800 を、項目名として書く
body = (
    f'{{"semester_id": {semester_id}, "subject_name": "科目", '
    '"weekday": 0, "start_time": "09:00", "end_time": "10:00", '
    '"\\ud800": 1}'
)
```

定数 `UNUSABLE_CHARACTER_MESSAGE` と関数 `contains_unusable_character` を足し、3つの検証関数に検査を入れる前の時点では、S1〜S3・S8・A2・A3・B2・B3・B4・B6・B7の20件が合格する（このうちA2・A3・B2・B6・B7は、今の挙動を固定するテスト）。残りの20件（S4〜S7・A1・B1・B5）は、検証関数に検査を入れて、初めて合格する。

## 変更してよい既存のテスト

| ファイル | 変更してよいもの | それ以外 |
|---|---|---|
| `tests/test_api_helpers.py` | T1・T2の2つのテストの書き方。`import` の追加。T3・T4・S1〜S8の追加 | 変えない |
| `tests/test_subjects_api.py` | T5〜T8の対象のテスト。`import` の追加。補助の辞書（T8）の追加。B1〜B7の追加 | 変えない |
| `tests/test_semesters_api.py` | `import` の追加。A1〜A3の追加 | **既存のテストは変えない** |
| `tests/conftest.py` | C6の折り返しだけ | fixtureの挙動・名前は変えない |
| `tests/test_setup.py` | 変えない | |

- テストの期待値（状態コード・`code`・メッセージ・件数の確認）は、上の表で変えると書いたもの以外、変えない。テストを通すために、期待値を設計資料やTask 003・005のMDに反して変えない
- このタスクでの「既存のテスト」は、**作業の開始時からあり、T1〜T8で変えないテスト**のこと。**既存のテストが想定外に失敗した場合**は、テストの期待値やほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する（「注意」の停止の条件。`.github/copilot-instructions.md` の「テスト」の、原因が設計資料やタスクにある場合と同じく、停止して報告する）
- このタスクで追加・変更したテスト（T1〜T8、S1〜S8、A1〜A3、B1〜B7）が失敗した場合は、表の期待値を変えずに、実装やテストの書き間違いを直す。表の期待値そのものが、設計資料と食い違うと判断した場合は、直さずに停止して報告する

## 実装手順
1. ブランチ・作業ツリーの確認。`docs/architecture.md` に「使用できない文字」「文字列の項目の検査の順序」「`UNUSABLE_CHARACTER_MESSAGE`」が書かれていることを確認する。書かれていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBのハッシュと件数（「Copilot確認手順」の1）。`python -m pytest -q` が212件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** C1〜C6。`python -m pytest -q` が212件、すべて合格すること
4. **（段階2）** T1〜T8。`python -m pytest -q` が233件、すべて合格すること。79文字を超える行がないこと
5. **（段階3）** `api_helpers.py` の定数・関数・検証関数の変更 → `tests/test_api_helpers.py` のS1〜S8（合格を確認）→ `tests/test_semesters_api.py` のA1〜A3 → `tests/test_subjects_api.py` のB1〜B7。`python -m pytest -q` が273件、すべて合格すること
6. 「Copilot確認手順」を実施する
7. 結果を報告して止まる

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）を控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest -q` が、**273件、すべて合格**する（失敗・エラー・スキップが0件）。件数が273でない場合は、どのテストが違うか、理由を報告する
- 段階1の終わりに212件、段階2の終わりに233件が、すべて合格していた
- 段階2と段階3の表のテストが、すべて、表の名前で存在する
- `app/`・`tests/`・`run.py` に、79文字を超える行がない
- C1〜C5の変更が、「Copilot確認手順」の4のとおり
- 実行の前後で、開発用DB（`instance/app.db`）のハッシュが同じで、`semesters`・`subjects` の件数も同じ
- 変更したファイルが、「実装対象ファイル」の7つだけ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
```
# 1. 実施前
git branch --show-current      # feature/007-api-input-validation
git status                     # 変更なし
shasum -a 256 instance/app.db
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"
python -m pytest -q            # 212 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1：212 passed、段階2：233 passed、段階3：273 passed

# 3. 1行の長さ（段階2・段階3の終わり。出力がなければ合格）
python - <<'EOF'
from pathlib import Path
paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 79:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 検索（段階3の終わり）
grep -n "from datetime import time" app/routes/subjects.py     # 出力なし
grep -n "if payload is None" app/routes/subjects.py            # 出力なし
grep -n "semester_id < 1" app/routes/subjects.py               # 出力なし
grep -n "from app import models" app/__init__.py               # 1件（残っている）
grep -n "OverflowError\|ValueError" app/routes/subjects.py     # C5の①②のコメント
grep -n "^UNUSABLE_CHARACTER_MESSAGE = " app/api_helpers.py      # 定義の1件
grep -n "return None, UNUSABLE_CHARACTER_MESSAGE" app/api_helpers.py   # 3件（3つの検証関数）
grep -rn --include="*.py" "使用できない文字が含まれています" app/   # app/api_helpers.py の中だけ（routes などに、この文字列を書かない）
grep -n "^from\|^import\|db\." app/api_helpers.py              # db を import していない、db. を使っていない

# 5. 起動中のサーバーの、読み取りだけの確認（POSTは実行しない。終わったらサーバーを止める）
python run.py                  # 別のターミナルで、以下を実行
BASE=http://127.0.0.1:5001
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/semesters
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/subjects
curl -s -w '\nHTTP %{http_code}\n' "$BASE/api/subjects?semester_id=%ED%A0%80"
curl -s -o /dev/null -w 'HTTP %{http_code} %{content_type}\n' $BASE/

# 6. 実施後（サーバーを止めてから）
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"   # 実施前と同じ
git status                     # 変更：「実装対象ファイル」の7つだけ。新規ファイルなし
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 段階1：212件、段階2：233件、段階3：273件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ | 出力なし |
| 検索 | 上のコメントのとおり |
| 開発用DB | 実施の前後で、ハッシュ・`semesters`・`subjects` の件数が同じ |
| `GET /api/semesters`・`GET /api/subjects` | 200（既存のデータの一覧。変更なし） |
| `?semester_id=%ED%A0%80` | 400、`validation_error`、`fields.semester_id`＝「学期IDは整数で指定してください」 |
| `GET /` | 200、`text/html` |
| サーバー停止後 | `lsof -i :5001` の出力が空 |
| `git status` | 変更：`app/api_helpers.py`、`app/__init__.py`、`app/routes/subjects.py`、`tests/conftest.py`、`tests/test_api_helpers.py`、`tests/test_semesters_api.py`、`tests/test_subjects_api.py` のみ。`app/routes/semesters.py`・`app/models/`・`app/templates/`・`app/static/`・`migrations/`・`docs/`・`requirements.txt`・`run.py`・`instance/` に変更なし |
| `git diff` | `app/__init__.py` はコメントの追加だけ。`tests/conftest.py` は折り返しだけ。`app/routes/subjects.py` はC1〜C6だけ（APIの挙動は変えない）。`api_helpers.py` は、C6と、段階3の定数・関数・3つの検証関数の変更だけ |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**ブラウザでの確認は、このタスクにはない。**

## Komaの確認
1. `python -m pytest -q` を自分で実行し、**273件、すべて合格**することを確認する
2. 開発用DBで、孤立サロゲートを含む登録が400になり、データが増えないことを確かめる（どちらの登録も、検証で失敗するため、データは作られない）。`<学期のid>` は、`curl -s $BASE/api/semesters` で確かめた、実際の学期のid
```
python run.py          # 起動
BASE=http://127.0.0.1:5001
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' \
  -d '{"semester_id": <学期のid>, "subject_name": "\ud800", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}' \
  | python -m json.tool --no-ensure-ascii
curl -s -X POST $BASE/api/semesters -H 'Content-Type: application/json' \
  -d '{"name": "2099年度 前期\ud800", "start_date": "2099-04-01", "end_date": "2099-07-31"}' \
  | python -m json.tool --no-ensure-ascii
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"
```
期待：どちらも、`"code": "validation_error"`。授業は `fields.subject_name`、学期は `fields.name` が「使用できない文字が含まれています」。最後の件数が、最初と同じ（変更前のコードでは、授業の登録が500になる）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に `docs/architecture.md` の「未決定事項」に触れる場合）
  - 「変更しない」と定めたもの（`routes/semesters.py`、`migrations/`、`requirements.txt`、画面のファイルなど）を変更しないと実装できない
  - 作業の前の `python -m pytest` が、212件すべて合格しない
  - **既存のテスト**（作業の開始時からあり、T1〜T8で変えないテスト）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）が必要だと判断した。作らず・適用せずに報告し、承認を待つ
  - テストの実行の前後で、`instance/app.db` が変わった
- `flask db` コマンドを、一切実行しない。ライブラリを追加しない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 途中の承認ゲートはない。「Copilot確認手順」を実施したら、結果を報告して止まる
- 最後の報告に、次を含める：変更したファイル、各段階の `pytest` の件数と警告、1行の長さの確認の結果、検索の結果、開発用DBの前後のハッシュと件数、`git status`・`git diff --stat`、気になった点
