import time
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .logging_config import setup_logging, get_logger, request_id_var, client_ip_var
setup_logging()

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401  (register models)
from .routers import auth, cv, generate, billing, jobs, admin

log = get_logger("http")
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CVForge API", version="0.4.0")

# allow_credentials=True forbids the "*" wildcard origin (browsers reject it),
# so list explicit dev + configured frontend origins instead.
_cors_origins = {settings.app_url, "http://localhost:5173", "http://127.0.0.1:5173"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    request_id_var.set(rid)
    client = request.client.host if request.client else "-"
    # respect proxy-forwarded client IP (Render/Cloud Run sit behind proxies)
    fwd = request.headers.get("x-forwarded-for", "")
    client_ip_var.set(fwd.split(",")[0].strip() if fwd else client)
    t0 = time.perf_counter()
    log.info("-> %s %s from %s", request.method, request.url.path, client_ip_var.get())
    try:
        response = await call_next(request)
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        log.exception("xx %s %s unhandled error after %.0fms: %s",
                      request.method, request.url.path, dt, e)
        resp = JSONResponse(status_code=500, content={"detail": "internal error", "request_id": rid})
        resp.headers["X-Request-ID"] = rid
        return resp
    dt = (time.perf_counter() - t0) * 1000
    lvl = log.warning if response.status_code >= 400 else log.info
    lvl("<- %s %s %d %.0fms", request.method, request.url.path, response.status_code, dt)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    rid = request_id_var.get()
    resp = JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.detail, "request_id": rid})
    resp.headers["X-Request-ID"] = rid
    if exc.headers:
        resp.headers.update(exc.headers)
    return resp


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    rid = request_id_var.get()
    resp = JSONResponse(status_code=422,
                        content={"detail": exc.errors(), "request_id": rid})
    resp.headers["X-Request-ID"] = rid
    return resp


app.include_router(auth.router)
app.include_router(cv.router)
app.include_router(generate.router)
app.include_router(billing.router)
app.include_router(jobs.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
