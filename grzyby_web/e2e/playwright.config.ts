// End-to-end tests: a real browser against the real server and database.
// `just e2e` (scripts/.internal/e2e.sh) prepares an empty database and runs them; CI does the
// same. They start their own server and web app on 6211/3211, so the ones you run by hand on
// 6210/3210 and your local data stay untouched.
import { defineConfig, devices } from "@playwright/test";

const SERVER_PORT = 6211;
const WEB_PORT = 3211;

export default defineConfig({
    // The tests live next to the code they check (src/App.e2e.ts by App.tsx).
    testDir: "../src",
    testMatch: "**/*.e2e.ts",
    // One database for the run, so tests that create data would see each other's in parallel.
    workers: 1,
    // On CI a flaky failure is retried once; locally a failure shows at once.
    retries: process.env["CI"] ? 1 : 0,
    // Results (screenshots, traces, the HTML report) go where every generated file of the repo
    // goes: .artifacts/, outside git and the images.
    outputDir: "../../.artifacts/e2e/test-results",
    reporter: process.env["CI"] ? [["list"], ["html", { open: "never", outputFolder: "../../.artifacts/e2e/report" }]] : "list",
    timeout: 60_000,
    use: {
        baseURL: `http://localhost:${WEB_PORT}`,
        locale: "pl-PL",
        // What happened, step by step, when a test fails: npx playwright show-trace <file>.
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
    },
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
    webServer: [
        {
            command: "uv run python -m grzyby_server",
            cwd: "../../grzyby_server",
            url: `http://localhost:${SERVER_PORT}/health`,
            env: {
                PORT: String(SERVER_PORT),
                DATABASE_URL: process.env["E2E_DATABASE_URL"] ?? "postgresql://grzyby:grzyby@localhost:5443/grzyby_e2e",
            },
            reuseExistingServer: false,
            timeout: 60_000,
        },
        {
            command: `pnpm exec vite --port ${WEB_PORT} --strictPort`,
            cwd: "..",
            url: `http://localhost:${WEB_PORT}`,
            env: { API_PROXY_TARGET: `http://localhost:${SERVER_PORT}` },
            reuseExistingServer: false,
            timeout: 60_000,
        },
    ],
});
