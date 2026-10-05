// The page's look on both screens: photos beside the instructions where there is room, none on a
// phone, and never over the text.
import { expect, test } from "@playwright/test";

test("the photos sit beside the instructions on a laptop and are left out on a phone", async ({ page }, testInfo) => {
    await page.goto("/");
    const photos = page.locator(".side-photo");
    const tabs = page.getByRole("tablist");
    await expect(tabs).toBeVisible();

    await expect(photos).toHaveCount(2);
    if (testInfo.project.name === "phone") {
        for (const photo of await photos.all()) await expect(photo).toBeHidden();
        return;
    }
    const column = await tabs.boundingBox();
    if (!column) throw new Error("the tabs have no position");
    for (const photo of await photos.all()) {
        await expect(photo).toBeVisible();
        const box = await photo.boundingBox();
        if (!box) throw new Error("a photo has no position");
        expect(box.x + box.width <= column.x || box.x >= column.x + column.width).toBe(true);
    }
    // The photos themselves are served (a wrong path would leave an empty box).
    for (const src of ["/img/las.webp", "/img/borowik.webp"]) {
        const response = await page.request.get(src);
        expect(response.ok()).toBe(true);
        expect(response.headers()["content-type"]).toContain("image/webp");
    }
});
