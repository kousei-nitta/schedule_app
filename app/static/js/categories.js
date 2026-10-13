// カテゴリの対応表。DBの保存値（APIの category）から、画面に出す
// 表示名・アイコン・色のclassを引く。複数のモードで使うため、
// このファイルにまとめる（モードのファイル同士は、互いを import しない）。
// 色の値は、style.css の、className と同じ名前のclassに書く
// （JavaScriptでは、色の値を持たない）。

// 予定（Event）のカテゴリ。並びは、カレンダーの絞り込みの選択肢の並び。
// 課題・タスク（Task）のカテゴリは、課題・タスクの画面を作るタスクで足す。
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

// 予定のカテゴリの保存値に対応する項目を返す。対応表にない値は、
// DBに入らない想定だが、画面が止まらないように、保存値をそのまま
// 表示名にし、アイコンと色のclassを付けない。
export function eventCategoryOf(category) {
  if (Object.prototype.hasOwnProperty.call(EVENT_CATEGORIES, category)) {
    return EVENT_CATEGORIES[category];
  }
  return { label: category, icon: "", className: "" };
}
