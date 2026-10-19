import { ApiError, apiRequest } from "./api.js";
import { eventCategoryOf } from "./categories.js";
import { formatJapaneseDateWithWeekday } from "./dates.js";
import {
  SUBJECTS_LOADING_NOTE,
  currentSubjectsNote,
  fetchCurrentSubjects,
  renderSubjectOptions,
} from "./subject_options.js";
import {
  clearFormErrors,
  errorMessageOf,
  getElement,
  hideModal,
  setSubmitting,
  setVisible,
  showApiError,
  trackModalShowing,
} from "./ui.js";

// カレンダーモードの中の部品：予定の追加（その他（締切のみ）を含む）・
// 編集・削除の確認のモーダル。calendar.js だけが import する（calendar.js
// が大きくなりすぎないように、分けた）。登録・編集・削除ができたら、
// initEventForms で受け取った関数で、カレンダーに取得し直させる。

// 予定のカテゴリの保存値（categories.js の EVENT_CATEGORIES のキー）。
// その他（締切のみ）は、課題・タスクのその他として登録する（保存値は、
// 予定のその他と同じ "other"）。
const CLASS = "class";
const PART_TIME = "part_time";
const OTHER = "other";
// 追加フォームのカテゴリの初期値（カレンダーから追加する予定で、最も多い
// と考えられるため。授業の予定は、授業の登録で作られる）。
const DEFAULT_CATEGORY = PART_TIME;
// 追加フォームのカテゴリのラジオボタンの id（保存値 → id）。
const CATEGORY_RADIO_IDS = {
  [CLASS]: "event-add-category-class",
  [PART_TIME]: "event-add-category-part-time",
  [OTHER]: "event-add-category-other",
};
// 時刻のないクリック（月表示の日付）の、開始・終了時刻の初期値と、
// 締切時刻の初期値（課題と同じ）。
const DEFAULT_START_TIME = "09:00";
const DEFAULT_END_TIME = "10:00";
const DEFAULT_DUE_TIME = "23:59";
// 1日の最後の時刻。日付をまたぐ予定は、1件では登録できないため、終了時刻を
// 1時間後に合わせるときも、これより後にしない。
const LAST_TIME = "23:59";

const ADD_FIELDS = {
  subject_id: {
    inputIds: ["event-add-subject"],
    messageId: "event-add-subject-error",
  },
  title: {
    inputIds: ["event-add-title"],
    messageId: "event-add-title-error",
  },
  employer: {
    inputIds: ["event-add-employer"],
    messageId: "event-add-employer-error",
  },
  date: {
    inputIds: ["event-add-date"],
    messageId: "event-add-date-error",
  },
  start_time: {
    inputIds: ["event-add-start-time"],
    messageId: "event-add-start-time-error",
  },
  end_time: {
    inputIds: ["event-add-end-time"],
    messageId: "event-add-end-time-error",
  },
  due_datetime: {
    inputIds: ["event-add-due-date", "event-add-due-time"],
    messageId: "event-add-due-error",
  },
  room: {
    inputIds: ["event-add-room"],
    messageId: "event-add-room-error",
  },
  notes: {
    inputIds: ["event-add-notes"],
    messageId: "event-add-notes-error",
  },
};
const ADD_FORM_ERROR_ID = "event-add-form-error";
const ADD_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
const EDIT_FIELDS = {
  title: {
    inputIds: ["event-edit-title"],
    messageId: "event-edit-title-error",
  },
  employer: {
    inputIds: ["event-edit-employer"],
    messageId: "event-edit-employer-error",
  },
  date: {
    inputIds: ["event-edit-date"],
    messageId: "event-edit-date-error",
  },
  start_time: {
    inputIds: ["event-edit-start-time"],
    messageId: "event-edit-start-time-error",
  },
  end_time: {
    inputIds: ["event-edit-end-time"],
    messageId: "event-edit-end-time-error",
  },
  room: {
    inputIds: ["event-edit-room"],
    messageId: "event-edit-room-error",
  },
  notes: {
    inputIds: ["event-edit-notes"],
    messageId: "event-edit-notes-error",
  },
};
const EDIT_FORM_ERROR_ID = "event-edit-form-error";
const EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};
const GENERATED_DELETE_NOTE =
  "授業の登録で作られた予定です。" +
  "授業全体を編集すると、今日以降の分は、作り直されます。";

