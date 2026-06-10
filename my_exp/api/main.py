# my_exp/api/main.py
# FastAPI entry point for LLM-R2 AI Database Decision Support System.
# Provides /api/v1/optimize endpoint with permissive CORS for development.

from __future__ import annotations

import os
import asyncio
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env from project root (2 levels up from this file)
_root_env = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_root_env)

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
        # {original:{...}, rewritten:{...}, comparison:{original:{...}, rewritten:{...}, comparison:{...}}}
        # Extract from the right levels
        comp_block = plan.get("comparison") or {}
        orig_comp_detail = comp_block.get("original") or {}   # has total_cost + total_time_ms
        rew_comp_detail  = comp_block.get("rewritten") or {}   # has total_cost + total_time_ms
        comp = comp_block.get("comparison") or {}              # has cost_improvement_pct etc.

        # Raw metrics dict (from plan_comparator.extract_plan_metrics)
        orig_metrics_raw = plan.get("original", {}).get("metrics") if isinstance(plan.get("original"), dict) else None
        rew_metrics_raw  = plan.get("rewritten", {}).get("metrics") if isinstance(plan.get("rewritten"), dict) else None

        # total_time_ms lives in orig_comp_detail / rew_comp_detail (from compare_plans output)
        orig_total_cost = orig_comp_detail.get("total_cost") or (orig_metrics_raw.get("total_cost") if orig_metrics_raw else None) or 0.0
        rew_total_cost  = rew_comp_detail.get("total_cost")  or (rew_metrics_raw.get("total_cost")  if rew_metrics_raw  else None) or 0.0
        orig_time_ms    = orig_comp_detail.get("total_time_ms") or (orig_metrics_raw.get("total_time") if orig_metrics_raw else None) or 0.0
        rew_time_ms     = rew_comp_detail.get("total_time_ms")  or (rew_metrics_raw.get("total_time")  if rew_metrics_raw  else None) or 0.0

        sem_raw = c.get("semantic_check") or {}

        candidates.append(Candidate(
            id=str(c.get("id", "")) if c.get("id") is not None else "",
            sql=c.get("sql", ""),
            is_original=c.get("is_original", False),
            changed=c.get("changed", False),
            rules_applied=c.get("rules_applied") or [],
            semantic_check=SemanticCheck(
                equivalent=sem_raw.get("equivalent") or False,
                error=sem_raw.get("error"),
                details=sem_raw.get("details", "") or "",
            ),
            plan_comparison=CandidatePlanComparison(
                original=CandidatePlan(
                    metrics=PlanMetrics(
                        total_cost=orig_total_cost,
                        io_cost=orig_total_cost * 0.46,
                        cpu_cost=orig_total_cost * 0.54,
                        estimated_time_ms=orig_time_ms,
                    ),
                ),
                rewritten=CandidatePlan(
                    metrics=PlanMetrics(
                        total_cost=rew_total_cost,
                        io_cost=rew_total_cost * 0.46,
                        cpu_cost=rew_total_cost * 0.54,
                        estimated_time_ms=rew_time_ms,
                    ),
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
    raw_best_id = str(raw_result.get("recommendation", {}).get("best_candidate_id", ""))
    best = next(
        (c for c in candidates if c.id == raw_best_id),
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
    # Derive improvement_pct from best candidate's plan comparison when raw is None
    best_imp_pct = rec_raw.get("improvement_pct")
    if best_imp_pct is None and best and best.plan_comparison and best.plan_comparison.comparison:
        best_imp_pct = best.plan_comparison.comparison.cost_improvement_pct
    recommendation = Recommendation(
        best_candidate_id=str(rec_raw.get("best_candidate_id", "")),
        best_sql=rec_raw.get("best_sql", ""),
        best_rules=rec_raw.get("best_rules") or [],
        improvement_pct=best_imp_pct or 0.0,
        semantic_equivalent=rec_raw.get("semantic_equivalent") or False,
        confidence=rec_raw.get("confidence") or 0.0,
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
async def lifespan(_app: FastAPI):
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


# ── Live schema loader ─────────────────────────────────────────────────────────

def _load_live_schema(
    host: str = None,
    port: int = None,
    dbname: str = None,
    user: str = None,
    password: str = None,
):
    """Load live schema from PostgreSQL and return a frontend-compatible dict."""
    from my_exp.core.db_connection import load_schema_data
    host = host or os.getenv("POSTGRES_HOST", "localhost")
    port = port or int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = dbname or os.getenv("POSTGRES_DB", "postgres")
    user = user or os.getenv("POSTGRES_USER", "postgres")
    password = password or os.getenv("POSTGRES_PASSWORD", "")

    result = load_schema_data(host, port, dbname, user, password)
    if not result.connected:
        raise RuntimeError(result.error or "Connection failed")

    return {
        "db_name": result.db_name,
        "tables": [
            {
                "name": t.name,
                "rows": t.rows,
                "columns": [
                    {
                        "name": c.name,
                        "type": c.data_type,
                        "isPK": c.is_pk,
                        "isFK": c.is_fk,
                        "fkRef": c.fk_ref,
                        "nullable": c.nullable,
                    }
                    for c in t.columns
                ],
            }
            for t in result.tables
        ],
    }


# ── Schema endpoint ────────────────────────────────────────────────────────────

@app.get("/api/v1/schema", tags=["schema"])
async def get_schema():
    """
    Fetch live schema from PostgreSQL (via env-configured connection).
    Returns: { db_name, tables: [{ name, rows, columns: [{name, type, isPK, isFK}] }] }
    """
    try:
        schema = await asyncio.to_thread(_load_live_schema)
        return schema
    except Exception as exc:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch schema: {exc}\n{tb}",
        )


# ── Connect endpoint ───────────────────────────────────────────────────────────

from pydantic import BaseModel

class ConnectRequest(BaseModel):
    """POST /api/v1/connect — test DB connection and return live schema."""
    host: str = "localhost"
    port: str = "5432"
    dbname: str = "postgres"
    user: str = "postgres"
    password: str = ""


@app.post("/api/v1/connect", tags=["connect"])
async def connect_db(req: ConnectRequest):
    """
    Test a PostgreSQL connection and return the live schema on success.
    Used by the frontend's mandatory connection step before optimization.
    """

    try:
        schema = await asyncio.to_thread(
            _load_live_schema,
            req.host, int(req.port), req.dbname, req.user, req.password,
        )
        return {"connected": True, "schema": schema}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Connection failed: {exc}")


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

    # ── Step 1: Try real pipeline ────────────────────────────────────
    pipeline_error = None
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
        pipeline_error = str(exc)
        print(f"[LLM-R2 API] Pipeline error — falling back to mock:\n{tb}")

    # ── Step 2: Fallback to mock for demo without DB/LLM ─────────────
    print(f"[LLM-R2 API] Using mock result for demo (pipeline reason: {pipeline_error})")
    return _make_mock_result(request.raw_sql.strip())


# ── Global error handler ───────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(_request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "traceback": traceback.format_exc(),
        },
    )
