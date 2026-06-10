"""
TPC-H Benchmark Suite for LLM-R2
==================================
Runs all 22 TPC-H queries through the optimization pipeline and generates
a comparison table for thesis documentation.

Usage:
    python -m my_exp.benchmark.tpch_benchmark --output results/tpch_benchmark.md
"""

import argparse
import asyncio
import json
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

sys.path.insert(0, sys.argv[1].rsplit("/", 1)[0] if len(sys.argv) > 1 else ".")

# ── TPC-H Query Definitions ──────────────────────────────────────────────────

TPC_H_QUERIES = {
    1: """SELECT l_returnflag, l_linestatus,
           SUM(l_quantity) AS sum_qty,
           SUM(l_extendedprice) AS sum_base_price,
           SUM(l_extendedprice * (1 - l_discount)) AS sum_disc_price,
           SUM(l_extendedprice * (1 - l_discount) * (1 + l_tax)) AS sum_charge,
           AVG(l_quantity) AS avg_qty,
           AVG(l_extendedprice) AS avg_price,
           AVG(l_discount) AS avg_disc,
           COUNT(*) AS count_order
    FROM lineitem
    WHERE l_shipdate <= DATE '1998-09-02'
    GROUP BY l_returnflag, l_linestatus
    ORDER BY l_returnflag, l_linestatum;""",

    2: """SELECT s_acctbal, s_name, n_name, p_partkey, p_mfgr, s_address, s_phone, s_comment
    FROM part, supplier, partsupp, nation, region
    WHERE p_partkey = ps_partkey
      AND s_suppkey = ps_suppkey
      AND ps_availqty > 0
      AND p_size = 30
      AND p_type LIKE '%BRASS'
      AND s_nationkey = n_nationkey
      AND n_regionkey = r_regionkey
      AND r_name = 'EUROPE'
      AND ps_supplycost = (
          SELECT MIN(ps_supplycost)
          FROM partsupp, supplier, nation, region
          WHERE ps_suppkey = s_suppkey
            AND s_nationkey = n_nationkey
            AND n_regionkey = r_regionkey
            AND r_name = 'EUROPE'
      )
    ORDER BY s_acctbal DESC, n_name, s_name, p_partkey
    LIMIT 100;""",

    3: """SELECT l_orderkey,
           SUM(l_extendedprice * (1 - l_discount)) AS revenue,
           o_orderdate, o_shippriority
    FROM customer, orders, lineitem
    WHERE c_custkey = o_custkey
      AND l_orderkey = o_orderkey
      AND c_mktsegment = 'BUILDING'
      AND o_orderdate < DATE '1995-03-15'
      AND l_shipdate > DATE '1995-03-15'
    GROUP BY l_orderkey, o_orderdate, o_shippriority
    ORDER BY revenue DESC, o_orderdate
    LIMIT 10;""",

    4: """SELECT o_orderpriority, COUNT(*) AS order_count
    FROM orders
    WHERE o_orderdate >= DATE '1993-07-01'
      AND o_orderdate < DATE '1993-10-01'
      AND EXISTS (
          SELECT * FROM lineitem
          WHERE l_orderkey = o_orderkey
            AND l_commitdate < l_receiptdate
      )
    GROUP BY o_orderpriority
    ORDER BY o_orderpriority;""",

    5: """SELECT n_name,
           SUM(l_extendedprice * (1 - l_discount)) AS revenue
    FROM customer, orders, lineitem, supplier, nation, region
    WHERE c_custkey = o_custkey
      AND l_orderkey = o_orderkey
      AND l_suppkey = s_suppkey
      AND c_nationkey = s_nationkey
      AND s_nationkey = n_nationkey
      AND n_regionkey = r_regionkey
      AND r_name = 'ASIA'
      AND o_orderdate >= DATE '1994-01-01'
      AND o_orderdate < DATE '1995-01-01'
    GROUP BY n_name
    ORDER BY revenue DESC;""",

    6: """SELECT SUM(l_extendedprice * l_discount) AS revenue
    FROM lineitem
    WHERE l_shipdate >= DATE '1994-01-01'
      AND l_shipdate < DATE '1995-01-01'
      AND l_discount BETWEEN 0.05 AND 0.07
      AND l_quantity < 24;""",

    7: """SELECT suppnation, custnation, YEAR(o_orderdate) AS l_year,
           SUM(volume) AS revenue
    FROM (
        SELECT s_nationkey AS suppnation, c_nationkey AS custnation,
               l_extendedprice * (1 - l_discount) AS volume, o_orderdate
        FROM supplier, lineitem, orders, customer
        WHERE s_suppkey = l_suppkey
          AND o_orderkey = l_orderkey
          AND c_custkey = o_custkey
          AND (s_nationkey = 1 AND c_nationkey = 18
               OR s_nationkey = 18 AND c_nationkey = 1)
          AND o_orderdate >= DATE '1995-01-01'
          AND o_orderdate <= DATE '1996-12-31'
    ) AS shipping
    GROUP BY suppnation, custnation, YEAR(o_orderdate)
    ORDER BY suppnation, custnation, l_year;""",

    8: """SELECT YEAR(o_orderdate) AS o_year,
           SUM(CASE WHEN n2.n_name = 'BRAZIL' THEN l_extendedprice * (1 - l_discount) ELSE 0 END) AS mkt_share
    FROM orders, lineitem, supplier, customer, nation n1, nation n2, region
    WHERE s_suppkey = l_suppkey
      AND l_orderkey = o_orderkey
      AND o_custkey = c_custkey
      AND c_nationkey = n1.n_nationkey
      AND n1.n_regionkey = r_regionkey
      AND s_nationkey = n2.n_nationkey
      AND r_name = 'AMERICA'
      AND o_orderdate >= DATE '1995-01-01'
      AND o_orderdate <= DATE '1996-12-31'
    GROUP BY YEAR(o_orderdate)
    ORDER BY o_year;""",

    9: """SELECT n_name, YEAR(o_orderdate) AS o_year,
           SUM(l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity) AS amount
    FROM part, supplier, lineitem, partsupp, orders, nation
    WHERE s_suppkey = l_suppkey
      AND ps_suppkey = l_suppkey
      AND ps_partkey = l_partkey
      AND p_partkey = l_partkey
      AND o_orderkey = l_orderkey
      AND s_nationkey = n_nationkey
      AND p_name LIKE '%green%'
    GROUP BY n_name, YEAR(o_orderdate)
    ORDER BY n_name, o_year DESC;""",

    10: """SELECT c_custkey, c_name,
            SUM(l_extendedprice * (1 - l_discount)) AS revenue,
            c_acctbal, n_name, c_address, c_phone, c_comment
    FROM customer, orders, lineitem, nation
    WHERE c_custkey = o_custkey
      AND l_orderkey = o_orderkey
      AND o_orderdate >= DATE '1993-03-01'
      AND o_orderdate < DATE '1993-06-01'
      AND l_returnflag = 'R'
      AND c_nationkey = n_nationkey
    GROUP BY c_custkey, c_name, c_acctbal, n_name, c_address, c_phone, c_comment
    ORDER BY revenue DESC
    LIMIT 20;""",

    11: """SELECT ps_partkey, SUM(ps_supplycost * ps_availqty) AS part_value
    FROM partsupp, supplier, nation
    WHERE s_suppkey = ps_suppkey
      AND s_nationkey = n_nationkey
      AND n_name = 'GERMANY'
    GROUP BY ps_partkey
    HAVING SUM(ps_supplycost * ps_availqty) > (
        SELECT SUM(ps_supplycost * ps_availqty) * 0.0001
        FROM partsupp, supplier, nation
        WHERE s_suppkey = ps_suppkey
          AND s_nationkey = n_nationkey
          AND n_name = 'GERMANY'
    )
    ORDER BY part_value DESC;""",

    12: """SELECT l_shipmode,
            SUM(CASE WHEN o_orderpriority = '1-URGENT' OR o_orderpriority = '2-HIGH' THEN 1 ELSE 0 END) AS high_line_count,
            SUM(CASE WHEN o_orderpriority <> '1-URGENT' AND o_orderpriority <> '2-HIGH' THEN 1 ELSE 0 END) AS low_line_count
    FROM orders, lineitem
    WHERE o_orderkey = l_orderkey
      AND l_shipmode IN ('MAIL', 'SHIP')
      AND l_commitdate < l_receiptdate
      AND l_shipdate < l_commitdate
      AND l_receiptdate >= DATE '1994-01-01'
      AND l_receiptdate < DATE '1995-01-01'
    GROUP BY l_shipmode
    ORDER BY l_shipmode;""",

    13: """SELECT c_count, COUNT(*) AS custdist
    FROM (
        SELECT c_custkey, COUNT(o_orderkey) AS c_count
        FROM customer LEFT OUTER JOIN orders ON c_custkey = o_custkey
                      AND o_comment NOT LIKE '%special%requests%'
        GROUP BY c_custkey
    ) AS c_orders (c_custkey, c_count)
    GROUP BY c_count
    ORDER BY c_count DESC, custdist DESC;""",

    14: """SELECT 100.00 * SUM(CASE WHEN p_type LIKE 'PROMO%' THEN l_extendedprice * (1 - l_discount) ELSE 0 END)
                / SUM(l_extendedprice * (1 - l_discount)) AS promo_revenue
    FROM lineitem, part
    WHERE l_partkey = p_partkey
      AND l_shipdate >= DATE '1995-09-01'
      AND l_shipdate < DATE '1995-10-01';""",

    15: """WITH revenue (supplier_no, total_revenue) AS (
        SELECT l_suppkey, SUM(l_extendedprice * (1 - l_discount))
        FROM lineitem
        WHERE l_shipdate >= DATE '1996-01-01'
          AND l_shipdate < DATE '1996-04-01'
        GROUP BY l_suppkey
    )
    SELECT s_suppkey, s_name, s_address, s_phone, r_total, s_comment
    FROM supplier, revenue
    WHERE s_suppkey = supplier_no
      AND r_total = (SELECT MAX(total_revenue) FROM revenue)
    ORDER BY s_suppkey;""",

    16: """SELECT p_brand, p_type, p_size,
            COUNT(DISTINCT ps_suppkey) AS supplier_cnt
    FROM partsupp, part
    WHERE p_partkey = ps_partkey
      AND p_brand <> 'Brand#45'
      AND p_type NOT LIKE 'MEDIUM POLISHED%'
      AND p_size IN (49, 14, 23, 45, 19, 36, 9, 18)
      AND ps_suppkey NOT IN (
          SELECT s_suppkey FROM supplier WHERE s_comment LIKE '%bad%complaints%'
      )
    GROUP BY p_brand, p_type, p_size
    ORDER BY supplier_cnt DESC, p_brand, p_type, p_size;""",

    17: """SELECT SUM(l_extendedprice) / 7.0 AS avg_yearly
    FROM lineitem, part
    WHERE p_partkey = l_partkey
      AND p_brand = 'Brand#23'
      AND p_container = 'MED BOX'
      AND l_quantity = (SELECT 0.2 * AVG(l_quantity) FROM lineitem WHERE l_partkey = p_partkey);""",

    18: """SELECT c_name, c_custkey, o_orderkey, o_orderdate, o_totalprice, SUM(l_quantity)
    FROM customer, orders, lineitem
    WHERE c_custkey = o_custkey
      AND o_orderkey = l_orderkey
      AND o_orderkey IN (
          SELECT o_orderkey FROM lineitem GROUP BY o_orderkey HAVING SUM(l_quantity) > 300
      )
    GROUP BY c_name, c_custkey, o_orderkey, o_orderdate, o_totalprice
    ORDER BY o_totalprice DESC, o_orderdate
    LIMIT 100;""",

    19: """SELECT SUM(l_extendedprice * (1 - l_discount)) AS revenue
    FROM lineitem, part
    WHERE (p_partkey = l_partkey
      AND p_brand = 'Brand#12'
      AND p_container IN ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG')
      AND l_quantity >= 1 AND l_quantity <= 11
      AND p_size BETWEEN 1 AND 5
      AND l_shipmode IN ('AIR', 'AIR REG')
      AND l_shipinstruct = 'DELIVER IN PERSON')
      OR (p_partkey = l_partkey
      AND p_brand = 'Brand#23'
      AND p_container IN ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK')
      AND l_quantity >= 10 AND l_quantity <= 20
      AND p_size BETWEEN 1 AND 10
      AND l_shipmode IN ('AIR', 'AIR REG')
      AND l_shipinstruct = 'DELIVER IN PERSON')
      OR (p_partkey = l_partkey
      AND p_brand = 'Brand#34'
      AND p_container IN ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG')
      AND l_quantity >= 20 AND l_quantity <= 30
      AND p_size BETWEEN 1 AND 15
      AND l_shipmode IN ('AIR', 'AIR REG')
      AND l_shipinstruct = 'DELIVER IN PERSON');""",

    20: """SELECT s_name, s_address
    FROM supplier, nation
    WHERE s_suppkey IN (
        SELECT ps_suppkey FROM partsupp
        WHERE ps_partkey IN (
            SELECT p_partkey FROM part WHERE p_name LIKE 'forest%'
        )
        AND ps_availqty > (SELECT 0.5 * SUM(l_quantity) FROM lineitem
                          WHERE l_partkey = ps_partkey
                            AND l_shipdate >= DATE '1994-01-01'
                            AND l_shipdate < DATE '1995-01-01')
    )
    AND s_nationkey = n_nationkey
    AND n_name = 'CANADA'
    ORDER BY s_name;""",

    21: """SELECT s_name, COUNT(*) AS numwait
    FROM supplier, lineitem l1, orders, nation
    WHERE s_suppkey = l1.l_suppkey
      AND o_orderkey = l1.l_orderkey
      AND o_orderstatus = 'F'
      AND s_nationkey = n_nationkey
      AND n_name = 'SAUDI ARABIA'
      AND EXISTS (
          SELECT * FROM lineitem l2
          WHERE l2.l_orderkey = l1.l_orderkey
            AND l2.l_suppkey <> l1.l_suppkey
      )
      AND NOT EXISTS (
          SELECT * FROM lineitem l3
          WHERE l3.l_orderkey = l1.l_orderkey
            AND l3.l_suppkey <> l1.l_suppkey
            AND l3.l_receiptdate > l3.l_commitdate
      )
    GROUP BY s_name
    ORDER BY numwait DESC, s_name
    LIMIT 100;""",

    22: """SELECT cntrycode, COUNT(*) AS numcust, SUM(c_acctbal) AS totacctbal
    FROM (
        SELECT SUBSTRING(c_phone, 1, 2) AS cntrycode, c_acctbal
        FROM customer
        WHERE SUBSTRING(c_phone, 1, 2) IN ('13', '31', '23', '29', '30', '18', '17')
          AND c_acctbal > (
              SELECT AVG(c_acctbal) FROM customer
              WHERE c_acctbal > 0.00
                AND SUBSTRING(c_phone, 1, 2) IN ('13', '31', '23', '29', '30', '18', '17')
          )
          AND NOT EXISTS (
              SELECT * FROM orders WHERE o_custkey = c_custkey
          )
    ) AS sale
    GROUP BY cntrycode
    ORDER BY cntrycode;""",
}


