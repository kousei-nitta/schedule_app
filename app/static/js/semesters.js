import { ApiError, apiRequest } from "./api.js";

let semesters = [];
let selectedId = null;

function getElement(id) {
  return document.getElementById(id);
}

function setVisible(element, visible) {
  element.classList.toggle("d-none", !visible);
}

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

function clearFormErrors() {
  const formError = getElement("semester-form-error");
  formError.replaceChildren();
  setVisible(formError, false);

  for (const id of [
    "semester-name-error",
    "semester-start-date-error",
    "semester-end-date-error",
  ]) {
    getElement(id).replaceChildren();
  }

  for (const id of [
    "semester-year",
    "semester-term",
    "semester-start-date",
    "semester-end-date",
  ]) {
    getElement(id).classList.remove("is-invalid");
  }
}

function resetForm() {
  const now = new Date();
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
  submitButton.disabled = false;
  submitButton.textContent = "登録する";
  clearFormErrors();
}

function renderTabs() {
  const tabs = getElement("semester-tabs");
  const detail = getElement("semester-detail");
  const fragment = document.createDocumentFragment();

  for (const semester of semesters) {
    const item = document.createElement("li");
    item.className = "nav-item";

    const button = document.createElement("button");
    button.type = "button";
    button.id = `semester-tab-${semester.id}`;
    button.className = "nav-link";
    button.classList.toggle("active", semester.id === selectedId);
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "semester-detail");
    button.setAttribute(
      "aria-selected",
      semester.id === selectedId ? "true" : "false",
    );
    button.textContent = semester.name;
    button.addEventListener("click", () => {
      selectedId = semester.id;
      renderTabs();
      renderDetail();
    });

    item.append(button);
    fragment.append(item);
  }

  tabs.replaceChildren(fragment);
  const selected = semesters.find((semester) => semester.id === selectedId);
  if (selected !== undefined) {
    detail.setAttribute("aria-labelledby", `semester-tab-${selected.id}`);
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

function showLoading() {
  setVisible(getElement("semester-loading"), true);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), false);
}

function showLoadError(error) {
  getElement("semester-load-error-message").textContent = error.message;
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
  renderTabs();
  renderBanner();
  renderDetail();
}

async function loadSemesters(preferredId = null) {
  showLoading();
  try {
    semesters = await apiRequest("GET", "/api/semesters");
    if (semesters.length === 0) {
      selectedId = null;
      showEmpty();
      return;
    }

    const preferred = semesters.find(
      (semester) => semester.id === preferredId,
    );
    const initial =
      preferred ?? chooseInitialSemester(semesters, localDateString());
    selectedId = initial.id;
    showContent();
  } catch (error) {
    showLoadError(error);
  }
}

function setFieldError(messageId, inputIds, message) {
  getElement(messageId).textContent = message;
  for (const id of inputIds) {
    getElement(id).classList.add("is-invalid");
  }
}

function showSubmitError(error) {
  clearFormErrors();

  if (
    error instanceof ApiError &&
    error.code === "validation_error" &&
    error.fields !== null
  ) {
    const knownFields = new Set(["name", "start_date", "end_date"]);
    const unexpectedField = Object.keys(error.fields).some(
      (field) => !knownFields.has(field),
    );

    if (Object.hasOwn(error.fields, "name")) {
      setFieldError(
        "semester-name-error",
        ["semester-year", "semester-term"],
        error.fields.name,
      );
    }
    if (Object.hasOwn(error.fields, "start_date")) {
      setFieldError(
        "semester-start-date-error",
        ["semester-start-date"],
        error.fields.start_date,
      );
    }
    if (Object.hasOwn(error.fields, "end_date")) {
      setFieldError(
        "semester-end-date-error",
        ["semester-end-date"],
        error.fields.end_date,
      );
    }

    if (!unexpectedField && Object.keys(error.fields).length > 0) {
      return;
    }
    showFormMessage("入力内容に誤りがあります");
    return;
  }

  showFormMessage(error.message);
}

function showFormMessage(message) {
  const formError = getElement("semester-form-error");
  formError.textContent = message;
  setVisible(formError, true);
}

async function submitSemester(event) {
  event.preventDefault();
  clearFormErrors();

  const submitButton = getElement("semester-submit-button");
  submitButton.disabled = true;
  submitButton.textContent = "登録中…";

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
    window.bootstrap.Modal.getInstance(modal).hide();
    await loadSemesters(created.id);
  } catch (error) {
    showSubmitError(error);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "登録する";
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
