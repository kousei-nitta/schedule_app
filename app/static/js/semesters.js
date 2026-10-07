import { apiRequest } from "./api.js";
import {
  clearFormErrors,
  errorMessageOf,
  getElement,
  setSubmitting,
  setVisible,
  showApiError,
} from "./ui.js";

let semesters = [];
let selectedId = null;

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

function localDateString(date = new Date()) {
  // toISOString()はUTC日付に変換するため、ローカル日付が前日になることがある。
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function chooseInitialSemester(items, today) {
  // YYYY-MM-DDは桁が固定されているため、文字列の大小が日付の前後と一致する。
  const current = items.find(
    (semester) => semester.start_date <= today && today <= semester.end_date,
  );
  if (current !== undefined) {
    return current;
  }

  let next = null;
  for (const semester of items) {
    if (
      semester.start_date > today &&
      (next === null || semester.start_date < next.start_date)
    ) {
      next = semester;
    }
  }
  if (next !== null) {
    return next;
  }

  let mostRecent = null;
  for (const semester of items) {
    if (
      mostRecent === null ||
      semester.end_date > mostRecent.end_date
    ) {
      mostRecent = semester;
    }
  }
  return mostRecent;
}

function formatJapaneseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return `${year}年${month}月${day}日`;
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
  updateTabSelection();
}

function updateTabSelection() {
  for (const item of getElement("semester-tabs").children) {
    const button = item.querySelector('[role="tab"]');
    const selected = button.id === `semester-tab-${selectedId}`;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", selected ? "true" : "false");
  }

  const selected = semesters.find((semester) => semester.id === selectedId);
  if (selected !== undefined) {
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
  const selected = semesters.find((semester) => semester.id === selectedId);
  if (selected === undefined) {
    return;
  }

  getElement("semester-detail-name").textContent = selected.name;
  getElement("semester-detail-period").textContent =
    `${formatJapaneseDate(selected.start_date)} 〜 ` +
    `${formatJapaneseDate(selected.end_date)}`;
}

function selectSemester(id) {
  const previousId = selectedId;
  selectedId = id;

  updateTabSelection();
  renderDetail();

  if (previousId !== id) {
    const selected = semesters.find((semester) => semester.id === id);
    const semester =
      selected === undefined
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

async function loadSemesters(preferredId = null) {
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
      preferred ?? chooseInitialSemester(semesters, localDateString());
    showContent();
    renderTabs();
    selectSemester(initial.id);
  } catch (error) {
    showLoadError(error);
  }
}

async function submitSemester(event) {
  event.preventDefault();
  clearSemesterFormErrors();

  const submitButton = getElement("semester-submit-button");
  setSubmitting(submitButton, true, SEMESTER_SUBMIT_LABELS);

  const name =
    `${getElement("semester-year").value}年度 ` +
    getElement("semester-term").value;
  const startDate = getElement("semester-start-date").value;
  const endDate = getElement("semester-end-date").value;

  try {
    const created = await apiRequest("POST", "/api/semesters", {
      name,
      start_date: startDate,
      end_date: endDate,
    });
    const modal = getElement("semester-modal");
    window.bootstrap.Modal.getOrCreateInstance(modal).hide();
    await loadSemesters(created.id);
  } catch (error) {
    showApiError(error, SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SEMESTER_SUBMIT_LABELS);
  }
}

export function initSemesters() {
  getElement("semester-retry-button").addEventListener("click", () => {
    loadSemesters();
  });
  getElement("semester-modal").addEventListener("show.bs.modal", resetForm);
  getElement("semester-form").addEventListener("submit", submitSemester);
  loadSemesters();
}
