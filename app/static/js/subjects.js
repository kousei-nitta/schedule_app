import { apiRequest } from "./api.js";
import {
  clearFormErrors,
  errorMessageOf,
  getElement,
  setSubmitting,
  setVisible,
  showApiError,
} from "./ui.js";

let currentSemester = null;
let requestSerial = 0;

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

function resetSubjectForm(clearSuccess = true) {
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

function adjustEndTime() {
  const startTime = getElement("subject-start-time").value;
  const endTime = getElement("subject-end-time").value;
  if (endTime <= startTime) {
    // HH:MMは桁が固定されているため、文字列の大小で時刻を比較できる。
    const nextHour = String(Number(startTime.slice(0, 2)) + 1).padStart(
      2,
      "0",
    );
    getElement("subject-end-time").value = `${nextHour}:00`;
  }
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

    fragment.append(row);
  }

  tableBody.replaceChildren(fragment);
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), subjects.length === 0);
  setVisible(getElement("subject-list"), subjects.length > 0);
}

async function loadSubjects(showLoading = true) {
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

async function submitSubject(event) {
  event.preventDefault();
  clearFormErrors(SUBJECT_FIELDS, "subject-form-error");
  const success = getElement("subject-form-success");
  success.replaceChildren();
  setVisible(success, false);

  const submitButton = getElement("subject-submit-button");
  setSubmitting(submitButton, true, SUBJECT_SUBMIT_LABELS);

  try {
    const created = await apiRequest("POST", "/api/subjects", {
      semester_id: currentSemester.id,
      subject_name: getElement("subject-name").value,
      room: getElement("subject-room").value,
      weekday: Number(getElement("subject-weekday").value),
      start_time: getElement("subject-start-time").value,
      end_time: getElement("subject-end-time").value,
      notes: getElement("subject-notes").value,
    });

    success.textContent = `「${created.subject_name}」を登録しました`;
    setVisible(success, true);
    resetSubjectForm(false);
    getElement("subject-name").focus();
    await loadSubjects(false);
  } catch (error) {
    showApiError(error, SUBJECT_FIELDS, "subject-form-error");
    setSubmitting(submitButton, false, SUBJECT_SUBMIT_LABELS);
  }
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
  getElement("subject-start-time").addEventListener("change", adjustEndTime);
  getElement("subject-form").addEventListener("submit", submitSubject);
}
