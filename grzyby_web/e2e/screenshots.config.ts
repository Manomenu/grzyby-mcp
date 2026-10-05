// The README's pictures of the map widget (src/**/*.shots.ts) — `just screenshots`
// (scripts/.internal/screenshots.sh). Real answers of the production server, so no local server
// or database: the pictures land in docs/img/, everything else in .artifacts/.
import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "../src",
    testMatch: "**/*.shots.ts",
    workers: 1,
    timeout: 180_000,
    outputDir: "../../.artifacts/screenshots",
    reporter: "list",
    use: { locale: "pl-PL" },
});
