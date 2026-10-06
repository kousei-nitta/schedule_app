const NETWORK_ERROR_MESSAGE =
  "サーバーに接続できませんでした。時間をおいて、もう一度お試しください";
const INVALID_RESPONSE_MESSAGE =
  "サーバーから想定外の応答がありました。時間をおいて、もう一度お試しください";

export class ApiError extends Error {
  constructor(status, code, message, fields = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

function isErrorResponse(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const error = value.error;
  if (error === null || typeof error !== "object" || Array.isArray(error)) {
    return false;
  }

  if (typeof error.code !== "string" || typeof error.message !== "string") {
    return false;
  }

  return (
    error.fields === undefined ||
    error.fields === null ||
    (typeof error.fields === "object" && !Array.isArray(error.fields))
  );
}

function invalidResponse(status) {
  return new ApiError(status, "invalid_response", INVALID_RESPONSE_MESSAGE);
}

export async function apiRequest(method, url, body) {
  const options = { method };

  if (body !== undefined) {
    // GETなど本文がない通信にはContent-Typeを付けず、APIの共通ルールに合わせる。
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new ApiError(0, "network_error", NETWORK_ERROR_MESSAGE);
  }

  if (response.ok) {
    if (response.status === 204) {
      return null;
    }

    try {
      return await response.json();
    } catch {
      throw invalidResponse(response.status);
    }
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw invalidResponse(response.status);
  }

  if (!isErrorResponse(payload)) {
    throw invalidResponse(response.status);
  }

  throw new ApiError(
    response.status,
    payload.error.code,
    payload.error.message,
    payload.error.fields ?? null,
  );
}
