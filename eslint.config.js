// ESLint（JavaScriptの書き方の検査）の設定。
// docs/development/testing.md の「検査の道具」。
import js from "@eslint/js";
import globals from "globals";

const appFiles = ["app/static/js/**/*.js"];

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
    },
  },
];
