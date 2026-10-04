// The map widget (grzyby_server/grzyby_server/miejsca/mapa.html) the way a chatbot shows it —
// the one check that runs its JavaScript. Without it a typo there passes every other test and
// shows up as an empty map in Claude, after a deploy (docs/mcp-apps.md).
//
// Like the host: the widget comes from the real server over MCP (tools/list → resources/read),
// is served from an origin of its own under the CSP built from its own metadata (`_meta.ui.csp`,
// the rule in the MCP Apps spec), inside a sandbox without popups, and gets the tool result over
// postMessage from a stand-in host that records what the widget asks of it.
//
// The result is mapa.answer.json: a real answer of the server's search over a handful of made-up
// stands, the best of them a big pine forest under spot 1. Any valid answer works;
// tests/miejsca/test_model.py keeps it valid against the Answer model. Runs on the laptop and the
// phone project alike; the widget takes the page's width, as in a chat.
import { readFileSync } from "node:fs";

import { type APIRequestContext, expect, type FrameLocator, test } from "@playwright/test";

// The server playwright.config.ts starts for the run.
const MCP = "http://localhost:6211/mcp";
const HOST = "https://host.test/";
const WIDGET = "https://widget.test/mapa.html";

interface Answer {
    miejsca: { nazwa: string; trasa: string }[];
}
interface HostRecord {
    links: string[];
    displayModes: string[];
}
interface Csp {
    resourceDomains?: string[];
    connectDomains?: string[];
}

/** The whole dashed search circle is on the map, and fills most of it. */
async function circleFillsTheMap(widget: FrameLocator): Promise<boolean> {
    const map = await widget.locator("#map").boundingBox();
    const circle = await widget.locator("path.search-radius").boundingBox();
    if (!map || !circle) return false;
    const inside =
        circle.x >= map.x - 1 &&
        circle.y >= map.y - 1 &&
        circle.x + circle.width <= map.x + map.width + 1 &&
        circle.y + circle.height <= map.y + map.height + 1;
    return inside && Math.max(circle.width / map.width, circle.height / map.height) >= 0.75;
}

const answer = JSON.parse(readFileSync(new URL("./mapa.answer.json", import.meta.url), "utf8")) as Answer;

async function rpc<T>(request: APIRequestContext, method: string, params: object = {}): Promise<T> {
    const response = await request.post(MCP, {
        headers: { accept: "application/json, text/event-stream" },
        data: { jsonrpc: "2.0", id: 1, method, params },
    });
    expect(response.ok()).toBe(true);
    return ((await response.json()) as { result: T }).result;
}

/** The widget's HTML and its CSP, fetched the way a host does. */
async function fetchWidget(request: APIRequestContext): Promise<{ html: string; csp: string }> {
    const { tools } = await rpc<{ tools: { name: string; _meta: { ui: { resourceUri: string } } }[] }>(request, "tools/list");
    const tool = tools.find((t) => t.name === "gdzie_na_grzyby");
    if (!tool) throw new Error("the server lists no gdzie_na_grzyby");
    const { contents } = await rpc<{ contents: { text: string; mimeType: string; _meta?: { ui?: { csp?: Csp } } }[] }>(
        request,
        "resources/read",
        { uri: tool._meta.ui.resourceUri },
    );
    const [resource] = contents;
    if (!resource) throw new Error("the widget resource is empty");
    expect(resource.mimeType).toBe("text/html;profile=mcp-app");
    return { html: resource.text, csp: hostCsp(resource._meta?.ui?.csp ?? {}) };
}

/** The spec's "CSP Construction from Metadata": nothing but what the widget declared. */
function hostCsp({ resourceDomains = [], connectDomains = [] }: Csp): string {
    const resources = resourceDomains.join(" ");
    return [
        "default-src 'none'",
        `script-src 'self' 'unsafe-inline' ${resources}`,
        `style-src 'self' 'unsafe-inline' ${resources}`,
        `img-src 'self' data: ${resources}`,
        `font-src 'self' ${resources}`,
        `media-src 'self' data: ${resources}`,
        `connect-src 'self' ${connectDomains.join(" ")}`,
        "frame-src 'none'",
        "object-src 'none'",
    ].join("; ");
}

