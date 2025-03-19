from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .api.routes import prompts, datasets, experiments, traces, metrics, auth, models, chats
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="langchef API",
    description="API for managing LLM workflows, prompts, datasets, and experiments",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(traces.router, prefix="/api/traces", tags=["traces"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])

# For backward compatibility with existing code - add alternative routes
app.include_router(prompts.router, prefix="/prompts", tags=["prompts-alt"])
app.include_router(datasets.router, prefix="/datasets", tags=["datasets-alt"])
app.include_router(experiments.router, prefix="/experiments", tags=["experiments-alt"])
app.include_router(traces.router, prefix="/traces", tags=["traces-alt"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics-alt"])

@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the langchef API"}

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    ) 