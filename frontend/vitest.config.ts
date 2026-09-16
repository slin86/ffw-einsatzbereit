import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.test.ts", "src/main.ts", "src/router.ts", "src/types.ts"],
      reporter: ["text", "text-summary"],
      thresholds: { lines: 95, branches: 90, functions: 95, statements: 95 },
    },
  },
});
