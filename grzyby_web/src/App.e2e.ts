// The pages' look on both screens: photos beside the panel where there is room, none on a phone,
// and never over the text — on the front page and on the search alike.
import { expect, test } from "@playwright/test";

const PAGES = [
    { path: "/", panel: "the instructions' tabs" },
    { path: "/szukaj", panel: "the search form" },
] as const;

for (const { path, panel } of PAGES) {
    test(`the photos sit beside ${panel} on a laptop and are left out on a phone`, async ({ page }, testInfo) => {
        await page.goto(path);
        const photos = page.locator(".side-photo");
        const content = path === "/" ? page.getByRole("tablist") : page.locator("form");
        await expect(content).toBeVisible();

        await expect(photos).toHaveCount(2);
        if (testInfo.project.name === "phone") {
            for (const photo of await photos.all()) await expect(photo).toBeHidden();
            return;
        }
        const column = await content.boundingBox();
        if (!column) throw new Error(`${panel} has no position`);
        for (const photo of await photos.all()) {
            await expect(photo).toBeVisible();
            const box = await photo.boundingBox();
            if (!box) throw new Error("a photo has no position");
            expect(box.x + box.width <= column.x || box.x >= column.x + column.width).toBe(true);
        }
    });
}

test("the photos themselves are served", async ({ page }) => {
    // A wrong path would leave an empty box where a photo should be.
    for (const src of ["/img/las.webp", "/img/borowik.webp"]) {
        const response = await page.request.get(src);
        expect(response.ok()).toBe(true);
        expect(response.headers()["content-type"]).toContain("image/webp");
    }
});
