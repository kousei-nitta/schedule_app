import { apiRequest } from "./api.js";
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

let currentSemester = null;
let requestSerial = 0;
// 編集・削除の対象の授業（一覧の行の値のコピー）。モーダルを開くときに入れる。
let editingSubject = null;
let deletingSubject = null;
// 編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直したあとに
// 届いた古い応答で、今のモーダルの表示を変えないために使う。
let editSerial = 0;
let deleteSerial = 0;

const WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"];
const SUBJECT_FIELDS = {
  semester_id: {
    inputIds: [],
    messageId: "subject-semester-error",
  },
  subject_name: {
    inputIds: ["subject-name"],
    messageId: "subject-name-error",
  },
  room: {
    inputIds: ["subject-room"],
    messageId: "subject-room-error",
  },
  weekday: {
    inputIds: ["subject-weekday"],
    messageId: "subject-weekday-error",
  },
  start_time: {
    inputIds: ["subject-start-time"],
    messageId: "subject-start-time-error",
  },
  end_time: {
    inputIds: ["subject-end-time"],
    messageId: "subject-end-time-error",
  },
  notes: {
    inputIds: ["subject-notes"],
    messageId: "subject-notes-error",
  },
};
const SUBJECT_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
// 編集フォームの項目。学期（semester_id）は、編集では送らない。
const SUBJECT_EDIT_FIELDS = {
  subject_name: {
    inputIds: ["subject-edit-name"],
    messageId: "subject-edit-name-error",
  },
  room: {
    inputIds: ["subject-edit-room"],
    messageId: "subject-edit-room-error",
  },
  weekday: {
    inputIds: ["subject-edit-weekday"],
    messageId: "subject-edit-weekday-error",
  },
  start_time: {
    inputIds: ["subject-edit-start-time"],
    messageId: "subject-edit-start-time-error",
  },
  end_time: {
    inputIds: ["subject-edit-end-time"],
    messageId: "subject-edit-end-time-error",
  },
  notes: {
    inputIds: ["subject-edit-notes"],
    messageId: "subject-edit-notes-error",
  },
};
const SUBJECT_EDIT_FORM_ERROR_ID = "subject-edit-form-error";
const SUBJECT_EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const SUBJECT_DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};

// 授業を表す文字列（例：「プログラミング基礎」（月 09:00 〜 10:00））。
// 同じ科目名の授業（週2回の授業など）を区別できるように、曜日と時刻を含める。
function subjectLabel(subject) {
  return (
    `「${subject.subject_name}」` +
    `（${WEEKDAYS[subject.weekday]} ` +
    `${subject.start_time} 〜 ${subject.end_time}）`
  );
}

function resetSubjectForm({ clearSuccess = true } = {}) {
  getElement("subject-form").reset();
  getElement("subject-name").value = "";
  getElement("subject-room").value = "";
  getElement("subject-weekday").value = "0";
  getElement("subject-start-time").value = "09:00";
  getElement("subject-end-time").value = "10:00";
  getElement("subject-notes").value = "";
  getElement("subject-modal-semester").textContent = currentSemester.name;
  clearFormErrors(SUBJECT_FIELDS, "subject-form-error");
  if (clearSuccess) {
    const success = getElement("subject-form-success");
    success.replaceChildren();
    setVisible(success, false);
  }
  setSubmitting(
    getElement("subject-submit-button"),
    false,
    SUBJECT_SUBMIT_LABELS,
  );
}

// 開始時刻を変えて、終了時刻が開始時刻以下になったときは、終了時刻を、
// 開始時刻の1時間後に合わせる（登録・編集のフォームで使う）。
function adjustEndTime(startSelect, endSelect) {
  // HH:MMは桁が固定されているため、文字列の大小で時刻を比較できる。
  if (endSelect.value > startSelect.value) {
    return;
  }
  const nextHour = String(Number(startSelect.value.slice(0, 2)) + 1).padStart(
    2,
    "0",
  );
  const nextTime = `${nextHour}:00`;
  // 1時間後の時刻が選択肢にない場合（編集で、選択肢に足した時刻を選んだ
  // 場合など）は、変えない（APIの入力チェックで、誤りが表示される）。
  const hasNextTime = Array.from(endSelect.options).some(
    (option) => option.value === nextTime,
  );
  if (hasNextTime) {
    endSelect.value = nextTime;
  }
}

