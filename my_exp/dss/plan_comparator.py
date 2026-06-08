"""
my_exp.dss.plan_comparator
==========================
Compare execution plans between original and rewritten SQL queries.
Uses PostgreSQL EXPLAIN ANALYZE to get real execution metrics.
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
# Load .env so DB credentials are available even when called via asyncio.to_thread
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(_root_env)


def get_db_connection(dbname: str = None):
    """Create PostgreSQL connection."""
    dbname = dbname or os.getenv("POSTGRES_DB", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)


def extract_plan_metrics(plan: dict) -> dict:
    """Extract key metrics from PostgreSQL EXPLAIN ANALYZE JSON plan."""
    def walk(node, depth=0):
        metrics = {
            "total_cost": 0.0,
            "total_time": 0.0,
            "rows": 0,
            "max_cost": 0.0,
            "nodes": [],
        }
        if not node:
            return metrics

        cost = node.get("Total Cost", 0.0) or node.get("Execution Time", 0.0)
        time = node.get("Execution Time", 0.0) or 0.0
        rows = node.get("Plan Rows", 0) or 0
        node_type = node.get("Node Type", "")
        op_name = node.get("Operation", node_type)

        metrics["total_cost"] += cost
        metrics["total_time"] += time
        metrics["rows"] = max(metrics["rows"], rows)
        metrics["max_cost"] = max(metrics["max_cost"], cost)
        metrics["nodes"].append({
            "type": op_name,
            "cost": cost,
            "time": time,
            "rows": rows,
            "depth": depth,
        })

        for child in node.get("Plans", []):
            child_metrics = walk(child, depth + 1)
            for k in ["total_cost", "total_time", "rows", "max_cost"]:
                metrics[k] += child_metrics[k]
            metrics["nodes"].extend(child_metrics["nodes"])

        return metrics

    return walk(plan)


def get_explain_analyze(sql: str, conn, format: str = "json") -> Tuple[Optional[dict], Optional[str]]:
    """Get EXPLAIN ANALYZE output for a SQL query."""
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"EXPLAIN (ANALYZE, FORMAT {format}, COSTS, TIMING, BUFFERS) {sql}")
        raw = cur.fetchone()
        cur.close()

        if format == "json":
            plan_str = raw["QUERY PLAN"]
            if isinstance(plan_str, str):
                plans = json.loads(plan_str)
                if plans:
                    return plans[0], None
            elif isinstance(plan_str, list):
                if plan_str:
                    return plan_str[0], None
            return None, "Could not parse plan"
        else:
            return {"text": raw["QUERY PLAN"]}, None

    except psycopg2.Error as e:
        return None, str(e)
    except Exception as e:
        return None, f"Error: {str(e)}"


def compare_plans(original_plan: dict, rewritten_plan: dict) -> dict:
    """Compare two execution plans and compute metrics."""
    orig_metrics = extract_plan_metrics(original_plan)
    rew_metrics = extract_plan_metrics(rewritten_plan)

    cost_ratio = 0.0
    time_ratio = 0.0
    if rew_metrics["total_cost"] > 0:
        cost_ratio = ((orig_metrics["total_cost"] - rew_metrics["total_cost"])
                       / rew_metrics["total_cost"] * 100)
    if rew_metrics["total_time"] > 0:
        time_ratio = ((orig_metrics["total_time"] - rew_metrics["total_time"])
                      / rew_metrics["total_time"] * 100)

    # Determine improvement
    if cost_ratio > 5:
        verdict = "better"
        verdict_vi = "Tot hon"
    elif cost_ratio < -5:
        verdict = "worse"
        verdict_vi = "Kem hon"
    else:
        verdict = "similar"
        verdict_vi = "Tuong duong"

    return {
        "original": {
            "total_cost": round(orig_metrics["total_cost"], 2),
            "total_time_ms": round(orig_metrics["total_time"], 2),
            "estimated_rows": orig_metrics["rows"],
            "nodes": orig_metrics["nodes"],
        },
        "rewritten": {
            "total_cost": round(rew_metrics["total_cost"], 2),
            "total_time_ms": round(rew_metrics["total_time"], 2),
            "estimated_rows": rew_metrics["rows"],
            "nodes": rew_metrics["nodes"],
        },
        "comparison": {
            "cost_improvement_pct": round(cost_ratio, 2),
            "time_improvement_pct": round(time_ratio, 2),
            "verdict": verdict,
            "verdict_vi": verdict_vi,
            "faster": rew_metrics["total_time"] < orig_metrics["total_time"],
            "cheaper": rew_metrics["total_cost"] < orig_metrics["total_cost"],
        }
    }


class PlanComparator:
    """
    Compare execution plans for original vs rewritten SQL queries.
    """

    def __init__(self, dbname: str = None):
        self.dbname = dbname

    def compare(self, original_sql: str, rewritten_sql: str) -> dict:
        """Compare plans for original and rewritten SQL."""
        try:
            conn = get_db_connection(self.dbname)
        except psycopg2.Error as e:
            return {
                "error": f"Cannot connect: {e}",
                "original": None,
                "rewritten": None,
                "comparison": None,
            }

        try:
            orig_plan, orig_err = get_explain_analyze(original_sql, conn)
            rew_plan, rew_err = get_explain_analyze(rewritten_sql, conn)

            result = {
                "original": {
                    "plan": orig_plan,
                    "error": orig_err,
                    "metrics": extract_plan_metrics(orig_plan) if orig_plan else None,
                },
                "rewritten": {
                    "plan": rew_plan,
                    "error": rew_err,
                    "metrics": extract_plan_metrics(rew_plan) if rew_plan else None,
                },
                "comparison": None,
            }

            if orig_plan and rew_plan and not orig_err and not rew_err:
                result["comparison"] = compare_plans(orig_plan, rew_plan)
            elif orig_err:
                result["error"] = f"Original query error: {orig_err}"
            elif rew_err:
                result["error"] = f"Rewritten query error: {rew_err}"

            return result

        finally:
            conn.close()

    def compare_candidates(self, original_sql: str, candidates: list) -> list:
        """Compare plans for all candidates."""
        for c in candidates:
            plan_result = self.compare(original_sql, c["sql"])
            c["plan_comparison"] = plan_result
        return candidates