@dataclass
class BenchmarkResult:
    query_id: int
    status: str  # OK | ERROR | TIMEOUT
    error: Optional[str]

    # Original metrics
    orig_cost: Optional[float]
    orig_time_ms: Optional[float]
    orig_rows: Optional[int]

    # Best candidate metrics
    best_cand_id: Optional[int]
    best_rules: Optional[list]
    best_semantic_ok: bool
    rew_cost: Optional[float]
    rew_time_ms: Optional[float]
    rew_rows: Optional[int]

    # Improvement
    cost_improvement_pct: Optional[float]
    time_improvement_pct: Optional[float]
    improvement_type: Optional[str]  # BETTER | WORSE | SAME | NO_CANDIDATE | ERROR

    # Optimization details
    num_candidates: int
    method: Optional[str]

    # Index recommendations (NEW)
    index_recommendations: list

    # Raw pipeline result for debugging
    pipeline_error: Optional[str]


async def run_benchmark(
    queries: dict = TPC_H_QUERIES,
    db_params: dict = None,
    rules: list = None,
    timeout_sec: int = 60,
) -> list[BenchmarkResult]:
    """
    Run TPC-H benchmark queries through the optimization pipeline.
    Returns list of BenchmarkResult for each query.
    """
    if db_params is None:
        db_params = {
            "host": "localhost", "port": 5432, "dbname": "tpch",
            "user": "postgres", "password": "nhanpro12"
        }

    if rules is None:
        rules = [
            "predicate_pushdown", "projection_pruning", "join_reordering",
            "subquery_unnesting", "aggregation_pushdown",
            "filter_into_join", "limit_pushdown", "redundant_join_elimination",
        ]

    import requests
    import asyncio

    results = []

    for qid, sql in sorted(queries.items()):
        print(f"  Q{qid:02d}...", end=" ", flush=True)
        try:
            start = time.time()
            resp = requests.post(
                "http://127.0.0.1:8018/api/v1/optimize",
                json={"raw_sql": sql, "active_rules": rules},
                timeout=timeout_sec,
            )
            elapsed = time.time() - start

            if resp.status_code != 200:
                results.append(BenchmarkResult(
                    query_id=qid, status="ERROR", error=f"HTTP {resp.status_code}",
                    orig_cost=None, orig_time_ms=None, orig_rows=None,
                    best_cand_id=None, best_rules=None, best_semantic_ok=False,
                    rew_cost=None, rew_time_ms=None, rew_rows=None,
                    cost_improvement_pct=None, time_improvement_pct=None,
                    improvement_type="ERROR", num_candidates=0, method=None,
                    index_recommendations=[], pipeline_error=resp.text[:500],
                ))
                print(f"HTTP {resp.status_code}")
                continue

            data = resp.json()
            candidates = data.get("candidates") or []
            non_orig = [c for c in candidates if not c.get("is_original")]
            best_id = str(data.get("recommendation", {}).get("best_candidate_id", ""))
            best_id_norm = best_id.replace("cand_", "")
            best = next((c for c in candidates if str(c.get("id", "")) == best_id_norm), None)

            # Original metrics
            orig_plan = None
            for c in candidates:
                if c.get("is_original"):
                    orig_plan = c
                    break

            orig_cost = None
            orig_time_ms = None
            orig_rows = None
            if orig_plan and orig_plan.get("plan_comparison"):
                orig_metrics = orig_plan["plan_comparison"].get("original", {}).get("metrics") or {}
                orig_cost = orig_metrics.get("total_cost")
                orig_time_ms = orig_metrics.get("estimated_time_ms")
                orig_rows = orig_metrics.get("actual_rows")

            # Best candidate metrics
            best_rules = None
            best_semantic_ok = False
            rew_cost = None
            rew_time_ms = None
            rew_rows = None
            cost_imp = None
            time_imp = None

            if best and best.get("plan_comparison"):
                best_rules = best.get("rules_applied", [])
                sem = best.get("semantic_check") or {}
                best_semantic_ok = sem.get("equivalent", False)

                rew_metrics = best["plan_comparison"].get("rewritten", {}).get("metrics") or {}
                rew_cost = rew_metrics.get("total_cost")
                rew_time_ms = rew_metrics.get("estimated_time_ms")
                rew_rows = rew_metrics.get("actual_rows")

                comp = best["plan_comparison"].get("comparison") or {}
                cost_imp = comp.get("cost_improvement_pct")

                if orig_time_ms and rew_time_ms:
                    time_imp = ((orig_time_ms - rew_time_ms) / orig_time_ms) * 100

            # Determine improvement type
            if best is None or best.get("is_original"):
                imp_type = "NO_CANDIDATE"
            elif cost_imp and cost_imp > 0:
                imp_type = "BETTER"
            elif cost_imp and cost_imp < 0:
                imp_type = "WORSE"
            elif cost_imp == 0:
                imp_type = "SAME"
            else:
                imp_type = "UNKNOWN"

            results.append(BenchmarkResult(
                query_id=qid, status="OK", error=None,
                orig_cost=orig_cost, orig_time_ms=orig_time_ms, orig_rows=orig_rows,
                best_cand_id=int(best_id_norm) if best_id_norm.isdigit() else None,
                best_rules=best_rules, best_semantic_ok=best_semantic_ok,
                rew_cost=rew_cost, rew_time_ms=rew_time_ms, rew_rows=rew_rows,
                cost_improvement_pct=cost_imp, time_improvement_pct=time_imp,
                improvement_type=imp_type, num_candidates=len(non_orig),
                method=data.get("rule_recommendations", {}).get("method"),
                index_recommendations=data.get("index_recommendations") or [],
                pipeline_error=None,
            ))
            print(f"{imp_type} ({len(non_orig)} candidates, {elapsed:.1f}s)")

        except requests.exceptions.Timeout:
            results.append(BenchmarkResult(
                query_id=qid, status="TIMEOUT", error="60s timeout",
                orig_cost=None, orig_time_ms=None, orig_rows=None,
                best_cand_id=None, best_rules=None, best_semantic_ok=False,
                rew_cost=None, rew_time_ms=None, rew_rows=None,
                cost_improvement_pct=None, time_improvement_pct=None,
                improvement_type="TIMEOUT", num_candidates=0, method=None,
                index_recommendations=[], pipeline_error="Timeout after 60s",
            ))
            print("TIMEOUT")
        except Exception as exc:
            results.append(BenchmarkResult(
                query_id=qid, status="ERROR", error=str(exc),
                orig_cost=None, orig_time_ms=None, orig_rows=None,
                best_cand_id=None, best_rules=None, best_semantic_ok=False,
                rew_cost=None, rew_time_ms=None, rew_rows=None,
                cost_improvement_pct=None, time_improvement_pct=None,
                improvement_type="ERROR", num_candidates=0, method=None,
                index_recommendations=[], pipeline_error=traceback.format_exc()[:500],
            ))
            print(f"ERROR: {exc}")

    return results


