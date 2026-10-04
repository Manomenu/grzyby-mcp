"""A shared key in front of /mcp — the whole access control, on purpose.

The endpoint is public (chatbots call it from their own servers), so it asks for one secret:
`?key=…` in the URL — what a chatbot's connector settings can carry — or
`Authorization: Bearer …` for clients that send headers (Claude Code). No key configured
(on a laptop) means no check. Rotating it = a new value in the platform repo's setup.sh and the
new URL in the connector.
"""

import hmac
import logging
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

log = logging.getLogger("uvicorn.error")


class RequireKey:
    """ASGI wrapper: lets a request through only with the right key."""

    def __init__(self, app: ASGIApp, key: str | None) -> None:
        self.app = app
        self.key = key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.key and not _has_key(scope, self.key):
            # Why, never what: enough to tell a missing header from a wrong value.
            log.warning("/mcp refused: %s", "wrong key" if _given(scope) else "no key")
            response = JSONResponse({"detail": "missing or wrong key"}, status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _given(scope: Scope) -> str:
    given = parse_qs(scope.get("query_string", b"").decode()).get("key", [""])[0]
    for name, value in scope["headers"]:
        if name == b"authorization" and value.startswith(b"Bearer "):
            given = value[len(b"Bearer ") :].decode()
    return given


def _has_key(scope: Scope, key: str) -> bool:
    # Constant time: the comparison must not leak how many characters matched.
    return hmac.compare_digest(_given(scope).encode(), key.encode())
