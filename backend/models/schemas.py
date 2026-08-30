"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ChatRequest(BaseModel):
    """User chat message request."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")


class ChatResponse(BaseModel):
    """Agent response to a user question."""
    answer: str = Field(..., description="Business insight response")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="Structured metrics data")
    data_quality_notes: List[str] = Field(default_factory=list, description="Relevant data quality warnings")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made in the analysis")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "Skylark BI Agent"
    monday_connected: bool = False
    deals_board: bool = False
    work_orders_board: bool = False
