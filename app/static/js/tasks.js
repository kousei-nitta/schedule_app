import { apiRequest } from "./api.js";
import { taskCategoryOf } from "./categories.js";
import { chooseCurrentSemester } from "./current_semester.js";
import {
  formatJapaneseDateTime,
  localDateString,
  localDateTimeString,
} from "./dates.js";
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

// 課題のカテゴリの保存値（categories.js の TASK_CATEGORIES のキー）。
// このモードで追加できるのは、課題だけ。
const ASSIGNMENT = "assignment";
// 締切時刻の初期値（課題は、23:59の締切が多いため）。
const DEFAULT_DUE_TIME = "23:59";
const SUBJECT_PLACEHOLDER = "選択してください";
const SUBJECT_LOADING_NOTE = "授業を読み込み中…";

const TASK_FIELDS = {
  title: {
    inputIds: ["task-title"],
    messageId: "task-title-error",
  },
  subject_id: {
    inputIds: ["task-subject"],
    messageId: "task-subject-error",
  },
  due_datetime: {
    inputIds: ["task-due-date", "task-due-time"],
    messageId: "task-due-error",
  },
  notes: {
    inputIds: ["task-notes"],
    messageId: "task-notes-error",
  },
};
const TASK_FORM_ERROR_ID = "task-form-error";
const TASK_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
const TASK_EDIT_FIELDS = {
  title: {
    inputIds: ["task-edit-title"],
    messageId: "task-edit-title-error",
  },
  subject_id: {
    inputIds: ["task-edit-subject"],
    messageId: "task-edit-subject-error",
  },
  due_datetime: {
    inputIds: ["task-edit-due-date", "task-edit-due-time"],
    messageId: "task-edit-due-error",
  },
  notes: {
    inputIds: ["task-edit-notes"],
    messageId: "task-edit-notes-error",
  },
};
const TASK_EDIT_FORM_ERROR_ID = "task-edit-form-error";
const TASK_EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const TASK_DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};

// 一覧の取得の通し番号（古い応答で、今の一覧を上書きしないため）。
let requestSerial = 0;
// 編集・削除の対象の課題・タスク（一覧の行の値のコピー）。
let editingTask = null;
let deletingTask = null;
// 追加・編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直した
// あとに届いた古い応答で、今のモーダルの表示を変えないために使う。
let addSerial = 0;
let editSerial = 0;
let deleteSerial = 0;

// 課題・タスクを表す文字列（例：「レポート第1回」（締切 2026年10月20日（火）
// 23:59））。同じタイトルの課題・タスクを、締切で区別できるようにする。
function taskLabel(task) {
  return (
    `「${task.title}」` +
    `（締切 ${formatJapaneseDateTime(task.due_datetime)}）`
  );
}

// 締切日と締切時刻の入力欄の値を、APIの日時（YYYY-MM-DDTHH:MM）にする。
function dueDateTimeOf(dateInputId, timeInputId) {
  const date = getElement(dateInputId).value;
  const time = getElement(timeInputId).value;
  return `${date}T${time}`;
}

function showTaskLoading() {
  setVisible(getElement("task-loading"), true);
  setVisible(getElement("task-load-error"), false);
  setVisible(getElement("task-content"), false);
}

function showTaskLoadError(error) {
  getElement("task-load-error-message").textContent = errorMessageOf(error);
  setVisible(getElement("task-loading"), false);
  setVisible(getElement("task-load-error"), true);
  setVisible(getElement("task-content"), false);
}

function showActionError(error) {
  const actionError = getElement("task-action-error");
  actionError.textContent = errorMessageOf(error);
  setVisible(actionError, true);
}

function hideActionError() {
  const actionError = getElement("task-action-error");
  actionError.replaceChildren();
  setVisible(actionError, false);
}

