# MCP Apps — mapa w odpowiedzi chatbota

Jak działa widżet z mapą (`ui://grzyby/mapa.html`), czego wymaga Claude i jak szukać przyczyny,
gdy mapy nie widać. Spisane 4.10.2026 po pierwszym uruchomieniu w Claude; SDK `mcp` 2.3,
`@modelcontextprotocol/ext-apps` 2.0.3, specyfikacja MCP Apps 2026-01-26.

## Jak to działa

1. Narzędzie (`gdzie_na_grzyby`, `grzyby_server/miejsca/tools.py`) ma w `_meta` adres widżetu.
2. Chatbot, widząc ten adres w `tools/list`, pobiera widżet przez `resources/read` — HTML z typem
   `text/html;profile=mcp-app` — i renderuje go w piaskownicy (iframe w iframe).
3. Po `tools/call` host przekazuje wynik do widżetu; `mapa.html` odbiera go w
   `app.ontoolresult` (biblioteka `ext-apps`, klasa `App`) i rysuje znaczniki z
   `structuredContent`.
4. Ta sama odpowiedź ma też **tekst** (`content`): czyta go model, a klient bez MCP Apps (np.
   Claude Code) pokazuje tylko jego. Dlatego narzędzie zwraca `CallToolResult` z oboma formami,
   a nie sam model danych — inaczej tekstem byłby surowy JSON.

## Czego wymaga Claude — każda z tych rzeczy już raz nas zatrzymała

### 1. Nowy adres widżetu przy każdej zmianie jego treści

**Claude zapamiętuje widżet po adresie (`ui://…`).** Pobrał `mapa.html` raz — w wersji, która
w piaskownicy nie działała — i potem pokazywał tę zepsutą kopię, choć serwer od dawna podawał
poprawioną: adres się nie zmienił, więc nie pytał o nią ponownie (w logach: brak
`resources/read`, a Claude i tak pisze „mapka jest wyżej”). Dlatego adres zawiera skrót treści:

```python
MAP_URI = f"ui://grzyby/mapa-{hashlib.sha256(MAP_HTML.encode()).hexdigest()[:12]}.html"
```

Każda zmiana `mapa.html` = nowy adres = świeże pobranie. Pilnuje tego test
`test_the_map_address_changes_with_its_content`. Nowy widżet (np. drugie narzędzie z UI)
dostaje adres tak samo, nigdy na sztywno.

Obok `_meta.ui.resourceUri` narzędzie ma też starszy płaski klucz `_meta["ui/resourceUri"]` —
tak jak oficjalny helper TypeScript `registerAppTool()`. To nie on był przyczyną (Claude
pobrał widżet także bez niego), ale zgodność z helperem nic nie kosztuje.

### 2. CSP piaskownicy: żadnych workerów `blob:`, wszystko z zadeklarowanych hostów

Host buduje CSP z `_meta.ui.csp` zasobu (specyfikacja, „CSP Construction from Metadata”):

```
default-src 'none';
script-src 'self' 'unsafe-inline' <resourceDomains>;
style-src  'self' 'unsafe-inline' <resourceDomains>;
img-src    'self' data: <resourceDomains>;
connect-src 'self' <connectDomains>;
font-src / media-src — jak wyżej; frame-src 'none'; object-src 'none'
```

Wnioski:

- **Nie MapLibre ani inna mapa WebGL** — uruchamia worker z adresu `blob:`, którego CSP nie
  dopuszcza; mapa się nie rysuje. Dlatego **Leaflet** z kafelkami rastrowymi (zwykłe `<img>`).
- Każdy host, z którego coś ładujemy, musi być w `resource_domains` (`tools.py`): dziś
  `https://unpkg.com` (Leaflet, `ext-apps`) i `https://tile.openstreetmap.org` (kafelki).
  Zapytania `fetch` z widżetu — w `connect_domains`.
- **Kafelki CARTO wymagają już klucza API** (pokazują „API KEY REQUIRED”) — odpadły.
  OpenStreetMap: bez klucza, z przypisaniem; ich zasady wykluczają duży ruch — przy większym
  ruchu własne źródło kafelków.

### 2a. Linki, pełny ekran, rozmiar danych

- **Linki przez hosta:** piaskownica może blokować nowe okna, więc link do trasy idzie przez
  `app.openLink({ url })` (komunikat `ui/open-link`), a `window.open` jest tylko zapasem.
- **Pełny ekran:** widżet deklaruje `availableDisplayModes: ["inline", "fullscreen"]` w `App`,
  a przycisk pokazuje tylko wtedy, gdy host ma `fullscreen` w swoim
  `hostContext.availableDisplayModes` (specyfikacja: najpierw sprawdzić, potem prosić).
