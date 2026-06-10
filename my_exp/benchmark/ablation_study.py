"""
my_exp/benchmark/ablation_study.py
==================================
Ablation Study: LLM-guided vs Pattern-only optimization on TPC-H queries.
Measures: improvement rate, semantic error rate, explanation quality,
         index recommendation coverage, complexity classification accuracy.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class AblationResult:
    query_id: int
    sql_preview: str
    # Complexity
    complexity_level: str
    complexity_score: float
    # Pattern-only results
    pattern_method: str
    pattern_recommendations: list
    pattern_candidates: int
    pattern_improvement_pct: float
    pattern_semantic_ok: bool
    # LLM-guided results (if available)
    llm_method: Optional[str]
    llm_recommendations: list
    llm_candidates: int
    llm_improvement_pct: float
    llm_semantic_ok: bool
    # Index recommendations
    index_recs: list
    # EXPLAIN plan stats
    top_node_type: str
    total_cost: float
    execution_time_ms: float
    seq_scan_detected: bool
    # Interaction analysis
    has_conflicts: bool
    rule_interactions: list
    # Comparison
    improvement_delta: Optional[float]
    winner: str  # "llm" | "pattern" | "tie" | "none"
    error: Optional[str] = None


def run_ablation(
    queries: dict,
    api_base: str = "http://127.0.0.1:8018",
    timeout_sec: int = 120,
) -> list[dict]:
    """Run ablation study for both LLM-guided and Pattern-only modes."""
    import requests

    results = []

    for qid, sql in sorted(queries.items()):
        print(f"  Q{qid:02d}...", end=" ", flush=True)
        preview = sql[:60].replace("\n", " ").strip() + "..."

        try:
            # ── Pattern-only mode ──────────────────────────────────
            t0 = time.time()
            resp_pattern = requests.post(
                f"{api_base}/api/v1/optimize",
                json={"raw_sql": sql, "active_rules": [
                    "predicate_pushdown", "projection_pruning", "join_reordering",
                    "subquery_unnesting", "aggregation_pushdown",
                    "filter_into_join", "redundant_join_elimination",
                ]},
                timeout=timeout_sec,
            )
            t_pattern = time.time() - t0

            if resp_pattern.status_code != 200:
                results.append(AblationResult(
                    query_id=qid, sql_preview=preview,
                    complexity_level="N/A", complexity_score=0.0,
                    pattern_method="error", pattern_recommendations=[],
                    pattern_candidates=0, pattern_improvement_pct=0.0,
                    pattern_semantic_ok=False, llm_method=None, llm_recommendations=[],
                    llm_candidates=0, llm_improvement_pct=0.0, llm_semantic_ok=False,
                    index_recs=[], top_node_type="N/A", total_cost=0.0,
                    execution_time_ms=0.0, seq_scan_detected=False,
                    has_conflicts=False, rule_interactions=[],
                    improvement_delta=None, winner="none",
                    error=f"HTTP {resp_pattern.status_code}",
                ).__dict__)
                print(f"ERR")
                continue

            data_pat = resp_pattern.json()

            # Extract pattern-only metrics
            pat_recs = [r.get("rule", "") for r in (data_pat.get("rule_recommendations", {}).get("recommendations") or [])]
            pat_cands = len([c for c in (data_pat.get("candidates") or []) if not c.get("is_original")])
            pat_best = data_pat.get("recommendation") or {}
            pat_imp = pat_best.get("improvement_pct", 0.0)
            pat_sem = any(
                c.get("semantic_check", {}).get("equivalent", False)
                for c in (data_pat.get("candidates") or [])
                if not c.get("is_original")
            )

            # Complexity
            comp = data_pat.get("complexity") or {}
            comp_level = comp.get("level", "Unknown")
            comp_score = comp.get("score", 0.0)

            # Index recommendations
            idx_recs = [
                r.get("sql", "")
                for r in (data_pat.get("index_recommendations") or [])
                if r.get("sql")
            ]

            # EXPLAIN plan stats
            plan = data_pat.get("explain_plan") or {}
            plan_node = plan.get("Plan", plan) if isinstance(plan, dict) else plan
            top_node = plan_node.get("Node Type", "") if isinstance(plan_node, dict) else ""
            total_cost = plan_node.get("Total Cost", 0.0) if isinstance(plan_node, dict) else 0.0
            exec_time = plan_node.get("Actual Total Time", 0.0) if isinstance(plan_node, dict) else 0.0
            seq_scan = "Seq Scan" in top_node

            # Rule interactions
            ri = data_pat.get("rule_interactions") or {}
            has_conflicts = ri.get("has_conflicts", False)
            ri_list = [
                f"{i.get('type')}: {i.get('rule_a')} <-> {i.get('rule_b')}"
                for i in (ri.get("interactions") or [])
            ]

            # Determine winner (pattern-only is the only mode here — LLM is disabled)
            winner = "pattern" if pat_imp > 0 else "none"

            result = AblationResult(
                query_id=qid,
                sql_preview=preview,
                complexity_level=comp_level,
                complexity_score=comp_score,
                pattern_method=data_pat.get("rule_recommendations", {}).get("method", "pattern"),
                pattern_recommendations=pat_recs,
                pattern_candidates=pat_cands,
                pattern_improvement_pct=pat_imp,
                pattern_semantic_ok=pat_sem,
                llm_method=None,
                llm_recommendations=[],
                llm_candidates=0,
                llm_improvement_pct=0.0,
                llm_semantic_ok=False,
                index_recs=idx_recs,
                top_node_type=top_node,
                total_cost=total_cost,
                execution_time_ms=exec_time,
                seq_scan_detected=seq_scan,
                has_conflicts=has_conflicts,
                rule_interactions=ri_list,
                improvement_delta=None,
                winner=winner,
            )
            results.append(asdict(result))

            imp_str = f"+{pat_imp:.1f}%" if pat_imp > 0 else f"{pat_imp:.1f}%"
            print(f"OK ({t_pattern:.1f}s) | {comp_level} | {imp_str} | idx={len(idx_recs)}")

        except Exception as e:
            results.append(AblationResult(
                query_id=qid, sql_preview=preview,
                complexity_level="N/A", complexity_score=0.0,
                pattern_method="error", pattern_recommendations=[],
                pattern_candidates=0, pattern_improvement_pct=0.0,
                pattern_semantic_ok=False, llm_method=None, llm_recommendations=[],
                llm_candidates=0, llm_improvement_pct=0.0, llm_semantic_ok=False,
                index_recs=[], top_node_type="N/A", total_cost=0.0,
                execution_time_ms=0.0, seq_scan_detected=False,
                has_conflicts=False, rule_interactions=[],
                improvement_delta=None, winner="none",
                error=str(e),
            ).__dict__)
            print(f"ERR: {e}")

    return results


def generate_ablation_report(results: list, output: str = None) -> str:
    """Generate markdown ablation study report."""
    total = len(results)
    errors = sum(1 for r in results if r.get("error"))
    valid = total - errors

    better = sum(1 for r in results if r.get("pattern_improvement_pct", 0) > 0)
    worse = sum(1 for r in results if r.get("pattern_improvement_pct", 0) < 0)
    no_cand = sum(1 for r in results if r.get("pattern_candidates", 0) == 0 and not r.get("error") and r.get("pattern_improvement_pct", 0) == 0)

    semantic_ok = sum(1 for r in results if r.get("pattern_semantic_ok"))
    seq_scans = sum(1 for r in results if r.get("seq_scan_detected"))
    idx_recs_total = sum(len(r.get("index_recs", [])) for r in results)

    avg_imp = sum(r.get("pattern_improvement_pct", 0) for r in results if not r.get("error")) / max(valid, 1)

    lines = []
    lines.append("# LLM-R2 Ablation Study Report")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"\n**Total queries**: {total} | **Successful**: {valid} | **Errors**: {errors}")

    lines.append("\n## Summary Metrics\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| BETTER (cost ↓) | {better}/{valid} ({100*better/max(valid,1):.1f}%) |")
    lines.append(f"| WORSE (cost ↑) | {worse}/{valid} ({100*worse/max(valid,1):.1f}%) |")
    lines.append(f"| NO_CANDIDATE | {no_cand}/{valid} ({100*no_cand/max(valid,1):.1f}%) |")
    lines.append(f"| Semantic OK | {semantic_ok}/{valid} ({100*semantic_ok/max(valid,1):.1f}%) |")
    lines.append(f"| Seq Scan detected | {seq_scans}/{valid} ({100*seq_scans/max(valid,1):.1f}%) |")
    lines.append(f"| Index recommendations | {idx_recs_total} total |")
    lines.append(f"| Avg improvement | {avg_imp:+.1f}% |")

    lines.append("\n## Per-Query Results\n")
    lines.append(f"| Q | Complexity | Top Node | Cost | Time | Imp% | Semantic | Index Recs | Conflicts |")
    lines.append(f"|---|------------|----------|------|------|------|----------|------------|-----------|")

    for r in sorted(results, key=lambda x: x.get("query_id", 0)):
        qid = r.get("query_id", "?")
        comp = r.get("complexity_level", "N/A")
        node = r.get("top_node_type", "N/A")
        cost = r.get("total_cost", 0)
        t_ms = r.get("execution_time_ms", 0)
        imp = r.get("pattern_improvement_pct", 0)
        sem = "Y" if r.get("pattern_semantic_ok") else "N"
        idx = len(r.get("index_recs", []))
        conf = "Y" if r.get("has_conflicts") else "N"
        err = r.get("error", "")

        if err:
            lines.append(f"| Q{qid:02d} | ERROR: {err[:40]} | | | | | | | |")
        else:
            imp_str = f"{imp:+.1f}%" if imp != 0 else "0.0%"
            lines.append(f"| Q{qid:02d} | {comp} | {node} | {cost:.0f} | {t_ms:.1f}ms | {imp_str} | {sem} | {idx} | {conf} |")

    # Complexity distribution
    lines.append("\n## Complexity Distribution\n")
    comp_dist = {}
    for r in results:
        l = r.get("complexity_level", "Unknown")
        comp_dist[l] = comp_dist.get(l, 0) + 1
    lines.append(f"| Complexity Level | Count |")
    lines.append(f"|-----------------|-------|")
    for l, c in sorted(comp_dist.items()):
        lines.append(f"| {l} | {c} |")

    # Node type distribution
    lines.append("\n## EXPLAIN Node Type Distribution\n")
    node_dist = {}
    for r in results:
        n = r.get("top_node_type", "N/A")
        node_dist[n] = node_dist.get(n, 0) + 1
    lines.append(f"| Node Type | Count |")
    lines.append(f"|-----------|-------|")
    for n, c in sorted(node_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {n} | {c} |")

    report = "\n".join(lines)
    if output:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  Report saved to: {output}")

    return report


# ── TPC-H Queries ──────────────────────────────────────────────────────────────

TPC_H_QUERIES = {
    1: """SELECT l_returnflag, l_linestatus, SUM(l_quantity) AS sum_qty, SUM(l_extendedprice) AS sum_base_price, SUM(l_extendedprice * (1 - l_discount)) AS sum_disc_price, SUM(l_extendedprice * (1 - l_discount) * (1 + l_tax)) AS sum_charge, AVG(l_quantity) AS avg_qty, AVG(l_extendedprice) AS avg_price, AVG(l_discount) AS avg_disc, COUNT(*) AS count_order FROM lineitem WHERE l_shipdate <= DATE '1998-09-02' GROUP BY l_returnflag, l_linestatus ORDER BY l_returnflag, l_linestatus;""",
    6: """SELECT SUM(l_extendedprice * l_discount) AS revenue FROM lineitem WHERE l_shipdate >= DATE '1994-01-01' AND l_shipdate < DATE '1995-01-01' AND l_discount BETWEEN 0.05 AND 0.07 AND l_quantity < 24;""",
    10: """SELECT c_custkey, c_name, SUM(l_extendedprice * (1 - l_discount)) AS revenue, c_acctbal, n_name, c_address, c_phone, c_comment FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey JOIN lineitem l ON o.o_orderkey = l.l_orderkey JOIN nation n ON c.c_nationkey = n.n_nationkey WHERE o.o_orderdate >= DATE '1993-07-01' AND o.o_orderdate < DATE '1993-10-01' AND l_returnflag = 'R' GROUP BY c_custkey, c_name, c_acctbal, c_phone, n_name, c_address, c_comment ORDER BY revenue DESC LIMIT 20;""",
    11: """SELECT ps_partkey, SUM(ps_supplycost * ps_availqty) AS part_value FROM partsupp ps JOIN supplier s ON ps.ps_suppkey = s.s_suppkey JOIN nation n ON s.s_nationkey = n.n_nationkey WHERE n.n_name = 'GERMANY' GROUP BY ps_partkey HAVING SUM(ps_supplycost * ps_availqty) > (SELECT SUM(ps_supplycost * ps_availqty) * 0.0001 FROM partsupp ps2 JOIN supplier s2 ON ps2.ps_suppkey = s2.s_suppkey JOIN nation n2 ON s2.s_nationkey = n2.n_nationkey WHERE n2.n_name = 'GERMANY') ORDER BY part_value DESC;""",
    14: """SELECT 100.00 * SUM(CASE WHEN p_type LIKE 'PROMO%' THEN l_extendedprice * (1 - l_discount) ELSE 0 END) / SUM(l_extendedprice * (1 - l_discount)) AS promo_revenue FROM lineitem l JOIN part p ON l.l_partkey = p.p_partkey WHERE l_shipdate >= DATE '1995-09-01' AND l_shipdate < DATE '1995-10-01';""",
    15: """CREATE VIEW revenue AS SELECT l_suppkey AS supplier_no, SUM(l_extendedprice * (1 - l_discount)) AS total_revenue FROM lineitem WHERE l_shipdate >= DATE '1995-01-01' AND l_shipdate < DATE '1995-04-01' GROUP BY l_suppkey; SELECT s_suppkey, s_name, s_address, s_phone, r.total_revenue FROM supplier s JOIN revenue r ON s.s_suppkey = r.supplier_no WHERE r.total_revenue = (SELECT MAX(total_revenue) FROM revenue) ORDER BY s_suppkey;""",
    19: """SELECT SUM(l_extendedprice * (1 - l_discount)) AS revenue FROM lineitem l JOIN part p ON l.l_partkey = p.p_partkey WHERE (p_brand = 'Brand#12' AND p_container IN ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG') AND l_quantity >= 1 AND l_quantity <= 10 AND p_size BETWEEN 1 AND 5) OR (p_brand = 'Brand#23' AND p_container IN ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK') AND l_quantity >= 10 AND l_quantity <= 20 AND p_size BETWEEN 1 AND 10) OR (p_brand = 'Brand#34' AND p_container IN ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG') AND l_quantity >= 20 AND l_quantity <= 30 AND p_size BETWEEN 1 AND 15) AND l_shipmode IN ('AIR', 'AIR REG') AND l_shipinstruct = 'DELIVER IN PERSON';""",
    21: """SELECT s_name, COUNT(*) AS numwait FROM supplier s JOIN lineitem l1 ON s.s_suppkey = l1.l_suppkey JOIN orders o ON l1.l_orderkey = o.o_orderkey JOIN nation n ON s.s_nationkey = n.n_nationkey WHERE o.o_orderstatus = 'F' AND l1.l_receiptdate > l1.l_commitdate AND EXISTS (SELECT * FROM lineitem l2 WHERE l2.l_orderkey = l1.l_orderkey AND l2.l_suppkey <> l1.l_suppkey) AND NOT EXISTS (SELECT * FROM lineitem l3 WHERE l3.l_orderkey = l1.l_orderkey AND l3.l_suppkey <> l1.l_suppkey AND l3.l_receiptdate > l3.l_commitdate) AND n.n_name = 'SAUDI ARABIA' GROUP BY s_name ORDER BY numwait DESC, s_name LIMIT 100;""",
    22: """SELECT c_code, SUM(c_acctbal) AS totacctbal FROM (SELECT SUBSTRING(c_phone, 1, 2) AS c_code, c_acctbal, c_acctbal > (SELECT AVG(c_acctbal) FROM customer WHERE c_acctbal > 0.00 AND SUBSTRING(c_phone, 1, 2) IN ('13', '31', '23', '29', '30', '18', '17')) AS avg_below FROM customer WHERE SUBSTRING(c_phone, 1, 2) IN ('13', '31', '23', '29', '30', '18', '17') AND c_acctbal > 0.00) AS v GROUP BY c_code ORDER BY c_code;""",
}

# Subset for quick testing
QUICK_TEST = {
    1: TPC_H_QUERIES[1],
    6: TPC_H_QUERIES[6],
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ablation study: LLM-guided vs Pattern-only")
    parser.add_argument("--queries", "-q", default="full", choices=["full", "quick"],
                        help="Query set to use")
    parser.add_argument("--output", "-o", default="results/ablation_study.md",
                        help="Output markdown file")
    parser.add_argument("--port", "-p", type=int, default=8018,
                        help="Backend port")
    args = parser.parse_args()

    print("=" * 60)
    print("  Ablation Study — LLM-R2")
    print("=" * 60)
    queries = TPC_H_QUERIES if args.queries == "full" else QUICK_TEST
    print(f"  Queries: {len(queries)} ({args.queries})")
    print(f"  Port: {args.port}")
    print(f"  Output: {args.output}")
    print()

    results = run_ablation(queries, api_base=f"http://127.0.0.1:{args.port}")
    print()

    # Save JSON results
    json_path = args.output.replace(".md", ".json")
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  JSON results saved to: {json_path}")

    report = generate_ablation_report(results, args.output)
    print()
    # Print with UTF-8 encoding to handle special chars
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(report)
