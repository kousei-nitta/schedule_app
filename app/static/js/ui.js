import { ApiError } from "./api.js";

// 複数のモードで使う、表示とフォームの共通処理。
// fieldMap は { 項目名: { inputIds: [入力欄のid], messageId: エラー表示のid } }
// の形（項目名は、APIの fields の項目名と同じ）。

// idの要素を返す。見つからない場合は、idの書き間違いに気づけるように、
// idを含むエラーを投げる（null を返すと、あとで分かりにくい例外になるため）。
export function getElement(id) {
  const element = document.getElementById(id);
  if (element === null) {
    throw new Error(`要素が見つかりません：${id}`);
  }
  return element;
}

// visible が true なら表示し、false なら隠す（Bootstrapの d-none）。
export function setVisible(element, visible) {
  element.classList.toggle("d-none", !visible);
}

// 画面に出すエラーメッセージを返す。ApiError でない例外は、
// 固定のメッセージにし、詳細を console.error に出す。
export function errorMessageOf(error) {
  if (error instanceof ApiError) {
    return error.message;
  }

  console.error(error);
  return "予期しないエラーが発生しました。ページを再読み込みして、もう一度お試しください";
}

function setFieldError(field, message) {
  getElement(field.messageId).textContent = message;
  for (const inputId of field.inputIds) {
    getElement(inputId).classList.add("is-invalid");
  }
}

function showFormMessage(formErrorId, message) {
  const formError = getElement(formErrorId);
  formError.textContent = message;
  setVisible(formError, true);
}

// fieldMap の項目のエラー表示と、フォームの上部のエラー（formErrorId）を消す。
export function clearFormErrors(fieldMap, formErrorId) {
  for (const field of Object.values(fieldMap)) {
    getElement(field.messageId).replaceChildren();
    for (const inputId of field.inputIds) {
      getElement(inputId).classList.remove("is-invalid");
    }
  }

  const formError = getElement(formErrorId);
  formError.replaceChildren();
  setVisible(formError, false);
}

// API のエラーを表示する。fields の項目は、fieldMap の項目の下に出し、
// それ以外は、フォームの上部（formErrorId）に出す。
export function showApiError(error, fieldMap, formErrorId) {
  clearFormErrors(fieldMap, formErrorId);

  if (
    error instanceof ApiError &&
    error.code === "validation_error" &&
    error.fields !== null
  ) {
    let hasUnexpectedField = Object.keys(error.fields).length === 0;
    for (const [fieldName, message] of Object.entries(error.fields)) {
      const field = Object.prototype.hasOwnProperty.call(fieldMap, fieldName)
        ? fieldMap[fieldName]
        : undefined;
      if (field === undefined) {
        hasUnexpectedField = true;
      } else {
        setFieldError(field, message);
      }
    }

    if (hasUnexpectedField) {
      showFormMessage(formErrorId, "入力内容に誤りがあります");
    }
    return;
  }

  showFormMessage(formErrorId, errorMessageOf(error));
}

// 送信中の表示。labels は { idle: 通常の文字, busy: 送信中の文字 } の形。
export function setSubmitting(button, submitting, labels) {
  button.disabled = submitting;
  button.textContent = submitting ? labels.busy : labels.idle;
}

// 表示のアニメーションの途中（show.bs.modal から shown.bs.modal まで）の
// モーダルの要素。Bootstrapは、表示の途中の hide() を、何もせずに無視する
// ため、閉じるとき（hideModal）に確かめる。Bootstrapの内部の値は使わず、
// イベントで記録する。
const showingModals = new Set();

// modal（モーダルの要素）が、表示のアニメーションの途中かを記録する。
// JavaScriptから閉じる（hideModal を使う）モーダルごとに、初期化のときに
// 1回だけ呼ぶ。
export function trackModalShowing(modal) {
  modal.addEventListener("show.bs.modal", () => {
    showingModals.add(modal);
  });
  modal.addEventListener("shown.bs.modal", () => {
    showingModals.delete(modal);
  });
}

// modal（モーダルの要素）を閉じる。表示のアニメーションの途中なら、表示が
// 終わったとき（shown.bs.modal）に閉じる。trackModalShowing を呼んでおいた
// モーダルにだけ使う。
export function hideModal(modal) {
  const instance = window.bootstrap.Modal.getOrCreateInstance(modal);

  if (showingModals.has(modal)) {
    modal.addEventListener(
      "shown.bs.modal",
      () => {
        instance.hide();
      },
      { once: true },
    );
    return;
  }
  instance.hide();
}