def generate_markdown_table(results: list[BenchmarkResult]) -> str:
    """Generate markdown comparison table for thesis."""
    lines = []
    lines.append("# TPC-H Benchmark Results — LLM-R2 Enhanced")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"\n**Configuration**: PostgreSQL TPC-H, Groq llama-3.3-70b-versatile")
    lines.append(f"**Rules applied**: predicate_pushdown, projection_pruning, join_reordering, subquery_unnesting, aggregation_pushdown, filter_into_join, limit_pushdown, redundant_join_elimination")
    lines.append(f"\n**Summary**: {len([r for r in results if r.status == 'OK'])}/{len(results)} queries completed")
    lines.append(f"**Better**: {len([r for r in results if r.improvement_type == 'BETTER'])} | ")
    lines.append(f"**Worse**: {len([r for r in results if r.improvement_type == 'WORSE'])} | ")
    lines.append(f"**No candidate**: {len([r for r in results if r.improvement_type == 'NO_CANDIDATE'])} | ")
    lines.append(f"**Errors**: {len([r for r in results if r.status != 'OK'])}")
    lines.append("\n## Detailed Results\n")
    lines.append("| Q | Status | Orig Cost | Opt Cost | Cost | Type | Rules | Semantic | Index Recs |")
    lines.append("|---|--------|-----------|----------|--------|--------|-------|---------|------------|")

    for r in results:
        if r.status != "OK":
            lines.append(f"| Q{r.query_id:02d} | {r.status} | — | — | — | — | — | — | — |")
            continue

        orig_cost = f"{r.orig_cost:.1f}" if r.orig_cost else "—"
        rew_cost  = f"{r.rew_cost:.1f}" if r.rew_cost else "—"
        cost_delta = f"{r.cost_improvement_pct:+.1f}%" if r.cost_improvement_pct is not None else "—"

        rules_str = ", ".join(r.best_rules) if r.best_rules else "—"
        sem_str = "OK" if r.best_semantic_ok else "ERR"

        # Color indicator
        type_icon = {"BETTER": "[+]", "WORSE": "[-]", "SAME": "[=]", "NO_CANDIDATE": "[~]"}.get(r.improvement_type, "[?]")

        rules_str = ", ".join(r.best_rules) if r.best_rules else "—"
        idx_count = len(r.index_recommendations) if r.index_recommendations else 0
        idx_str = f"{idx_count} idx" if idx_count > 0 else "—"

        lines.append(f"| Q{r.query_id:02d} | {type_icon} | {orig_cost} | {rew_cost} | {cost_delta} | {r.improvement_type} | {rules_str[:25]} | {sem_str} | {idx_str} |")

    lines.append("\n## Legend")
    lines.append("- **Cost**: PostgreSQL planner estimated cost (from EXPLAIN)")
    lines.append("- **Time**: Actual execution time from EXPLAIN ANALYZE")
    lines.append("- **Cost Δ%**: (orig_cost - rew_cost) / orig_cost × 100 — positive = improved")
    lines.append("- **Time Δ%**: (orig_time - rew_time) / orig_time × 100 — positive = improved")
    lines.append("- **Semantic**: ✅ equivalent, ❌ not equivalent")
    lines.append("- **Rules**: optimization rules applied by LLM-R2")
    lines.append("- **Method**: LLM (Groq llama-3.3-70b-versatile) or pattern fallback")

    return "\n".join(lines)


