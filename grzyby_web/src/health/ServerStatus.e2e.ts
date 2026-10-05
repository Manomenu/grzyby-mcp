// The page reaches the server through the same /api path the cluster uses; when it cannot, the
// visitor is told on top of the page, not only in the quiet line at its foot.
import { expect, test } from "@playwright/test";

test("the page shows that the server answers", async ({ page }) => {
    await page.goto("/");

    // exact: a substring match would also pass on "nie działa (…)".
    await expect(page.getByText("serwer: działa", { exact: true })).toBeVisible();
    await expect(page.getByText("Serwer teraz nie odpowiada", { exact: true })).toHaveCount(0);
});

test("a server that does not answer gets a banner on top", async ({ page }) => {
    await page.route("**/api/health", (route) => route.fulfill({ status: 503, json: { detail: "przerwa" } }));
    await page.goto("/");

    const banner = page.getByRole("alert");
    await expect(banner).toContainText("Serwer teraz nie odpowiada");
    const heading = await page.getByRole("heading", { name: "Gdzie na grzyby", exact: true }).boundingBox();
    const top = await banner.boundingBox();
    if (!heading || !top) throw new Error("the banner or the heading has no position");
    expect(top.y).toBeLessThan(heading.y);
});