// 登録・編集・削除ができたときに呼ぶ関数（initEventForms で受け取る）。
let notifyEventsChanged = () => {};
let notifyTasksChanged = () => {};
// 追加フォームを開くときに入れる値（openEventAddModal と「同じ内容で別の
// 日も登録」で控える）。入れるのは、モーダルを開くとき（show.bs.modal）。
let addValues = null;
// 追加・編集のフォームで、最初にフォーカスを置く欄の id。
let addFocusId = "";
let editFocusId = "";
// 追加フォームの授業の選択肢（今の学期の授業。教室の初期値に使う）。
let addSubjects = [];
// 最後に登録したアルバイト（「同じ内容で別の日も登録」で使う）。
let lastPartTimeEvent = null;
// 編集・削除の対象（予定のコピー）。
let editingEvent = null;
let deletingEvent = null;
// 追加・編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直した
// あとに届いた古い応答で、今のモーダルの表示を変えないために使う。
let addSerial = 0;
let editSerial = 0;
let deleteSerial = 0;
// 派遣会社の候補の取得の通し番号（古い応答で、候補を上書きしないため）。
let employerSerial = 0;

// 予定を表す文字列（例：「倉庫の仕分け」（2026年10月24日（土） 17:00 〜
// 21:00））。登録の知らせと、削除の確認の文に使う。
function eventLabel(apiEvent) {
  return (
    `「${apiEvent.title}」` +
    `（${formatJapaneseDateWithWeekday(apiEvent.date)} ` +
    `${apiEvent.start_time} 〜 ${apiEvent.end_time}）`
  );
}

// 時刻（HH:MM）の1時間後。23時台は、日付をまたがないように LAST_TIME。
function oneHourLater(time) {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours >= 23) {
    return LAST_TIME;
  }
  return (
    `${String(hours + 1).padStart(2, "0")}:` +
    `${String(minutes).padStart(2, "0")}`
  );
}

// 開始時刻を変えて、終了時刻が開始時刻以下になったときは、終了時刻を、
// 開始時刻の1時間後に合わせる（授業の登録と同じ。追加・編集のフォームで
// 使う）。HH:MMは桁が固定されているため、文字列の大小で時刻を比べられる。
function adjustEndTime(startInputId, endInputId) {
  const startInput = getElement(startInputId);
  const endInput = getElement(endInputId);
  if (startInput.value === "" || endInput.value > startInput.value) {
    return;
  }
  endInput.value = oneHourLater(startInput.value);
}

// 欄（rowId）を表示・非表示にし、中の入力欄を、表示するときだけ使える
// ようにする（隠した欄の入力チェック（必須）で、送信が止まらないように、
// 隠した入力欄は無効にする）。
function setFieldRowVisible(rowId, inputIds, visible) {
  setVisible(getElement(rowId), visible);
  for (const inputId of inputIds) {
    getElement(inputId).disabled = !visible;
  }
}

// モーダル（modalId）を、JavaScriptから開く。
function showModal(modalId) {
  window.bootstrap.Modal.getOrCreateInstance(getElement(modalId)).show();
}

// 派遣会社の入力候補（datalist）を、予定APIの派遣会社の候補（新しく
// 使った順）で作り直す。候補は入力の補助のため、取得に失敗しても、何も
// 表示しない（候補なしで入力できる。それまでの候補は残る）。
async function loadEmployerOptions() {
  const currentRequest = ++employerSerial;
  let employers;
  try {
    employers = await apiRequest("GET", "/api/events/employers");
  } catch (error) {
    // ApiError でない例外（プログラムの誤りなど）は、console.error に出す。
    if (!(error instanceof ApiError)) {
      console.error(error);
    }
    return;
  }

  if (currentRequest !== employerSerial) {
    return;
  }
  const options = employers.map((employer) => {
    const option = document.createElement("option");
    option.value = employer;
    return option;
  });
  getElement("event-employer-options").replaceChildren(...options);
}

