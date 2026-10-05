import { useEffect, useState } from "react";

import { fetchHealth } from "./api";
import { statusOf, type ServerStatus } from "./status";

/** Whether the API answers, asked once when the page opens. */
export function useServerStatus(): ServerStatus {
    const [status, setStatus] = useState<ServerStatus>({ kind: "checking" });

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

    return status;
}
