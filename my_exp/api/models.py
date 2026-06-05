# my_exp/api/models.py
# Pydantic models — data contract between FastAPI backend and React frontend.
# All response fields use Optional + defaults so the frontend never breaks
# if the legacy LLM pipeline returns incomplete data.

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """POST /api/v1/optimize — incoming SQL + active rules."""

    raw_sql: str = Field(..., description="Raw SQL query string")
    active_rules: list[str] = Field(
        default_factory=list,
        description="List of active rule IDs to apply, e.g. ['projection_pruning', 'join_reordering']",
    )


# ── Metrics ──────────────────────────────────────────────────────────────────

class Metrics(BaseModel):
    """Top-level cost/time metrics for a candidate."""

    total_cost: float = Field(default=0.0, description="Planner total cost estimate")
    io_cost: float = Field(default=0.0, description="I/O cost component")
    cpu_cost: float = Field(default=0.0, description="CPU cost component")
    execution_time_ms: float = Field(default=0.0, description="Estimated execution time in milliseconds")


# ── Rule Recommendation ──────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    """
    A single rule recommendation.
    before_snippet / after_snippet default to "" so the UI always renders.
    """

    rule: str = Field(default="unknown", description="Rule ID, e.g. 'projection_pruning'")
    priority: int = Field(default=99, description="Application priority (1 = highest)")
    reason: str = Field(default="", description="Why this rule should be applied")
    before_snippet: str = Field(default="", description="SQL fragment before optimization")
    after_snippet: str = Field(default="", description="SQL fragment after optimization")


class RuleRecommendations(BaseModel):
    """Top-level rule recommendations block."""

    method: str = Field(default="pattern", description="'llm' or 'pattern'")
    overall_analysis: str = Field(default="", description="LLM's overall analysis of the query")
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="List of rule recommendations with snippets",
    )


# ── Root response ─────────────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """
    POST /api/v1/optimize — full response payload.
    Strictly matches the frontend's expected JSON structure.
    """

    query_id: str = Field(default="unknown", description="Generated or provided query identifier")
    timestamp: str = Field(default="", description="ISO 8601 timestamp")
    original_sql: str = Field(default="", description="The original input SQL")

    rule_recommendations: Optional[RuleRecommendations] = Field(
        default=None,
        description="LLM rule reasoning with before/after snippets",
    )

    metrics: Optional[Metrics] = Field(
        default=None,
        description="Performance metrics for the best candidate",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "q_00001",
                "timestamp": "2026-06-04T10:00:00Z",
                "original_sql": "SELECT * FROM orders WHERE status = 'active'",
                "rule_recommendations": {
                    "method": "llm",
                    "overall_analysis": "Query selects all columns unnecessarily.",
                    "recommendations": [
                        {
                            "rule": "projection_pruning",
                            "priority": 1,
                            "reason": "Removing unnecessary columns reduces I/O.",
                            "before_snippet": "SELECT *",
                            "after_snippet": "SELECT id, status",
                        },
                    ],
                },
                "metrics": {
                    "total_cost": 820.0,
                    "io_cost": 380.0,
                    "cpu_cost": 440.0,
                    "execution_time_ms": 125.0,
                },
            }
        }
