"""
JohnnyBets API

FastAPI application for the JohnnyBets sports betting assistant.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from api.routes import chat, tools, entities, payments, scores, daily_intro


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🎰 JohnnyBets API starting...")
    print(f"📊 Model: {os.getenv('BETTING_AGENT_MODEL', 'x-ai/grok-4.1-fast')}")
    yield
    # Shutdown
    print("👋 JohnnyBets API shutting down...")


app = FastAPI(
    title="JohnnyBets API",
    description="AI-powered sports betting analysis with real-time odds, arbitrage detection, and contextual prop analysis.",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:3001",
        "https://johnnybets.ai",  # Production
        "https://www.johnnybets.ai",
        "https://johnnybets.com",
        "https://www.johnnybets.com",
        "https://ca-jbet-web-stg-eus2.blueplant-0e5d4fc7.eastus2.azurecontainerapps.io",  # Staging
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(chat.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(entities.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(scores.router, prefix="/api")
app.include_router(daily_intro.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "JohnnyBets API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat",
            "tools": "/api/tools",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "johnnybets-api",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An error occurred",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

