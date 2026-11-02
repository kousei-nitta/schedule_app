// 戻る・進むのキャッシュ（bfcache）から、ログイン中の画面が戻ったときの
// 守り（docs/architecture/security.md の「ログアウト」）。
//
// 画面は Cache-Control: no-store だが、Safari は、HTTP のページでは、
// no-store でも前の画面を bfcache に残し、「戻る」で、そのまま見せる
// （ログアウトのあとでも、取得済みのデータが見える。Task 025で、
// KomaのMacで見つけた）。そのため、ブラウザによらず、次のようにする。
// - 画面を離れて、bfcache に入るときに、画面を隠す（戻った瞬間に、
//   データが見えないように）
// - bfcache から戻ったときに、読み込み直す（ログアウトしていれば、
//   サーバーがログインの画面に移す。ログイン中なら、最新のデータになる）
export function initPageRestore() {
  window.addEventListener("pagehide", (event) => {
    if (event.persisted) {
      document.body.classList.add("d-none");
    }
  });

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      window.location.reload();
    }
  });
}
