import { apiRequest } from "./api.js";
import { formatJapaneseDateWithWeekday } from "./dates.js";
import {
  clearFormErrors,
  errorMessageOf,
  getElement,
  setSubmitting,
  setVisible,
  showApiError,
} from "./ui.js";

let currentSemester = null;
// 一覧の取得の通し番号。古い応答で、今の一覧を上書きしないために使う。
let requestSerial = 0;
// 学期の選択の通し番号。追加・削除の途中で、学期が変わったかを確かめる。
// 一覧の取得し直しでは選択は変わらないため、requestSerialとは別に持つ。
let selectionSerial = 0;

const CLOSURE_FIELDS = {
  semester_id: {
    inputIds: [],
    messageId: "closure-semester-error",
  },
  date: {
    inputIds: ["closure-date"],
    messageId: "closure-date-error",
  },
  name: {
    inputIds: ["closure-name"],
    messageId: "closure-name-error",
  },
};
// 欄の上部のエラー表示。追加の、項目に結びつかないエラーと、削除のエラーを出す。
const CLOSURE_FORM_ERROR_ID = "closure-form-error";
const CLOSURE_SUBMIT_LABELS = {
  idle: "追加する",
  busy: "追加中…",
};
const CLOSURE_DELETE_LABELS = {
  idle: "削除",
  busy: "削除中…",
};

function clearClosureErrors() {
  clearFormErrors(CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
}

function resetClosureForm() {
  getElement("closure-form").reset();
  getElement("closure-date").value = "";
  getElement("closure-name").value = "";
  clearClosureErrors();
  setSubmitting(
    getElement("closure-submit-button"),
    false,
    CLOSURE_SUBMIT_LABELS,
  );
}

function clearClosureList() {
  getElement("closure-list").replaceChildren();
  setVisible(getElement("closure-loading"), false);
  setVisible(getElement("closure-load-error"), false);
  setVisible(getElement("closure-empty"), false);
  setVisible(getElement("closure-list"), false);
}

function showClosureLoading() {
  setVisible(getElement("closure-loading"), true);
  setVisible(getElement("closure-load-error"), false);
  setVisible(getElement("closure-empty"), false);
  setVisible(getElement("closure-list"), false);
}

function showClosureLoadError(error) {
  getElement("closure-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("closure-loading"), false);
  setVisible(getElement("closure-load-error"), true);
  setVisible(getElement("closure-empty"), false);
  setVisible(getElement("closure-list"), false);
}

function renderClosures(closures) {
  const list = getElement("closure-list");
  const fragment = document.createDocumentFragment();

  for (const closure of closures) {
    const item = document.createElement("li");
    item.className =
      "list-group-item d-flex justify-content-between align-items-center";

    const dateLabel = formatJapaneseDateWithWeekday(closure.date);
    const text = document.createElement("div");
    const dateText = document.createElement("span");
    dateText.textContent = dateLabel;
    text.append(dateText);
    if (closure.name !== null) {
      const name = document.createElement("span");
      name.className = "ms-2 text-muted";
      name.textContent = closure.name;
      text.append(name);
    }
    item.append(text);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.id = `closure-delete-${closure.id}`;
    deleteButton.className = "btn btn-outline-danger btn-sm text-nowrap ms-2";
    deleteButton.textContent = CLOSURE_DELETE_LABELS.idle;
    // 読み上げで、どの休講日の「削除」ボタンかを区別できるようにする。
    deleteButton.setAttribute("aria-label", `${dateLabel}の休講日を削除`);
    deleteButton.addEventListener("click", () => {
      deleteClosure(closure.id, deleteButton);
    });
    item.append(deleteButton);

    fragment.append(item);
  }

  list.replaceChildren(fragment);
  setVisible(getElement("closure-loading"), false);
  setVisible(getElement("closure-load-error"), false);
  setVisible(getElement("closure-empty"), closures.length === 0);
  setVisible(list, closures.length > 0);
}

async function loadClosures({ showLoading = true } = {}) {
  if (currentSemester === null) {
    clearClosureList();
    return;
  }

  const semesterId = currentSemester.id;
  const currentRequest = ++requestSerial;
  if (showLoading) {
    showClosureLoading();
  }

  try {
    const closures = await apiRequest(
      "GET",
      `/api/closures?semester_id=${semesterId}`,
    );
    // タブ切替後に古い応答が届いても、現在の休講日の一覧を上書きしない。
    if (currentRequest !== requestSerial) {
      return;
    }
    renderClosures(closures);
  } catch (error) {
    if (currentRequest !== requestSerial) {
      return;
    }
    showClosureLoadError(error);
  }
}

async function submitClosure(event) {
  event.preventDefault();
  // 追加の途中で学期が変わったら、結果を今の画面に出さないために控える。
  const startedSelection = selectionSerial;
  clearClosureErrors();

  const submitButton = getElement("closure-submit-button");
  setSubmitting(submitButton, true, CLOSURE_SUBMIT_LABELS);

  // try で囲むのは、追加の要求だけにする（成功後の処理の例外を、
  // 「追加の失敗」として表示しないため）。
  try {
    await apiRequest("POST", "/api/closures", {
      semester_id: currentSemester.id,
      date: getElement("closure-date").value,
      name: getElement("closure-name").value,
    });
  } catch (error) {
    if (startedSelection !== selectionSerial) {
      return;
    }
    showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
    setSubmitting(submitButton, false, CLOSURE_SUBMIT_LABELS);
    return;
  }

  if (startedSelection !== selectionSerial) {
    return;
  }
  resetClosureForm();
  getElement("closure-date").focus();
  await loadClosures({ showLoading: false });
}

async function deleteClosure(closureId, button) {
  // 削除の途中で学期が変わったら、結果を今の画面に出さないために控える。
  const startedSelection = selectionSerial;
  clearClosureErrors();
  setSubmitting(button, true, CLOSURE_DELETE_LABELS);

  // try で囲むのは、削除の要求だけにする（追加と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/closures/${closureId}`);
  } catch (error) {
    if (startedSelection !== selectionSerial) {
      return;
    }
    showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
    setSubmitting(button, false, CLOSURE_DELETE_LABELS);
    return;
  }

  if (startedSelection !== selectionSerial) {
    return;
  }
  await loadClosures({ showLoading: false });
}

export function initClosures() {
  document.addEventListener("semester-selected", (event) => {
    currentSemester = event.detail.semester;
    selectionSerial += 1;
    requestSerial += 1;
    // ほかの学期への入力や、ほかの学期で出たエラーを残さない。
    resetClosureForm();
    if (currentSemester === null) {
      clearClosureList();
      return;
    }
    loadClosures();
  });

  getElement("closure-retry-button").addEventListener("click", () => {
    loadClosures();
  });
  getElement("closure-form").addEventListener("submit", submitClosure);
}
