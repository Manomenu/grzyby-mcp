// This feature's HTTP calls, typed from the generated OpenAPI types.
import { request } from "../api/client";
import type { components } from "../api/openapi";
import { toSearch, type Question } from "./question";

export type Answer = components["schemas"]["Answer"];

export function fetchAnswer(question: Question, signal: AbortSignal): Promise<Answer> {
    return request<Answer>(`/miejsca?${toSearch(question)}`, { signal });
}

/** The widget the chatbots show, served by the server next to the API. */
export const WIDGET_URL = `${import.meta.env.VITE_API_BASE ?? "/api"}/mapa.html`;
