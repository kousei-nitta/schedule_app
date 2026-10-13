import { initCalendar } from "./calendar.js";
import { initClosures } from "./closures.js";
import { initSemesters } from "./semesters.js";
import { initSubjects } from "./subjects.js";

// 今後のモードの初期化も、ここに足す。
// semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
initSubjects();
initClosures();
initSemesters();
// カレンダーは、ほかのモードとイベントでつながらない。予期しない例外で、
// ほかのモードの初期化が止まらないように、最後に初期化する。
initCalendar();
