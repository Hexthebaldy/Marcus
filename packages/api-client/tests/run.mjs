import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

// Compile the real client into a disposable CommonJS directory; no test dependencies.
const root = fileURLToPath(new URL("../", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "marcus-client-test-"));
try {
  const compile = spawnSync(
    process.execPath,
    [
      fileURLToPath(
        new URL("../../../node_modules/typescript/bin/tsc", import.meta.url),
      ),
      "src/index.ts",
      "--outDir",
      output,
      "--module",
      "commonjs",
      "--target",
      "ES2022",
      "--lib",
      "ES2022,DOM",
      "--strict",
      "--skipLibCheck",
    ],
    { cwd: root, stdio: "inherit" },
  );
  if (compile.status !== 0) process.exitCode = compile.status ?? 1;
  else {
    const tests = spawnSync(
      process.execPath,
      ["--test", "tests/client.test.cjs"],
      {
        cwd: root,
        stdio: "inherit",
        env: { ...process.env, MARCUS_TEST_CLIENT: join(output, "index.js") },
      },
    );
    process.exitCode = tests.status ?? 1;
  }
} finally {
  rmSync(output, { recursive: true, force: true });
}
