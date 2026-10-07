// The question the search page asks, and its place in the page's address: a search can be
// bookmarked or sent to a friend, and opening the link asks it again.
import type { components } from "../api/openapi";

export type Grzyb = components["schemas"]["Grzyb"];

/** The mushrooms in the order the form offers them, with the names people read. */
export const GRZYBY: Record<Grzyb, string> = {
    borowik: "borowik",
    podgrzybek: "podgrzybek",
    kurka: "kurka",
    kozlarz: "koźlarz",
    maslak: "maślak",
    rydz: "rydz",
};

export interface Question {
    miejscowosc: string;
    grzyby: Grzyb[];
    promien_km: number;
    ile_miejsc: number;
    za_ile_dni: number;
}

// The server's bounds (miejsca/api.py); a link with anything else is brought back inside them.
export const RADII = [2, 5, 10, 15, 20, 30] as const;
export const MAX_SPOTS = 15;
export const DAYS_AHEAD = 5;

export const START: Question = { miejscowosc: "", grzyby: ["borowik"], promien_km: 10, ile_miejsc: 5, za_ile_dni: 0 };

function isGrzyb(name: string): name is Grzyb {
    return Object.hasOwn(GRZYBY, name);
}

function whole(text: string | null, min: number, max: number, fallback: number): number {
    const n = Number(text);
    return text !== null && Number.isInteger(n) ? Math.min(max, Math.max(min, n)) : fallback;
}

/** The question in an address's query string, or null when it holds none (no place). */
export function fromSearch(search: string): Question | null {
    const params = new URLSearchParams(search);
    const miejscowosc = params.get("miejscowosc")?.trim() ?? "";
    if (!miejscowosc) return null;
    const grzyby = [...new Set(params.getAll("grzyby").filter(isGrzyb))];
    return {
        miejscowosc,
        grzyby: grzyby.length > 0 ? grzyby : START.grzyby,
        promien_km: whole(params.get("promien_km"), 1, 30, START.promien_km),
        ile_miejsc: whole(params.get("ile_miejsc"), 1, MAX_SPOTS, START.ile_miejsc),
        za_ile_dni: whole(params.get("za_ile_dni"), 0, DAYS_AHEAD, START.za_ile_dni),
    };
}

/** The question as a query string — the same for the page's address and for the API. */
export function toSearch(question: Question): string {
    const params = new URLSearchParams({ miejscowosc: question.miejscowosc.trim() });
    for (const grzyb of question.grzyby) params.append("grzyby", grzyb);
    params.set("promien_km", String(question.promien_km));
    params.set("ile_miejsc", String(question.ile_miejsc));
    params.set("za_ile_dni", String(question.za_ile_dni));
    return params.toString();
}

/** A day ahead in words: dziś, jutro, pojutrze, za 3 dni. */
export function dayName(daysAhead: number): string {
    if (daysAhead === 0) return "dziś";
    if (daysAhead === 1) return "jutro";
    if (daysAhead === 2) return "pojutrze";
    return `za ${String(daysAhead)} dni`;
}
