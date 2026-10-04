"""GET a JSON document from a public service — the only way the server reaches the internet.

Plain urllib, no client library: a handful of GETs (forest data, entry bans, geocoding) needs
nothing more. Code that fetches takes a `GetJson` as a parameter, so tests pass a fake that
answers from recorded responses instead of the network.
"""

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Who is asking — Nominatim's usage policy requires an identifying User-Agent, and it does no
# harm elsewhere.
USER_AGENT = "grzyby-mcp/0.1 (+https://grzyby.gugnowski.com)"

type GetJson = Callable[[str, Mapping[str, str | int]], Any]


def get_json(url: str, params: Mapping[str, str | int]) -> Any:  # noqa: ANN401 — the services' JSON has no schema of ours
    request = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})  # noqa: S310 — the URLs are constants of this package, all https
    with urlopen(request, timeout=30) as response:  # noqa: S310 — as above
        return json.load(response)