- **`structuredContent` nie trafia do kontekstu modelu** (specyfikacja: „not added to model
  context”) — kształty drzewostanów nie kosztują tokenów; model czyta tylko `content` (tekst).
  Limit ~150 000 znaków dalej obowiązuje: budżet w `miejsca/map_data.py`, kształty jako encoded
  polyline (ok. ¼ GeoJSON), cechy drzewostanów kolumnami (klucze raz, nie 2000 razy).
- **Dwa tysiące wielokątów:** Leaflet z `preferCanvas: true` — płynnie, bez SVG.

### 3. Zgoda użytkownika

Przy pierwszym użyciu Claude pyta, czy wyświetlić aplikację („Allow” / „Always allow”). Bez
zgody widać tylko tekst.

### 4. Świeża lista narzędzi

Claude pamięta też `tools/list` — nowa rozmowa nie zawsze go odświeża. Po zmianie narzędzi
(nazwy, opisu, `_meta`): w ustawieniach konektora odłączyć i podłączyć go ponownie.

### 5. Nie potrzebujemy: `ui.domain`

`_meta.ui.domain` daje widżetowi stały origin (`{hash}.claudemcpcontent.com`) — potrzebny tylko
aplikacji z własnym logowaniem OAuth. Jeśli kiedyś: hash to pierwsze 32 znaki hex SHA-256
**dokładnego** adresu konektora (`https://grzyby.gugnowski.com/mcp`, bez ukośnika na końcu);
zła wartość kończy się błędem `ui.domain mismatch` zamiast mapy.

## Pozostałe pułapki z dokumentacji Claude

- **Wynik narzędzia > ~150 000 znaków** — claude.ai zapisuje go do pliku zamiast przekazać
  widżetowi, mapa się nie wypełnia. Odpowiedź trzymać małą (kilka miejsc, nie GeoJSON całych
  drzewostanów); szczegóły dociągać osobnym narzędziem.
- **iOS nie wysyła `Referer`** przy zasobach z innego originu. Serwer, który go wymaga (np.
  kafelki z filtrem po `Referer`), odrzuci telefon, choć komputer działa. Filtrować po `Origin`
  (`*.claudemcpcontent.com`).
- **Zerowa wysokość** — widżet musi mieć wymiary (`#map { height: 360px }`).

## Gdy mapy nie widać — kolejność sprawdzania

1. **Logi nginx** — czy Claude w ogóle pobrał widżet:

   ```sh
   kubectl -n grzyby logs deploy/grzyby-web --since=15m | grep -v healthz
   ```

   Każda operacja MCP to `POST /mcp` (bez nazwy metody w logu); rozpoznaje się je po
   rozmiarze odpowiedzi. `resources/read` widżetu to ~4 KB (`mapa.html` + JSON). Brak takiej
   odpowiedzi po zmianie widżetu = Claude używa kopii z pamięci → adres się nie zmienił
   (punkt 1) albo stara lista narzędzi (punkt 4). Jest, a mapy nie ma → CSP/skrypt widżetu
   (punkt 2) albo brak zgody (punkt 3).
   Ramka „mapy” narysowana przez samego Claude (jego własna wizualizacja z danych narzędzia)
   to nie nasz widżet — nie myli się tego z sukcesem.
2. **Odmowy klucza** — serwer loguje przyczynę, nigdy wartości:

   ```sh
   kubectl -n grzyby logs deploy/grzyby-server --since=15m | grep refused
   ```

   `no key` = konektor nie wysyła nagłówka; `wrong key` = stary albo przekręcony klucz.
3. **Widżet pod CSP lokalnie** — robi to test `grzyby_web/src/miejsca/mapa.e2e.ts` (`just e2e`):
   pobiera widżet z serwera przez MCP, podaje go z CSP zbudowanym z `_meta.ui.csp`, w iframe
   bez zgody na nowe okna, i rozmawia z nim jak host (`ui/initialize`, wynik narzędzia,
   `ui/open-link`, `ui/request-display-mode`). Każdy błąd w konsoli — także naruszenie CSP —
   oblewa test. `--headed` pokazuje przeglądarkę.
4. **Narzędzia deweloperskie Claude Desktop:** Help → Troubleshooting → Enable Developer Mode,
   potem `Ctrl+Shift+I`; widżet to wewnętrzny iframe w iframe pod wywołaniem narzędzia.

## Źródła

- Claude: [Get started with MCP Apps](https://claude.com/docs/connectors/building/mcp-apps/getting-started),
  [Troubleshoot MCP Apps](https://claude.com/docs/connectors/building/mcp-apps/troubleshooting)
- Specyfikacja: [ext-apps, apps.mdx](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- Helper serwerowy z oboma kluczami: `@modelcontextprotocol/ext-apps/server`, `registerAppTool()`
- Python: `mcp.server.apps` (klasa `Apps`) w SDK `mcp`
