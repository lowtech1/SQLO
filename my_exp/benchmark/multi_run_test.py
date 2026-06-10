"""
my_exp/benchmark/multi_run_test.py
================================
Multi-run performance testing for LLM-R2.
Runs each query N times to get stable latency metrics (p50, p95, p99).
"""

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

sys.path.insert(0, ".")

import psycopg2


@dataclass
class RunResult:
    query_id: int
    runs: int  # number of successful runs
    orig_times_ms: list  # per-run execution times (original)
    rew_times_ms: list  # per-run execution times (rewritten best)
    orig_costs: list  # planner costs
    rew_costs: list
    orig_latencies: dict  # {"p50": x, "p95": x, "p99": x, "mean": x, "stddev": x}
    rew_latencies: dict
    improvement_pct: Optional[float]  # based on median
    stable: bool  # stddev < 10% of mean
    error: Optional[str]


def percentile(data: list, p: float) -> float:
    """Calculate the p-th percentile of data (0 <= p <= 100)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100.0
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def compute_stats(times: list) -> dict:
    if not times:
        return {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "stddev": 0, "min": 0, "max": 0}
    return {
        "p50": round(percentile(times, 50), 2),
        "p95": round(percentile(times, 95), 2),
        "p99": round(percentile(times, 99), 2),
        "mean": round(statistics.mean(times), 2),
        "stddev": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
        "min": round(min(times), 2),
        "max": round(max(times), 2),
    }


def is_stable(times: list) -> bool:
    """Check if latency is stable (stddev < 10% of mean)."""
    if len(times) < 3:
        return False
    stats = compute_stats(times)
    mean = stats["mean"]
    stddev = stats["stddev"]
    if mean <= 0:
        return False
    return (stddev / mean) < 0.10


def run_query_times(conn, sql: str, n_runs: int = 5) -> tuple[list, list]:
    """
    Run a SQL query n_runs times via EXPLAIN ANALYZE.
    Returns (execution_times_ms, planner_costs).
    """
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '120s'")

    times = []
    costs = []

    for _ in range(n_runs):
        try:
            cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON, TIMING, COSTS) {sql}")
            result = cur.fetchone()[0]
            plan = result[0].get("Plan", {}) if isinstance(result, list) else result.get("Plan", {})
            exec_time = plan.get("Actual Total Time", 0)
            cost = plan.get("Total Cost", 0)
            times.append(exec_time)
            costs.append(cost)
        except Exception as e:
            times.append(0)
            costs.append(0)

    cur.close()
    return times, costs


def run_multi_test(
    sql: str,
    n_runs: int = 5,
    db_params: dict = None,
    rewrite_sql: Optional[str] = None,
) -> dict:
    """
    Run multi-run test for both original and rewritten query.
    """
    if db_params is None:
        db_params = {
            "host": "localhost", "port": 5432, "dbname": "tpch",
            "user": "postgres", "password": "nhanpro12",
        }

    conn = psycopg2.connect(**db_params, connect_timeout=10)
    conn.autocommit = True

    try:
        # Run original query
        orig_times, orig_costs = run_query_times(conn, sql, n_runs)

        # Run rewritten query if provided
        rew_times = []
        rew_costs = []
        if rewrite_sql:
            rew_times, rew_costs = run_query_times(conn, rewrite_sql, n_runs)

        orig_latencies = compute_stats(orig_times)
        rew_latencies = compute_stats(rew_times) if rew_times else {}

        # Improvement based on median (p50)
        if orig_latencies["p50"] > 0 and rew_latencies.get("p50"):
            improvement_pct = (
                (orig_latencies["p50"] - rew_latencies["p50"])
                / orig_latencies["p50"]
            ) * 100
        else:
            improvement_pct = None

        return {
            "orig_times": orig_times,
            "rew_times": rew_times,
            "orig_costs": orig_costs,
            "rew_costs": rew_costs,
            "orig_latencies": orig_latencies,
            "rew_latencies": rew_latencies,
            "improvement_pct": round(improvement_pct, 2) if improvement_pct is not None else None,
            "stable": is_stable(orig_times),
        }

    finally:
        conn.close()


def test_queries(queries: list, n_runs: int = 5, _output: str = None):
    """
    Test multiple queries with multi-run A/B.
    queries: list of (name, sql) tuples
    """
    results = []

    for i, (name, sql) in enumerate(queries):
        print(f"  [{i+1}/{len(queries)}] {name}...", end=" ", flush=True)
        try:
            start = time.time()
            result = run_multi_test(sql, n_runs=n_runs)
            elapsed = time.time() - start
            print(f"OK ({elapsed:.1f}s) — p50={result['orig_latencies']['p50']:.1f}ms, "
                  f"stable={result['stable']}")
            results.append({"name": name, "sql": sql, **result})
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"name": name, "sql": sql, "error": str(e)})

    return results


def generate_ab_report(results: list, output: str = None) -> str:
    """Generate markdown A/B testing report."""
    lines = []
    lines.append("# LLM-R2 Multi-Run A/B Test Report")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"\n**Runs per query**: 5 | **Metrics**: p50, p95, p99, mean, stddev")
    lines.append("\n## Per-Query Results\n")

    for r in results:
        if "error" in r:
            lines.append(f"### {r['name']} — ERROR\n")
            lines.append(f"  `{r['error']}`\n")
            continue

        orig_l = r["orig_latencies"]
        rew_l = r.get("rew_latencies") or {}

        lines.append(f"### {r['name']}")
        def fmt(v, suffix=""):
            if isinstance(v, (int, float)) and v > 0:
                return f"{v:.1f}{suffix}"
            return "-"

        imp = r.get("improvement_pct")
        imp_str = f"{imp:+.1f}%" if imp is not None else "-"

        lines.append(f"| Metric | Original | Rewritten | Delta |")
        lines.append("|--------|----------|-----------|-------|")
        lines.append(f"| p50    | {fmt(orig_l['p50'],'ms')} | {fmt(rew_l.get('p50'),'ms')} | {imp_str} |")
        lines.append(f"| p95    | {fmt(orig_l['p95'],'ms')} | {fmt(rew_l.get('p95'),'ms')} | — |")
        lines.append(f"| p99    | {fmt(orig_l['p99'],'ms')} | {fmt(rew_l.get('p99'),'ms')} | — |")
        lines.append(f"| Mean   | {fmt(orig_l['mean'],'ms')} | {fmt(rew_l.get('mean'),'ms')} | — |")
        lines.append(f"| StdDev | {fmt(orig_l['stddev'],'ms')} | {fmt(rew_l.get('stddev'),'ms')} | — |")
        lines.append(f"| Min    | {fmt(orig_l['min'],'ms')} | {fmt(rew_l.get('min'),'ms')} | — |")
        lines.append(f"| Max    | {fmt(orig_l['max'],'ms')} | {fmt(rew_l.get('max'),'ms')} | — |")
        imp_val = r.get("improvement_pct")
        if imp_val is not None and isinstance(imp_val, (int, float)):
            imp_str = f"{imp_val:+.1f}%"
        else:
            imp_str = "-"
        lines.append(f"**Stable**: {'Yes' if r.get('stable') else 'No'} | **Runs**: {len(r.get('orig_times', []))} | **Improvement**: {imp_str}")
        lines.append("")

    # Summary
    stable_count = sum(1 for r in results if "error" not in r and r.get("stable"))
    lines.append("## Summary\n")
    lines.append(f"- Queries tested: {len(results)}")
    lines.append(f"- Stable results (stddev < 10%): {stable_count}/{len(results)}")

    report = "\n".join(lines)
    if output:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  Report saved to: {output}")

    return report


# ── Quick test queries ─────────────────────────────────────────────────────────

QUICK_TEST = [
    ("Q1 aggregate", "SELECT l_returnflag, l_linestatus, SUM(l_quantity), SUM(l_extendedprice), COUNT(*) FROM lineitem WHERE l_shipdate <= DATE '1998-09-02' GROUP BY l_returnflag, l_linestatus;"),
    ("Q6 discount", "SELECT SUM(l_extendedprice * l_discount) AS revenue FROM lineitem WHERE l_shipdate >= DATE '1994-01-01' AND l_shipdate < DATE '1995-01-01' AND l_discount BETWEEN 0.05 AND 0.07 AND l_quantity < 24;"),
    ("SELECT JOIN", "SELECT c.c_name, o.o_totalprice FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey WHERE c.c_mktsegment = 'AUTOMOBILE' LIMIT 50;"),
    ("Subquery", "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 500000) AND c_nationkey = 1;"),
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-run A/B testing for LLM-R2")
    parser.add_argument("--runs", "-r", type=int, default=5, help="Number of runs per query")
    parser.add_argument("--output", "-o", default="results/ab_test.md", help="Output file")
    args = parser.parse_args()

    print("=" * 60)
    print("  Multi-Run A/B Testing — LLM-R2")
    print("=" * 60)
    print(f"  Runs per query: {args.runs}")
    print(f"  Output: {args.output}")
    print()

    results = test_queries(QUICK_TEST, n_runs=args.runs)
    print()
    report = generate_ab_report(results, args.output)
    print(report)
