import { Badge } from "@mantine/core";
import { useEffect, useState } from "react";

import { fetchHealth } from "./api";
import { describe, statusOf, type ServerStatus as Status } from "./status";

/** Whether the API answers — a badge. The template's only feature; delete it when it is in the way. */
export function ServerStatus() {
    const [status, setStatus] = useState<Status>({ kind: "checking" });

    useEffect(() => {
        // StrictMode runs effects twice in development: abort the first request, ignore its result.
        const controller = new AbortController();
        fetchHealth(controller.signal)
            .then((health) => {
                setStatus(statusOf(health));
            })
            .catch((e: unknown) => {
                if (!controller.signal.aborted) setStatus(statusOf(e instanceof Error ? e : new Error(String(e))));
            });
        return () => {
            controller.abort();
        };
    }, []);

    return (
        <Badge variant="light" size="lg" color={status.kind === "down" ? "red" : "indigo"}>
            serwer: {describe(status)}
        </Badge>
    );
}
