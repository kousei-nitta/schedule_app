import { initSemesters } from "./semesters.js";
import { initSubjects } from "./subjects.js";

// 今後のモードの初期化も、ここに足す。
// semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
initSubjects();
initSemesters();
