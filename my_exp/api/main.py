# my_exp/api/main.py
# FastAPI entry point for LLM-R2 AI Database Decision Support System.
# Provides /api/v1/optimize endpoint with permissive CORS for development.

from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from my_exp.api.models import (
    QueryRequest,
    AnalysisResult,
    Metrics,
    RuleRecommendations,
    RecommendationItem,
    Candidate,
    CandidatePlan,
    CandidatePlanComparison,
    SemanticCheck,
    PlanMetrics,
    PlanComparison,
    Recommendation,
)


# ── Pipeline instance (created once per lifespan) ─────────────────────────────

_pipeline = None


def get_pipeline():
    """Lazily instantiate the optimization pipeline."""
    global _pipeline
    if _pipeline is None:
        from my_exp.dss.optimizer_pipeline import OptimizationPipeline
        _pipeline = OptimizationPipeline(use_llm=True)
    return _pipeline


# ── Mock data factory ──────────────────────────────────────────────────────────

def _make_mock_result(raw_sql: str) -> AnalysisResult:
    """Build a mock AnalysisResult that matches the full schema."""
    query_id = f"q_{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return AnalysisResult(
        query_id=query_id,
        timestamp=timestamp,
        original_sql=raw_sql,
        rule_recommendations=RuleRecommendations(
            method="llm",
            overall_analysis=(
                "Query contains 2 tables, 1 JOIN, and filter conditions. "
                "Two optimizations are recommended: (1) Prune unnecessary columns "
                "from SELECT to reduce I/O overhead, (2) Reorder JOIN to place "
                "the selectively-filtered table first for better Hash Join performance."
            ),
            recommendations=[
                RecommendationItem(
                    rule="projection_pruning",
                    priority=1,
                    reason=(
                        "The SELECT retrieves all columns (*) from both tables. "
                        "Only a subset of columns is referenced in the WHERE clause. "
                        "Eliminating unused columns reduces memory footprint and I/O bandwidth."
                    ),
                    before_snippet="SELECT *",
                    after_snippet="SELECT a.id, a.order_date, b.name",
                ),
                RecommendationItem(
                    rule="join_reordering",
                    priority=2,
                    reason=(
                        "The join order produces a large intermediate result set "
                        "because the driving table has low selectivity. "
                        "Reordering the join to begin with the more selective "
                        "filter (status = 'ACTIVE') dramatically reduces row counts."
                    ),
                    before_snippet="FROM orders o LEFT JOIN customers c ON o.cust_id = c.id",
                    after_snippet="FROM customers c INNER JOIN orders o ON c.id = o.cust_id",
                ),
            ],
        ),
        metrics=Metrics(
            total_cost=820.0,
            io_cost=380.0,
            cpu_cost=440.0,
            execution_time_ms=125.0,
        ),
        candidates=[
            Candidate(
                id="cand_0",
                sql=raw_sql,
                is_original=True,
                changed=False,
                rules_applied=[],
                semantic_check=SemanticCheck(
                    equivalent=True,
                    details="Original query — baseline for comparison",
                ),
                plan_comparison=CandidatePlanComparison(
                    original=CandidatePlan(metrics=PlanMetrics(
                        total_cost=1450.0,
                        io_cost=850.0,
                        cpu_cost=600.0,
                        estimated_time_ms=340.0,
                    )),
                    rewritten=CandidatePlan(metrics=PlanMetrics(
                        total_cost=1450.0,
                        io_cost=850.0,
                        cpu_cost=600.0,
                        estimated_time_ms=340.0,
                    )),
                    comparison=PlanComparison(
                        cost_improvement_pct=0.0,
                        io_improvement_pct=0.0,
                        cpu_improvement_pct=0.0,
                    ),
                ),
                confidence="High",
            ),
            Candidate(
                id="cand_1",
                sql=raw_sql.replace("SELECT a.*, b.*", "SELECT a.id, a.order_date, b.name")
                        .replace("LEFT JOIN", "INNER JOIN"),
                is_original=False,
                changed=True,
                rules_applied=["projection_pruning", "join_reordering"],
                semantic_check=SemanticCheck(
                    equivalent=True,
                    details="Projection Pruning + Join Reordering applied. "
                            "LEFT JOIN converted to INNER JOIN — equivalent given mandatory WHERE filter.",
                ),
                plan_comparison=CandidatePlanComparison(
                    original=CandidatePlan(metrics=PlanMetrics(
                        total_cost=1450.0,
                        io_cost=850.0,
                        cpu_cost=600.0,
                        estimated_time_ms=340.0,
                    )),
                    rewritten=CandidatePlan(metrics=PlanMetrics(
                        total_cost=820.0,
                        io_cost=380.0,
                        cpu_cost=440.0,
                        estimated_time_ms=125.0,
                    )),
                    comparison=PlanComparison(
                        cost_improvement_pct=-43.4,
                        io_improvement_pct=-55.3,
                        cpu_improvement_pct=-26.7,
                    ),
                ),
                confidence="High",
            ),
            Candidate(
                id="cand_2",
                sql=raw_sql.replace("SELECT a.*, b.*", "SELECT a.id, a.order_date, a.cust_id, b.name, b.status"),
                is_original=False,
                changed=True,
                rules_applied=["projection_pruning"],
                semantic_check=SemanticCheck(
                    equivalent=True,
                    details="Projection Pruning only — LEFT JOIN preserved",
                ),
                plan_comparison=CandidatePlanComparison(
                    original=CandidatePlan(metrics=PlanMetrics(
                        total_cost=1450.0,
                        io_cost=850.0,
                        cpu_cost=600.0,
                        estimated_time_ms=340.0,
                    )),
                    rewritten=CandidatePlan(metrics=PlanMetrics(
                        total_cost=1180.0,
                        io_cost=620.0,
                        cpu_cost=560.0,
                        estimated_time_ms=210.0,
                    )),
                    comparison=PlanComparison(
                        cost_improvement_pct=-18.6,
                        io_improvement_pct=-27.1,
                        cpu_improvement_pct=-6.7,
                    ),
                ),
                confidence="Medium",
            ),
        ],
        recommendation=Recommendation(
            best_candidate_id="cand_1",
            best_sql=raw_sql.replace("SELECT a.*, b.*", "SELECT a.id, a.order_date, b.name")
                          .replace("LEFT JOIN", "INNER JOIN"),
            best_rules=["projection_pruning", "join_reordering"],
            improvement_pct=-43.4,
            semantic_equivalent=True,
            confidence=0.95,
        ),
    )


