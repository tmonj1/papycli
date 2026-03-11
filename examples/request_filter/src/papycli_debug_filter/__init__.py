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
    print(f"  Query  : {json.dumps(q_dict, ensure_ascii=False) if q_dict else '(none)'}", file=sys.stderr)
    print(f"  Body   : {json.dumps(ctx.body, ensure_ascii=False) if ctx.body is not None else '(none)'}", file=sys.stderr)
    print(f"  Headers: {json.dumps(ctx.headers, ensure_ascii=False) if ctx.headers else '(none)'}", file=sys.stderr)

    return ctx
