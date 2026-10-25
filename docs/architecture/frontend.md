# JavaScriptの構成（ES modules）

> 仕様の正本。変更は、Komaの承認を得てから、PRで行う（`docs/development/workflow.md`）。

- すべて `app/static/js/` に置き、`<script type="module">` で読み込む
- 入口は `main.js` の1つだけ。`base.html` に `{% block scripts %}` を用意し、`index.html` で、その中に次の1行を書く。他のファイルは `main.js` から `import` するので、ファイルを足してもHTMLの変更は不要
  `<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>`

| ファイル | 役割 |
|---|---|
| `main.js` | 入口。各モードの初期化を呼ぶ |
| `api.js` | `fetch` の共通処理。JSONの送受信を行い、`204` のときは `null` を返す。エラーは `ApiError`（`status`・`code`・`message`・`fields`）として投げる。画面のコードは、APIを呼ぶときに必ずこれを使い、`fetch` を直接呼ばない。仕様は、下の「`api.js` の仕様」 |
| `ui.js` | 複数のモードで使う、表示とフォームの共通処理（DOM要素の取得、表示・非表示の切り替え、フォームのエラーの表示と消去、送信中の表示（フォーカスの扱いを含む。下の規則）、エラーメッセージの取得、JavaScriptからモーダルを閉じる処理）。公開する関数は、`getElement`・`setVisible`・`errorMessageOf`・`clearFormErrors`・`showApiError`・`setSubmitting`・`trackModalShowing`・`hideModal` の8つ（各関数の直前に、引数の形を日本語のコメントで書く。モーダルの2つは、下の規則）。`getElement` は、要素が見つからない場合、`null` を返さず、「要素が見つかりません：<id>」のエラーを投げる（idの書き間違いに、すぐ気づけるようにするため）。日付の補助（`dates.js`）や、リソース固有の処理は持たない |
| `dates.js` | 複数のモードで使う、日付の補助処理。今日の日付の文字列（`localDateString`：「2026-09-21」）、今の日時の文字列（`localDateTimeString`：「2026-10-20T23:59」。課題・タスクのAPIの日時と同じ形。秒は持たない）、日付の表示（`formatJapaneseDate`：「2026年9月21日」、`formatJapaneseDateWithWeekday`：「2026年5月15日（金）」）、日時の表示（`formatJapaneseDateTime`：「2026年10月20日（火） 23:59」）。公開する関数は、この5つ。DOMとAPIは扱わない |
| `categories.js` | 複数のモードで使う、カテゴリの対応表。DBの保存値（`category`）から、表示名・アイコン・色のclassを引く。公開するのは、予定（Event）のカテゴリの対応表 `EVENT_CATEGORIES`（並びは、`app/categories.py` の `EVENT_CATEGORIES` と同じ。カレンダーの絞り込みの選択肢の並びは、`calendar.js` で決める。2026-10-18）と、`eventCategoryOf`（保存値に対応する項目を返す。対応表にない値は、DBに入らない想定だが、画面が止まらないように、保存値をそのまま表示名にし、アイコンと色のclassを付けない）。課題・タスク（Task）のカテゴリの対応表 `TASK_CATEGORIES`（課題・その他）と、`taskCategoryOf`（`eventCategoryOf` と同じ規則）も公開する（2026-10-16に足した）。色の値は持たない（`style.css` の、同じ名前のclassに書く）。DOMとAPIは扱わない |
| `current_semester.js` | 複数のモードで使う、今の学期を選ぶ規則（`chooseCurrentSemester(semesters, today)`。`ui_ux.md` の「授業モード」の学期の「初期選択」の1〜3。学期が0件なら `null`）。授業モードの学期の初期選択（`semesters.js`）と、今の学期の授業から選ぶ欄（`subject_options.js`）で使う（2026-10-16に、`semesters.js` から移した。2つ目の利用者が出たため）。公開する関数は、この1つ。DOMとAPIは扱わない |
| `subject_options.js` | 複数のモードで使う、今の学期の授業から選ぶ欄（プルダウン）の共通処理。今の学期（`current_semester.js`）と、その学期の授業の一覧の取得（`fetchCurrentSubjects()`：`{ semester, subjects }`。学期が0件なら `semester` は `null`）、欄の下の説明の文（`currentSubjectsNote(semester, subjects)`）、選択肢の作成（`renderSubjectOptions(select, subjects, extraSubject = null)`。先頭は「選択してください」）、取得中の説明の文の定数 `SUBJECTS_LOADING_NOTE`。課題の対象授業（`tasks.js`）と、カレンダーから追加する単発の授業（`event_forms.js`）で使う（2026-10-19に、`tasks.js` から移した。2つ目の利用者が出たため。APIとDOMを扱うため、`current_semester.js` には入れない）。公開するのは、この4つ |
| `task_display.js` | 複数のモードで使う、課題・タスクの表示の共通処理。課題・タスクを表す文字列（`taskLabel`：「「レポート第1回」（締切 2026年10月20日（火） 23:59）」。読み上げの名前（`aria-label`）と、削除の確認の文に使う）、期限切れの判定（`isTaskOverdue(task, now)`：未完了で、締切日時が `now`（`YYYY-MM-DDTHH:MM`）より前）、期限切れの印（`createOverdueBadge`）、カテゴリのアイコンと課題名の表示（`createTaskTitle`。アイコンは読み上げず、カテゴリの表示名を見えない文字で添える）。課題・タスクモード（`tasks.js`）と、カレンダーの「直近の締切」欄（`calendar.js`）で使う（2026-10-18に、`tasks.js` から移した。2つ目の利用者が出たため）。公開する関数は、この4つ。APIは扱わない |
| `semesters.js` | 授業モードの学期タブ、学期の登録フォーム、選択中の学期の編集フォーム・削除の確認（2026-10-20）。選択中の学期が変わったこと（と、選択中の学期を編集したこと）を、`semester-selected` で知らせる |
| `subjects.js` | 授業モードの授業の一覧・登録フォーム・編集フォーム・削除の確認。`semester-selected` を購読する |
| `closures.js` | 授業モードの、選択中の学期の休講日の一覧・追加・削除。`semester-selected` を購読する |
| `calendar.js` | カレンダーモード。FullCalendarの設定、予定の取得（予定API）、締切の表示と「直近の締切」欄（課題・タスクAPI）、カテゴリの絞り込み、空き枠のクリック（追加フォームを開く）、予定の詳細パネル（「編集」「削除」）、締切の詳細パネル（完了の切り替えと、「編集」「削除」）。使い方の規則は、下の「FullCalendarの使い方（`calendar.js`）」。課題・タスクの表示の共通処理は、`task_display.js`。予定の追加・編集・削除のモーダルは、`event_forms.js` |
| `event_forms.js` | カレンダーモードの中の部品（2026-10-19）。予定の追加（その他（締切のみ）を含む）・編集・削除の確認のモーダルと、アルバイトを登録したことの知らせ（「同じ内容で別の日も登録」）。`calendar.js` だけが `import` する（下の規則の、モードの中の部品）。公開する関数は、`initEventForms({ onEventsChanged, onTasksChanged })`（登録・編集・削除ができたときに呼ぶ関数を受け取る。カレンダーが、予定・締切を取得し直す）、`openEventAddModal({ date, time = null, deadlineOnly = false })`、`openEventEditModal(apiEvent)`、`openEventDeleteModal(apiEvent)` の4つ |
| `tasks.js` | 課題・タスクモードの一覧（未完了・完了）、完了の切り替え、課題の追加、編集、削除の確認。対象授業の選択肢は、今の学期の授業（`subject_options.js`）。課題・タスクの表示の共通処理は、`task_display.js`。カレンダーとは、`CustomEvent` でつながる（締切の詳細パネルの「編集」「削除」で、このモードの編集・削除のモーダルを開く。編集・削除の結果を知らせる。下の「モード間の連携」。2026-10-19） |

