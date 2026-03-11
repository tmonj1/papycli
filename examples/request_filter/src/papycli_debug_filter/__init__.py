"""papycli request filter plugin — debug filter.

Prints the outgoing RequestContext to stderr before each request.

WARNING: This plugin is intended for debugging and development only.
         It prints request headers without redaction, which may expose
         sensitive values such as Authorization tokens or API keys.
         Do NOT use this plugin in production environments.
"""

from __future__ import annotations

import json
import sys

from papycli.request_filter import RequestContext


def _to_json(value: object) -> str:
    """Serialize value to a JSON string, falling back to repr() on TypeError."""
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return repr(value)


def request_filter(ctx: RequestContext) -> RequestContext:
    """Print request context fields to stderr and return it unchanged."""
    q_dict: dict[str, object] = {}
    for k, v in ctx.query_params:
        existing = q_dict.get(k)
        if existing is None:
            q_dict[k] = v
        elif isinstance(existing, list):
            existing.append(v)
        else:
            q_dict[k] = [existing, v]

    print("[papycli-debug-filter]", file=sys.stderr)
    print(f"  Method : {ctx.method.upper()}", file=sys.stderr)
    print(f"  URL    : {ctx.url}", file=sys.stderr)
    print(f"  Query  : {_to_json(q_dict) if q_dict else '(none)'}", file=sys.stderr)
    print(f"  Body   : {_to_json(ctx.body) if ctx.body is not None else '(none)'}", file=sys.stderr)
    print(f"  Headers: {_to_json(ctx.headers) if ctx.headers else '(none)'}", file=sys.stderr)

    return ctx
