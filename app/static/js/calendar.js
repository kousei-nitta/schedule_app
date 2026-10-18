import { ApiError, apiRequest } from "./api.js";
import {
  EVENT_CATEGORIES,
  TASK_CATEGORIES,
  eventCategoryOf,
  taskCategoryOf,
} from "./categories.js";
import {
  formatJapaneseDateTime,
  formatJapaneseDateWithWeekday,
  localDateString,
  localDateTimeString,
} from "./dates.js";
import {
  createOverdueBadge,
  createTaskTitle,
  isTaskOverdue,
  taskLabel,
} from "./task_display.js";
import { errorMessageOf, getElement, setVisible } from "./ui.js";

// 表示の種類（FullCalendarの表示の名前）。
const WEEK_VIEW = "timeGridWeek";
const MONTH_VIEW = "dayGridMonth";
const LIST_VIEW = "listFourWeeks";
// 一覧表示の期間の日数（今日から4週間）。前後への移動も、この日数ずつ。
const LIST_DAYS = 28;
// 「直近の締切」欄に載せる範囲。期限切れと、締切日が今日からこの日数後
// までのもの（来週の同じ曜日の締切まで入る）。欄の説明の文（index.html）の
// 日数と合わせる。
const UPCOMING_DAYS = 7;
// 締切の取得元（FullCalendarの eventSources）のid。
const DEADLINE_SOURCE_ID = "deadlines";
// 絞り込みの選択肢（保存値と、カテゴリの対応表の項目）。並びは、授業・
// 課題・アルバイト・その他。その他は、予定（時間指定あり）と課題・タスク
// （締切のみ）で保存値が同じ（"other"）のため、1つの選択肢で両方を
// 切り替える。
const FILTER_CATEGORIES = [
  ["class", EVENT_CATEGORIES.class],
  ["assignment", TASK_CATEGORIES.assignment],
  ["part_time", EVENT_CATEGORIES.part_time],
  ["other", EVENT_CATEGORIES.other],
];
// 一覧表示の行で、タイトルの横に出す主要項目（カテゴリの保存値 → 予定の項目）。
const LIST_DETAIL_FIELDS = new Map([
  ["class", "room"],
  ["part_time", "employer"],
]);
const LIBRARY_ERROR_MESSAGE =
  "カレンダーの部品を読み込めませんでした。" +
  "ネットワークの接続を確かめて、ページを再読み込みしてください";

let calendar = null;
// 絞り込みで外したカテゴリの保存値。初期状態は、すべてのカテゴリを表示する。
const hiddenCategories = new Set();
// 予定の取得の通し番号。古い取得の結果で、今の表示（エラーの表示）を
// 変えないために使う（古い取得の予定は、FullCalendarが捨てる）。
let requestSerial = 0;
// 未完了の課題・タスク（課題・タスクAPIの一覧。締切日時・idの昇順）。
// カレンダーの締切と、「直近の締切」欄で使う。
let incompleteTasks = [];
// 課題・タスクの取得の通し番号（古い応答で、今の表示を変えないため）。
let taskRequestSerial = 0;
// カレンダーに締切を出すか。一覧表示では出さない（期限型は載せないため）。
let deadlinesShown = true;
// 課題・タスクの詳細パネルの対象（課題・タスクのコピー）と、開いたときの
// 日時（期限切れの判定に使う）。開くたびに増やす通し番号は、閉じて開き
// 直したあとに届いた古い応答で、今の表示を変えないために使う。
let detailTask = null;
let detailOpenedAt = "";
let detailSerial = 0;

