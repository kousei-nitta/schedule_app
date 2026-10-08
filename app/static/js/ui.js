import { ApiError } from "./api.js";

export function getElement(id) {
  return document.getElementById(id);
}

export function setVisible(element, visible) {
  element.classList.toggle("d-none", !visible);
}

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

export function setSubmitting(button, submitting, labels) {
  button.disabled = submitting;
  button.textContent = submitting ? labels.busy : labels.idle;
}
