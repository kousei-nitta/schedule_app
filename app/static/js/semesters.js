import { apiRequest } from "./api.js";
import { chooseCurrentSemester } from "./current_semester.js";
import { formatJapaneseDate, localDateString } from "./dates.js";
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

let semesters = [];
let selectedId = null;
// 編集・削除の対象の学期（選択中の学期の値のコピー）。モーダルを開くときに
// 入れる。
let editingSemester = null;
let deletingSemester = null;
// 編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直したあとに
// 届いた古い応答で、今のモーダルの表示を変えないために使う。
let editSerial = 0;
let deleteSerial = 0;

// 学期名の形（「2026年度 前期」。APIが検査する）。編集のときに、年度と
// 種別に分けるために使う。
const SEMESTER_NAME_PATTERN = /^([0-9]{4})年度 (前期|後期)$/;

const SEMESTER_FIELDS = {
  name: {
    inputIds: ["semester-year", "semester-term"],
    messageId: "semester-name-error",
  },
  start_date: {
    inputIds: ["semester-start-date"],
    messageId: "semester-start-date-error",
  },
  end_date: {
    inputIds: ["semester-end-date"],
    messageId: "semester-end-date-error",
  },
};

const SEMESTER_FORM_ERROR_ID = "semester-form-error";
const SEMESTER_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
const SEMESTER_EDIT_FIELDS = {
  name: {
    inputIds: ["semester-edit-year", "semester-edit-term"],
    messageId: "semester-edit-name-error",
  },
  start_date: {
    inputIds: ["semester-edit-start-date"],
    messageId: "semester-edit-start-date-error",
  },
  end_date: {
    inputIds: ["semester-edit-end-date"],
    messageId: "semester-edit-end-date-error",
  },
};
const SEMESTER_EDIT_FORM_ERROR_ID = "semester-edit-form-error";
const SEMESTER_EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const SEMESTER_DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};

// 年度と種別から、学期名（「2026年度 前期」）を組み立てる。
function semesterName(year, term) {
  return `${year}年度 ${term}`;
}

// 学期の期間を表す文字列（「2026年9月21日 〜 2026年12月27日」）。
function semesterPeriod(semester) {
  return (
    `${formatJapaneseDate(semester.start_date)} 〜 ` +
    `${formatJapaneseDate(semester.end_date)}`
  );
}

// 選択中の学期（なければ null）。
function selectedSemester() {
  return semesters.find((semester) => semester.id === selectedId) ?? null;
}

function clearSemesterFormErrors() {
  clearFormErrors(SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
}

function resetForm() {
  const now = new Date();
  // getMonth()は0始まり（3は4月、7は8月）。
  const year = now.getFullYear() - (now.getMonth() < 3 ? 1 : 0);
  const term = now.getMonth() >= 3 && now.getMonth() <= 7 ? "前期" : "後期";
  const form = getElement("semester-form");
  const submitButton = getElement("semester-submit-button");

  // モーダルを開くたび前回の入力や失敗表示を残さず、今日に基づく初期値から始める。
  form.reset();
  getElement("semester-year").value = String(year);
  getElement("semester-term").value = term;
  getElement("semester-start-date").value = "";
  getElement("semester-end-date").value = "";
  setSubmitting(submitButton, false, SEMESTER_SUBMIT_LABELS);
  clearSemesterFormErrors();
}

function renderTabs() {
  const tabs = getElement("semester-tabs");
  const fragment = document.createDocumentFragment();

  for (const semester of semesters) {
    const item = document.createElement("li");
    item.className = "nav-item";
    item.setAttribute("role", "presentation");

    const button = document.createElement("button");
    button.type = "button";
    button.id = `semester-tab-${semester.id}`;
    button.className = "nav-link";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "semester-detail");
    button.textContent = semester.name;
    button.addEventListener("click", () => {
      selectSemester(semester.id);
    });

    item.append(button);
    fragment.append(item);
  }

  tabs.replaceChildren(fragment);
}

function updateTabSelection() {
  for (const item of getElement("semester-tabs").children) {
    const button = item.querySelector('[role="tab"]');
    const selected = button.id === `semester-tab-${selectedId}`;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", selected ? "true" : "false");
  }

  const selected = selectedSemester();
  if (selected !== null) {
    getElement("semester-detail").setAttribute(
      "aria-labelledby",
      `semester-tab-${selected.id}`,
    );
  }
}

function renderBanner() {
  const today = localDateString();
  const hasCurrentSemester = semesters.some(
    (semester) => semester.start_date <= today && today <= semester.end_date,
  );
  setVisible(getElement("semester-banner"), !hasCurrentSemester);
}