function showLoadError(error) {
  getElement("calendar-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("calendar-load-error"), true);
}

function hideLoadError() {
  setVisible(getElement("calendar-load-error"), false);
}

// FullCalendarの期間（終わりの日を含まない Date）を、予定APIの期間
// （両端を含む YYYY-MM-DD）にする。終わりの日は、その前の日にする。
function toApiRange(start, end) {
  // 日に0を渡すと、前の月の最後の日になる（月をまたいでも正しい）。
  const lastDate = new Date(
    end.getFullYear(),
    end.getMonth(),
    end.getDate() - 1,
  );
  return {
    startDate: localDateString(start),
    endDate: localDateString(lastDate),
  };
}

// 予定APIの予定を、FullCalendarの予定の形にする。日時は、タイムゾーンの
// ない「YYYY-MM-DDTHH:MM」で渡す（ブラウザのローカルの日時として読まれる）。
function toCalendarEvent(apiEvent) {
  const category = eventCategoryOf(apiEvent.category);
  return {
    id: String(apiEvent.id),
    title: apiEvent.title,
    start: `${apiEvent.date}T${apiEvent.start_time}`,
    end: `${apiEvent.date}T${apiEvent.end_time}`,
    classNames: category.className === "" ? [] : [category.className],
    // 詳細パネルと一覧表示で使うため、APIの予定のコピーを持たせる。
    extendedProps: { apiEvent: { ...apiEvent } },
  };
}

// FullCalendarが、表示する期間が変わるたびと、refetchEvents() のたびに
// 呼ぶ。予定APIから期間の予定を取得し、絞り込みで外したカテゴリを除く。
async function fetchEvents(fetchInfo) {
  requestSerial += 1;
  const serial = requestSerial;
  const { startDate, endDate } = toApiRange(fetchInfo.start, fetchInfo.end);
  const query = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  let apiEvents;
  try {
    apiEvents = await apiRequest("GET", `/api/events?${query}`);
  } catch (error) {
    if (serial === requestSerial) {
      showLoadError(error);
    }
    // FullCalendarに、取得の失敗を伝える。
    throw error;
  }

  if (serial === requestSerial) {
    hideLoadError();
  }
  return apiEvents
    .filter((apiEvent) => !hiddenCategories.has(apiEvent.category))
    .map(toCalendarEvent);
}

// 課題・タスクを、FullCalendarの締切（締切日の終日の予定）にする。週表示の
// 「締切」の行（終日の行）と、月表示の日付の中に、●の印とタイトルで出す。
function toDeadlineEvent(task) {
  const category = taskCategoryOf(task.category);
  const [dueDate] = task.due_datetime.split("T");
  return {
    id: `task-${task.id}`,
    title: task.title,
    start: dueDate,
    allDay: true,
    // ●の印で表示する（時間型の予定は、カレンダー全体の eventDisplay の
    // "block"。色のブロック）。
    display: "list-item",
    classNames: category.className === "" ? [] : [category.className],
    // dueDateTime は、同じ日の締切を、締切日時の順に並べるため（eventOrder）。
    // 詳細パネルで使うため、課題・タスクのコピーを持たせる。
    extendedProps: {
      dueDateTime: task.due_datetime,
      apiTask: { ...task },
    },
  };
}

// 締切の取得元。FullCalendarが、表示する期間が変わるたびと、refetch の
// たびに呼ぶ。課題・タスクは loadDeadlines で取得済みのため、APIは呼ばず、
// すぐに結果を返す（async にせず、successCallback を呼ぶ。待つ間に描画が
// 入らないようにするため）。一覧表示と、絞り込みで外したカテゴリの締切は
// 出さない。
function fetchDeadlines(fetchInfo, successCallback, failureCallback) {
  let deadlineEvents;
  try {
    deadlineEvents = deadlinesShown
      ? incompleteTasks
          .filter((task) => !hiddenCategories.has(task.category))
          .map(toDeadlineEvent)
      : [];
  } catch (error) {
    // 形の変換の例外も、FullCalendarに失敗として伝える（eventSourceFailure）。
    failureCallback(error);
    return;
  }
  successCallback(deadlineEvents);
}

function refetchDeadlines() {
  calendar.getEventSourceById(DEADLINE_SOURCE_ID).refetch();
}

// 表示を切り替える（週・月・一覧のボタン）。一覧表示では、締切を出さない。
// 一覧表示に、締切が一瞬でも出ないように、一覧表示へは、締切を外してから
// 切り替え、週・月の表示へは、切り替えてから締切を戻す（どちらも、同じ
// 処理の中で続けて行うため、画面に出るのは、最後の状態だけ）。
function switchView(viewType) {
  if (viewType === LIST_VIEW) {
    deadlinesShown = false;
    refetchDeadlines();
    calendar.changeView(viewType);
    return;
  }
  calendar.changeView(viewType);
  deadlinesShown = true;
  refetchDeadlines();
}

// 一覧表示の行の、タイトルの欄の中身。アイコン・タイトルと、カテゴリごとの
// 主要項目（授業＝教室、アルバイト＝派遣会社）を、textContent で作る。
function renderListEventContent(arg) {
  const apiEvent = arg.event.extendedProps.apiEvent;
  const category = eventCategoryOf(apiEvent.category);

  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;

  const title = document.createElement("span");
  title.textContent = apiEvent.title;

  const nodes = [icon, title];
  const detailField = LIST_DETAIL_FIELDS.get(apiEvent.category);
  if (detailField !== undefined && apiEvent[detailField] !== null) {
    const detail = document.createElement("span");
    detail.className = "ms-2 text-muted small";
    detail.textContent = apiEvent[detailField];
    nodes.push(detail);
  }
  return { domNodes: nodes };
}

// 詳細パネルの1行（教室・派遣会社・対象授業・メモ）。値がなければ、行ごと
// 隠す。
function setDetailRow(rowId, valueId, value) {
  getElement(valueId).textContent = value ?? "";
  setVisible(getElement(rowId), value !== null);
}

// 予定の詳細パネルを開く（読み取りだけ。閉じるのは、利用者のボタンだけ）。
function showEventDetail(apiEvent) {
  const category = eventCategoryOf(apiEvent.category);
  getElement("event-modal-title").textContent = apiEvent.title;
  getElement("event-modal-category-icon").textContent = category.icon;
  getElement("event-modal-category").textContent = category.label;
  getElement("event-modal-date").textContent =
    formatJapaneseDateWithWeekday(apiEvent.date);
  getElement("event-modal-time").textContent =
    `${apiEvent.start_time} 〜 ${apiEvent.end_time}`;
  setDetailRow("event-modal-room-row", "event-modal-room", apiEvent.room);
  setDetailRow(
    "event-modal-employer-row",
    "event-modal-employer",
    apiEvent.employer,
  );
  setDetailRow("event-modal-notes-row", "event-modal-notes", apiEvent.notes);

  const modal = window.bootstrap.Modal.getOrCreateInstance(
    getElement("event-modal"),
  );
  modal.show();
}

function showDeadlineLoading() {
  setVisible(getElement("calendar-deadline-loading"), true);
  setVisible(getElement("calendar-deadline-load-error"), false);
  setVisible(getElement("calendar-deadline-content"), false);
}

function showDeadlineLoadError(error) {
  getElement("calendar-deadline-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("calendar-deadline-loading"), false);
  setVisible(getElement("calendar-deadline-load-error"), true);
  setVisible(getElement("calendar-deadline-content"), false);
}

function showDeadlineActionError(error) {
  const actionError = getElement("calendar-deadline-action-error");
  actionError.textContent = errorMessageOf(error);
  setVisible(actionError, true);
}

function hideDeadlineActionError() {
  const actionError = getElement("calendar-deadline-action-error");
  actionError.replaceChildren();
  setVisible(actionError, false);
}

// 「直近の締切」欄の1行（完了のチェックボックス、締切と期限切れの印、
// アイコンと課題名、対象授業）。now は、期限切れの判定に使う今の日時。
function createDeadlineItem(task, now) {
  const item = document.createElement("li");
  item.className = "d-flex gap-2 py-2 border-top";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `calendar-deadline-complete-${task.id}`;
  checkbox.className = "form-check-input flex-shrink-0 mt-1";
  checkbox.setAttribute("aria-label", `${taskLabel(task)}の完了`);
  checkbox.addEventListener("change", () => {
    toggleDeadlineCompleted(task, checkbox);
  });

  // 区切れる場所のない長い文字列も、欄の中で折り返す。
  const body = document.createElement("div");
  body.className = "text-break";

  const due = document.createElement("div");
  due.className = "small";
  due.textContent = formatJapaneseDateTime(task.due_datetime);
  if (isTaskOverdue(task, now)) {
    due.append(createOverdueBadge());
  }
  body.append(due, createTaskTitle(task));

  if (task.subject_name !== null) {
    const subject = document.createElement("div");
    subject.className = "small text-muted";
    subject.textContent = task.subject_name;
    body.append(subject);
  }

  item.append(checkbox, body);
  return item;
}

// 「直近の締切」欄を作り直す。期限切れと、締切日が今日から UPCOMING_DAYS
// 日後までの未完了を、締切日時の順（APIの並び）に並べる。カテゴリの
// 絞り込みの影響を受けない。今日と期限切れは、作り直すときの、ブラウザの
// 日付・時刻で決める。
function renderDeadlinePanel() {
  const now = new Date();
  const lastDate = localDateString(
    new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + UPCOMING_DAYS,
    ),
  );
  const nowText = localDateTimeString(now);
  // 期限切れ（締切日時が今より前）は、締切日が今日以前のため、すべて入る。
  const tasks = incompleteTasks.filter(
    (task) => task.due_datetime.split("T")[0] <= lastDate,
  );

  const fragment = document.createDocumentFragment();
  for (const task of tasks) {
    fragment.append(createDeadlineItem(task, nowText));
  }
  getElement("calendar-deadline-list").replaceChildren(fragment);
  setVisible(getElement("calendar-deadline-empty"), tasks.length === 0);
  setVisible(getElement("calendar-deadline-list"), tasks.length > 0);
  setVisible(getElement("calendar-deadline-loading"), false);
  setVisible(getElement("calendar-deadline-load-error"), false);
  setVisible(getElement("calendar-deadline-content"), true);
}

// 未完了の課題・タスクを取得し、「直近の締切」欄と、カレンダーの締切を
// 作り直す。失敗したときは、欄に、エラーと「再読み込み」を出す（カレンダーの
// 締切は、それまでに表示していたものが残る）。
async function loadDeadlines({ showLoading = true } = {}) {
  const currentRequest = ++taskRequestSerial;
  if (showLoading) {
    showDeadlineLoading();
  }

  let tasks;
  try {
    tasks = await apiRequest("GET", "/api/tasks?is_completed=false");
  } catch (error) {
    // 新しい取得を始めていたら、古い取得の結果で、画面を変えない。
    if (currentRequest !== taskRequestSerial) {
      return;
    }
    showDeadlineLoadError(error);
    return;
  }

  if (currentRequest !== taskRequestSerial) {
    return;
  }
  incompleteTasks = tasks;
  renderDeadlinePanel();
  refetchDeadlines();
}

// 「直近の締切」欄の完了の切り替え（チェックボックス）。確認は出さない。
// 成功したら、取得し直す（完了にしたものは、欄とカレンダーから消える）。
// 失敗したら、チェックを元に戻し、エラーを欄の上部に出す。
async function toggleDeadlineCompleted(task, checkbox) {
  hideDeadlineActionError();
  checkbox.disabled = true;

  // try で囲むのは、切り替えの要求だけにする（成功後の処理の例外を、
  // 「切り替えの失敗」として表示しないため）。
  try {
    await apiRequest("PATCH", `/api/tasks/${task.id}`, {
      is_completed: checkbox.checked,
    });
  } catch (error) {
    checkbox.checked = !checkbox.checked;
    checkbox.disabled = false;
    showDeadlineActionError(error);
    return;
  }

  await loadDeadlines({ showLoading: false });
}

// 課題・タスクの詳細パネルを開く（カレンダーの締切のクリック）。値は、
// 開くとき（show.bs.modal）に入れる。閉じるのは、利用者のボタンだけ。
function showTaskDetail(apiTask) {
  detailTask = { ...apiTask };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("task-detail-modal"),
  ).show();
}