必要になったタスクで、1つずつ作る。

規則：
- 1リソース＝ `routes/<名前>.py` と `static/js/<名前>.js` を対応させる
- HTMLの中に、自作のJavaScriptを書かない
- Jinjaの値をJavaScriptに直接埋め込まない。データはAPIから取得する
- ユーザーの入力を画面に表示するときは、`textContent` を使い、`innerHTML` に直接入れない
- 各モードのファイルは、`initXxx()`（例：`initSemesters()`）を `export` し、`main.js` が呼ぶ。`export` は名前つきにし、`export default` は使わない
- 1つのモードのファイルが大きくなるときは、そのモードの中の部品を、別のファイルに分けてよい（2026-10-19。例：カレンダーモードの `event_forms.js`）。部品のファイルは、そのモードのファイルだけが `import` し、ほかのモードのファイルを `import` しない。部品の初期化（`initXxx()`）は、そのモードのファイルが呼ぶ（`main.js` からは呼ばない）。部品からモードへの知らせ（登録できたら取得し直す、など）は、初期化のときに受け取る関数で行う
- 画面の骨組み（ボタン・モーダル・表示領域）のHTMLは、`index.html`（または、そこから `{% include %}` する部分テンプレート）に書く。JavaScriptが行うのは、表示・非表示の切り替え（Bootstrapの `d-none`）と、文字（`textContent`）の変更。動的に作るのは、件数によって増える部分（一覧のタブや行、課題の対象授業のプルダウンの選択肢など）だけで、`createElement` で作り、`replaceChildren()` で差し替える（例外：カレンダーのカテゴリの絞り込みの選択肢は、表示名を1か所で持つため、`categories.js` の対応表から作る）
- DOMの `id` は、`<リソース名の単数形>-<部分>` の形にする（例：`semester-tabs`、`semester-form`）。入力欄のエラー表示の `id` は、`<項目>-error`（例：`semester-start-date-error`）
- モーダルはBootstrapのものを使う。決まった操作で開くときは、HTMLの `data-bs-toggle="modal"` を使ってよい。値を設定して開くときなどは、JavaScriptから `window.bootstrap.Modal` で開く。閉じるときも、`window.bootstrap.Modal` を使う（インスタンスは、`getOrCreateInstance` で取得する）。`base.html` のBootstrapの `<script>` は通常のスクリプトで、先に読み込まれ、`type="module"` のスクリプトは、ページの解析後に実行されるため、`window.bootstrap` を使える。モーダルのHTMLは、`<main>` や `.tab-pane` の外（ページの最上位）に置く
- JavaScriptからモーダルを閉じるとき（例：登録・編集・削除に成功したとき）は、表示のアニメーションの途中でも閉じられるようにする。Bootstrapは、モーダルを開き始めてから表示が終わるまで（`show.bs.modal` から `shown.bs.modal` まで）の `hide()` を、何もせずに無視するため、そのまま呼ぶと、開いた直後の操作でモーダルが閉じずに残る。この処理は、`ui.js` の共通の関数で行う（2026-10-14に決定。それまでの未決定事項「モーダルを閉じる処理の共通化」。学期の登録に続いて、授業の編集・削除が、2つ目のモジュールとして必要としたため）
  - `trackModalShowing(modal)`：モーダル（要素）が表示の途中かを、`show.bs.modal` と `shown.bs.modal` のイベントで、`ui.js` の中の集合（`Set`）に記録する。Bootstrapの内部の値（`_isTransitioning` など）は使わない。JavaScriptから閉じるモーダルごとに、各モードの初期化（`initXxx()`）で1回だけ呼ぶ
  - `hideModal(modal)`：モーダルを閉じる。表示の途中なら、`shown.bs.modal` を待ってから閉じる。`trackModalShowing` を呼んでおいたモーダルにだけ使う。インスタンスは、`getOrCreateInstance` で取得する
  - 時間を待つ方式（`setTimeout`）にしない（アニメーションの長さに依存するため）
  - 使うのは、学期の登録・編集・削除（`semesters.js`。編集・削除は2026-10-20）と、授業の編集・削除（`subjects.js`）と、課題・タスクの追加・編集・削除（`tasks.js`）と、予定の追加・編集・削除（`event_forms.js`）と、予定・締切の詳細パネル（`calendar.js`。「編集」「削除」で閉じるため。2026-10-19）のモーダル。利用者のボタン（`data-bs-dismiss`）だけで閉じるモーダル（授業の登録）には使わない