function renderDetail() {
  const selected = selectedSemester();
  if (selected === null) {
    return;
  }

  getElement("semester-detail-name").textContent = selected.name;
  getElement("semester-detail-period").textContent = semesterPeriod(selected);
  // 読み上げで、どの学期のボタンかが分かるように、aria-label に学期名を
  // 入れる。
  getElement("semester-edit-button").setAttribute(
    "aria-label",
    `「${selected.name}」を編集`,
  );
  getElement("semester-delete-button").setAttribute(
    "aria-label",
    `「${selected.name}」を削除`,
  );
}

// 学期を選ぶ。選択中の学期が変わったときに、semester-selected を発行する。
// notifySameSemester が true なら、同じ学期を選び直したときも発行する
// （選択中の学期を編集したとき。休講日の一覧や、授業の登録先の学期名を、
// 新しい値で作り直してもらうため）。
function selectSemester(id, { notifySameSemester = false } = {}) {
  const previousId = selectedId;
  selectedId = id;

  updateTabSelection();
  renderDetail();

  if (previousId !== id || notifySameSemester) {
    const selected = selectedSemester();
    const semester =
      selected === null
        ? null
        : {
            id: selected.id,
            name: selected.name,
            start_date: selected.start_date,
            end_date: selected.end_date,
          };
    // 状態変更と通知をここに集約し、購読側が更新済みの画面を扱えるよう描画後に発行する。
    document.dispatchEvent(
      new CustomEvent("semester-selected", {
        detail: { semester },
      }),
    );
  }
}

function showLoading() {
  setVisible(getElement("semester-loading"), true);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), false);
}

function showLoadError(error) {
  getElement("semester-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("semester-loading"), false);
  setVisible(getElement("semester-load-error"), true);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), false);
}

function showEmpty() {
  setVisible(getElement("semester-loading"), false);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), true);
  setVisible(getElement("semester-content"), false);
}

function showContent() {
  setVisible(getElement("semester-loading"), false);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), true);
  renderBanner();
}

// 学期の一覧を取得し、学期を選ぶ。preferredId の学期があれば、その学期を
// 選ぶ（なければ、今の学期の規則で選ぶ）。notifySameSemester は、
// selectSemester と同じ。
async function loadSemesters({
  preferredId = null,
  notifySameSemester = false,
} = {}) {
  showLoading();
  try {
    semesters = await apiRequest("GET", "/api/semesters");
    if (semesters.length === 0) {
      showEmpty();
      selectSemester(null);
      return;
    }

    const preferred = semesters.find(
      (semester) => semester.id === preferredId,
    );
    const initial =
      preferred ?? chooseCurrentSemester(semesters, localDateString());
    showContent();
    renderTabs();
    selectSemester(initial.id, { notifySameSemester });
  } catch (error) {
    showLoadError(error);
  }
}

async function submitSemester(event) {
  event.preventDefault();
  clearSemesterFormErrors();

  const submitButton = getElement("semester-submit-button");
  setSubmitting(submitButton, true, SEMESTER_SUBMIT_LABELS);

  const name = semesterName(
    getElement("semester-year").value,
    getElement("semester-term").value,
  );
  const startDate = getElement("semester-start-date").value;
  const endDate = getElement("semester-end-date").value;

  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
  // 「登録の失敗」として表示しないため）。
  let created;
  try {
    created = await apiRequest("POST", "/api/semesters", {
      name,
      start_date: startDate,
      end_date: endDate,
    });
  } catch (error) {
    showApiError(error, SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SEMESTER_SUBMIT_LABELS);
    return;
  }

  // 表示のアニメーションの途中でも、表示が終わってから閉じる（ui.js）。
  hideModal(getElement("semester-modal"));
  await loadSemesters({ preferredId: created.id });
}

// 編集のモーダルを開くたびに、選択中の学期の今の値を入力欄に入れ、
// エラーの表示を消す。「編集」ボタンは、学期の本文（学期を選んでいる
// ときだけ表示する）にあり、data-bs-toggle で、このモーダルを開く。
function fillEditForm() {
  editSerial += 1;
  editingSemester = { ...selectedSemester() };
  const match = SEMESTER_NAME_PATTERN.exec(editingSemester.name);

  getElement("semester-edit-form").reset();
  if (match !== null) {
    getElement("semester-edit-year").value = match[1];
    getElement("semester-edit-term").value = match[2];
  }
  getElement("semester-edit-start-date").value = editingSemester.start_date;
  getElement("semester-edit-end-date").value = editingSemester.end_date;
  clearFormErrors(SEMESTER_EDIT_FIELDS, SEMESTER_EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("semester-edit-submit-button"),
    false,
    SEMESTER_EDIT_SUBMIT_LABELS,
  );
}

