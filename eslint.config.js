// ESLint（JavaScriptの書き方の検査）の設定。
// docs/development/testing.md の「検査の道具」。
import js from "@eslint/js";
import globals from "globals";

const appFiles = ["app/static/js/**/*.js"];

// HTMLとして解釈される書き方（利用者の入力が入ると、スクリプトとして
// 動きうる。XSS）。文字は textContent で入れる（CLAUDE.md）
const htmlMessage =
  "HTMLとして解釈される書き方は使わない。文字は textContent で入れる";
// 見た目を、スクリプトで直接変える書き方。見た目は CSS の class で変える
// （CLAUDE.md。style 属性は、CSPでも止まりうる）
const styleMessage =
  "style を直接変えない。見た目は CSS の class（style.css）で変える";

export default [
  // 推奨の規則（定義していない変数、使わない変数など）
  { files: appFiles, ...js.configs.recommended },
  {
    files: appFiles,
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
    },
    rules: {
      "no-var": "error",
      "prefer-const": "error",
      eqeqeq: "error",
      "max-len": ["error", { code: 80 }],
      // 中に " を含む文字列だけ、単引用符を許す
      quotes: ["error", "double", { avoidEscape: true }],

      // ここから、セキュリティのための禁止（CLAUDE.md の「使わない」を、
      // 機械で確かめる。docs/architecture/security.md）
      // 文字列を、コードとして実行する書き方（eval、setTimeout("…")、
      // new Function("…")）
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-restricted-properties": [
        "error",
        { property: "innerHTML", message: htmlMessage },
        { property: "outerHTML", message: htmlMessage },
        { property: "insertAdjacentHTML", message: htmlMessage },
        { object: "document", property: "write", message: htmlMessage },
        { object: "document", property: "writeln", message: htmlMessage },
        { property: "style", message: styleMessage },
      ],
      "no-restricted-syntax": [
        "error",
        {
          // setAttribute("onclick", …) など。イベントは addEventListener
          selector:
            "CallExpression[callee.property.name='setAttribute']" +
            "[arguments.0.value=/^on/i]",
          message: "on… の属性は使わない。addEventListener を使う",
        },
        {
          selector:
            "CallExpression[callee.property.name='setAttribute']" +
            "[arguments.0.value=/^style$/i]",
          message: styleMessage,
        },
      ],
    },
  },
];