// 詳細パネルの期限切れの印を、今の完了の状態に合わせる（判定の日時は、
// 開いたとき）。
function updateDetailOverdue() {
  setVisible(
    getElement("task-detail-overdue"),
    isTaskOverdue(detailTask, detailOpenedAt),
  );
}

function showDetailError(error) {
  const detailError = getElement("task-detail-error");
  detailError.textContent = errorMessageOf(error);
  setVisible(detailError, true);
}

function hideDetailError() {
  const detailError = getElement("task-detail-error");
  detailError.replaceChildren();
  setVisible(detailError, false);
}

// 詳細パネルを開くたびに、対象の値を表示し、エラーを消す。
function prepareTaskDetail() {
  detailSerial += 1;
  detailOpenedAt = localDateTimeString();
  const task = detailTask;
  const category = taskCategoryOf(task.category);

  getElement("task-detail-modal-title").textContent = task.title;
  getElement("task-detail-category-icon").textContent = category.icon;
  getElement("task-detail-category").textContent = category.label;
  getElement("task-detail-due").textContent = formatJapaneseDateTime(
    task.due_datetime,
  );
  updateDetailOverdue();
  setDetailRow(
    "task-detail-subject-row",
    "task-detail-subject",
    task.subject_name,
  );
  setDetailRow("task-detail-notes-row", "task-detail-notes", task.notes);

  const checkbox = getElement("task-detail-completed");
  checkbox.checked = task.is_completed;
  checkbox.disabled = false;
  hideDetailError();
}