// 編集フォームで、時刻のプルダウンに足した選択肢を取り除く。
function removeAddedTimeOptions(select) {
  for (const option of select.querySelectorAll("option[data-added-time]")) {
    option.remove();
  }
}

// 時刻のプルダウンで、time を選ぶ。選択肢にない時刻（APIで登録した授業の、
// 9〜19時・1時間刻み以外の時刻など）は、時刻の順の位置に選択肢を足して
// から選ぶ（足さないと、空欄になり、必須のエラーになるため）。
function selectTime(select, time) {
  const options = Array.from(select.options);
  if (!options.some((option) => option.value === time)) {
    const option = document.createElement("option");
    option.value = time;
    option.textContent = time;
    option.dataset.addedTime = "true";
    const nextOption = options.find((item) => item.value > time);
    select.insertBefore(option, nextOption ?? null);
  }
  select.value = time;
}

function clearSubjectList() {
  getElement("subject-table-body").replaceChildren();
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), false);
  setVisible(getElement("subject-list"), false);
}

function showSubjectLoading() {
  setVisible(getElement("subject-loading"), true);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), false);
  setVisible(getElement("subject-list"), false);
}

function showSubjectError(error) {
  getElement("subject-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), true);
  setVisible(getElement("subject-empty"), false);
  setVisible(getElement("subject-list"), false);
}

function appendNotes(cell, notes) {
  const memo = document.createElement("div");
  memo.className = "text-muted small";
  const lines = notes.split(/\r?\n/);

  lines.forEach((line, index) => {
    if (index > 0) {
      memo.append(document.createElement("br"));
    }
    memo.append(document.createTextNode(line));
  });

  cell.append(memo);
}

function renderSubjects(subjects) {
  const tableBody = getElement("subject-table-body");
  const fragment = document.createDocumentFragment();

  for (const subject of subjects) {
    const row = document.createElement("tr");

    const weekday = document.createElement("td");
    weekday.textContent = WEEKDAYS[subject.weekday];
    row.append(weekday);

    const time = document.createElement("td");
    time.textContent = `${subject.start_time} 〜 ${subject.end_time}`;
    row.append(time);

    const name = document.createElement("td");
    const subjectName = document.createElement("div");
    subjectName.textContent = subject.subject_name;
    name.append(subjectName);
    if (subject.notes !== null) {
      appendNotes(name, subject.notes);
    }
    row.append(name);

    const room = document.createElement("td");
    room.textContent = subject.room ?? "—";
    row.append(room);

    // 読み上げで、どの授業のボタンかを区別できるように、aria-label に
    // 授業を表す文字列を入れる。
    const label = subjectLabel(subject);
    const actions = document.createElement("td");
    actions.className = "text-end text-nowrap";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.id = `subject-edit-${subject.id}`;
    editButton.className = "btn btn-outline-secondary btn-sm";
    editButton.textContent = "編集";
    editButton.setAttribute("aria-label", `${label}を編集`);
    editButton.addEventListener("click", () => {
      openEditModal(subject);
    });
    actions.append(editButton);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.id = `subject-delete-${subject.id}`;
    deleteButton.className = "btn btn-outline-danger btn-sm ms-1";
    deleteButton.textContent = "削除";
    deleteButton.setAttribute("aria-label", `${label}を削除`);
    deleteButton.addEventListener("click", () => {
      openDeleteModal(subject);
    });
    actions.append(deleteButton);

    row.append(actions);
    fragment.append(row);
  }

  tableBody.replaceChildren(fragment);
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), subjects.length === 0);
  setVisible(getElement("subject-list"), subjects.length > 0);
}

