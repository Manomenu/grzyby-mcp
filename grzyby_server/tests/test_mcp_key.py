from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from grzyby_server.mcp_key import RequireKey

KEY = "s3cret-key"


def endpoint_behind(key: str | None, *, allow_public: bool = False) -> TestClient:
    # A response is itself an ASGI app: the simplest thing to put behind the key.
    return TestClient(Starlette(routes=[Route("/mcp", endpoint=RequireKey(PlainTextResponse("ok"), key, allow_public=allow_public))]))


def test_the_key_in_the_url_opens_it() -> None:
    assert endpoint_behind(KEY).get(f"/mcp?key={KEY}").text == "ok"


def test_the_key_as_a_bearer_token_opens_it() -> None:
    assert endpoint_behind(KEY).get("/mcp", headers={"authorization": f"Bearer {KEY}"}).text == "ok"


def test_no_key_or_a_wrong_one_is_refused() -> None:
    client = endpoint_behind(KEY)

    assert client.get("/mcp").status_code == 401
    assert client.get("/mcp?key=guess").status_code == 401
    assert client.get("/mcp", headers={"authorization": "Bearer guess"}).status_code == 401


def test_without_a_configured_key_it_is_open() -> None:
    assert endpoint_behind(None).get("/mcp").text == "ok"


def test_public_lets_anyone_in_and_the_key_still_works() -> None:
    client = endpoint_behind(KEY, allow_public=True)

    assert client.get("/mcp").text == "ok"
    assert client.get("/mcp", headers={"authorization": f"Bearer {KEY}"}).text == "ok"