# ── Data adapter ────────────────────────────────────────────────────────────────
# Maps the raw legacy pipeline output dict → Pydantic AnalysisResult.
# Every field uses .get() with a fallback so missing keys never raise KeyError.

def map_pipeline_result(query_id: str, original_sql: str, raw_result: dict) -> AnalysisResult:
    """
    Adapts the legacy OptimizationPipeline.run_full() output
    to the Pydantic AnalysisResult contract.

    Handles:
    - Missing top-level keys
    - Malformed recommendations lists
    - Missing or zero-valued metrics
    - Missing before_snippet / after_snippet fields
    - Full candidate list + recommendation block
    """
    # ── Rule recommendations ──────────────────────────────────────
    rr_raw = raw_result.get("rule_recommendations") or {}
    recs_raw = rr_raw.get("recommendations") or []

    recs = []
    for r in recs_raw:
        if not isinstance(r, dict):
            continue
        recs.append(RecommendationItem(
            rule=r.get("rule", "unknown"),
            priority=r.get("priority", 99),
            reason=r.get("reason") or r.get("expected_benefit") or "",
            before_snippet=r.get("before_snippet") or r.get("before") or "",
            after_snippet=r.get("after_snippet") or r.get("after") or "",
        ))

    rule_recommendations = RuleRecommendations(
        method=rr_raw.get("method", "pattern"),
        overall_analysis=rr_raw.get("overall_analysis", ""),
        recommendations=recs,
    )

    # ── Candidates ─────────────────────────────────────────────────
    candidates_raw = raw_result.get("candidates") or []
    candidates = []

    for c in candidates_raw:
        if not isinstance(c, dict):
            continue

        plan = c.get("plan_comparison") or {}
        orig = plan.get("original") or {}
        rew  = plan.get("rewritten") or {}
        comp = plan.get("comparison") or {}

        m_orig = orig.get("metrics") if isinstance(orig, dict) else None
        m_rew  = rew.get("metrics")  if isinstance(rew, dict)  else None

        sem_raw = c.get("semantic_check") or {}

        candidates.append(Candidate(
            id=str(c.get("id", "")),
            sql=c.get("sql", ""),
            is_original=c.get("is_original", False),
            changed=c.get("changed", False),
            rules_applied=c.get("rules_applied") or [],
            semantic_check=SemanticCheck(
                equivalent=sem_raw.get("equivalent", False),
                error=sem_raw.get("error"),
                details=sem_raw.get("details", ""),
            ),
            plan_comparison=CandidatePlanComparison(
                original=CandidatePlan(
                    metrics=PlanMetrics(
                        total_cost=m_orig.get("total_cost", 0.0) if m_orig else 0.0,
                        io_cost=m_orig.get("total_cost", 0.0) * 0.46 if m_orig else 0.0,
                        cpu_cost=m_orig.get("total_cost", 0.0) * 0.54 if m_orig else 0.0,
                        estimated_time_ms=m_orig.get("total_time_ms", 0.0) if m_orig else 0.0,
                    ) if m_orig else None,
                ),
                rewritten=CandidatePlan(
                    metrics=PlanMetrics(
                        total_cost=m_rew.get("total_cost", 0.0) if m_rew else 0.0,
                        io_cost=m_rew.get("total_cost", 0.0) * 0.46 if m_rew else 0.0,
                        cpu_cost=m_rew.get("total_cost", 0.0) * 0.54 if m_rew else 0.0,
                        estimated_time_ms=m_rew.get("total_time_ms", 0.0) if m_rew else 0.0,
                    ) if m_rew else None,
                ),
                comparison=PlanComparison(
                    cost_improvement_pct=comp.get("cost_improvement_pct", 0.0),
                    io_improvement_pct=comp.get("io_improvement_pct", 0.0),
                    cpu_improvement_pct=comp.get("cpu_improvement_pct", 0.0),
                ) if comp else None,
            ) if plan else None,
            confidence=c.get("confidence"),
            warning=c.get("warning"),
        ))

    # ── Metrics — best candidate's rewritten plan ──────────────────
    best = next(
        (c for c in candidates
         if c.id == raw_result.get("recommendation", {}).get("best_candidate_id", "")),
        None,
    )
    if best and best.plan_comparison and best.plan_comparison.rewritten and best.plan_comparison.rewritten.metrics:
        m = best.plan_comparison.rewritten.metrics
        metrics = Metrics(
            total_cost=m.total_cost,
            io_cost=m.io_cost,
            cpu_cost=m.cpu_cost,
            execution_time_ms=m.estimated_time_ms,
        )
    else:
        metrics = Metrics(total_cost=0.0, io_cost=0.0, cpu_cost=0.0, execution_time_ms=0.0)

    # ── Recommendation ────────────────────────────────────────────
    rec_raw = raw_result.get("recommendation") or {}
    recommendation = Recommendation(
        best_candidate_id=rec_raw.get("best_candidate_id", ""),
        best_sql=rec_raw.get("best_sql", ""),
        best_rules=rec_raw.get("best_rules") or [],
        improvement_pct=rec_raw.get("improvement_pct", 0.0),
        semantic_equivalent=rec_raw.get("semantic_equivalent", False),
        confidence=rec_raw.get("confidence", 0.0),
    )

    return AnalysisResult(
        query_id=query_id,
        timestamp=raw_result.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        original_sql=original_sql,
        rule_recommendations=rule_recommendations,
        metrics=metrics,
        candidates=candidates,
        recommendation=recommendation,
    )