async function loadSubjects({ showLoading = true } = {}) {
  if (currentSemester === null) {
    clearSubjectList();
    return;
  }

  const semesterId = currentSemester.id;
  const currentRequest = ++requestSerial;
  if (showLoading) {
    showSubjectLoading();
  }

  try {
    const subjects = await apiRequest(
      "GET",
      `/api/subjects?semester_id=${semesterId}`,
    );
    // タブ切替後に古い応答が届いても、現在の授業一覧を上書きしない。
    if (currentRequest !== requestSerial) {
      return;
    }
    renderSubjects(subjects);
  } catch (error) {
    if (currentRequest !== requestSerial) {
      return;
    }
    showSubjectError(error);
  }
}

// 登録済みのメッセージ。作成された予定の件数によって、文言を変える。
function subjectCreatedMessage(created) {
  const registered = `「${created.subject_name}」を登録しました`;
  if (created.generated_event_count === 0) {
    return (
      `${registered}（学期の期間内に、この曜日の授業日がないため、` +
      "予定は作成されませんでした）"
    );
  }
  return `${registered}（予定${created.generated_event_count}件を作成）`;
}

async function submitSubject(event) {
  event.preventDefault();
  clearFormErrors(SUBJECT_FIELDS, "subject-form-error");
  const success = getElement("subject-form-success");
  success.replaceChildren();
  setVisible(success, false);

  const submitButton = getElement("subject-submit-button");
  setSubmitting(submitButton, true, SUBJECT_SUBMIT_LABELS);

  // try で囲むのは、登録の要求だけにする。登録の成功後の処理で例外が
  // 起きた場合に、「登録の失敗」として表示しないため。
  let created;
  try {
    created = await apiRequest("POST", "/api/subjects", {
      semester_id: currentSemester.id,
      subject_name: getElement("subject-name").value,
      room: getElement("subject-room").value,
      weekday: Number(getElement("subject-weekday").value),
      start_time: getElement("subject-start-time").value,
      end_time: getElement("subject-end-time").value,
      notes: getElement("subject-notes").value,
    });
  } catch (error) {
    showApiError(error, SUBJECT_FIELDS, "subject-form-error");
    setSubmitting(submitButton, false, SUBJECT_SUBMIT_LABELS);
    return;
  }

  success.textContent = subjectCreatedMessage(created);
  setVisible(success, true);
  resetSubjectForm({ clearSuccess: false });
  getElement("subject-name").focus();
  await loadSubjects({ showLoading: false });
}

// 一覧の「編集」ボタン。対象の授業を控えて、編集のモーダルを開く
// （入力欄は、モーダルを開くとき（show.bs.modal）に入れる）。
function openEditModal(subject) {
  editingSubject = { ...subject };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("subject-edit-modal"),
  ).show();
}

// 編集のモーダルを開くたびに、対象の授業の今の値を入力欄に入れ、
// エラーの表示を消す。
function fillEditForm() {
  editSerial += 1;
  const subject = editingSubject;
  const startSelect = getElement("subject-edit-start-time");
  const endSelect = getElement("subject-edit-end-time");

  getElement("subject-edit-form").reset();
  removeAddedTimeOptions(startSelect);
  removeAddedTimeOptions(endSelect);
  getElement("subject-edit-modal-semester").textContent =
    currentSemester.name;
  getElement("subject-edit-name").value = subject.subject_name;
  getElement("subject-edit-room").value = subject.room ?? "";
  getElement("subject-edit-weekday").value = String(subject.weekday);
  selectTime(startSelect, subject.start_time);
  selectTime(endSelect, subject.end_time);
  getElement("subject-edit-notes").value = subject.notes ?? "";
  clearFormErrors(SUBJECT_EDIT_FIELDS, SUBJECT_EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("subject-edit-submit-button"),
    false,
    SUBJECT_EDIT_SUBMIT_LABELS,
  );
}

async function submitSubjectEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const subjectId = editingSubject.id;
  clearFormErrors(SUBJECT_EDIT_FIELDS, SUBJECT_EDIT_FORM_ERROR_ID);

  const submitButton = getElement("subject-edit-submit-button");
  setSubmitting(submitButton, true, SUBJECT_EDIT_SUBMIT_LABELS);

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  // すべての項目を送る（変えていない項目も、今の値のまま送る）。
  try {
    await apiRequest("PATCH", `/api/subjects/${subjectId}`, {
      subject_name: getElement("subject-edit-name").value,
      room: getElement("subject-edit-room").value,
      weekday: Number(getElement("subject-edit-weekday").value),
      start_time: getElement("subject-edit-start-time").value,
      end_time: getElement("subject-edit-end-time").value,
      notes: getElement("subject-edit-notes").value,
    });
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, SUBJECT_EDIT_FIELDS, SUBJECT_EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SUBJECT_EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("subject-edit-modal"));
  }
  await loadSubjects({ showLoading: false });
}