// The stand-in host: answers ui/initialize offering full screen, sends the tool result once the
// widget is ready, and records the links and display modes it is asked for.
const hostPage = (result: Answer) => `<!doctype html>
<html><head><meta charset="utf-8" /></head><body style="margin:0">
<iframe id="widget" src="${WIDGET}" sandbox="allow-scripts allow-same-origin" style="width:100%;height:860px;border:0"></iframe>
<script>
const result = ${JSON.stringify({ content: [{ type: "text", text: "…" }], structuredContent: result })};
const widget = document.getElementById("widget");
window.host = { links: [], displayModes: [] };
const reply = (id, value) => widget.contentWindow.postMessage({ jsonrpc: "2.0", id, result: value }, "*");
window.addEventListener("message", (event) => {
    const m = event.data;
    if (!m || m.jsonrpc !== "2.0" || !m.method) return;
    if (m.method === "ui/initialize") {
        reply(m.id, {
            protocolVersion: "2026-01-26",
            hostInfo: { name: "e2e-host", version: "0" },
            hostCapabilities: { openLinks: {} },
            hostContext: { theme: "light", displayMode: "inline", availableDisplayModes: ["inline", "fullscreen"] },
        });
    } else if (m.method === "ui/notifications/initialized") {
        widget.contentWindow.postMessage({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: result }, "*");
    } else if (m.method === "ui/open-link") {
        window.host.links.push(m.params.url);
        reply(m.id, {});
    } else if (m.method === "ui/request-display-mode") {
        window.host.displayModes.push(m.params.mode);
        reply(m.id, { mode: m.params.mode });
    } else if (m.id !== undefined) {
        reply(m.id, {});
    }
});
</script>
</body></html>`;

test("the map widget draws the answer under the host's CSP and talks to the host", async ({ page, request }) => {
    const { html, csp } = await fetchWidget(request);
    await page.route(HOST, (route) => route.fulfill({ contentType: "text/html; charset=utf-8", body: hostPage(answer) }));
    await page.route(WIDGET, (route) =>
        route.fulfill({ contentType: "text/html; charset=utf-8", headers: { "Content-Security-Policy": csp }, body: html }),
    );
    // Every error in any frame — a CSP violation, a script that failed — fails the test. Map tiles
    // are left out: an OpenStreetMap hiccup is not a bug of ours.
    const errors: string[] = [];
    page.on("console", (message) => {
        if (message.type() === "error" && !message.location().url.includes("tile.openstreetmap.org")) errors.push(message.text());
    });
    page.on("pageerror", (error) => errors.push(error.message));
    const host = () => page.evaluate(() => (window as unknown as { host: HostRecord }).host);

    await page.goto(HOST);
    const widget = page.frameLocator("#widget");

    // A numbered marker and a line of the list for every spot.
    await expect(widget.locator(".spot-number")).toHaveCount(answer.miejsca.length);
    for (const spot of answer.miejsca) await expect(widget.locator("#list").getByText(spot.nazwa, { exact: true })).toBeVisible();

    // The first view is the whole search circle — also after the host resizes the widget, as it
    // may when the content arrives or on a narrower screen.
    await expect.poll(() => circleFillsTheMap(widget)).toBe(true);
    const resize = (width: string) =>
        page.evaluate((w) => {
            const frame = document.getElementById("widget");
            if (frame) frame.style.width = w;
        }, width);
    await resize("320px");
    await expect.poll(() => circleFillsTheMap(widget)).toBe(true);
    await resize("100%");
    await expect.poll(() => circleFillsTheMap(widget)).toBe(true);

    // Map modes: the legend follows the pressed button. On a phone the legend starts folded, so
    // as not to cover the map — open it first.
    if ((await widget.locator("details.legend").getAttribute("open")) === null) {
        await widget.getByText("Legenda", { exact: true }).click();
    }
    await expect(widget.getByText("bardzo dobry", { exact: true })).toBeVisible();
    const trees = widget.getByRole("button", { name: "Drzewa", exact: true });
    await trees.click();
    await expect(trees).toHaveAttribute("aria-pressed", "true");
    await expect(widget.getByText("sosna", { exact: true })).toBeVisible();

    // A click on the forest explains its score. Spot 1 stands in the middle of the big pine
    // forest; just below its marker is forest, not the marker.
    const first = await widget.locator(".spot-number").first().boundingBox();
    if (!first) throw new Error("spot 1 has no position");
    await page.mouse.click(first.x + first.width / 2, first.y + first.height + 12);
    await expect(widget.locator(".popup")).toContainText("Las sosnowy — bardzo dobry");
    await expect(widget.locator(".popup")).toContainText("Siedlisko: BMŚW");

    // Routes open through the host: the sandbox allows no new windows.
    await widget.locator("#list").getByRole("link", { name: "trasa w Google Maps" }).first().click();
    await expect.poll(async () => (await host()).links).toEqual([answer.miejsca[0]?.trasa]);

    // Full screen is offered, because this host offers it, and asked of the host.
    await widget.getByRole("button", { name: "Pełny ekran", exact: true }).click();
    await expect(widget.getByRole("button", { name: "Zamknij pełny ekran", exact: true })).toBeVisible();
    expect((await host()).displayModes).toEqual(["fullscreen"]);

    expect(errors).toEqual([]);
});
