import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import pluginImport from "eslint-plugin-import";
import globals from "globals";

export default [
  js.configs.recommended,
  eslintConfigPrettier,
  {
    files: ["src/**/*.js"],
    ignores: ["src/**/*.test.js", "src/**/__mocks__/**"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2022
      }
    },
    plugins: {
      import: pluginImport
    },
    rules: {
      "no-console": "warn",
      "no-debugger": "error",
      "import/order": [
        "warn",
        {
          "alphabetize": { "order": "asc", "caseInsensitive": true },
          "groups": ["builtin", "external", "internal", ["parent", "sibling", "index"]],
          "newlines-between": "always"
        }
      ]
    }
  }
];
