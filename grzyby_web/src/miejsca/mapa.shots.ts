// The README's four pictures of the map widget: laptop and phone, in the chat and on full screen,
// each in another mode of the map. Real questions to the production server (SHOTS_MCP to point
// elsewhere), so the forests, the search circle and the numbered spots are the real ones; the
// widget is shown by the same kind of stand-in host as in mapa.e2e.ts, inside a plain chat column.
import { fileURLToPath } from "node:url";

import { type APIRequestContext, type Browser, devices, expect, test } from "@playwright/test";

import { fetchWidget, rpc } from "../../e2e/helpers";

const MCP = process.env["SHOTS_MCP"] ?? "https://grzyby.gugnowski.com/mcp";
const OUT = fileURLToPath(new URL("../../../docs/img/", import.meta.url));
const HOST = "https://host.test/";
const WIDGET = "https://widget.test/mapa.html";

const LAPTOP = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 };
// Two device pixels per CSS pixel, not the S24's three: as sharp on a screen, a third the file.
const PHONE = { ...devices["Galaxy S24"], deviceScaleFactor: 2 };

interface Shot {
    file: string;
    device: typeof LAPTOP | typeof PHONE;
    question: string;
    args: { miejscowosc: string; grzyby: string[]; promien_km: number; ile_miejsc: number };
    mode: "Wynik" | "Drzewa" | "Wiek" | "Siedlisko" | "Pogoda";
    fullscreen: boolean;
}

const SHOTS: Shot[] = [
    {
        file: "laptop-chat.png",
        device: LAPTOP,
        question: "Gdzie na podgrzybki koło Suwałk? Pokaż 10 miejsc.",
        args: { miejscowosc: "Suwałki", grzyby: ["podgrzybek"], promien_km: 10, ile_miejsc: 10 },
        mode: "Wynik",
        fullscreen: false,
    },
    {
        file: "laptop-fullscreen.png",
        device: LAPTOP,
        question: "A blisko Płociczna-Osiedla, do 2 km, na wszystkie grzyby?",
        args: {
            miejscowosc: "Płociczno-Osiedle",
            grzyby: ["borowik", "podgrzybek", "kurka", "kozlarz", "maslak", "rydz"],
            promien_km: 2,
            ile_miejsc: 4,
        },
        mode: "Drzewa",
        fullscreen: true,
    },
    {
        file: "phone-chat.png",
        device: PHONE,
        question: "Gdzie na prawdziwki i podgrzybki koło Chełma?",
        args: { miejscowosc: "Chełm", grzyby: ["borowik", "podgrzybek"], promien_km: 10, ile_miejsc: 5 },
        mode: "Pogoda",
        fullscreen: false,
    },
    {
        file: "phone-fullscreen.png",
        device: PHONE,
        question: "Prawdziwki i kurki koło Augustowa, blisko?",
        args: { miejscowosc: "Augustów", grzyby: ["borowik", "kurka"], promien_km: 6, ile_miejsc: 6 },
        mode: "Wiek",
        fullscreen: true,
    },
];

// A plain chat column: the question, then the widget. The stand-in host answers ui/initialize
// offering full screen, sends the tool result, fits the frame to the size the widget reports and,
// asked for full screen, gives it the whole page.
const hostPage = (question: string, result: unknown) => `<!doctype html>
<html lang="pl"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
body { margin: 0; background: #f5f4ef; font: 15px/1.5 system-ui, sans-serif; color: #222; }
main { max-width: 760px; margin: 0 auto; padding: 24px 12px; }
.question { margin: 0 0 16px auto; width: fit-content; max-width: 80%; background: #e4e1d6; padding: 10px 14px; border-radius: 16px; }
#widget { display: block; width: 100%; height: 600px; border: 1px solid #ddd; border-radius: 12px; background: white; }
body.full main { max-width: none; padding: 0; }
body.full .question { display: none; }
body.full #widget { position: fixed; inset: 0; height: 100vh; border: 0; border-radius: 0; }
</style></head><body>
<main><p class="question">${question}</p>
<iframe id="widget" title="Mapa" src="${WIDGET}" sandbox="allow-scripts allow-same-origin"></iframe></main>
<script>
const result = ${JSON.stringify(result)};
const widget = document.getElementById("widget");
const reply = (id, value) => widget.contentWindow.postMessage({ jsonrpc: "2.0", id, result: value }, "*");
window.addEventListener("message", (event) => {
    const m = event.data;
    if (!m || m.jsonrpc !== "2.0" || !m.method) return;
    if (m.method === "ui/initialize") {
        reply(m.id, {
            protocolVersion: "2026-01-26",
            hostInfo: { name: "shots-host", version: "0" },
            hostCapabilities: { openLinks: {} },
            hostContext: { theme: "light", displayMode: "inline", availableDisplayModes: ["inline", "fullscreen"] },
        });
    } else if (m.method === "ui/notifications/initialized") {
        widget.contentWindow.postMessage({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: result }, "*");
    } else if (m.method === "ui/notifications/size-changed") {
        if (!document.body.classList.contains("full") && m.params.height) widget.style.height = m.params.height + "px";
    } else if (m.method === "ui/request-display-mode") {
        document.body.classList.toggle("full", m.params.mode === "fullscreen");
        widget.style.height = "";
        reply(m.id, { mode: m.params.mode });
    } else if (m.id !== undefined) {
        reply(m.id, {});
    }
});
</script></body></html>`;

async function shoot(browser: Browser, request: APIRequestContext, shot: Shot): Promise<void> {
    const { html, csp } = await fetchWidget(request, MCP);
    const result = await rpc<{ isError?: boolean }>(request, MCP, "tools/call", { name: "gdzie_na_grzyby", arguments: shot.args });
    expect(result.isError ?? false).toBe(false);

    const context = await browser.newContext(shot.device);
    const page = await context.newPage();
    await page.route(HOST, (route) => route.fulfill({ contentType: "text/html; charset=utf-8", body: hostPage(shot.question, result) }));
    await page.route(WIDGET, (route) =>
        route.fulfill({ contentType: "text/html; charset=utf-8", headers: { "Content-Security-Policy": csp }, body: html }),
    );
    await page.goto(HOST);
    const widget = page.frameLocator("#widget");
    await expect(widget.locator(".spot-number").first()).toBeVisible();

    if (shot.fullscreen) {
        await widget.getByRole("button", { name: "Pełny ekran", exact: true }).click();
        await expect(widget.getByRole("button", { name: "Zamknij pełny ekran", exact: true })).toBeVisible();
    }
    await widget.getByRole("button", { name: shot.mode, exact: true }).click();
    // On a phone the legend starts folded; on full screen there is room to show it.
    const legend = widget.locator("details.legend");
    if (shot.fullscreen && (await legend.getAttribute("open")) === null) await widget.getByText("Legenda", { exact: true }).click();

    // Every map tile loaded, and Leaflet's fade-in over.
    await expect
        .poll(() =>
            page
                .frame({ url: WIDGET })
                ?.evaluate(() =>
                    Array.from(document.querySelectorAll<HTMLImageElement>("img.leaflet-tile")).every(
                        (i) => i.complete && i.naturalWidth > 0,
                    ),
                ),
        )
        .toBe(true);
    await page.waitForTimeout(600);
    await page.screenshot({ path: OUT + shot.file });
    await context.close();
}

for (const shot of SHOTS) {
    test(shot.file, async ({ browser, request }) => {
        await shoot(browser, request, shot);
    });
}
