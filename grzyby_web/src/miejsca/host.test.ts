import { describe, expect, it } from "vitest";

import { respond } from "./host";

const request = (method: string, params: object = {}) => ({ jsonrpc: "2.0", id: 7, method, params });

describe("the page as the widget's host", () => {
    it("offers full screen when the widget starts", () => {
        const [action] = respond(request("ui/initialize"));
        expect(action).toMatchObject({
            kind: "reply",
            id: 7,
            result: { hostContext: { availableDisplayModes: ["inline", "fullscreen"] } },
        });
    });

    it("sends the answer once the widget is ready", () => {
        expect(respond({ jsonrpc: "2.0", method: "ui/notifications/initialized" })).toEqual([{ kind: "send-result" }]);
    });

    it("fits the frame to the size the widget reports", () => {
        expect(respond({ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: { height: 812 } })).toEqual([
            { kind: "resize", height: 812 },
        ]);
        expect(respond({ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: {} })).toEqual([]);
    });

    it("opens web links and refuses anything else", () => {
        const route = "https://www.google.com/maps/dir/?api=1&destination=54.1,22.9";
        expect(respond(request("ui/open-link", { url: route }))).toEqual([
            { kind: "open", url: route },
            { kind: "reply", id: 7, result: {} },
        ]);
        expect(respond(request("ui/open-link", { url: "javascript:alert(1)" }))).toEqual([
            { kind: "reply", id: 7, result: { isError: true } },
        ]);
    });

    it("goes full screen and back", () => {
        expect(respond(request("ui/request-display-mode", { mode: "fullscreen" }))).toEqual([
            { kind: "display", fullscreen: true },
            { kind: "reply", id: 7, result: { mode: "fullscreen" } },
        ]);
        expect(respond(request("ui/request-display-mode", { mode: "inline" }))[0]).toEqual({ kind: "display", fullscreen: false });
    });

    it("answers any other request and ignores what is not the widget's", () => {
        expect(respond(request("ui/update-model-context"))).toEqual([{ kind: "reply", id: 7, result: {} }]);
        expect(respond({ jsonrpc: "2.0", method: "ui/notifications/something" })).toEqual([]);
        expect(respond({ jsonrpc: "1.0", method: "ping" })).toEqual([]);
    });
});
