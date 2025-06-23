import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

export default [
  // Use compat to include Next.js and TypeScript-specific rules
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  
  // Main configuration
  {
    files: ["**/*.{js,jsx,ts,tsx}"], // Lint JavaScript and TypeScript files
    plugins: {
      jest: {}, // Add the Jest plugin
    },
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        jest: "readonly", // Enable Jest globals
      },
    },
    rules: {
      // Jest-specific rules
      "jest/no-disabled-tests": "warn",
      "jest/no-focused-tests": "error",
      "jest/no-identical-title": "error",

      // Other rules
      "@typescript-eslint/explicit-function-return-type": "warn",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/consistent-type-imports": "error",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-debugger": "warn",
    },
  },

  // Ignore certain files and directories
  {
    ignores: [
      ".build/",
      "dist/",
      "out/",
      ".next/",
      "coverage/",
      "node_modules/",
      ".vscode/",
      ".idea/",
      "*.log",
      "*.tmp",
      "*.cache",
      "**/.ipynb_checkpoints/",
      "public/",
      "*.d.ts",
      ".eslintcache",
      ".env",
      ".env.*",
    ],
  },
];