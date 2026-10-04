import { describe as group, expect, it } from "vitest";

import { describe, statusOf } from "./status";

group("statusOf", () => {
    it("is up when the server says ok", () => {
        expect(statusOf({ status: "ok" })).toEqual({ kind: "up" });
    });

    it("is down with the reason when the request failed", () => {
        expect(describe(statusOf(new Error("502 Bad Gateway")))).toBe("nie działa (502 Bad Gateway)");
    });
});
