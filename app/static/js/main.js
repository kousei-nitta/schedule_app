import { initCalendar } from "./calendar.js";
import { initClosures } from "./closures.js";
import { initLogoutProtection } from "./logout_protection.js";
import { initSemesters } from "./semesters.js";
import { initSubjects } from "./subjects.js";
import { initTasks } from "./tasks.js";

// ログアウトのあとに、前の画面が見えないようにする守りは、ほかの
// 初期化で例外が起きても効くように、最初に登録する。
initLogoutProtection();
// 今後のモードの初期化も、ここに足す。
// semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
initSubjects();
initClosures();
initSemesters();
// 課題・タスクとカレンダーは、カレンダーの締切の詳細パネルの「編集」
// 「削除」（task-edit-requested・task-delete-requested）と、編集・削除の
// 結果（task-changed）で、イベントでつながる。どちらも、利用者の操作の
// あとに発行するため、初期化の順序によらない。
initTasks();
// カレンダーは、予期しない例外で、ほかのモードの初期化が止まらないように、
// 最後に初期化する。
initCalendar();
