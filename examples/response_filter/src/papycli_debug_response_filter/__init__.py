"""papycli response filter plugin — debug filter.

Prints the received ResponseContext to stderr after each request.

WARNING: This plugin is intended for debugging and development only.
         It prints response headers without redaction, which may expose
         sensitive values such as Set-Cookie or authentication tokens.
         Do NOT use this plugin in production environments.
"""

from __future__ import annotations

import json
import sys

from papycli.request_filter import ResponseContext


def _to_json(value: object) -> str:
    """Serialize value to a JSON string, falling back to repr() on TypeError."""
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return repr(value)


def response_filter(ctx: ResponseContext) -> ResponseContext:
    """Print response context fields to stderr and return it unchanged."""
    print("[papycli-debug-response-filter]", file=sys.stderr)
    print(f"  Method  : {ctx.method.upper()}", file=sys.stderr)
    print(f"  URL     : {ctx.url}", file=sys.stderr)
    print(f"  Status  : {ctx.status_code} {ctx.reason}", file=sys.stderr)
    print(
        f"  Headers : {_to_json(ctx.headers) if ctx.headers else '(none)'}",
        file=sys.stderr,
    )
    print(
        f"  Body    : {_to_json(ctx.body) if ctx.body is not None else '(none)'}",
        file=sys.stderr,
    )

    return ctx