- モーダルの中で始める要求（例：学期・授業の編集・削除と、削除の確認の件数の取得。課題・タスクの追加・編集・削除と、対象授業の選択肢のための授業の一覧の取得。締切の詳細パネルの完了の切り替え。予定の追加・編集・削除と、単発の授業の選択肢のための授業の一覧の取得）は、モーダルを開くたびに増やす通し番号を控え、応答が届いたときに、モーダルを開き直していれば（通し番号が違えば）、そのモーダルの表示（入力欄・メッセージ・ボタン）を変えず、閉じない。一覧の取得し直しは行う（データは変わっているため）。モーダルを開いている間は、背後の画面（学期のタブなど）を操作できないため、下の「選択に依存する画面での登録・削除」の、選択の通し番号は使わない
- タブ（`role="tablist"`）の直下の `li` には、`role="presentation"` を付ける。選択が変わったときは、タブを作り直さず、既存のボタンの `active` と `aria-selected` を付け替える（キーボードのフォーカスを保つため）
- 日付の補助処理（今日の日付の文字列、日付の表示形式など）は、`dates.js` に置く。モードのファイルに、同じ処理を作らない（日付の処理を1か所にまとめ、表記をそろえるため）。日付は、APIと同じ `YYYY-MM-DD` の文字列で受け渡す
  - 今日の日付は、ブラウザのローカルの日付から作り（`toISOString()` は使わない）、`YYYY-MM-DD` の文字列のまま比較する
  - 日付の文字列から曜日を求めるときは、`new Date("YYYY-MM-DD")` を使わず、年・月・日を分けて作る（`new Date(year, month - 1, day)`）。`new Date("YYYY-MM-DD")` は、UTCの0時として読まれ、タイムゾーンによっては、前の日の曜日になるため
  - 曜日の表示の並びは、`Date.getDay()` の並び（0=日曜〜6=土曜）。授業の曜日（0=月曜〜6=日曜。DB・APIと同じ）とは並びが違うため、混ぜて使わない。授業の `weekday`（整数）を表示する対応表は、授業の表示の一部として `subjects.js` が持つ（日付の補助処理には含めない）
