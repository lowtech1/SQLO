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
    """Build a mock AnalysisResult when no DB is available."""
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
    )


# ── Data adapter ────────────────────────────────────────────────────────────────
# Maps the raw legacy pipeline output dict → Pydantic AnalysisResult.
# Every field uses .get() with a fallback so missing keys never raise KeyError.

def _extract_snippet(full_sql: str, changed_fragment: str) -> tuple[str, str]:
    """
    Extract before/after snippets from full SQL strings.
    Falls back to the full SQL if no clear fragment is identifiable.
    """
    if not full_sql:
        return "", ""
    if not changed_fragment:
        return full_sql, full_sql
    return changed_fragment, full_sql


def map_pipeline_result(query_id: str, original_sql: str, raw_result: dict) -> AnalysisResult:
    """
    Adapts the legacy OptimizationPipeline.run_full() output
    to the Pydantic AnalysisResult contract.

    Handles:
    - Missing top-level keys
    - Malformed recommendations lists
    - Missing or zero-valued metrics
    - Missing before_snippet / after_snippet fields
    """
    # ── Rule recommendations ──────────────────────────────────────
    rr_raw = raw_result.get("rule_recommendations") or {}
    recs_raw = rr_raw.get("recommendations") or []

    recs = []
    for r in recs_raw:
        if not isinstance(r, dict):
            continue
        before = r.get("before_snippet") or r.get("before") or ""
        after  = r.get("after_snippet")  or r.get("after")  or ""
        if not before and not after:
            before, after = _extract_snippet(original_sql, r.get("rule", ""))

        recs.append(RecommendationItem(
            rule=r.get("rule", "unknown"),
            priority=r.get("priority", 99),
            reason=r.get("reason") or r.get("expected_benefit") or "",
            before_snippet=before,
            after_snippet=after,
        ))

    rule_recommendations = RuleRecommendations(
        method=rr_raw.get("method", "pattern"),
        overall_analysis=rr_raw.get("overall_analysis", ""),
        recommendations=recs,
    )

    # ── Metrics — pick the best candidate's rewritten metrics ──────
    metrics = None
    candidates = raw_result.get("candidates") or []
    for c in candidates:
        plan = c.get("plan_comparison") or {}
        rewritten = plan.get("rewritten") or {}
        m = rewritten.get("metrics") if isinstance(rewritten, dict) else None
        if m:
            metrics = Metrics(
                total_cost=m.get("total_cost", 0.0),
                io_cost=m.get("total_cost", 0.0) * 0.46,   # approximate split
                cpu_cost=m.get("total_cost", 0.0) * 0.54,
                execution_time_ms=m.get("total_time_ms", 0.0),
            )
            break

    if metrics is None:
        metrics = Metrics(total_cost=0.0, io_cost=0.0, cpu_cost=0.0, execution_time_ms=0.0)

    return AnalysisResult(
        query_id=query_id,
        timestamp=raw_result.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        original_sql=original_sql,
        rule_recommendations=rule_recommendations,
        metrics=metrics,
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

# ── CORS — allow all origins for local development ───────────────────────────
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


# ── Optimize endpoint — fully defensive ───────────────────────────────────────

@app.post("/api/v1/optimize", tags=["optimize"])
async def optimize(request: QueryRequest) -> AnalysisResult:
    """
    Analyze a SQL query and return optimization recommendations.

    **Request body:**
    - `raw_sql`        — raw SQL query string
    - `active_rules`   — optional list of active rule IDs to apply/enable

    **Response:** AnalysisResult with before/after snippets and metrics.

    All errors are caught and returned as a structured 500 response so the
    React frontend can read the exact failure reason.
    """
    if not request.raw_sql or not request.raw_sql.strip():
        raise HTTPException(status_code=400, detail="raw_sql cannot be empty")

    query_id = f"q_{uuid.uuid4().hex[:8].upper()}"

    try:
        # ── Run the legacy pipeline in a thread pool (non-blocking) ─────
        pipeline = get_pipeline()

        raw_result = await asyncio.to_thread(
            pipeline.run_full,
            request.raw_sql.strip(),
            max_candidates=5,
        )

        # ── Adapt raw pipeline output → Pydantic contract ───────────────
        result = map_pipeline_result(query_id, request.raw_sql.strip(), raw_result)

        return result

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