// 詳細パネルの完了の切り替え（チェックボックス）。確認は出さない。パネルは
// 開いたまま（チェックを外せば、未完了に戻せる）。保存が終わったら、
// チェックボックスを押せるように戻し、フォーカスを戻す（押せなくしたときに、
// フォーカスがページ本体に移り、Escapeキーでパネルを閉じられなくなるため。
// 017-N2）。カレンダーの締切と「直近の締切」欄は、取得し直す。
async function toggleDetailCompleted() {
  // 応答が届くまでに、パネルを開き直したかを確かめるために控える。
  const startedSerial = detailSerial;
  const task = detailTask;
  const checkbox = getElement("task-detail-completed");
  const completed = checkbox.checked;
  hideDetailError();
  checkbox.disabled = true;

  // try で囲むのは、切り替えの要求だけにする。
  try {
    await apiRequest("PATCH", `/api/tasks/${task.id}`, {
      is_completed: completed,
    });
  } catch (error) {
    // パネルを開き直していたら、今のパネルの表示を変えない。
    if (startedSerial === detailSerial) {
      checkbox.checked = !completed;
      checkbox.disabled = false;
      checkbox.focus();
      showDetailError(error);
    }
    return;
  }

  if (startedSerial === detailSerial) {
    task.is_completed = completed;
    updateDetailOverdue();
    checkbox.disabled = false;
    checkbox.focus();
  }
  await loadDeadlines({ showLoading: false });
}

