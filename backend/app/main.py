from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import run_startup_migrations_in_background, get_migration_state

# Import routers after config/database imports. Do not perform database work at
# module import time; Render must see the HTTP port quickly.
from app.api import auth, query, schema, analytics, history, websocket

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI Database Copilot",
    description="Enterprise-grade conversational database assistant",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(schema.router, prefix="/api/schema", tags=["Schema"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])


@app.on_event("startup")
async def startup_event():
    run_startup_migrations_in_background()


@app.get("/")
async def root():
    return {"status": "ok", "service": "AI Database Copilot"}


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "migration": get_migration_state(),
    }