def generate_summary_stats(results: list[BenchmarkResult]) -> dict:
    """Generate summary statistics."""
    ok = [r for r in results if r.status == "OK"]
    better = [r for r in ok if r.improvement_type == "BETTER"]
    worse  = [r for r in ok if r.improvement_type == "WORSE"]
    no_cand = [r for r in ok if r.improvement_type == "NO_CANDIDATE"]
    errors = [r for r in results if r.status != "OK"]

    cost_imps = [r.cost_improvement_pct for r in ok if r.cost_improvement_pct is not None]
    time_imps = [r.time_improvement_pct for r in ok if r.time_improvement_pct is not None]

    return {
        "total_queries": len(results),
        "completed": len(ok),
        "errors": len(errors),
        "better_count": len(better),
        "worse_count": len(worse),
        "no_candidate_count": len(no_cand),
        "avg_cost_improvement": sum(cost_imps) / len(cost_imps) if cost_imps else 0,
        "avg_time_improvement": sum(time_imps) / len(time_imps) if time_imps else 0,
        "max_cost_improvement": max(cost_imps) if cost_imps else 0,
        "max_time_improvement": max(time_imps) if time_imps else 0,
        "semantic_error_rate": (len([r for r in ok if not r.best_semantic_ok]) / len(ok) * 100) if ok else 0,
        "llm_method_count": len([r for r in ok if r.method == "llm"]),
        "pattern_method_count": len([r for r in ok if r.method == "pattern"]),
    }


