# Gdzie na grzyby

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/visual/board/img/readme/hero-dark.png">
  <img alt="Gdzie na grzyby (where to pick mushrooms), an MCP server: ask your chatbot (Claude, ChatGPT) where to pick mushrooms in Poland and get a map of forests coloured by your chances, with the best spots and a route. Works without a chatbot too; no login, no key. 6 mushroom groups, up to 15 spots on the map, 5 days ahead, state forests in all of Poland." src="docs/visual/board/img/readme/hero-light.png" width="100%">
</picture>

*Gdzie na grzyby* is Polish for “where to pick mushrooms”. The app, its map and its answers are in Polish.

![The map in a laptop chat: bay boletes near Suwałki, ten numbered spots in a 10 km circle, forests coloured by score](docs/img/laptop-chat.png)

![The map full screen on a laptop: Płociczno-Osiedle, a 2 km circle, forests coloured by tree species](docs/img/laptop-fullscreen.png)

<p align="center">
  <img src="docs/img/phone-chat.png" width="49%" alt="The map in a phone chat: boletes and bay boletes near Chełm, weather squares showing where the ground is wet after rain" />
  <img src="docs/img/phone-fullscreen.png" width="49%" alt="The map full screen on a phone: Augustów, forests coloured by stand age" />
</p>

## What you get

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/visual/board/img/readme/features-dark.png">
  <img alt="What you get. Spots, not generalities: specific forest stands at least a kilometre apart, 3 by default, up to 15. Why right there: trees, forest age, season and recent weather. Each mushroom on its own: spots for all together and for each separately. A map with modes: score, trees, age, habitat, weather; a click explains the score. When to go: today and 5 days ahead, with the best day. Only where you may enter: skips national parks, nature reserves and forests under an entry ban." src="docs/visual/board/img/readme/features-light.png" width="100%">
</picture>

The mushrooms it knows: borowik (king bolete and its relatives), podgrzybek (bay bolete), kurka (chanterelle), koźlarz
(birch and aspen boletes), maślak (slippery jack) and rydz (saffron milk cap).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/visual/board/img/readme/choose-dark.png">
  <img alt="What to ask. Where are bay boletes near Suwałki: a map and 3 spots. 10 chanterelle spots within 20 km of Augustów: a map and 10 spots. Best day for chanterelles near Augustów: the best day. No chatbot: the website grzyby.gugnowski.com/szukaj." src="docs/visual/board/img/readme/choose-light.png" width="100%">
</picture>

The first question about a new area takes a few seconds, because its forest data is fetched then; after that it is quick.

## Without a chatbot

The same tool runs on a page: **[grzyby.gugnowski.com/szukaj](https://grzyby.gugnowski.com/szukaj)**. Type a place, choose
the mushrooms and get the same map. The search is in the page's address, so a link to it can be saved or sent to a friend.

## Connect it

Server address: **`https://grzyby.gugnowski.com/mcp`**, no login and no key.

Step-by-step instructions (in Polish) are at **[grzyby.gugnowski.com](https://grzyby.gugnowski.com)**, separately for Claude
(claude.ai and the desktop app), ChatGPT and Claude Code, so for an agent in the terminal too.

If the map looks old after a server update, disconnect the connector and connect it again: chatbots remember its old version.

## How it works

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/visual/board/img/readme/flow-dark.png">
  <img alt="Where an answer comes from. 1 You ask a chatbot or the website: a place and a radius, which mushrooms, which day. 2 Forest stands from the Forest Data Bank (BDL): trees, age, habitat, without parks, reserves or entry bans. 3 Recent weather from Open-Meteo: rain and soil moisture, temperature, frost. 4 An open formula, no AI: what the mushroom likes and whether it is in season. 5 A map in the chat or the browser: numbered spots, why there, a route link." src="docs/visual/board/img/readme/flow-light.png" width="100%">
</picture>

## What it doesn't know

- **State forests only.** Private and municipal forests are blank on the map, not because nothing grows there but because
  there is no data about them.
- **The score is a formula, not an oracle.** It combines what pickers know about each mushroom with the weather of recent
  days. It suggests where to start; you still have to find the mushrooms yourself, and know them.
  Never pick a mushroom you can't identify.
- **Check entry bans on site.** The signs at the forest matter more than the map.

## Data sources

- Forest stands and entry bans: [Bank Danych o Lasach](https://www.bdl.lasy.gov.pl/) (Forest Data Bank, CC BY 4.0).
- National parks and nature reserves: Generalna Dyrekcja Ochrony Środowiska.
- Weather: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
- Place locations: Nominatim, © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
- Base map: © OpenStreetMap contributors, © [CARTO](https://carto.com/attributions).

A hobby project: free, no ads, no collecting of data about you.

For developers (in Polish): [docs/dev/README.md](docs/dev/README.md). The pictures in this README are drawn on
`docs/visual/board/readme.html` and rendered with `vdoc.py render` of the suwagent plugin; `just screenshots` takes the map's.