// 一覧の「削除」ボタン。対象の授業を控えて、削除の確認のモーダルを開く
// （件数は、モーダルを開くとき（show.bs.modal）に取得する）。
function openDeleteModal(subject) {
  deletingSubject = { ...subject };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("subject-delete-modal"),
  ).show();
}

function showDeleteError(error) {
  const deleteError = getElement("subject-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("subject-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、対象の授業を表示し、削除される予定と
// 課題の件数を、授業の1件取得（event_count・task_count）で取得する。
// 件数が表示されるまで、「削除する」ボタンは押せない。
async function prepareDeleteModal() {
  const currentSerial = ++deleteSerial;
  const subject = deletingSubject;
  const loading = getElement("subject-delete-loading");
  const counts = getElement("subject-delete-counts");
  const submitButton = getElement("subject-delete-submit-button");

  getElement("subject-delete-target").textContent =
    `${subjectLabel(subject)}を削除します。`;
  counts.replaceChildren();
  setVisible(counts, false);
  setVisible(loading, true);
  hideDeleteError();
  submitButton.textContent = SUBJECT_DELETE_SUBMIT_LABELS.idle;
  submitButton.disabled = true;

  let detail;
  try {
    detail = await apiRequest("GET", `/api/subjects/${subject.id}`);
  } catch (error) {
    // モーダルを開き直していたら、今のモーダルの表示を変えない。
    if (currentSerial !== deleteSerial) {
      return;
    }
    setVisible(loading, false);
    // 件数を取得できなかったときは、「削除する」ボタンを押せないままにする。
    showDeleteError(error);
    return;
  }

  if (currentSerial !== deleteSerial) {
    return;
  }
  setVisible(loading, false);
  counts.textContent =
    `この授業の予定${detail.event_count}件（今日より前の分を含む）と、` +
    `課題${detail.task_count}件も、まとめて削除されます。`;
  setVisible(counts, true);
  submitButton.disabled = false;
}

async function submitSubjectDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const subjectId = deletingSubject.id;
  hideDeleteError();

  const submitButton = getElement("subject-delete-submit-button");
  setSubmitting(submitButton, true, SUBJECT_DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/subjects/${subjectId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, SUBJECT_DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("subject-delete-modal"));
  }
  await loadSubjects({ showLoading: false });
}

export function initSubjects() {
  document.addEventListener("semester-selected", (event) => {
    currentSemester = event.detail.semester;
    requestSerial += 1;
    if (currentSemester === null) {
      clearSubjectList();
      return;
    }
    loadSubjects();
  });

  getElement("subject-retry-button").addEventListener("click", () => {
    loadSubjects();
  });
  getElement("subject-modal").addEventListener("show.bs.modal", () => {
    resetSubjectForm();
  });
  getElement("subject-modal").addEventListener("shown.bs.modal", () => {
    getElement("subject-name").focus();
  });
  getElement("subject-start-time").addEventListener("change", () => {
    adjustEndTime(
      getElement("subject-start-time"),
      getElement("subject-end-time"),
    );
  });
  getElement("subject-form").addEventListener("submit", submitSubject);

  // 編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const editModal = getElement("subject-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", fillEditForm);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement("subject-edit-name").focus();
  });
  getElement("subject-edit-start-time").addEventListener("change", () => {
    adjustEndTime(
      getElement("subject-edit-start-time"),
      getElement("subject-edit-end-time"),
    );
  });
  getElement("subject-edit-form").addEventListener("submit", submitSubjectEdit);

  const deleteModal = getElement("subject-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("subject-delete-cancel-button").focus();
  });
  getElement("subject-delete-submit-button").addEventListener(
    "click",
    submitSubjectDelete,
  );
}