async def main():
    parser = argparse.ArgumentParser(description="TPC-H Benchmark Suite for LLM-R2")
    parser.add_argument("--output", "-o", default="results/tpch_benchmark.md",
                        help="Output markdown file")
    parser.add_argument("--timeout", "-t", type=int, default=60,
                        help="Timeout per query in seconds")
    parser.add_argument("--skip", "-s", type=int, nargs="*", default=[],
                        help="Skip these query numbers (e.g., 2 11 13)")
    args = parser.parse_args()

    print("=" * 60)
    print("  LLM-R2 TPC-H Benchmark Suite")
    print("=" * 60)
    print(f"  Output: {args.output}")
    print(f"  Timeout: {args.timeout}s per query")
    if args.skip:
        print(f"  Skipping: Q{', Q'.join(str(x) for x in args.skip)}")
    print()

    # Filter queries
    queries = {k: v for k, v in TPC_H_QUERIES.items() if k not in args.skip}
    print(f"  Running {len(queries)} TPC-H queries...")

    results = await run_benchmark(queries=queries, timeout_sec=args.timeout)

    print()
    print("=" * 60)
    print("  Results Summary")
    print("=" * 60)

    stats = generate_summary_stats(results)
    print(f"  Completed: {stats['completed']}/{stats['total_queries']}")
    print(f"  Better:    {stats['better_count']} | Worse: {stats['worse_count']} | No candidate: {stats['no_candidate_count']}")
    print(f"  Errors:    {stats['errors']}")
    print(f"  Avg Cost improvement: {stats['avg_cost_improvement']:+.1f}% | Max: {stats['max_cost_improvement']:+.1f}%")
    print(f"  Avg Time improvement: {stats['avg_time_improvement']:+.1f}% | Max: {stats['max_time_improvement']:+.1f}%")
    print(f"  LLM method: {stats['llm_method_count']} | Pattern: {stats['pattern_method_count']}")
    print(f"  Semantic error rate: {stats['semantic_error_rate']:.1f}%")
    print()

    # Generate markdown
    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    md = generate_markdown_table(results)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  Markdown saved to: {args.output}")

    # Also save JSON for programmatic use
    json_path = args.output.replace(".md", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "stats": stats,
            "results": [asdict(r) for r in results],
        }, f, indent=2, default=str)
    print(f"  JSON saved to: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