- 学期の登録フォームの初期値（今日の年度・種別）のように、リソースに固有の日付の処理は、そのリソースのファイルに置く（`semesters.js`）。今の学期の選び方は、2つのモード（授業・課題・タスク）で使うため、`current_semester.js` に置く
- 登録・削除などの要求で、`try` で囲むのは、要求（`apiRequest`）だけにする。成功後の処理（メッセージの表示、入力欄を戻す、一覧の取得し直しなど）は、`try` の外に書く（成功後の処理で例外が起きた場合に、要求の失敗として表示しないため）
- 送信中の表示（`ui.js` の `setSubmitting`）では、ボタンを押せなくする。押せなくしたボタンからは、フォーカスがページ本体に移り、モーダルをEscapeキーで閉じられなくなる（017-N2）。そのため、送信を始めるときに、ボタンにフォーカスがあれば覚えておき、ボタンがモーダルの中なら、フォーカスをモーダル（の要素。`tabindex="-1"`）に移す。送信が終わって、ボタンを押せるように戻すときに、フォーカスがモーダルかページ本体にあれば、ボタンに戻す（ほかの欄に移していれば、そのまま）。この扱いは `setSubmitting` の中だけで行い、各モードのファイルは変えない（2026-10-19に決定。モーダルの外のボタン（休講日の「追加する」「削除」）も、失敗のあとに、フォーカスがボタンに戻る）
- 関数に、意味が呼び出し側から読めない真偽値を、位置の引数で渡さない。名前つきの引数（オブジェクトの分割代入。例：`loadSubjects({ showLoading: false })`）にする。共通の関数の `setVisible(element, visible)`・`setSubmitting(button, submitting, labels)` は、関数名から意味が読めるため、この形のままにする
- 画面のエラー表示：`ApiError` の `fields` があるときは、該当する項目の下に表示する。それ以外のエラーは、`message` を、フォームの上部や画面に表示する。`ApiError` でない例外（プログラムの誤りなど）は、技術的なメッセージを画面に出さず、固定の日本語のメッセージを表示し、詳細は `console.error` に出す
- 選択に依存する取得（例：学期ごとの授業）は、要求のたびに通し番号を増やし、応答が届いたときに、通し番号が違えば（その間に、新しい要求や、選択の解除があれば）、その結果を捨てる
- 選択に依存する画面での登録・削除（例：学期ごとの休講日）は、要求を始めたときの選択を控え、応答が届いたときに選択が変わっていれば、画面（入力欄・メッセージ・ボタン・一覧）を変えない。新しい選択の画面は、選択が変わったときに作り直しているため。控えるのは、選択が変わるたびに増やす通し番号で、取得の通し番号とは別にする（一覧の取得し直しでは、選択は変わらないため）。要求そのものは取り消さない（サーバーでは、登録・削除が行われ、元の選択に戻ると、一覧に反映されている）