// 絞り込みの選択肢を、カテゴリの対応表から作る（表示名を1か所で持つため）。
function renderFilter() {
  const fragment = document.createDocumentFragment();

  for (const [code, category] of FILTER_CATEGORIES) {
    const item = document.createElement("div");
    item.className = "form-check form-check-inline me-0";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "form-check-input";
    checkbox.id = `calendar-filter-${code}`;
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        hiddenCategories.delete(code);
      } else {
        hiddenCategories.add(code);
      }
      // fetchEvents・fetchDeadlines が、今の絞り込みで選び直すように、
      // 取得し直す。
      calendar.refetchEvents();
    });

    const label = document.createElement("label");
    label.className = "form-check-label";
    label.htmlFor = checkbox.id;
    const swatch = document.createElement("span");
    swatch.className = `category-swatch ${category.className} me-1`;
    swatch.setAttribute("aria-hidden", "true");
    label.append(swatch, category.label);

    item.append(checkbox, label);
    fragment.append(item);
  }

  getElement("calendar-filter").replaceChildren(fragment);
}

export function initCalendar() {
  // FullCalendarは、base.html の通常のスクリプトで、このファイルより先に
  // 読み込まれる。読み込めなかった場合（ネットワークにつながらないなど）は、
  // ほかのモードを止めないように、例外にせず、メッセージだけを出す
  // （「直近の締切」欄も出さない）。
  if (window.FullCalendar === undefined) {
    getElement("calendar-load-error-message").textContent =
      LIBRARY_ERROR_MESSAGE;
    setVisible(getElement("calendar-retry-button"), false);
    setVisible(getElement("calendar-load-error"), true);
    setVisible(getElement("calendar-content"), false);
    return;
  }

  renderFilter();
  calendar = new window.FullCalendar.Calendar(getElement("calendar-view"), {
    locale: "ja",
    // 日曜始まり
    firstDay: 0,
    initialView: WEEK_VIEW,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: `${WEEK_VIEW},${MONTH_VIEW},${LIST_VIEW}`,
    },
    // 表示の切り替えのボタン。表示と同じ名前の独自のボタンにして、切り替えを
    // switchView に通す（一覧表示では、締切を出さないため）。FullCalendarは、
    // 同じ名前の独自のボタンを、表示のボタンの代わりに置き、今の表示の
    // ボタンを、押された状態（fc-button-active・aria-pressed）にする。
    customButtons: {
      [WEEK_VIEW]: {
        text: "週",
        hint: "週表示",
        click: () => switchView(WEEK_VIEW),
      },
      [MONTH_VIEW]: {
        text: "月",
        hint: "月表示",
        click: () => switchView(MONTH_VIEW),
      },
      [LIST_VIEW]: {
        text: "一覧",
        hint: "一覧表示",
        click: () => switchView(LIST_VIEW),
      },
    },
    // 日本語の文言のファイルは読み込まず、使う文言を、ここで指定する。
    buttonText: { today: "今日" },
    buttonHints: { prev: "前へ", next: "次へ", today: "今日を表示" },
    navLinkHint: "$0を含む週を表示",
    moreLinkText: (count) => `＋${count}件`,
    moreLinkHint: (count) => `ほかに${count}件の予定（週の表示へ）`,
    noEventsText: "表示する予定はありません",
    timeHint: "時間",
    eventHint: "予定",
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    // 予定は、色のブロックで表示する（締切は、toDeadlineEvent で、●の印に
    // する）。この設定は、表示ごと（views）には指定できず、週表示と一覧表示の
    // 見た目は変わらない。
    eventDisplay: "block",
    // 同じ日の予定の並び。FullCalendarの既定の並び（開始・長さ・終日）に、
    // 締切日時（締切だけが持つ）を足す。月表示では、締切（終日）が、
    // その日の時間型の予定より上に、締切日時の順に並ぶ。
    eventOrder: "start,-duration,allDay,dueDateTime,title",
    // 週表示：終日の行を、締切の行（「締切」）にする（予定は、すべて時刻を
    // 持つため、終日の行には締切だけが入る）。時間軸は0〜24時の全体にし
    // （範囲の外の予定が消えないように）、8時から見せる。
    allDayText: "締切",
    scrollTime: "08:00:00",
    views: {
      [MONTH_VIEW]: {
        // 時間型の予定は、時刻を出さず、タイトルだけを表示する。
        displayEventTime: false,
        // 1日3件まで（締切を含む）。4件目以降は「＋N件」にまとめる。
        dayMaxEvents: 3,
        // 日付と「＋N件」のクリックで、その日を含む週の週表示へ移る。
        navLinks: true,
        navLinkDayClick: WEEK_VIEW,
        moreLinkClick: WEEK_VIEW,
      },
      [LIST_VIEW]: {
        type: "list",
        // 日数（days）で指定する。週（weeks）で指定すると、日曜日に
        // そろってしまうため。日数なら、表示中の日付（初めは今日）から始まる。
        duration: { days: LIST_DAYS },
        // 日付の見出しに、曜日を付ける（例：2026年10月13日(火)）。
        listDayFormat: {
          year: "numeric",
          month: "long",
          day: "numeric",
          weekday: "short",
        },
        eventContent: renderListEventContent,
      },
    },
    eventSources: [
      { id: "events", events: fetchEvents },
      { id: DEADLINE_SOURCE_ID, events: fetchDeadlines },
    ],
    // 予定の取得の失敗（ApiError）は、fetchEvents が画面に出すため、ここでは
    // 出さない（FullCalendarの既定の、コンソールへの警告も出さない）。取得の
    // あとの処理（絞り込み・形の変換）の例外など、ApiError でない例外は、
    // ここで画面に出す（errorMessageOf が、固定のメッセージにし、詳細を
    // console.error に出す。013-L1）。
    eventSourceFailure: (error) => {
      if (!(error instanceof ApiError)) {
        showLoadError(error);
      }
    },
    loading: (isLoading) => {
      setVisible(getElement("calendar-loading"), isLoading);
    },
    eventClick: (info) => {
      const { apiEvent, apiTask } = info.event.extendedProps;
      if (apiTask !== undefined) {
        showTaskDetail(apiTask);
        return;
      }
      showEventDetail(apiEvent);
    },
  });

  getElement("calendar-retry-button").addEventListener("click", () => {
    calendar.refetchEvents();
  });
  getElement("calendar-deadline-retry-button").addEventListener(
    "click",
    () => {
      loadDeadlines();
    },
  );
  getElement("calendar-tab").addEventListener("shown.bs.tab", () => {
    // ほかのモードでの登録（授業・休講日・課題など）を反映するため、カレンダー
    // のモードを開くたびに、予定と課題・タスクを取得し直す。隠れている間に
    // 画面の幅が変わった場合に備えて、大きさも計算し直す。前の完了の切り替えの
    // エラーは消す。
    calendar.updateSize();
    calendar.refetchEvents();
    hideDeadlineActionError();
    loadDeadlines();
  });
  getElement("task-detail-modal").addEventListener(
    "show.bs.modal",
    prepareTaskDetail,
  );
  getElement("task-detail-completed").addEventListener(
    "change",
    toggleDetailCompleted,
  );
  calendar.render();
  // カレンダーのモードは、ページを開いたときに表示されているため、ここで
  // 課題・タスクを取得する（タブの shown.bs.tab は、最初は起きない）。
  loadDeadlines();
}
