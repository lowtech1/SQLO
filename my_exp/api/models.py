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
    active_rules: list = Field(
        default_factory=list,
        description="List of active rule IDs to apply, e.g. ['projection_pruning', 'join_reordering']",
    )


# ── Metrics ──────────────────────────────────────────────────────────────────

class Metrics(BaseModel):
    """Top-level cost/time metrics for the best candidate."""

    total_cost: float = Field(default=0.0, description="Planner total cost estimate")
    io_cost: float = Field(default=0.0, description="I/O cost component")
    cpu_cost: float = Field(default=0.0, description="CPU cost component")
    execution_time_ms: float = Field(default=0.0, description="Estimated execution time in milliseconds")


# ── Rule Recommendation ──────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    """
    A single rule recommendation with before/after snippet highlighting.
    All fields default to safe values so the UI always renders cleanly.
    """

    rule: str = Field(default="unknown", description="Rule ID, e.g. 'projection_pruning'")
    priority: int = Field(default=99, description="Application priority (1 = highest)")
    reason: str = Field(default="", description="Why this rule should be applied")
    before_snippet: str = Field(default="", description="Exact SQL fragment before optimization")
    after_snippet: str = Field(default="", description="Exact SQL fragment after optimization")


class RuleRecommendations(BaseModel):
    """LLM / pattern reasoning block with top-N recommended rules."""

    method: str = Field(default="pattern", description="'llm' or 'pattern'")
    overall_analysis: str = Field(default="", description="High-level analysis of the query")
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="Ordered list of recommended rules with snippets",
    )


# ── Rule Interactions ────────────────────────────────────────────────────────────

class RuleInteractionItem(BaseModel):
    type: str = Field(default="", description="Interaction type: conflict, order, missing_prereq, redundant")
    rule_a: str = Field(default="", description="Primary rule involved")
    rule_b: Optional[str] = Field(default=None, description="Secondary rule involved")
    description: str = Field(default="", description="Human-readable description")
    severity: str = Field(default="info", description="info | warning | error")
    suggestion: str = Field(default="", description="How to resolve")


class RuleInteractions(BaseModel):
    has_conflicts: bool = Field(default=False)
    has_order_issues: bool = Field(default=False)
    has_missing_prereqs: bool = Field(default=False)
    interactions: list[RuleInteractionItem] = Field(default_factory=list)
    safe_sequence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Query Complexity ─────────────────────────────────────────────────────────────

class QueryComplexity(BaseModel):
    level: str = Field(default="Unknown", description="Complexity level: O(n), O(n log n), O(n^2), O(n^3)")
    score: float = Field(default=0.0, description="Complexity score 0-100")
    label: str = Field(default="", description="Human-readable label")
    factors: list[str] = Field(default_factory=list, description="Contributing factors")
    recommended_rules: list[str] = Field(default_factory=list, description="Rules most effective for this complexity")
    bottleneck_description: str = Field(default="", description="Plain-English bottleneck description")
    complexity_explanation: str = Field(default="", description="Technical explanation")


# ── Index Recommendation ────────────────────────────────────────────────────────

class IndexRecommendation(BaseModel):
    """
    Index recommendation derived from EXPLAIN plan analysis.
    Detects sequential scans on large tables and suggests CREATE INDEX.
    """

    table: str = Field(default="", description="Table name requiring index")
    column: str = Field(default="", description="Column to index")
    index_type: str = Field(default="btree", description="Index type: btree, hash, gist, etc.")
    estimated_size: int = Field(default=0, description="Estimated row count in the table")
    seq_scan_rows: int = Field(default=0, description="Rows scanned by the sequential scan")
    cost_before: float = Field(default=0.0, description="Planner cost before index")
    cost_after: float = Field(default=0.0, description="Estimated planner cost after index")
    improvement_pct: float = Field(default=0.0, description="Estimated cost reduction percentage")
    rationale: str = Field(default="", description="Why this index helps, referencing plan statistics")
    sql: str = Field(default="", description="Full CREATE INDEX DDL statement")


# ── Candidate models (legacy pipeline format) ─────────────────────────────────

class PlanMetrics(BaseModel):
    """Metrics embedded inside a plan comparison block."""

    total_cost: float = Field(default=0.0)
    io_cost: float = Field(default=0.0)
    cpu_cost: float = Field(default=0.0)
    estimated_time_ms: float = Field(default=0.0)


class PlanComparison(BaseModel):
    """Pct improvement computed between original and rewritten plan."""

    cost_improvement_pct: float = Field(default=0.0)
    io_improvement_pct: float = Field(default=0.0)
    cpu_improvement_pct: float = Field(default=0.0)


class CandidatePlan(BaseModel):
    """Wrapper that holds metrics for one side of the comparison."""

    metrics: Optional[PlanMetrics] = Field(default=None)


class CandidatePlanComparison(BaseModel):
    """Full before/after plan comparison inside a candidate."""

    original: Optional[CandidatePlan] = Field(default=None)
    rewritten: Optional[CandidatePlan] = Field(default=None)
    comparison: Optional[PlanComparison] = Field(default=None)


class SemanticCheck(BaseModel):
    """Semantic equivalence result for a candidate rewrite."""

    equivalent: bool = Field(default=False)
    error: Optional[str] = Field(default=None)
    details: str = Field(default="")


class Candidate(BaseModel):
    """
    A single SQL rewrite candidate produced by the MultiRewriteEngine.
    Matches the structure returned by pipeline.run_full() internally.
    """

    id: str = Field(default="cand_0")
    sql: str = Field(default="")
    is_original: bool = Field(default=False)
    changed: bool = Field(default=False)
    rules_applied: list[str] = Field(default_factory=list)
    semantic_check: Optional[SemanticCheck] = Field(default=None)
    plan_comparison: Optional[CandidatePlanComparison] = Field(default=None)
    confidence: Optional[str] = Field(default=None)   # "High" | "Medium" | "Low"
    warning: Optional[str] = Field(default=None)


class Recommendation(BaseModel):
    """Top-level recommendation block — identifies the best candidate."""

    best_candidate_id: str = Field(default="")
    best_sql: str = Field(default="")
    best_rules: list[str] = Field(default_factory=list)
    improvement_pct: float = Field(default=0.0)
    semantic_equivalent: bool = Field(default=False)
    confidence: float = Field(default=0.0)


# ── Root response ─────────────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """
    POST /api/v1/optimize — full response payload.
    Contains both the high-level summary (rule_recommendations + metrics)
    and the full candidate list from the legacy pipeline.
    """

    query_id: str = Field(default="unknown", description="Unique query identifier")
    timestamp: str = Field(default="", description="ISO 8601 timestamp")
    original_sql: str = Field(default="", description="The original input SQL")

    rule_recommendations: Optional[RuleRecommendations] = Field(
        default=None,
        description="LLM/pattern reasoning + ordered rule recommendations",
    )

    rule_interactions: Optional[RuleInteractions] = Field(
        default=None,
        description="Cross-rule conflict, order, and prerequisite analysis",
    )

    explain_plan: Optional[dict] = Field(
        default=None,
        description="Raw PostgreSQL EXPLAIN ANALYZE JSON plan — powers the Visual EXPLAIN Tree",
    )

    complexity: Optional[QueryComplexity] = Field(
        default=None,
        description="Query complexity classification and analysis",
    )

    index_recommendations: list[IndexRecommendation] = Field(
        default_factory=list,
        description="Index recommendations from EXPLAIN plan analysis",
    )

    metrics: Optional[Metrics] = Field(
        default=None,
        description="Performance metrics for the best candidate",
    )

    # Legacy candidate list — powers DecisionCard feed and MetricsPanel
    candidates: list[Candidate] = Field(
        default_factory=list,
        description="All rewrite candidates generated by the pipeline",
    )

    recommendation: Optional[Recommendation] = Field(
        default=None,
        description="Identifies the best candidate and its rules",
    )