## FullCalendarの使い方（`calendar.js`）
- FullCalendarは、`window.FullCalendar` として使う（`base.html` の通常のスクリプト。`window.bootstrap` と同じ）。読み込めなかった場合（`window.FullCalendar` がない）は、例外にせず、カレンダーの場所にメッセージを出す（ほかのモードは使える）。`main.js` は、`initCalendar()` を最後に呼ぶ（カレンダーは、ほかのモードと `CustomEvent` でつながらないため、順序の制約がない。予期しない例外で、ほかのモードの初期化が止まらないようにする）
- **予定の取得は、`api.js` で行う。** FullCalendarに予定APIのURLを渡す方式（取得をFullCalendarに任せる方式）は使わない。`events` に関数を渡し、その中で `apiRequest` を呼ぶ（`fetch` は `api.js` の中だけ、の規則のため。URLの方式は、期間を `start`・`end` の名前の、時刻つきの値で送るため、予定APIの形とも合わない）。関数は、FullCalendarの予定の配列を返す（`Promise`）。失敗したときは、例外を投げて、FullCalendarに失敗を伝える
- **期間の変換**：FullCalendarが渡す期間（`Date`。終わりの日を含まない）を、`dates.js` の `localDateString` で `YYYY-MM-DD` にする。終わりは、その前の日を `end_date` にする（予定APIの期間は、両端を含むため）。この変換は、FullCalendarに固有のため、`calendar.js` に置く
- 古い取得の予定は、FullCalendarが捨てる。画面の表示（取得の失敗の表示）は、取得のたびに増やす通し番号で、最新の取得の結果だけを反映する（「選択に依存する取得」の規則と同じ考え方）
- **取得の失敗**（`eventSourceFailure`）：`ApiError` の失敗は、`fetchEvents` が画面に表示するため、何もしない（FullCalendarの既定の、コンソールへの警告も出さない）。`ApiError` でない例外（取得のあとの絞り込み・形の変換の例外など）は、`showLoadError` で、カレンダーの上に表示する（`errorMessageOf` が、固定のメッセージにし、詳細を `console.error` に出す。2026-10-18に決定。それまでは、何もしない関数で、このような例外が、画面にもコンソールにも出なかった）
- 予定の日時は、タイムゾーンのない `YYYY-MM-DDTHH:MM` で渡す（ブラウザのローカルの日時として読まれる。「データ設計」の、タイムゾーンなしの約束と同じ）
- **色**：予定に、カテゴリのclass（`categories.js` の `className`）を付け、色は `style.css` で、そのclassに、FullCalendarのCSSの変数（`--fc-event-bg-color`・`--fc-event-border-color`・`--fc-event-text-color`）として設定する。JavaScriptでは色を指定しない（FullCalendarの `backgroundColor`・`eventColor` などの色の設定も使わない）
- 表示の中身を変えるとき（一覧表示の行など）は、`eventContent` で、`createElement` と `textContent` で作った要素（`domNodes`）を返す。HTMLの文字列（`html`）は返さない（`innerHTML` を使わない規則と同じ理由）
- **絞り込み**：選択肢（チェックボックス）は、`categories.js` の対応表から作る（表示名を1か所で持つため）。絞り込みを変えたら、予定と締切を取得し直し（`refetchEvents`）、取得した予定・締切から、外したカテゴリのものを除く。対応表にないカテゴリの予定・締切は、絞り込みによらず表示する
- カレンダーのモードを開くたび（`calendar-tab` の `shown.bs.tab`）に、予定と、未完了の課題・タスクを取得し直す（ほかのモードでの登録を反映するため）。あわせて、大きさを計算し直す（`updateSize`。隠れている間に、画面の幅が変わった場合に備えるため）
- **詳細パネル**：Bootstrapのモーダル（予定は `event-modal`、締切は `task-detail-modal`）。JavaScriptから開く。予定・締切のクリック（`eventClick`）で、締切（`extendedProps` に `apiTask` がある）なら締切の詳細パネル、それ以外は予定の詳細パネルを開く
  - 「編集」「削除」（2026-10-19）：パネルを、`ui.js` の `hideModal` で閉じ（表示の途中なら、表示が終わってから閉じる。そのため、2つのパネルに `trackModalShowing` を使う）、閉じ終わってから（`hidden.bs.modal`）、次のモーダルを開く（Bootstrapでは、2つのモーダルを重ねて開けないため）。閉じたあとに行う操作は、1つの変数に控え、パネルを開くとき（`show.bs.modal`）に消す
  - 予定の詳細パネルの「編集」「削除」は、`event_forms.js` の `openEventEditModal`・`openEventDeleteModal` を呼ぶ。締切の詳細パネルの「編集」「削除」は、`task-edit-requested`・`task-delete-requested` を発行し、課題・タスクモード（`tasks.js`）の編集・削除のモーダルを開く（「モード間の連携」）
