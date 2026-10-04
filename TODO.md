# TODO — grzyby-mcp

Serwer MCP podpinany do chatbota (Claude, ChatGPT): pytasz „gdzie w okolicy X są teraz
grzyby?”, dostajesz **mapkę** z zaznaczonym kawałkiem lasu, krótkie „dlaczego” i link do
trasy w Google Maps. Później strona `gdzie-na-grzyby.pl` z instrukcją instalacji, MCP pod
`/mcp`.

Tło, konkurencja, koszty i ocena danych: notatka w Obsidianie „Aplikacja dla grzybiarza
(mcp)”. Proponowany stack: [`docs/dev/propozycja-stacka.md`](docs/dev/propozycja-stacka.md)
(plik roboczy — po decyzjach znika, a ustalenia trafiają do README / AGENTS.md).

Zasada przewodnia: **hobby, nie biznes** — koszt ≈ domena; nic komercyjnego, dopóki nie
sprawdzimy licencji danych.

---

## 0. Rozpoznanie, zanim powstanie kod

- [x] **Licencja Banku Danych o Lasach** — CC BY 4.0 + obowiązki z regulaminu (`docs/dev/rozpoznanie-danych.md`); zostaje mail do BDL przed publicznym startem.
- [x] **Warstwy BDL** — OGC API Features: gatunek, wiek, siedlisko; zakazy przez ArcGIS REST; próbka w `.artifacts/dane/`.
- [x] **IMGW** — tylko bieżący pomiar (stacja Suwałki); historia z Open-Meteo albo własne zbieranie.
- [ ] **Open-Meteo** — wilgotność gleby dla tych samych punktów (darmowe niekomercyjnie);
      porównać z IMGW, czy warto mieć oba.
- [ ] **MCP Apps** — sprawdzić aktualny stan rozszerzenia (widżet z mapą) w Claude i ChatGPT,
      zrobić „hello world”: narzędzie zwraca mapkę z jednym punktem.
- [x] **Wybór okolicy pilotażowej** — Suwałki / Wigierski Park Narodowy (park sam w sobie: zbiór zakazany, do potwierdzenia).

## 1. MVP — jedna okolica, jedno narzędzie

- [ ] Import drzewostanów i zakazów z BDL do PostGIS dla okolicy pilotażowej (skrypt,
      powtarzalny, raz na jakiś czas).
- [ ] Codzienne pobranie opadów i temperatur (IMGW, ew. Open-Meteo) z ostatnich ~30 dni.
- [ ] **Wynik punktowy** dla wydzielenia: gatunek drzew × opady z ostatnich 2–3 tygodni ×
      temperatura × pora roku. Prosty, czytelny wzór — żadnego AI. Każdy składnik ma
      opis „dlaczego”, który trafia do odpowiedzi.
- [ ] Wyłączenie miejsc, gdzie nie wolno: zakazy wstępu, parki narodowe, rezerwaty.
- [ ] Narzędzie MCP `gdzie_na_grzyby(miejsce, promien_km)` → 3 najlepsze miejsca: mapka,
      uzasadnienie, link `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`.
- [ ] Geokodowanie „miejsca” (nazwa miejscowości → współrzędne).
- [ ] Testy: wzór punktowy na przykładowych danych; narzędzie MCP end-to-end na nagranych
      odpowiedziach BDL/IMGW.

## 2. Sprawdzian w terenie

- [ ] Kilka wyjść do lasu według wskazań, zapis: gdzie, kiedy, co znalezione / nic.
- [ ] Porównanie z mapą, korekta wag wzoru. Dopiero gdy wskazania mają sens — dalej.

## 3. Wdrożenie i strona

- [ ] Projekt w `suwalski-platform` (Argo, baza w CloudNativePG z PostGIS, tunel Cloudflare —
      **publiczny**, bez Cloudflare Access na `/mcp`).
- [ ] Ochrona przed nadużyciem: limit zapytań (Cloudflare), cache wyników na dzień.
- [ ] Domena `gdzie-na-grzyby.pl` (sprawdzić cenę **odnowienia**, nie tylko pierwszego roku).
- [ ] Strona: czym to jest, instrukcja „Ustawienia → Konektory → Dodaj własny” dla Claude
      i ChatGPT, przypisanie źródeł danych (BDL, IMGW, mapa).

## Później / może

- [ ] Prognoza na kilka dni naprzód (Open-Meteo forecast).
- [ ] Gatunki grzybów: borowik / podgrzybek / kurka — każdy z własnymi drzewami i progiem.
- [ ] Zgłoszenia „byłem, były / nie było” od użytkowników — jedyna droga do sprawdzania trafności.
- [ ] Rozszerzenie z okolicy pilotażowej na województwo / kraj.