async function submitSemesterEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const semesterId = editingSemester.id;
  clearFormErrors(SEMESTER_EDIT_FIELDS, SEMESTER_EDIT_FORM_ERROR_ID);

  const submitButton = getElement("semester-edit-submit-button");
  setSubmitting(submitButton, true, SEMESTER_EDIT_SUBMIT_LABELS);

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  // すべての項目を送る（変えていない項目も、今の値のまま送る）。
  try {
    await apiRequest("PATCH", `/api/semesters/${semesterId}`, {
      name: semesterName(
        getElement("semester-edit-year").value,
        getElement("semester-edit-term").value,
      ),
      start_date: getElement("semester-edit-start-date").value,
      end_date: getElement("semester-edit-end-date").value,
    });
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, SEMESTER_EDIT_FIELDS, SEMESTER_EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SEMESTER_EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("semester-edit-modal"));
  }
  // 同じ学期でも、semester-selected を発行する（期間の外になった休講日は
  // 削除されているため、休講日の一覧を取得し直してもらう。授業の登録先の
  // 学期名も、新しい名前にする）。
  await loadSemesters({ preferredId: semesterId, notifySameSemester: true });
}

function showDeleteError(error) {
  const deleteError = getElement("semester-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("semester-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、選択中の学期を表示し、授業と休講日の
// 件数を、学期の1件取得（subject_count・closure_count）で取得する。授業が
// ある学期は、削除できない（「削除する」ボタンは、押せないまま）。
// 「削除」ボタンは、「編集」ボタンと同じく、data-bs-toggle で開く。
async function prepareDeleteModal() {
  const currentSerial = ++deleteSerial;
  deletingSemester = { ...selectedSemester() };
  const semester = deletingSemester;
  const loading = getElement("semester-delete-loading");
  const counts = getElement("semester-delete-counts");
  const warning = getElement("semester-delete-warning");
  const submitButton = getElement("semester-delete-submit-button");

  getElement("semester-delete-target").textContent =
    `「${semester.name}」（${semesterPeriod(semester)}）を削除します。`;
  counts.replaceChildren();
  setVisible(counts, false);
  setVisible(loading, true);
  setVisible(warning, true);
  hideDeleteError();
  submitButton.textContent = SEMESTER_DELETE_SUBMIT_LABELS.idle;
  submitButton.disabled = true;

  let detail;
  try {
    detail = await apiRequest("GET", `/api/semesters/${semester.id}`);
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
  if (detail.subject_count > 0) {
    counts.textContent =
      `この学期には、授業が${detail.subject_count}件登録されているため、` +
      "削除できません。先に、この画面の授業の一覧から、" +
      "授業をすべて削除してください。";
    setVisible(counts, true);
    setVisible(warning, false);
    return;
  }
  counts.textContent =
    `この学期の休講日${detail.closure_count}件も、まとめて削除されます。`;
  setVisible(counts, true);
  submitButton.disabled = false;
}

async function submitSemesterDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const semesterId = deletingSemester.id;
  hideDeleteError();

  const submitButton = getElement("semester-delete-submit-button");
  setSubmitting(submitButton, true, SEMESTER_DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/semesters/${semesterId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, SEMESTER_DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("semester-delete-modal"));
  }
  // 削除した学期はないため、今の学期の規則で、学期を選び直す。
  await loadSemesters();
}

export function initSemesters() {
  getElement("semester-retry-button").addEventListener("click", () => {
    loadSemesters();
  });
  const modal = getElement("semester-modal");
  // 登録に成功したら、JavaScriptから閉じるため、表示の途中かを記録する。
  trackModalShowing(modal);
  modal.addEventListener("show.bs.modal", resetForm);
  getElement("semester-form").addEventListener("submit", submitSemester);

  // 編集・削除のモーダルも、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const editModal = getElement("semester-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", fillEditForm);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement("semester-edit-year").focus();
  });
  getElement("semester-edit-form").addEventListener(
    "submit",
    submitSemesterEdit,
  );

  const deleteModal = getElement("semester-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("semester-delete-cancel-button").focus();
  });
  getElement("semester-delete-submit-button").addEventListener(
    "click",
    submitSemesterDelete,
  );

  loadSemesters();
}