- **空き枠のクリック**（2026-10-19）：FullCalendarの `dateClick`（標準のバンドルに含まれる）。クリックした日時から、`event_forms.js` の `openEventAddModal` で追加フォームを開く。週表示の時間軸（`allDay` が `false`）は、日付と、30分の枠の始まりの時刻。週表示の終日の行（締切の行）は、その他の「締切のみ」（`deadlineOnly: true`）。月表示の日付の枠は、日付だけ。日時は、`dates.js` の `localDateTimeString` で `YYYY-MM-DD` と `HH:MM` にする。`dateClick` は、予定・締切・月表示の日付の数字（`navLinks`）・「＋N件」のクリックでは起きない（FullCalendarの仕様）。一覧表示では起きない。範囲を選ぶ操作（`selectable`）は使わない
- 予定の追加・編集・削除、その他（締切のみ）の追加ができたら、`event_forms.js` が、`initEventForms` で受け取った関数を呼ぶ。`calendar.js` は、予定なら `refetchEvents()`、締切のみなら、未完了の課題・タスクを取得し直す（締切の取得元と「直近の締切」欄）
- **締切（課題・タスク）**（2026-10-18に決定）
  - 予定とは別の取得元（`eventSources` の2つ目。id は `deadlines`）で、未完了の課題・タスクを、締切日の終日の予定（`allDay: true`）として渡す。見た目は、予定ごとの `display: "list-item"`（●の印とタイトル。カレンダー全体の `eventDisplay` の `"block"` より優先される）。色は、予定と同じく、カテゴリのclass（`categories.js` の `className`）
  - 週表示では、終日の行に出る。終日の行を、締切の行にする（`allDayText: "締切"`。予定は、すべて時刻を持つため、終日の行には締切だけが入る）
  - 課題・タスクは、`calendar.js` が `GET /api/tasks?is_completed=false` で取得し、締切の取得元と「直近の締切」欄で共有する。取得するのは、ページを開いたとき、カレンダーのモードを開いたとき、欄の「再読み込み」、完了の切り替えのあと。取得したら、締切の取得元を `refetch` する。古い応答は、取得のたびに増やす通し番号で捨てる
  - 締切の取得元の関数は、APIを呼ばず、取得済みの課題・タスクから作った締切を、`successCallback` で、すぐに返す（`async` の関数にしない。結果を待つ間に描画が入り、一覧表示に締切が出ることがあったため）。形の変換で例外が起きたときは、`failureCallback` で、FullCalendarに失敗を伝える（`eventSourceFailure` が表示する）
  - 同じ日の並びは、`eventOrder: "start,-duration,allDay,dueDateTime,title"`（FullCalendarの既定の並びに、締切日時（締切の `extendedProps` の `dueDateTime`）を足した）。月表示では、締切（終日）が、時間型の予定より上に、締切日時の順に並ぶ
  - 絞り込みで外したカテゴリの締切は、取得元の関数で除く（予定と同じ）。絞り込みの選択肢の並び（授業・課題・アルバイト・その他）は、`calendar.js` で決める。その他は、予定と課題・タスクで保存値が同じ（`other`）のため、1つの選択肢で両方を切り替える