// 追加フォームで選んでいるカテゴリ（保存値）。
function selectedAddCategory() {
  for (const [category, radioId] of Object.entries(CATEGORY_RADIO_IDS)) {
    if (getElement(radioId).checked) {
      return category;
    }
  }
  return DEFAULT_CATEGORY;
}

// 追加フォームが、その他の「締切のみ」か。
function isDeadlineOnly() {
  return (
    selectedAddCategory() === OTHER &&
    getElement("event-add-other-type-deadline").checked
  );
}

// 追加フォームの欄を、選んでいるカテゴリに合わせる（入力した値は残す）。
function applyAddCategory() {
  const category = selectedAddCategory();
  const timed = !isDeadlineOnly();
  setVisible(getElement("event-add-other-type-row"), category === OTHER);
  setFieldRowVisible(
    "event-add-subject-row",
    ["event-add-subject"],
    category === CLASS,
  );
  setFieldRowVisible(
    "event-add-title-row",
    ["event-add-title"],
    category !== CLASS,
  );
  setFieldRowVisible(
    "event-add-employer-row",
    ["event-add-employer"],
    category === PART_TIME,
  );
  setFieldRowVisible("event-add-date-row", ["event-add-date"], timed);
  setFieldRowVisible(
    "event-add-time-row",
    ["event-add-start-time", "event-add-end-time"],
    timed,
  );
  setFieldRowVisible(
    "event-add-due-row",
    ["event-add-due-date", "event-add-due-time"],
    !timed,
  );
  setFieldRowVisible(
    "event-add-room-row",
    ["event-add-room"],
    category === CLASS,
  );
  getElement("event-add-title-label").textContent =
    category === PART_TIME ? "仕事内容" : "タイトル";
}

// 追加フォームを開く（カレンダーの空き枠のクリック）。date は
// 「YYYY-MM-DD」。time は、クリックした時刻（「HH:MM」。時刻のない
// クリックは null）。deadlineOnly が true なら、その他の「締切のみ」を
// 選んだ状態で開く（週表示の「締切」の行のクリック）。
export function openEventAddModal({ date, time = null, deadlineOnly = false }) {
  addValues = {
    category: deadlineOnly ? OTHER : DEFAULT_CATEGORY,
    deadlineOnly,
    date,
    startTime: time ?? DEFAULT_START_TIME,
    endTime: time === null ? DEFAULT_END_TIME : oneHourLater(time),
    dueDate: date,
    dueTime: time ?? DEFAULT_DUE_TIME,
    title: "",
    employer: "",
    notes: "",
    // 最初のフォーカスは、カテゴリで決める（null）。
    focusId: null,
  };
  showModal("event-add-modal");
}

// 「同じ内容で別の日も登録」。最後に登録したアルバイトの、日付以外を
// 入れた追加フォームを開く（日付は空。最初のフォーカスは、日付の欄）。
function openRepeatAddModal() {
  const source = lastPartTimeEvent;
  addValues = {
    category: PART_TIME,
    deadlineOnly: false,
    date: "",
    startTime: source.start_time,
    endTime: source.end_time,
    dueDate: "",
    dueTime: DEFAULT_DUE_TIME,
    title: source.title,
    employer: source.employer ?? "",
    notes: source.notes ?? "",
    focusId: "event-add-date",
  };
  showModal("event-add-modal");
}

// カレンダーの上の、アルバイトを登録したことの知らせ（「同じ内容で別の日も
// 登録」のボタンつき）。
function showAddedNotice(createdEvent) {
  lastPartTimeEvent = { ...createdEvent };
  getElement("event-added-notice-message").textContent =
    `${eventLabel(createdEvent)}を登録しました。`;
  setVisible(getElement("event-added-notice"), true);
}

function hideAddedNotice() {
  setVisible(getElement("event-added-notice"), false);
}

