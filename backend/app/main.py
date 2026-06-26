from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import auth, query, schema, analytics, history, websocket
from app.core.config import settings
from app.core.database import engine, Base

Base.metadata.create_all(bind=engine)

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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