- **一覧表示には、締切を出さない**（2026-10-18に決定）
  - 表示の切り替えのボタン（週・月・一覧）は、`customButtons` で、表示と同じ名前（`timeGridWeek`・`dayGridMonth`・`listFourWeeks`）の独自のボタンにし、切り替えを `calendar.js` の関数（`switchView`）に通す。FullCalendar 6.1.21は、同じ名前の独自のボタンを、表示のボタンの代わりに置き、今の表示のボタンを、押された状態（`fc-button-active`・`aria-pressed="true"`）にする。ボタンの文言（週・月・一覧）と説明（週表示・月表示・一覧表示）は、`customButtons` で指定する
  - `switchView` は、締切を出すか（`deadlinesShown`）を変え、締切の取得元を `refetch` する。一覧表示へは、締切を外してから `changeView` し、週・月の表示へは、`changeView` のあとで締切を戻す（同じ処理の中で続けて行うため、画面に出るのは最後の状態だけ）
  - 使わない方法：表示が変わったあとのイベント（`datesSet`）で締切を外す方法（一覧表示に、締切が一瞬出るため）。`batchRendering` で、締切の出し入れと `changeView` をまとめる方法（試したところ、一覧表示で、締切と週表示の部品が描画されて、例外になったため）
  - 月表示の日付・「＋N件」のクリック（`navLinkDayClick`・`moreLinkClick`）は、週表示へ移り、`switchView` を通らない。週・月の表示では締切を出すため、そのままでよい
- **日本語**：日付の表示は `locale: "ja"`。ボタン・「＋N件」・予定がないときの文言・ボタンの説明（マウスを重ねたときに出る文字）などは、設定で日本語を指定する（「FullCalendarの読み込み」）
- `eventDisplay`（予定の表示の形）は、表示ごと（`views`）には指定できない（FullCalendar 6 の仕様。指定しても効かない）。カレンダー全体に `"block"` を指定する
- 一覧表示の期間は、日数（`duration: { days: 28 }`）で指定する。週（`weeks`）で指定すると、期間の始まりが日曜日にそろってしまうため

