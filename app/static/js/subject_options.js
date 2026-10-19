import { apiRequest } from "./api.js";
import { chooseCurrentSemester } from "./current_semester.js";
import { localDateString } from "./dates.js";

// 今の学期の授業から選ぶ欄（プルダウン）の共通処理。課題の対象授業
// （tasks.js）と、カレンダーから追加する単発の授業（event_forms.js）で使う
// （モードのファイル同士は、互いを import しないため、このファイルに
// まとめる）。

// 授業を取得している間に、欄の下に出す説明。
export const SUBJECTS_LOADING_NOTE = "授業を読み込み中…";
const SUBJECT_PLACEHOLDER = "選択してください";

// 今の学期（授業モードで最初に選ばれる学期と同じ規則。current_semester.js）
// と、その学期の授業の一覧（授業の一覧APIの並び。曜日・開始時刻の順）を
// 取得する。学期が0件なら、semester は null、subjects は空の配列。
export async function fetchCurrentSubjects() {
  const semesters = await apiRequest("GET", "/api/semesters");
  const semester = chooseCurrentSemester(semesters, localDateString());
  if (semester === null) {
    return { semester: null, subjects: [] };
  }
  const subjects = await apiRequest(
    "GET",
    `/api/subjects?semester_id=${semester.id}`,
  );
  return { semester, subjects };
}

// 授業の欄の下に出す説明。semester・subjects は、fetchCurrentSubjects の
// 結果。
export function currentSubjectsNote(semester, subjects) {
  if (semester === null) {
    return (
      "学期が登録されていません。" +
      "授業モードで、学期と授業を登録してください"
    );
  }
  if (subjects.length === 0) {
    return (
      `${semester.name}には、授業が登録されていません。` +
      "授業モードで、授業を登録してください"
    );
  }
  return `${semester.name}の授業から選びます`;
}

// 授業のプルダウン（select）の選択肢を作る。先頭は「選択してください」
// （値は空）。extraSubject は、subjects にない授業（課題の編集で、今の
// 対象授業が、今の学期の授業にないとき。{ id, subject_name }）で、先頭の
// 次に足す。ないときは null。
export function renderSubjectOptions(select, subjects, extraSubject = null) {
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = SUBJECT_PLACEHOLDER;
  const options = [placeholder];
  const items =
    extraSubject === null ? subjects : [extraSubject, ...subjects];
  for (const subject of items) {
    const option = document.createElement("option");
    option.value = String(subject.id);
    option.textContent = subject.subject_name;
    options.push(option);
  }
  select.replaceChildren(...options);
}
