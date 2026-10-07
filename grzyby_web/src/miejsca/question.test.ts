import { describe, expect, it } from "vitest";

import { dayName, fromSearch, START, toSearch, type Question } from "./question";

const QUESTION: Question = { miejscowosc: "Suwałki", grzyby: ["kurka", "borowik"], promien_km: 15, ile_miejsc: 10, za_ile_dni: 1 };

describe("the question in the address", () => {
    it("comes back as it went in", () => {
        expect(fromSearch(toSearch(QUESTION))).toEqual(QUESTION);
    });

    it("is no question without a place", () => {
        expect(fromSearch("")).toBeNull();
        expect(fromSearch("?grzyby=kurka&miejscowosc=%20")).toBeNull();
    });

    it("keeps a hand-edited link inside the server's bounds", () => {
        expect(fromSearch("?miejscowosc=Chełm&grzyby=kania&grzyby=rydz&grzyby=rydz&promien_km=99&ile_miejsc=0&za_ile_dni=x")).toEqual({
            miejscowosc: "Chełm",
            grzyby: ["rydz"],
            promien_km: 30,
            ile_miejsc: 1,
            za_ile_dni: START.za_ile_dni,
        });
    });

    it("falls back to the first mushroom when none is known", () => {
        expect(fromSearch("?miejscowosc=Chełm&grzyby=kania")?.grzyby).toEqual(START.grzyby);
    });
});

describe("a day in words", () => {
    it.each([
        [0, "dziś"],
        [1, "jutro"],
        [2, "pojutrze"],
        [5, "za 5 dni"],
    ])("%i is %s", (days, name) => {
        expect(dayName(days)).toBe(name);
    });
});
