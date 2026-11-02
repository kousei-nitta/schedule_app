// ログアウトのあとに、ログイン中の画面（取得済みのデータ）が見えない
// ようにする守り（docs/architecture/security.md の「ログアウト」）。
//
// 画面は Cache-Control: no-store だが、Safari は、HTTP のページでは、
// no-store でも、前の画面を戻る・進むのキャッシュ（bfcache）に残し、
// 「戻る」で、そのまま見せる（Task 025で、KomaのMacで見つけた）。
// また、Safari は、スワイプで戻るときに見せる「画面の写し」を、次の画面へ
// 移る直前に撮る。そのため、ブラウザによらず、次のようにする。
// 1. ログアウトのフォームを送る前に、画面を隠し、隠した画面が描かれて
//    から送る（写しに、ログイン中の画面が残らないように）
// 2. 画面を離れて、bfcache に入るときに、画面を隠す（戻った瞬間に、
//    データが見えないように）
// 3. bfcache から戻ったときに、隠したまま読み込み直す（ログアウトして
//    いれば、サーバーがログインの画面に移す。ログイン中なら、最新の
//    データになる）
import { getElement } from "./ui.js";

const LOGOUT_FORM_IDS = ["logout-form", "logout-all-form"];

function hidePage() {
  document.body.classList.add("d-none");
}

// event：ログアウトのフォームの submit のイベント
function hidePageThenSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  hidePage();
  // requestAnimationFrame を2回待つと、隠した画面が、1回描かれたあとに
  // なる。form.submit() は、submit のイベントを起こさない（繰り返さない）
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      form.submit();
    });
  });
}

export function initLogoutProtection() {
  for (const formId of LOGOUT_FORM_IDS) {
    getElement(formId).addEventListener("submit", hidePageThenSubmit);
  }

  window.addEventListener("pagehide", (event) => {
    if (event.persisted) {
      hidePage();
    }
  });

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      // 2. で隠れているはずだが、ブラウザによる違いに備えて、ここでも隠す
      hidePage();
      window.location.reload();
    }
  });
}
