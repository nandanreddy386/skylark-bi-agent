"""Skylark BI Agent — FastAPI Backend.

Provides the REST API for the conversational BI agent.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models.schemas import ChatRequest, ChatResponse, HealthResponse
from agent.agent import BIAgent
from services.monday_service import MondayService, MondayServiceError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Skylark BI Agent API",
    description="AI-powered Business Intelligence agent for Skylark Drones",
    version="1.0.0",
)

# CORS configuration
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent (lazy — will error if env vars missing)
_agent = None


def get_agent() -> BIAgent:
    """Get or create the BIAgent singleton."""
    global _agent
    if _agent is None:
        _agent = BIAgent()
    return _agent


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint — verifies backend and Monday.com connectivity."""
    response = HealthResponse(status="ok", service="Skylark BI Agent")

    try:
        settings = get_settings()
        if settings.monday_api_token:
            monday = MondayService(settings.monday_api_token)
            response.monday_connected = await monday.verify_connection()

            if response.monday_connected and settings.deals_board_id:
                response.deals_board = await monday.check_board_exists(settings.deals_board_id)

            if response.monday_connected and settings.work_orders_board_id:
                response.work_orders_board = await monday.check_board_exists(settings.work_orders_board_id)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        response.status = "degraded"

    return response


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user's business question.

    The agent will:
    1. Classify the question intent
    2. Fetch relevant data from Monday.com
    3. Run deterministic analytics
    4. Generate a business explanation
    """
    logger.info(f"Chat request: {request.message[:100]}")

    try:
        agent = get_agent()
        result = await agent.process_question(request.message)

        return ChatResponse(
            answer=result["answer"],
            metrics=result.get("metrics"),
            data_quality_notes=result.get("data_quality_notes", []),
            assumptions=result.get("assumptions", []),
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your question. Please try again.",
        )


@app.post("/api/refresh")
async def refresh_cache():
    """Force a refresh of the Monday.com data cache."""
    try:
        agent = get_agent()
        agent.clear_cache()
        return {"status": "ok", "message": "Cache cleared. Next query will fetch fresh data."}
    except Exception as e:
        logger.error(f"Cache refresh error: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh cache.")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Skylark BI Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