// 一覧の1行を作る。overdueBefore は、期限切れの判定に使う今の日時
// （YYYY-MM-DDTHH:MM）。完了の表では null（期限切れを出さない）。
function createTaskRow(task, overdueBefore) {
  const category = taskCategoryOf(task.category);
  const label = taskLabel(task);
  const row = document.createElement("tr");

  const completedCell = document.createElement("td");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `task-complete-${task.id}`;
  checkbox.className = "form-check-input";
  checkbox.checked = task.is_completed;
  checkbox.setAttribute("aria-label", `${label}の完了`);
  checkbox.addEventListener("change", () => {
    toggleTaskCompleted(task, checkbox);
  });
  completedCell.append(checkbox);
  row.append(completedCell);

  const dueCell = document.createElement("td");
  dueCell.textContent = formatJapaneseDateTime(task.due_datetime);
  // 締切日時が今より前なら、期限切れ（YYYY-MM-DDTHH:MMは桁が固定されて
  // いるため、文字列の大小で前後を比べられる）。
  if (overdueBefore !== null && task.due_datetime < overdueBefore) {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-danger ms-1";
    badge.textContent = "期限切れ";
    dueCell.append(badge);
  }
  row.append(dueCell);

  const titleCell = document.createElement("td");
  const titleLine = document.createElement("div");
  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;
  // アイコンは読み上げないため、カテゴリの表示名を、見えない文字で添える。
  const categoryName = document.createElement("span");
  categoryName.className = "visually-hidden";
  categoryName.textContent = `${category.label}：`;
  titleLine.append(icon, categoryName, task.title);
  titleCell.append(titleLine);
  if (task.notes !== null) {
    const notes = document.createElement("div");
    notes.className = "text-muted small text-pre-wrap";
    notes.textContent = task.notes;
    titleCell.append(notes);
  }
  row.append(titleCell);

  const subjectCell = document.createElement("td");
  subjectCell.textContent = task.subject_name ?? "—";
  row.append(subjectCell);

  const actions = document.createElement("td");
  actions.className = "text-end text-nowrap";

  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.id = `task-edit-${task.id}`;
  editButton.className = "btn btn-outline-secondary btn-sm";
  editButton.textContent = "編集";
  editButton.setAttribute("aria-label", `${label}を編集`);
  editButton.addEventListener("click", () => {
    openEditModal(task);
  });
  actions.append(editButton);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.id = `task-delete-${task.id}`;
  deleteButton.className = "btn btn-outline-danger btn-sm ms-1";
  deleteButton.textContent = "削除";
  deleteButton.setAttribute("aria-label", `${label}を削除`);
  deleteButton.addEventListener("click", () => {
    openDeleteModal(task);
  });
  actions.append(deleteButton);

  row.append(actions);
  return row;
}

// 1つの表（未完了か完了）の行を作り直す。0件なら、表を隠して、
// 0件の文言を出す。
function renderTaskTable(tasks, { bodyId, listId, emptyId, overdueBefore }) {
  const fragment = document.createDocumentFragment();
  for (const task of tasks) {
    fragment.append(createTaskRow(task, overdueBefore));
  }
  getElement(bodyId).replaceChildren(fragment);
  setVisible(getElement(emptyId), tasks.length === 0);
  setVisible(getElement(listId), tasks.length > 0);
}

// 一覧を、未完了と完了の2つの表に分けて表示する。APIの並びは、締切日時の
// 早い順。未完了は、そのまま（期限切れが上に来る）。完了は、逆にして、
// 締切日時の新しい順にする。期限切れは、表示するときの日時で判定する。
function renderTasks(tasks) {
  const incomplete = tasks.filter((task) => !task.is_completed);
  const completed = tasks.filter((task) => task.is_completed).reverse();

  renderTaskTable(incomplete, {
    bodyId: "task-incomplete-body",
    listId: "task-incomplete-list",
    emptyId: "task-incomplete-empty",
    overdueBefore: localDateTimeString(),
  });
  renderTaskTable(completed, {
    bodyId: "task-completed-body",
    listId: "task-completed-list",
    emptyId: "task-completed-empty",
    overdueBefore: null,
  });
  setVisible(getElement("task-loading"), false);
  setVisible(getElement("task-load-error"), false);
  setVisible(getElement("task-content"), true);
}

async function loadTasks({ showLoading = true } = {}) {
  const currentRequest = ++requestSerial;
  if (showLoading) {
    showTaskLoading();
  }

  let tasks;
  try {
    tasks = await apiRequest("GET", "/api/tasks");
  } catch (error) {
    // 新しい取得を始めていたら、古い取得の結果で、画面を変えない。
    if (currentRequest !== requestSerial) {
      return;
    }
    showTaskLoadError(error);
    return;
  }

  if (currentRequest !== requestSerial) {
    return;
  }
  renderTasks(tasks);
}

// 完了の切り替え（チェックボックス）。確認は出さない。成功したら、一覧を
// 取得し直す（行が、もう一方の表へ移る）。失敗したら、チェックを元に戻し、
// エラーを一覧の上部に出す。
async function toggleTaskCompleted(task, checkbox) {
  hideActionError();
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
    showActionError(error);
    return;
  }

  await loadTasks({ showLoading: false });
}

// 対象授業のプルダウンの選択肢を作る。先頭は「選択してください」（値は空）。
// extraSubject は、今の学期の授業の一覧にない、課題の今の対象授業（編集の
// とき。{ id, subject_name }）。ないときは null。
function renderSubjectOptions(select, subjects, extraSubject) {
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = SUBJECT_PLACEHOLDER;
  const options = [placeholder];
  const items =
    extraSubject === null ? subjects : [extraSubject, ...subjects];
  for (const subject of items) {
    const option = document.createElement("option");
    option.value = String(subject.id);
    option.textContent = subject.subject_name;
    options.push(option);
  }
  select.replaceChildren(...options);
}

