import { useEffect, useRef, useState } from "react";

import { WIDGET_URL, type Answer } from "./api";
import { respond, type Message } from "./host";

/** The chatbots' map widget in a sandboxed frame, with this page as its host (host.ts). One
 *  frame per answer: the parent gives each answer its own key. */
export function MapWidget({ answer }: { answer: Answer }) {
    const frame = useRef<HTMLIFrameElement>(null);
    const [height, setHeight] = useState(640);
    const [fullscreen, setFullscreen] = useState(false);

    useEffect(() => {
        function onMessage(event: MessageEvent) {
            const widget = frame.current?.contentWindow;
            // Only the widget's own messages; anything else on the page is not ours to answer.
            if (!widget || event.source !== widget || typeof event.data !== "object" || event.data === null) return;
            for (const action of respond(event.data as Message)) {
                switch (action.kind) {
                    case "reply":
                        widget.postMessage({ jsonrpc: "2.0", id: action.id, result: action.result }, "*");
                        break;
                    case "send-result":
                        widget.postMessage(
                            {
                                jsonrpc: "2.0",
                                method: "ui/notifications/tool-result",
                                params: { content: [{ type: "text", text: "" }], structuredContent: answer },
                            },
                            "*",
                        );
                        break;
                    case "resize":
                        setHeight(action.height);
                        break;
                    case "open":
                        window.open(action.url, "_blank", "noopener");
                        break;
                    case "display":
                        setFullscreen(action.fullscreen);
                        break;
                }
            }
        }
        window.addEventListener("message", onMessage);
        return () => {
            window.removeEventListener("message", onMessage);
        };
    }, [answer]);

    // Full screen: the page behind must not scroll under the map.
    useEffect(() => {
        if (!fullscreen) return;
        const before = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            document.body.style.overflow = before;
        };
    }, [fullscreen]);

    return (
        <iframe
            ref={frame}
            title="Mapa miejsc na grzyby"
            src={WIDGET_URL}
            // Scripts only: no access to this page, no popups — links come to the host instead.
            sandbox="allow-scripts"
            style={
                fullscreen
                    ? { position: "fixed", inset: 0, width: "100vw", height: "100dvh", border: 0, zIndex: 1000, background: "white" }
                    : { display: "block", width: "100%", height, border: 0, background: "white" }
            }
        />
    );
}