// 追加フォームの授業の選択肢（今の学期の授業）を取得する。currentSerial
// は、取得を始めたときの追加のモーダルの通し番号。
async function loadAddSubjects(currentSerial) {
  const select = getElement("event-add-subject");
  const note = getElement("event-add-subject-note");
  addSubjects = [];
  // 授業を取得するまでは、「選択してください」だけ（必須のため、ブラウザの
  // 入力チェックで、授業の登録は止まる）。
  renderSubjectOptions(select, []);
  note.textContent = SUBJECTS_LOADING_NOTE;

  let result;
  try {
    result = await fetchCurrentSubjects();
  } catch (error) {
    // モーダルを開き直していたら、今のモーダルの表示を変えない。
    if (currentSerial !== addSerial) {
      return;
    }
    // 授業の欄の下に出す（ほかのカテゴリは、登録できる）。
    note.textContent = errorMessageOf(error);
    return;
  }

  if (currentSerial !== addSerial) {
    return;
  }
  addSubjects = result.subjects;
  renderSubjectOptions(select, result.subjects);
  note.textContent = currentSubjectsNote(result.semester, result.subjects);
}

// 授業を選んだら、その授業の教室を、教室の欄に入れる（選び直すたびに
// 入れ直す。教室のない授業と、「選択してください」は、空にする）。
function fillRoomFromSubject() {
  const subjectId = Number(getElement("event-add-subject").value);
  const subject = addSubjects.find((item) => item.id === subjectId);
  getElement("event-add-room").value = subject?.room ?? "";
}

// 追加のモーダルを開くたびに、入力欄に、控えた値を入れ、エラーの表示と、
// アルバイトを登録したことの知らせを消す。授業の選択肢と、派遣会社の
// 候補を取得する。
function prepareAddModal() {
  const currentSerial = ++addSerial;
  const values = addValues;

  hideAddedNotice();
  getElement("event-add-form").reset();
  getElement(CATEGORY_RADIO_IDS[values.category]).checked = true;
  getElement(
    values.deadlineOnly
      ? "event-add-other-type-deadline"
      : "event-add-other-type-timed",
  ).checked = true;
  getElement("event-add-title").value = values.title;
  getElement("event-add-employer").value = values.employer;
  getElement("event-add-date").value = values.date;
  getElement("event-add-start-time").value = values.startTime;
  getElement("event-add-end-time").value = values.endTime;
  getElement("event-add-due-date").value = values.dueDate;
  getElement("event-add-due-time").value = values.dueTime;
  getElement("event-add-room").value = "";
  getElement("event-add-notes").value = values.notes;
  clearFormErrors(ADD_FIELDS, ADD_FORM_ERROR_ID);
  setSubmitting(
    getElement("event-add-submit-button"),
    false,
    ADD_SUBMIT_LABELS,
  );
  applyAddCategory();
  if (values.focusId !== null) {
    addFocusId = values.focusId;
  } else {
    addFocusId =
      values.category === CLASS ? "event-add-subject" : "event-add-title";
  }

  loadAddSubjects(currentSerial);
  loadEmployerOptions();
}

// 追加フォームの値から、登録の要求（URLと本文）を作る。
function addRequestOf() {
  const category = selectedAddCategory();
  const notes = getElement("event-add-notes").value;
  if (isDeadlineOnly()) {
    // 締切のみは、課題・タスクのAPIで、その他として登録する。
    const dueDate = getElement("event-add-due-date").value;
    const dueTime = getElement("event-add-due-time").value;
    return {
      url: "/api/tasks",
      body: {
        category: OTHER,
        title: getElement("event-add-title").value,
        due_datetime: `${dueDate}T${dueTime}`,
        notes,
      },
    };
  }

  const body = {
    category,
    date: getElement("event-add-date").value,
    start_time: getElement("event-add-start-time").value,
    end_time: getElement("event-add-end-time").value,
    notes,
  };
  if (category === CLASS) {
    // 授業の予定のタイトルは、送らない（授業の科目名になる）。
    body.subject_id = Number(getElement("event-add-subject").value);
    body.room = getElement("event-add-room").value;
  } else {
    body.title = getElement("event-add-title").value;
  }
  if (category === PART_TIME) {
    body.employer = getElement("event-add-employer").value;
  }
  return { url: "/api/events", body };
}

