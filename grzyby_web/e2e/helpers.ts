// What the browser tests and the README's pictures (*.shots.ts) share: the map widget fetched from
// an MCP server the way a chatbot does — tools/list → resources/read — with the CSP a host builds
// from the widget's own metadata (`_meta.ui.csp`, the rule in the MCP Apps spec).
import { type APIRequestContext, expect } from "@playwright/test";

interface Csp {
    resourceDomains?: string[];
    connectDomains?: string[];
}

/** One JSON-RPC call to the MCP endpoint at `mcp`. */
export async function rpc<T>(request: APIRequestContext, mcp: string, method: string, params: object = {}): Promise<T> {
    const response = await request.post(mcp, {
        headers: { accept: "application/json, text/event-stream" },
        data: { jsonrpc: "2.0", id: 1, method, params },
    });
    expect(response.ok()).toBe(true);
    return ((await response.json()) as { result: T }).result;
}

/** The widget's HTML and its CSP, fetched the way a host does. */
export async function fetchWidget(request: APIRequestContext, mcp: string): Promise<{ html: string; csp: string }> {
    const { tools } = await rpc<{ tools: { name: string; _meta: { ui: { resourceUri: string } } }[] }>(request, mcp, "tools/list");
    const tool = tools.find((t) => t.name === "gdzie_na_grzyby");
    if (!tool) throw new Error("the server lists no gdzie_na_grzyby");
    const { contents } = await rpc<{ contents: { text: string; mimeType: string; _meta?: { ui?: { csp?: Csp } } }[] }>(
        request,
        mcp,
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
