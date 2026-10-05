# Monetyzacja — luźne wątki

Notatka do przemyślenia, nic pilnego ani rozstrzygniętego (spisane 4.10.2026). Punkt wyjścia
z TODO: **hobby, nie biznes** — koszt ≈ domena. Zero zdzierstwa.

## Co kosztuje utrzymanie

- Domena: kilkadziesiąt zł rocznie (sprawdzić cenę odnowienia).
- Serwer: dziś własny homelab — prąd i czas, nie faktura.
- **Ukryte koszty, które pojawią się przy ruchu:**
  - kafelki mapy — CARTO: za darmo do 5 mln kafli miesięcznie niekomercyjnie, ale przy
    zarabianiu tylko do 1 mln (ok. 20 tys. obejrzeń mapy), powyżej płatny plan od 500 USD/mies.
    — wtedy raczej własny serwer kafelków;
  - Nominatim — to samo, przy ruchu własna instancja albo płatne geokodowanie;
  - **Open-Meteo jest darmowe tylko niekomercyjnie.** Gdy usługa zaczyna zarabiać, to już
    użycie komercyjne → ich płatny plan. Czyli: monetyzacja sama w sobie generuje koszt.
  - BDL (CC BY 4.0) i GDOŚ — komercyjnie wolno, z przypisaniem (GDOŚ do potwierdzenia).
- Mój czas — największy koszt, ale tego się nie wycenia w hobby.

## Pomysły

1. **„Postaw kawę” / dobrowolna wpłata** — jak GrzyboRadar (buycoffee.to). Bez kont, bez
   logowania, bez zmian w kodzie. Komunikat w stylu: „Utrzymanie kosztuje — jeśli się
   przydało, możesz się dorzucić”. Najmniej pracy, najbardziej w duchu projektu.
2. **Jednorazowa opłata za sezon** — np. kilkanaście zł za sezon grzybowy (sierpień–listopad),
   bez subskrypcji i bez automatycznego odnawiania. Cena mówi „to kosztuje utrzymać”, a nie
   „zarabiam na tobie”.
3. **Jednorazowo na zawsze** („lifetime”) — jedna niewielka kwota. Prosta w komunikacji, ale
   koszty przy ruchu rosną co roku, a wpływy nie.
4. **Darmowe z limitem + wspierający bez limitu** — np. kilka zapytań dziennie za darmo, dla
   tych, co się dorzucili, bez limitu. Wymaga kont / kluczy na osobę.
5. **„Zapłać, ile chcesz”** — jednorazowo, z kwotą sugerowaną.
6. **Nie monetyzować wcale** — zostawić jako projekt dla siebie, znajomych i portfolio;
   ewentualnie tylko punkt 1, żeby pokryć domenę.

## Co by trzeba zbudować (dla 2–5)

- Konta albo klucz na osobę zamiast jednego wspólnego `MCP_KEY` — w MCP naturalne jest OAuth
  (Claude umie się logować do konektora), albo klucz wysyłany mailem po wpłacie.
- Płatności: Stripe, Przelewy24 / BLIK, Patronite, buycoffee.to — od najbardziej do
  najmniej pracy po naszej stronie.
- Formalności: przy sprzedaży w Polsce działalność (choćby nierejestrowana do limitu
  przychodu), regulamin, polityka prywatności, faktury/paragony — sprawdzić.

## Co robi konkurencja

- **sezonnagrzyby.pl** — reklamy Google AdSense, za darmo.
- **grzyboradar.pl** — za darmo, „Postaw mi kawę” (buycoffee.to), bez reklam.
- **grzyby.pl** — pełna wersja po zalogowaniu.
- W chatbocie reklam i tak się nie da wstawić — zostają wpłaty albo płatny dostęp.

## Za i przeciw w ogóle

- Za: pokrywa realne koszty, gdy przyjdzie ruch; wygoda (pytanie w czacie, mapa,
  uzasadnienie) jest czymś, za co ludzie płacą.
- Przeciw: płatność = zobowiązanie (działa w sezonie, odpowiada na maile), zmienia licencje
  danych (Open-Meteo), wymaga kont i formalności. Konkurencja jest darmowa.
- Rozsądna kolejność: najpierw punkt 1 (kawa), zobaczyć, czy ktoś w ogóle używa; płatny
  dostęp dopiero, gdy koszty realnie urosną.
