// 日付の補助処理。複数のモードで使うため、このファイルにまとめる。
// 日付は、APIと同じ「YYYY-MM-DD」の文字列で受け渡す。

// Date.getDay()の並び（0=日曜〜6=土曜）の曜日の表示。授業の曜日
// （0=月曜〜6=日曜。DB・APIと同じ）とは並びが違うため、混ぜて使わない。
const WEEKDAY_LABELS = ["日", "月", "火", "水", "木", "金", "土"];

export function localDateString(date = new Date()) {
  // toISOString()はUTC日付に変換するため、ローカル日付が前日になることがある。
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatJapaneseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return `${year}年${month}月${day}日`;
}

export function formatJapaneseDateWithWeekday(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  // new Date("YYYY-MM-DD")はUTCの0時として読まれ、タイムゾーンによっては
  // 前の日の曜日になる。年・月・日を分けて渡し、ローカルの日付として作る
  // （月は0始まり）。
  const weekday = new Date(year, month - 1, day).getDay();
  return `${formatJapaneseDate(dateString)}（${WEEKDAY_LABELS[weekday]}）`;
}
