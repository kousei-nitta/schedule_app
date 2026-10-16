// 今の学期を選ぶ規則。複数のモードで使うため、このファイルにまとめる
// （授業モードの学期の初期選択と、課題の対象授業の選択肢）。
// DOMとAPIは扱わない。

// semesters は、学期のAPIの一覧の並び（開始日の新しい順。タブの並び）の
// 配列。today は「YYYY-MM-DD」。学期が0件なら null を返す。
// 1. 今日を含む学期（複数あれば、並びで先の学期）
// 2. なければ、今日より後に始まる学期のうち、最も早く始まるもの
// 3. なければ、最も最近終わった学期（終了日が最も新しいもの）
export function chooseCurrentSemester(semesters, today) {
  // YYYY-MM-DDは桁が固定されているため、文字列の大小が日付の前後と一致する。
  const current = semesters.find(
    (semester) => semester.start_date <= today && today <= semester.end_date,
  );
  if (current !== undefined) {
    return current;
  }

  let next = null;
  for (const semester of semesters) {
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
  for (const semester of semesters) {
    if (
      mostRecent === null ||
      semester.end_date > mostRecent.end_date
    ) {
      mostRecent = semester;
    }
  }
  return mostRecent;
}