// 今の学期（授業モードで最初に選ばれる学期と同じ規則。current_semester.js）
// と、その学期の授業の一覧を取得する。学期が0件なら、semester は null。
async function fetchCurrentSubjects() {
  const semesters = await apiRequest("GET", "/api/semesters");
  const semester = chooseCurrentSemester(semesters, localDateString());
  if (semester === null) {
    return { semester: null, subjects: [] };
  }
  const subjects = await apiRequest(
    "GET",
    `/api/subjects?semester_id=${semester.id}`,
  );
  return { semester, subjects };
}

// 対象授業の欄の下に出す説明。
function subjectNoteOf(semester, subjects) {
  if (semester === null) {
    return (
      "学期が登録されていません。" +
      "授業モードで、学期と授業を登録してください"
    );
  }
  if (subjects.length === 0) {
    return (
      `${semester.name}には、授業が登録されていません。` +
      "授業モードで、授業を登録してください"
    );
  }
  return `${semester.name}の授業から選びます`;
}

// 追加のモーダルを開くたびに、入力欄を初期値に戻し、今の学期の授業を
// 取得して、対象授業の選択肢を作る。
async function prepareAddModal() {
  const currentSerial = ++addSerial;
  const select = getElement("task-subject");
  const note = getElement("task-subject-note");

  getElement("task-form").reset();
  getElement("task-title").value = "";
  getElement("task-due-date").value = "";
  getElement("task-due-time").value = DEFAULT_DUE_TIME;
  getElement("task-notes").value = "";
  clearFormErrors(TASK_FIELDS, TASK_FORM_ERROR_ID);
  setSubmitting(
    getElement("task-submit-button"),
    false,
    TASK_SUBMIT_LABELS,
  );
  // 授業を取得するまでは、「選択してください」だけ（必須のため、
  // ブラウザの入力チェックで、登録は止まる）。
  renderSubjectOptions(select, [], null);
  note.textContent = SUBJECT_LOADING_NOTE;

  let result;
  try {
    result = await fetchCurrentSubjects();
  } catch (error) {
    // モーダルを開き直していたら、今のモーダルの表示を変えない。
    if (currentSerial !== addSerial) {
      return;
    }
    note.replaceChildren();
    showApiError(error, TASK_FIELDS, TASK_FORM_ERROR_ID);
    return;
  }

  if (currentSerial !== addSerial) {
    return;
  }
  renderSubjectOptions(select, result.subjects, null);
  note.textContent = subjectNoteOf(result.semester, result.subjects);
}

async function submitTask(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = addSerial;
  clearFormErrors(TASK_FIELDS, TASK_FORM_ERROR_ID);

  const submitButton = getElement("task-submit-button");
  setSubmitting(submitButton, true, TASK_SUBMIT_LABELS);

  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
  // 「登録の失敗」として表示しないため）。
  try {
    await apiRequest("POST", "/api/tasks", {
      category: ASSIGNMENT,
      subject_id: Number(getElement("task-subject").value),
      title: getElement("task-title").value,
      due_datetime: dueDateTimeOf("task-due-date", "task-due-time"),
      notes: getElement("task-notes").value,
    });
  } catch (error) {
    if (startedSerial !== addSerial) {
      return;
    }
    showApiError(error, TASK_FIELDS, TASK_FORM_ERROR_ID);
    setSubmitting(submitButton, false, TASK_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === addSerial) {
    hideModal(getElement("task-modal"));
  }
  await loadTasks({ showLoading: false });
}

// 一覧の「編集」ボタン。対象を控えて、編集のモーダルを開く（入力欄は、
// モーダルを開くとき（show.bs.modal）に入れる）。
function openEditModal(task) {
  editingTask = { ...task };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("task-edit-modal"),
  ).show();
}