async function submitEventAdd(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = addSerial;
  const deadlineOnly = isDeadlineOnly();
  const { url, body } = addRequestOf();
  clearFormErrors(ADD_FIELDS, ADD_FORM_ERROR_ID);

  const submitButton = getElement("event-add-submit-button");
  setSubmitting(submitButton, true, ADD_SUBMIT_LABELS);

  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
  // 「登録の失敗」として表示しないため）。
  let created;
  try {
    created = await apiRequest("POST", url, body);
  } catch (error) {
    if (startedSerial !== addSerial) {
      return;
    }
    showApiError(error, ADD_FIELDS, ADD_FORM_ERROR_ID);
    setSubmitting(submitButton, false, ADD_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === addSerial) {
    hideModal(getElement("event-add-modal"));
    if (!deadlineOnly && created.category === PART_TIME) {
      showAddedNotice(created);
    }
  }
  if (deadlineOnly) {
    notifyTasksChanged();
    return;
  }
  notifyEventsChanged();
}

// 日付を変えられない予定か（自動生成の授業の予定。「カレンダーからの
// 授業の予定の操作」）。自動生成の予定は、授業の予定だけ。
function hasFixedDate(apiEvent) {
  return apiEvent.is_generated;
}

// 編集のモーダルを開く（予定の詳細パネルの「編集」）。入力欄は、モーダルを
// 開くとき（show.bs.modal）に入れる。
export function openEventEditModal(apiEvent) {
  editingEvent = { ...apiEvent };
  showModal("event-edit-modal");
}

// 編集のモーダルを開くたびに、対象の今の値を入力欄に入れ、エラーの表示を
// 消す。カテゴリと、授業の予定の授業は、表示だけ（変えられない）。
function prepareEditModal() {
  editSerial += 1;
  const target = editingEvent;
  const category = eventCategoryOf(target.category);
  const isClass = target.category === CLASS;
  const fixedDate = hasFixedDate(target);

  getElement("event-edit-form").reset();
  getElement("event-edit-category-icon").textContent = category.icon;
  getElement("event-edit-category").textContent = category.label;
  // 授業の予定のタイトルは、追加・作成したときの授業の科目名の控え。
  getElement("event-edit-subject").textContent = target.title;
  setVisible(getElement("event-edit-subject-row"), isClass);
  setFieldRowVisible("event-edit-title-row", ["event-edit-title"], !isClass);
  getElement("event-edit-title-label").textContent =
    target.category === PART_TIME ? "仕事内容" : "タイトル";
  setFieldRowVisible(
    "event-edit-employer-row",
    ["event-edit-employer"],
    target.category === PART_TIME,
  );
  setFieldRowVisible("event-edit-date-row", ["event-edit-date"], !fixedDate);
  setVisible(getElement("event-edit-fixed-date-row"), fixedDate);
  setFieldRowVisible("event-edit-room-row", ["event-edit-room"], isClass);

  getElement("event-edit-title").value = isClass ? "" : target.title;
  getElement("event-edit-employer").value = target.employer ?? "";
  getElement("event-edit-date").value = target.date;
  getElement("event-edit-fixed-date").textContent =
    formatJapaneseDateWithWeekday(target.date);
  getElement("event-edit-start-time").value = target.start_time;
  getElement("event-edit-end-time").value = target.end_time;
  getElement("event-edit-room").value = target.room ?? "";
  getElement("event-edit-notes").value = target.notes ?? "";
  clearFormErrors(EDIT_FIELDS, EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("event-edit-submit-button"),
    false,
    EDIT_SUBMIT_LABELS,
  );
  editFocusId = isClass ? "event-edit-start-time" : "event-edit-title";

  if (target.category === PART_TIME) {
    loadEmployerOptions();
  }
}

// 編集の本文。変えられる項目を、すべて送る（変えていない項目も、今の値の
// まま送る）。変えられない項目（カテゴリ・授業・授業の予定のタイトル・
// 自動生成の予定の日付）は、送らない。
function editRequestBodyOf(target) {
  const body = {
    start_time: getElement("event-edit-start-time").value,
    end_time: getElement("event-edit-end-time").value,
    notes: getElement("event-edit-notes").value,
  };
  if (!hasFixedDate(target)) {
    body.date = getElement("event-edit-date").value;
  }
  if (target.category === CLASS) {
    body.room = getElement("event-edit-room").value;
  } else {
    body.title = getElement("event-edit-title").value;
  }
  if (target.category === PART_TIME) {
    body.employer = getElement("event-edit-employer").value;
  }
  return body;
}

async function submitEventEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const target = editingEvent;
  const body = editRequestBodyOf(target);
  clearFormErrors(EDIT_FIELDS, EDIT_FORM_ERROR_ID);

  const submitButton = getElement("event-edit-submit-button");
  setSubmitting(submitButton, true, EDIT_SUBMIT_LABELS);

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("PATCH", `/api/events/${target.id}`, body);
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, EDIT_FIELDS, EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("event-edit-modal"));
  }
  notifyEventsChanged();
}

