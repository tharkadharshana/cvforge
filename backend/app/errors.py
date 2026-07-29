"""Turn an internal/upstream exception into a client-safe 502, so raw
provider/DB error payloads (which can include quota internals, SQL, stack
info) never reach the response body -- logs the full exception server-side
instead."""
from __future__ import annotations
import logging
from fastapi import HTTPException


def opaque_502(log: logging.Logger, context: str, e: Exception) -> HTTPException:
    log.error("%s: %s", context, e, exc_info=True)
    return HTTPException(status_code=502, detail=f"{context}. Please try again.")
