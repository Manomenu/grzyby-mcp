// What a visitor relies on: a tab per chatbot, each with the address or command to copy.
import { expect, test } from "@playwright/test";

test("the page shows how to add the server to each chatbot", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Gdzie na grzyby", exact: true })).toBeVisible();

    // Claude first: the address and a button to copy it.
    await expect(page.getByRole("tab", { name: "Claude (web i aplikacja)", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText("https://grzyby.gugnowski.com/mcp", { exact: true })).toBeVisible();
    const copy = page.getByRole("button", { name: "Kopiuj adres dla Claude", exact: true });
    await expect(copy).toBeVisible();
    // The copy button stays inside the page, also beside a long address on a phone.
    const button = await copy.boundingBox();
    if (!button) throw new Error("the copy button has no position");
    expect(button.x + button.width).toBeLessThanOrEqual(page.viewportSize()?.width ?? 0);

    await page.getByRole("tab", { name: "ChatGPT", exact: true }).click();
    await expect(page.getByText("Developer mode", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Kopiuj adres dla ChatGPT", exact: true })).toBeVisible();

    await page.getByRole("tab", { name: "Claude Code", exact: true }).click();
    await expect(page.getByText("claude mcp add --transport http grzyby https://grzyby.gugnowski.com/mcp", { exact: true })).toBeVisible();
});
