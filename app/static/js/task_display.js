import { taskCategoryOf } from "./categories.js";
import { formatJapaneseDateTime } from "./dates.js";

// 課題・タスクの表示の共通処理。課題・タスクモード（tasks.js）と、
// カレンダーの「直近の締切」欄（calendar.js）で使う（モードのファイル同士は、
// 互いを import しないため、このファイルにまとめる）。APIは扱わない。

// 課題・タスクを表す文字列（例：「レポート第1回」（締切 2026年10月20日（火）
// 23:59））。読み上げの名前（aria-label）と、削除の確認の文に使う。同じ
// タイトルの課題・タスクを、締切で区別できるようにする。
export function taskLabel(task) {
  return (
    `「${task.title}」` +
    `（締切 ${formatJapaneseDateTime(task.due_datetime)}）`
  );
}

// 期限切れかを返す。未完了で、締切日時が now（今の日時。YYYY-MM-DDTHH:MM。
// dates.js の localDateTimeString）より前なら、期限切れ。締切日時と同じ分は、
// まだ期限切れではない。YYYY-MM-DDTHH:MMは桁が固定されているため、文字列の
// 大小で前後を比べられる。
export function isTaskOverdue(task, now) {
  return !task.is_completed && task.due_datetime < now;
}

// 期限切れの印（赤い「期限切れ」）を作る。
export function createOverdueBadge() {
  const badge = document.createElement("span");
  badge.className = "badge text-bg-danger ms-1";
  badge.textContent = "期限切れ";
  return badge;
}

// 課題名の表示（カテゴリのアイコンと、課題名）を作る。アイコンは読み上げず、
// 代わりに、カテゴリの表示名（「課題：」など）を、見えない文字で添える。
export function createTaskTitle(task) {
  const category = taskCategoryOf(task.category);
  const title = document.createElement("div");

  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;

  const categoryName = document.createElement("span");
  categoryName.className = "visually-hidden";
  categoryName.textContent = `${category.label}：`;

  title.append(icon, categoryName, task.title);
  return title;
}