// 削除の確認のモーダルを開く（予定の詳細パネルの「削除」）。
export function openEventDeleteModal(apiEvent) {
  deletingEvent = { ...apiEvent };
  showModal("event-delete-modal");
}

function showDeleteError(error) {
  const deleteError = getElement("event-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("event-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、対象を表示し、エラーを消す。自動生成の
// 授業の予定には、作り直されることの注意を添える（それ以外は、注意の
// 文字を空にする。読み上げの説明（aria-describedby）に入らないように）。
function prepareDeleteModal() {
  deleteSerial += 1;
  const generated = deletingEvent.is_generated;
  getElement("event-delete-target").textContent =
    `${eventLabel(deletingEvent)}を削除します。`;
  const note = getElement("event-delete-generated-note");
  note.textContent = generated ? GENERATED_DELETE_NOTE : "";
  setVisible(note, generated);
  hideDeleteError();
  setSubmitting(
    getElement("event-delete-submit-button"),
    false,
    DELETE_SUBMIT_LABELS,
  );
}

async function submitEventDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const eventId = deletingEvent.id;
  hideDeleteError();

  const submitButton = getElement("event-delete-submit-button");
  setSubmitting(submitButton, true, DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/events/${eventId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("event-delete-modal"));
  }
  notifyEventsChanged();
}

// 初期化。onEventsChanged は、予定を登録・編集・削除できたときに、
// onTasksChanged は、その他（締切のみ）を登録できたときに呼ぶ関数
// （カレンダーの予定・締切を取得し直す）。
export function initEventForms({ onEventsChanged, onTasksChanged }) {
  notifyEventsChanged = onEventsChanged;
  notifyTasksChanged = onTasksChanged;

  // 追加・編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const addModal = getElement("event-add-modal");
  trackModalShowing(addModal);
  addModal.addEventListener("show.bs.modal", prepareAddModal);
  addModal.addEventListener("shown.bs.modal", () => {
    getElement(addFocusId).focus();
  });
  const addRadioIds = [
    ...Object.values(CATEGORY_RADIO_IDS),
    "event-add-other-type-timed",
    "event-add-other-type-deadline",
  ];
  for (const radioId of addRadioIds) {
    getElement(radioId).addEventListener("change", applyAddCategory);
  }
  getElement("event-add-subject").addEventListener(
    "change",
    fillRoomFromSubject,
  );
  getElement("event-add-start-time").addEventListener("change", () => {
    adjustEndTime("event-add-start-time", "event-add-end-time");
  });
  getElement("event-add-form").addEventListener("submit", submitEventAdd);

  // アルバイトを登録したことの知らせ。カレンダーのモードを開き直したときも
  // 消す。
  getElement("event-repeat-button").addEventListener(
    "click",
    openRepeatAddModal,
  );
  getElement("event-added-notice-close-button").addEventListener(
    "click",
    hideAddedNotice,
  );
  getElement("calendar-tab").addEventListener("shown.bs.tab", hideAddedNotice);

  const editModal = getElement("event-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", prepareEditModal);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement(editFocusId).focus();
  });
  getElement("event-edit-start-time").addEventListener("change", () => {
    adjustEndTime("event-edit-start-time", "event-edit-end-time");
  });
  getElement("event-edit-form").addEventListener("submit", submitEventEdit);

  const deleteModal = getElement("event-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("event-delete-cancel-button").focus();
  });
  getElement("event-delete-submit-button").addEventListener(
    "click",
    submitEventDelete,
  );
}
