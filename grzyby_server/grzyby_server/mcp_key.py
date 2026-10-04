"""A shared key in front of /mcp — the whole access control, on purpose.

The endpoint is public (chatbots call it from their own servers), so it asks for one secret:
`?key=…` in the URL — what a chatbot's connector settings can carry — or
`Authorization: Bearer …` for clients that send headers (Claude Code). No key configured
(on a laptop) means no check. Rotating it = a new value in the platform repo's setup.sh and the
new URL in the connector.
"""

import hmac
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RequireKey:
    """ASGI wrapper: lets a request through only with the right key."""

    def __init__(self, app: ASGIApp, key: str | None) -> None:
        self.app = app
        self.key = key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.key and not _has_key(scope, self.key):
            response = JSONResponse({"detail": "missing or wrong key"}, status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _has_key(scope: Scope, key: str) -> bool:
    given = parse_qs(scope.get("query_string", b"").decode()).get("key", [""])[0]
    for name, value in scope["headers"]:
        if name == b"authorization" and value.startswith(b"Bearer "):
            given = value[len(b"Bearer ") :].decode()
    # Constant time: the comparison must not leak how many characters matched.
    return hmac.compare_digest(given.encode(), key.encode())
