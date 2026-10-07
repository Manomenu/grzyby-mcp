// The page as the widget's host: the few MCP Apps messages mapa.html sends its chatbot, answered
// the way a chatbot does — so the one widget serves both (grzyby_server/.../miejsca/mapa.html).
// A pure function of the message: MapWidget.tsx carries out what it returns.

export interface Message {
    jsonrpc?: unknown;
    id?: unknown;
    method?: unknown;
    params?: unknown;
}

export type Action =
    | { kind: "reply"; id: unknown; result: object }
    | { kind: "send-result" }
    | { kind: "resize"; height: number }
    | { kind: "open"; url: string }
    | { kind: "display"; fullscreen: boolean };

const HOST_CONTEXT = { theme: "light", displayMode: "inline", availableDisplayModes: ["inline", "fullscreen"] };

function field(params: unknown, name: string): unknown {
    return typeof params === "object" && params !== null ? (params as Record<string, unknown>)[name] : undefined;
}

/** What to do about one message from the widget; nothing for anything that is not one of its. */
export function respond(message: Message): Action[] {
    if (message.jsonrpc !== "2.0" || typeof message.method !== "string") return [];
    const { id, params } = message;
    switch (message.method) {
        case "ui/initialize":
            return [
                {
                    kind: "reply",
                    id,
                    result: {
                        protocolVersion: "2026-01-26",
                        hostInfo: { name: "gdzie-na-grzyby", version: "1" },
                        hostCapabilities: { openLinks: {} },
                        hostContext: HOST_CONTEXT,
                    },
                },
            ];
        case "ui/notifications/initialized":
            return [{ kind: "send-result" }];
        case "ui/notifications/size-changed": {
            const height = field(params, "height");
            return typeof height === "number" && height > 0 ? [{ kind: "resize", height }] : [];
        }
        case "ui/open-link": {
            const url = field(params, "url");
            // Only web links: the widget's links are routes in Google Maps.
            const ok = typeof url === "string" && url.startsWith("https://");
            return ok
                ? [
                      { kind: "open", url },
                      { kind: "reply", id, result: {} },
                  ]
                : [{ kind: "reply", id, result: { isError: true } }];
        }
        case "ui/request-display-mode": {
            const fullscreen = field(params, "mode") === "fullscreen";
            return [
                { kind: "display", fullscreen },
                { kind: "reply", id, result: { mode: fullscreen ? "fullscreen" : "inline" } },
            ];
        }
        default:
            // A request the page has nothing to add to still gets its answer, so the widget never waits.
            return id === undefined ? [] : [{ kind: "reply", id, result: {} }];
    }
}