## モード間の連携（`CustomEvent`）
- モード（機能）のファイル同士は、互いを `import` しない。連携は、`document` に対する `CustomEvent` で行う
- イベント名は、`<リソース名>-<出来事>`（例：`semester-selected`）。`detail` には、必要な値の**コピー**を入れる（オブジェクトの参照を渡さない）
- 購読は、`initXxx()` の中（同期処理）で行う。ページを開いたときに発行するイベント（`semester-selected`）は、`main.js` で、購読する側の `initXxx()` を、発行する側より先に呼ぶ（発行は、APIの応答を待ったあとなので、順序がずれても動くが、規則として固定する）。利用者の操作のあとにだけ発行するイベント（`task-edit-requested`・`task-delete-requested`・`task-changed`）は、初期化の順序によらない（カレンダーは、予期しない例外で、ほかのモードの初期化が止まらないように、最後に初期化する）
- 共有する状態の変更と、イベントの発行は、1つの関数にまとめる（`semesters.js` では `selectSemester(id)`）

| イベント | 発行元 | `detail` | 発行する場面 |
|---|---|---|---|
| `semester-selected` | `semesters.js` | `{ semester: { id, name, start_date, end_date } \| null }`（学期がないときは `null`） | 選択中の学期が変わったとき（最初の選択を含む）。学期が0件になったとき（`null`）。同じ学期を選び直したときは、発行しない。ただし、選択中の学期を編集したときは、同じ学期でも発行する（休講日の一覧（期間の外になった休講日は削除されている）と、授業の登録先の学期名を、新しい値で作り直してもらうため。2026-10-20） |
| `task-edit-requested`・`task-delete-requested` | `calendar.js` | `{ task: 課題・タスク }`（課題・タスクAPIの形のコピー） | 締切の詳細パネルの「編集」「削除」で、パネルを閉じ終わったとき（2026-10-19）。購読する `tasks.js` が、編集・削除の確認のモーダルを開く |
| `task-changed` | `tasks.js` | なし | 課題・タスクの編集・削除に成功したとき（一覧から開いた場合も、締切の詳細パネルから開いた場合も。2026-10-19）。購読する `calendar.js` が、未完了の課題・タスクを取得し直す（締切と「直近の締切」欄）。追加と完了の切り替えでは、発行しない（課題・タスクモードからの追加・切り替えは、カレンダーのモードを開くたびの取得で反映する） |

## `api.js` の仕様
- `export class ApiError extends Error`：`status`（HTTPのステータス。応答がないときは `0`）、`code`（文字列）、`message`（画面に出せる日本語）、`fields`（オブジェクトまたは `null`）を持つ
- `export async function apiRequest(method, url, body)`
  - `body` が `undefined` でないときだけ、`Content-Type: application/json` を付けて、`JSON.stringify(body)` を送る（`GET`・`DELETE` には付けない。サーバーも、これらには要求しない）
  - 成功（2xx）：`204` なら `null`、それ以外は、JSONを解析した値を返す
  - 失敗：応答の `{"error": {"code", "message", "fields"}}` から `ApiError` を作って投げる
  - サーバーに接続できない場合（`fetch` が例外）：`status: 0`、`code: "network_error"`、`message: "サーバーに接続できませんでした。時間をおいて、もう一度お試しください"` の `ApiError` を投げる
  - 応答がJSONとして読めない、または `{"error": {...}}` の形でない場合：`code: "invalid_response"`、`message: "サーバーから想定外の応答がありました。時間をおいて、もう一度お試しください"` の `ApiError` を投げる（`status` は、実際の値）
- `network_error` と `invalid_response` は、サーバーが返すコードではなく、`api.js` が作る（「エラー」の表には含めない）
- 再試行・キャッシュ・ログは持たない
