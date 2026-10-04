import { describe, expect, it } from "vitest";

import { toError } from "./client";

describe("toError", () => {
    it("carries the server's detail", async () => {
        const response = new Response(JSON.stringify({ detail: "not found" }), { status: 404 });

        expect((await toError(response)).message).toBe("not found");
    });

    it("falls back to the status when the body says nothing", async () => {
        const response = new Response("oops", { status: 502, statusText: "Bad Gateway" });

        expect((await toError(response)).message).toBe("502 Bad Gateway");
    });
});