// 編集のモーダルを開くたびに、対象の今の値を入力欄に入れ、エラーの表示を
// 消す。課題は、今の学期の授業を取得して、対象授業の選択肢を作る。
// その他（締切のみ）は、対象授業の欄を出さない。
async function prepareEditModal() {
  const currentSerial = ++editSerial;
  const task = editingTask;
  const isAssignment = task.category === ASSIGNMENT;
  const select = getElement("task-edit-subject");
  const note = getElement("task-edit-subject-note");

  getElement("task-edit-form").reset();
  getElement("task-edit-modal-title").textContent = isAssignment
    ? "課題を編集"
    : "その他（締切のみ）を編集";
  getElement("task-edit-title-label").textContent = isAssignment
    ? "課題名"
    : "タイトル";
  const [dueDate, dueTime] = task.due_datetime.split("T");
  getElement("task-edit-title").value = task.title;
  getElement("task-edit-due-date").value = dueDate;
  getElement("task-edit-due-time").value = dueTime;
  getElement("task-edit-notes").value = task.notes ?? "";
  clearFormErrors(TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("task-edit-submit-button"),
    false,
    TASK_EDIT_SUBMIT_LABELS,
  );

  setVisible(getElement("task-edit-subject-row"), isAssignment);
  // 隠した欄の入力チェック（必須）で、保存が止まらないように、
  // その他では、プルダウンを無効にする。
  select.disabled = !isAssignment;
  if (!isAssignment) {
    renderSubjectOptions(select, [], null);
    note.replaceChildren();
    return;
  }

  // 授業を取得するまでは、今の対象授業だけを選んだ状態にする（取得に
  // 失敗しても、ほかの項目は保存できる）。
  const currentSubject = {
    id: task.subject_id,
    subject_name: task.subject_name,
  };
  renderSubjectOptions(select, [], currentSubject);
  select.value = String(task.subject_id);
  note.textContent = SUBJECT_LOADING_NOTE;

  let result;
  try {
    result = await fetchCurrentSubjects();
  } catch (error) {
    if (currentSerial !== editSerial) {
      return;
    }
    note.replaceChildren();
    showApiError(error, TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);
    return;
  }

  if (currentSerial !== editSerial) {
    return;
  }
  // 今の対象授業が、今の学期の授業にない場合（ほかの学期の授業の課題）は、
  // 選択肢に足す（足さないと、空欄になり、保存すると必須のエラーになる）。
  const inCurrentSemester = result.subjects.some(
    (subject) => subject.id === task.subject_id,
  );
  renderSubjectOptions(
    select,
    result.subjects,
    inCurrentSemester ? null : currentSubject,
  );
  select.value = String(task.subject_id);
  note.textContent = subjectNoteOf(result.semester, result.subjects);
}

async function submitTaskEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const task = editingTask;
  clearFormErrors(TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);

  const submitButton = getElement("task-edit-submit-button");
  setSubmitting(submitButton, true, TASK_EDIT_SUBMIT_LABELS);

  // すべての項目を送る（変えていない項目も、今の値のまま送る）。
  // 対象授業は、課題だけ（その他は、授業を指定できない）。
  const body = {
    title: getElement("task-edit-title").value,
    due_datetime: dueDateTimeOf("task-edit-due-date", "task-edit-due-time"),
    notes: getElement("task-edit-notes").value,
  };
  if (task.category === ASSIGNMENT) {
    body.subject_id = Number(getElement("task-edit-subject").value);
  }

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("PATCH", `/api/tasks/${task.id}`, body);
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, TASK_EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("task-edit-modal"));
  }
  await loadTasks({ showLoading: false });
}

// 一覧の「削除」ボタン。対象を控えて、削除の確認のモーダルを開く。
function openDeleteModal(task) {
  deletingTask = { ...task };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("task-delete-modal"),
  ).show();
}

function showDeleteError(error) {
  const deleteError = getElement("task-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("task-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、対象を表示し、エラーを消す。
function prepareDeleteModal() {
  deleteSerial += 1;
  getElement("task-delete-target").textContent =
    `${taskLabel(deletingTask)}を削除します。`;
  hideDeleteError();
  setSubmitting(
    getElement("task-delete-submit-button"),
    false,
    TASK_DELETE_SUBMIT_LABELS,
  );
}

async function submitTaskDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const taskId = deletingTask.id;
  hideDeleteError();

  const submitButton = getElement("task-delete-submit-button");
  setSubmitting(submitButton, true, TASK_DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/tasks/${taskId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, TASK_DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("task-delete-modal"));
  }
  await loadTasks({ showLoading: false });
}

export function initTasks() {
  // 課題・タスクのモードを開くたびに、一覧を取得し直す（ほかのモードでの
  // 授業の削除などを反映し、期限切れを、開いたときの日時で判定するため）。
  // 前の切り替えのエラーは消す。
  getElement("tasks-tab").addEventListener("shown.bs.tab", () => {
    hideActionError();
    loadTasks();
  });
  getElement("task-retry-button").addEventListener("click", () => {
    loadTasks();
  });

  // 追加・編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const addModal = getElement("task-modal");
  trackModalShowing(addModal);
  addModal.addEventListener("show.bs.modal", prepareAddModal);
  addModal.addEventListener("shown.bs.modal", () => {
    getElement("task-title").focus();
  });
  getElement("task-form").addEventListener("submit", submitTask);

  const editModal = getElement("task-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", prepareEditModal);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement("task-edit-title").focus();
  });
  getElement("task-edit-form").addEventListener("submit", submitTaskEdit);

  const deleteModal = getElement("task-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("task-delete-cancel-button").focus();
  });
  getElement("task-delete-submit-button").addEventListener(
    "click",
    submitTaskDelete,
  );
}
