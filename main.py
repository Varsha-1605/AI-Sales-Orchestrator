"""
Main FastAPI Application
AI Sales Orchestrator for Omnichannel Retail
"""

import asyncio
import sys
import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ai_workflow.api.routes import router as api_router
from ai_workflow.channels.web import router as web_router
from ai_workflow.graph.orchestrator_graph import create_orchestrator_graph
from ai_workflow.metrics import REQUEST_SECONDS, REQUESTS
from ai_workflow.settings import settings
from ai_workflow.storage.postgres_store import check_postgres, close_postgres, get_checkpointer, open_postgres
from ai_workflow.storage.redis_store import close_redis, ping_redis
from ai_workflow.warmup import warm_up

STARTUP_ATTEMPTS = 5
STARTUP_WAIT_SECONDS = 2

# Logs: one line per event with the request id, or one JSON object per line when LOG_JSON is set
logger.remove()
logger.configure(extra={"request_id": "-"})
logger.add(
    sys.stderr,
    level="DEBUG" if settings.DEBUG_MODE else "INFO",
    serialize=settings.LOG_JSON,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[request_id]} | {message}",
)

# The Postgres driver cannot run on Windows' default event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def retry_startup(name: str, connect):
    """Run `connect` until it works, so the app can start while Redis or Postgres is still booting."""
    for attempt in range(1, STARTUP_ATTEMPTS + 1):
        try:
            return await connect()
        except Exception as error:
            if attempt == STARTUP_ATTEMPTS:
                logger.error("{} is not reachable after {} attempts", name, STARTUP_ATTEMPTS)
                raise
            logger.warning("{} not ready ({}). Retrying in {}s", name, error, STARTUP_WAIT_SECONDS)
            await asyncio.sleep(STARTUP_WAIT_SECONDS)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Sales Orchestrator...")
    await retry_startup("Redis", lambda: asyncio.to_thread(ping_redis))
    await retry_startup("Postgres", open_postgres)
    app.state.graph = create_orchestrator_graph(get_checkpointer())
    await warm_up()
    logger.info("System ready!")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await close_postgres()
    close_redis()

# Create FastAPI app
app = FastAPI(
    title="AI Sales Orchestrator",
    description="Multi-agent system for omnichannel retail",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Token", "Idempotency-Key", "X-Request-ID"],
)


@app.middleware("http")
async def log_and_measure(request: Request, call_next):
    """Give every request an id, log it, and record its time for /metrics."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
        seconds = time.perf_counter() - started
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        REQUESTS.labels(request.method, path, response.status_code).inc()
        REQUEST_SECONDS.labels(request.method, path).observe(seconds)
        logger.info("{} {} -> {} in {:.0f}ms", request.method, request.url.path, response.status_code, seconds * 1000)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(api_router)
app.include_router(web_router)

@app.get("/")
async def root():
    return {
        "message": "AI Sales Orchestrator API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """200 when Redis (and Postgres, if configured) answer; 503 otherwise."""
    try:
        await asyncio.to_thread(ping_redis)
        redis_status = "ok"
    except Exception as error:
        logger.error("Redis health check failed: {}", error)
        redis_status = "down"
    postgres_status = await check_postgres()

    healthy = redis_status == "ok" and postgres_status != "down"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "healthy" if healthy else "unhealthy", "redis": redis_status, "postgres": postgres_status},
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics. Keep this path private (do not route it through Nginx to the internet)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.DEBUG_MODE
    )
