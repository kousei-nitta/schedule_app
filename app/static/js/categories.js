// カテゴリの対応表。DBの保存値（APIの category）から、画面に出す
// 表示名・アイコン・色のclassを引く。複数のモードで使うため、
// このファイルにまとめる（モードのファイル同士は、互いを import しない）。
// 色の値は、style.css の、className と同じ名前のclassに書く
// （JavaScriptでは、色の値を持たない）。

// 予定（Event）のカテゴリ。並びは、app/categories.py の EVENT_CATEGORIES と
// 同じ（カレンダーの絞り込みの選択肢の並びは、calendar.js で決める）。
export const EVENT_CATEGORIES = {
  class: {
    label: "授業",
    icon: "📖",
    className: "category-class",
  },
  part_time: {
    label: "アルバイト",
    icon: "💼",
    className: "category-part-time",
  },
  other: {
    label: "その他",
    icon: "⭐",
    className: "category-other",
  },
};

// 課題・タスク（Task）のカテゴリ。その他（締切のみ）は、予定のその他と
// 同じ色・アイコンを使う。
export const TASK_CATEGORIES = {
  assignment: {
    label: "課題",
    icon: "✅",
    className: "category-assignment",
  },
  other: {
    label: "その他",
    icon: "⭐",
    className: "category-other",
  },
};

// 対応表（categories）から、保存値（category）に対応する項目を返す。
// 対応表にない値は、DBに入らない想定だが、画面が止まらないように、
// 保存値をそのまま表示名にし、アイコンと色のclassを付けない。
function categoryOf(categories, category) {
  if (Object.prototype.hasOwnProperty.call(categories, category)) {
    return categories[category];
  }
  return { label: category, icon: "", className: "" };
}

// 予定のカテゴリの保存値に対応する項目を返す。
export function eventCategoryOf(category) {
  return categoryOf(EVENT_CATEGORIES, category);
}

// 課題・タスクのカテゴリの保存値に対応する項目を返す。
export function taskCategoryOf(category) {
  return categoryOf(TASK_CATEGORIES, category);
}
