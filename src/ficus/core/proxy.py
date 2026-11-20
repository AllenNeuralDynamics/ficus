from starlette.types import ASGIApp, Receive, Scope, Send


class ForwardedPrefixMiddleware:
    """Serve under the prefix a reverse proxy stripped, as given in ``X-Forwarded-Prefix``.

    Routing is unchanged (the proxy already removed the prefix); the prefix becomes the request's
    ``root_path``, so the docs page and the OpenAPI ``servers`` point back through the proxy.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            for name, value in scope["headers"]:
                if name == b"x-forwarded-prefix":
                    prefix = value.decode("latin-1").strip().rstrip("/")
                    if prefix:
                        scope = {**scope, "root_path": "/" + prefix.lstrip("/")}
                    break
        await self.app(scope, receive, send)
