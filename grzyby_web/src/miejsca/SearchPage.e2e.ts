// The search without a chatbot, the way a visitor uses it: from the front page's button, a
// question in the form, the map the chatbots show (the real widget from the server), a route,
// full screen, and the link that asks the same again. The answer itself is mapa.answer.json —
// the search behind it has its own tests; here the outside world would only make it slow.
import { readFileSync } from "node:fs";

import { expect, type Page, test } from "@playwright/test";

const answer = JSON.parse(readFileSync(new URL("./mapa.answer.json", import.meta.url), "utf8")) as {
    miejsca: { nazwa: string; trasa: string }[];
};

/** Answers every search with the fixture and records what was asked. */
async function standIn(page: Page): Promise<URL[]> {
    const asked: URL[] = [];
    await page.route("**/api/miejsca?*", async (route) => {
        asked.push(new URL(route.request().url()));
        await route.fulfill({ json: answer });
    });
    return asked;
}

test("a visitor finds spots without a chatbot", async ({ page }) => {
    const asked = await standIn(page);
    await page.goto("/");
    await page.getByRole("link", { name: "Szukaj bez chatbota →", exact: true }).click();
    await expect(page).toHaveURL(/\/szukaj$/);

    // Nothing else on the page: the form, and the map once there is an answer.
    await expect(page.getByRole("heading", { name: "Jak podłączyć" })).toHaveCount(0);
    await page.getByLabel("Miejscowość", { exact: true }).fill("Suwałki");
    // The chip itself, as a finger taps it; its checkbox is hidden behind the label.
    await page.getByText("kurka", { exact: true }).click();
    await expect(page.getByRole("checkbox", { name: "kurka", exact: true })).toBeChecked();
    await page.getByRole("button", { name: "Szukaj", exact: true }).click();

    await expect.poll(() => asked.length).toBe(1);
    const question = asked[0]?.searchParams;
    expect(question?.get("miejscowosc")).toBe("Suwałki");
    expect(question?.getAll("grzyby")).toEqual(["borowik", "kurka"]);
    // The question is in the address: the page can be bookmarked or sent.
    await expect(page).toHaveURL(/\/szukaj\?miejscowosc=Suwa%C5%82ki&grzyby=borowik&grzyby=kurka/);

    const widget = page.frameLocator('iframe[title="Mapa miejsc na grzyby"]');
    await expect(widget.locator(".spot-number")).toHaveCount(answer.miejsca.length);
    // The map is brought into view, also on a phone where it starts below the screen.
    await expect(page.locator('iframe[title="Mapa miejsc na grzyby"]')).toBeInViewport();

    // A route opens in a new tab: the page is the widget's host and opens it.
    const tab = page.context().waitForEvent("page");
    await widget.locator("#list").getByRole("link", { name: "trasa w Google Maps" }).first().click();
    expect((await tab).url()).toContain("google.com/maps");

    // Full screen: the map takes the whole window, and gives it back.
    await widget.getByRole("button", { name: "Pełny ekran", exact: true }).click();
    const frame = page.locator('iframe[title="Mapa miejsc na grzyby"]');
    await expect.poll(async () => (await frame.boundingBox())?.height).toBe(page.viewportSize()?.height);
    await widget.getByRole("button", { name: "Zamknij pełny ekran", exact: true }).click();
    await expect.poll(async () => (await frame.boundingBox())?.y).toBeGreaterThan(0);
});

test("a link to a search asks it again on opening", async ({ page }) => {
    const asked = await standIn(page);
    await page.goto("/szukaj?miejscowosc=Che%C5%82m&grzyby=rydz&promien_km=5&ile_miejsc=10&za_ile_dni=1");

    await expect(page.frameLocator('iframe[title="Mapa miejsc na grzyby"]').locator(".spot-number").first()).toBeVisible();
    expect(asked[0]?.search).toBe("?miejscowosc=Che%C5%82m&grzyby=rydz&promien_km=5&ile_miejsc=10&za_ile_dni=1");
    await expect(page.getByLabel("Miejscowość", { exact: true })).toHaveValue("Chełm");
    await expect(page.getByRole("checkbox", { name: "rydz", exact: true })).toBeChecked();
});

test("a failed search says why, in the visitor's language", async ({ page }) => {
    await page.route("**/api/miejsca?*", (route) => route.fulfill({ status: 503, json: { detail: "Serwer jest przeciążony" } }));
    await page.goto("/szukaj?miejscowosc=Suwa%C5%82ki&grzyby=borowik");

    await expect(page.getByRole("alert")).toContainText("Serwer jest przeciążony");
});