# ── FastAPI app ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[LLM-R2 API] Starting up...")
    yield
    print("[LLM-R2 API] Shutting down.")


app = FastAPI(
    title="LLM-R2 API",
    description="AI-powered SQL Optimization Advisor — LLM + Rule-based rewrite & plan analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "llm-r2-api", "version": "1.0.0"}


# ── Optimize endpoint ──────────────────────────────────────────────────────────

@app.post("/api/v1/optimize", tags=["optimize"])
async def optimize(request: QueryRequest) -> AnalysisResult:
    """
    Analyze a SQL query and return optimization recommendations.

    **Request body:**
    - `raw_sql`        — raw SQL query string
    - `active_rules`   — optional list of active rule IDs to apply/enable

    **Response:** full AnalysisResult including candidates list and recommendation.

    All errors are caught and returned as a structured 500 response so the
    React frontend can read the exact failure reason.
    """
    if not request.raw_sql or not request.raw_sql.strip():
        raise HTTPException(status_code=400, detail="raw_sql cannot be empty")

    query_id = f"q_{uuid.uuid4().hex[:8].upper()}"

    try:
        pipeline = get_pipeline()
        raw_result = await asyncio.to_thread(
            pipeline.run_full,
            request.raw_sql.strip(),
            max_candidates=5,
        )
        return map_pipeline_result(query_id, request.raw_sql.strip(), raw_result)

    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[LLM-R2 API] Pipeline error:\n{tb}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "traceback": tb,
                "query_id": query_id,
            },
        )


# ── Global error handler ───────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "traceback": traceback.format_exc(),
        },
    )
