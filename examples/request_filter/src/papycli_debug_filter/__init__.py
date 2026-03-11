"""papycli request filter plugin — debug filter.

Prints the outgoing RequestContext to stdout before each request.
"""

from __future__ import annotations

import json

from papycli.request_filter import RequestContext


def request_filter(ctx: RequestContext) -> RequestContext:
    """Print request context fields to stdout and return it unchanged."""
    q_dict: dict[str, object] = {}
    for k, v in ctx.query_params:
        existing = q_dict.get(k)
        if existing is None:
            q_dict[k] = v
        elif isinstance(existing, list):
            existing.append(v)
        else:
            q_dict[k] = [existing, v]

    print("[papycli-debug-filter]")
    print(f"  Method : {ctx.method.upper()}")
    print(f"  URL    : {ctx.url}")
    print(f"  Query  : {json.dumps(q_dict, ensure_ascii=False) if q_dict else '(none)'}")
    print(f"  Body   : {json.dumps(ctx.body, ensure_ascii=False) if ctx.body is not None else '(none)'}")
    print(f"  Headers: {json.dumps(ctx.headers, ensure_ascii=False) if ctx.headers else '(none)'}")

    return ctx
