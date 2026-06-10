"""
my_exp.dss.optimizer_pipeline
============================
Main optimization pipeline that orchestrates all DSS components.
Entry point for the interactive SQL advisor.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from typing import Optional
import uuid
from datetime import datetime

from my_exp.core.multi_rewrite_engine import MultiRewriteEngine
from my_exp.core.sql_analyzer import SQLFeatureExtractor
from my_exp.core.rules import get_rule
from my_exp.dss.llm_rule_selector import LLMRuleSelector
from my_exp.dss.semantic_checker import SemanticChecker
from my_exp.dss.plan_comparator import PlanComparator
from my_exp.dss.index_advisor import IndexAdvisor
from my_exp.core.query_complexity import QueryComplexityClassifier
from my_exp.core.rule_interaction import detect_interactions


class OptimizationPipeline:
    """
    Main pipeline: SQL Input → Analysis → Rule Selection → Rewrite → Compare → Report

    Orchestrates all components:
    1. SQL Feature Extraction
    2. Rule Recommendation (LLM or Pattern)
    3. Multi-Candidate Rewrite Generation
    4. Plan Comparison
    5. Semantic Verification
    6. Final Recommendation
    """

    def __init__(self, use_llm: bool = True, dbname: str = None):
        self.use_llm = use_llm
        self.dbname = dbname
        self.engine = MultiRewriteEngine()
        self.extractor = SQLFeatureExtractor()
        self.rule_selector = LLMRuleSelector(use_llm=use_llm)
        self.semantic_checker = SemanticChecker(dbname=dbname)
        self.plan_comparator = PlanComparator(dbname=dbname)
        self.index_advisor = IndexAdvisor()
        self.complexity_classifier = QueryComplexityClassifier()

    def analyze(self, sql: str) -> dict:
        """Step 1: Analyze SQL query."""
        features = self.extractor.extract(sql)
        summary = self.engine.get_summary(sql)
        return {
            "query_id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "original_sql": sql,
            "parsing_success": features.get("parsing", {}).get("success", False),
            "features": features,
            "summary": summary,
        }

    def select_rules(self, sql: str, plan_context: str = "") -> dict:
        """Step 2: Get rule recommendations."""
        return self.rule_selector.select_rules(sql, plan_context=plan_context)

    def generate_rewrites(self, sql: str, max_candidates: int = 5) -> list:
        """Step 3: Generate rewrite candidates."""
        return self.engine.generate_candidates(sql, max_candidates=max_candidates)

    def compare_plans(self, original_sql: str, candidates: list) -> list:
        """Step 4: Compare execution plans for all candidates."""
        return self.plan_comparator.compare_candidates(original_sql, candidates)

    def verify_semantic(self, original_sql: str, candidates: list) -> list:
        """Step 5: Verify semantic equivalence for all candidates."""
        return self.semantic_checker.check_candidates(original_sql, candidates)

    def recommend(self, original_sql: str, candidates: list) -> dict:
        """
        Step 6: Final recommendation — pick the best candidate.
        Ranking logic:
        1. Must be semantically equivalent
        2. Must have plan comparison available
        3. Rank by cost improvement
        """
        valid = []
        for c in candidates:
            sem = c.get("semantic_check", {})
            plan = c.get("plan_comparison", {})
            comp = plan.get("comparison") if plan else None

            if c.get("is_original"):
                # Original query is always a valid baseline — keep it as fallback
                score = -999
            elif not sem.get("equivalent", False):
                # Skip rewrites that changed semantics
                continue
            elif comp:
                score = comp.get("cost_improvement_pct", 0)
            else:
                score = -10  # No plan data

            valid.append({**c, "_rank_score": score})

        # Sort by score descending (highest improvement = best optimization)
        # Original has score -999 so it only wins when ALL rewrites are invalid
        valid.sort(key=lambda x: x["_rank_score"], reverse=True)

        if not valid:
            return {"error": "No valid candidates"}

        best = valid[0]
        plan_comp = best.get("plan_comparison") or {}
        sem_check = best.get("semantic_check") or {}
        comparison = plan_comp.get("comparison") if plan_comp else None

        return {
            "best_candidate_id": best["id"],
            "best_sql": best["sql"],
            "best_rules": best["rules_applied"],
            "is_original": best["is_original"],
            "rank_score": best["_rank_score"],
            "improvement_pct": comparison.get("cost_improvement_pct") if comparison else None,
            "semantic_equivalent": sem_check.get("equivalent"),
            "confidence": self._compute_confidence(best),
        }

    def _compute_confidence(self, candidate: dict) -> float:
        """Compute overall confidence score for a candidate."""
        sem = candidate.get("semantic_check", {})
        plan = candidate.get("plan_comparison", {})
        comp = plan.get("comparison") if plan else None

        score = 1.0

        # Penalize non-equivalent
        if not sem.get("equivalent", True):
            score *= 0.2

        # Bonus for plan improvement
        if comp and comp.get("cost_improvement_pct", 0) > 20:
            score *= 1.2

        # Penalize if no plan data
        if not comp:
            score *= 0.8

        return min(score, 1.0)

    def _summarize_plan(self, plan_data: dict) -> str:
        """
        Extract bottleneck summary from EXPLAIN JSON plan for LLM context.
        Returns a human-readable plan summary.
        """
        if not plan_data:
            return ""

        plan = plan_data.get("Plan", {})
        lines = []

        # Top-level metrics
        total_cost = plan.get("Total Cost", 0)
        est_rows = plan.get("Plan Rows", 0)
        total_time = plan.get("Actual Total Time", 0)
        lines.append(f"Total Cost: {total_cost:.1f} | Estimated Rows: {est_rows} | Execution Time: {total_time:.2f}ms")

        # Bottleneck nodes — recursively traverse plan tree
        def extract_bottlenecks(node: dict, depth: int = 0) -> list:
            bottlenecks = []
            node_type = node.get("Node Type", "")
            cost = node.get("Total Cost", 0)
            rows = node.get("Plan Rows", 0)
            actual_time = node.get("Actual Total Time", 0)
            rel = node.get("Relation Name", "")

            # Skip trivial nodes
            if cost > 0 and depth <= 3:
                label = f"{'  ' * depth}{node_type}"
                if rel:
                    label += f" on {rel}"
                label += f" (cost={cost:.0f}, rows={rows}"
                if actual_time > 0:
                    label += f", time={actual_time:.2f}ms"
                label += ")"
                bottlenecks.append(label)

            # Check for specific bottlenecks
            if node_type in ("Seq Scan", "Parallel Seq Scan"):
                filter_str = node.get("Filter", "")
                if filter_str:
                    bottlenecks.append(f"  {'  ' * depth}  -> Filter: {filter_str[:80]}")

            # Recurse into children
            for key in ("Plans", "Inner", "Outer", "Parent Relationship"):
                child = node.get(key)
                if isinstance(child, dict):
                    bottlenecks.extend(extract_bottlenecks(child, depth + 1))
                elif isinstance(child, list):
                    for c in child:
                        if isinstance(c, dict):
                            bottlenecks.extend(extract_bottlenecks(c, depth + 1))

            return bottlenecks

        lines.extend(extract_bottlenecks(plan))

        # Key plan statistics
        buf_stats = plan_data.get("Buffers", {})
        shared_hit = buf_stats.get("shared_hit", 0) if isinstance(buf_stats, dict) else 0
        shared_read = buf_stats.get("shared_read", 0) if isinstance(buf_stats, dict) else 0

        if shared_read > 0 or shared_hit > 0:
            lines.append(f"Buffers: {shared_hit} hits, {shared_read} reads")

        return "\n".join(lines[:40])  # Cap at 40 lines for prompt length

    def explain_query(self, sql: str) -> Optional[dict]:
        """
        Get EXPLAIN ANALYZE output for a SQL query.
        Returns the plan JSON dict or None on error.
        """
        try:
            import psycopg2
            import os
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=self.dbname or os.getenv("POSTGRES_DB", "postgres"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                connect_timeout=10,
            )
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f"SET statement_timeout = '60s'")
            cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON, COSTS, TIMING, BUFFERS) {sql}")
            result = cur.fetchone()
            cur.close()
            conn.close()
            if result and result[0] is not None:
                # psycopg2 may return JSON as dict/list automatically
                plan_data = result[0]
                if isinstance(plan_data, str):
                    import json
                    plan_data = json.loads(plan_data)
                return plan_data[0] if isinstance(plan_data, list) else plan_data
            return None
        except Exception:
            return None

    def run_full(self, sql: str, max_candidates: int = 5) -> dict:
        """
        Run the complete optimization pipeline with EXPLAIN-guided LLM.

        Pipeline order:
        1. Analyze SQL structure
        2. Get EXPLAIN ANALYZE of original query  ← NEW
        3. LLM rule selection WITH plan context   ← KEY IMPROVEMENT
        4. Generate rewrite candidates
        5. Compare execution plans
        6. Semantic verification
        7. Final recommendation
        """
        # Step 1: Analyze
        analysis = self.analyze(sql)

        # Step 2: Get EXPLAIN plan of original (NEW — feeds LLM context)
        plan_json = self.explain_query(sql)
        plan_summary = self._summarize_plan(plan_json) if plan_json else ""

        # Step 2b: Query complexity analysis (NEW)
        complexity = self.complexity_classifier.classify(sql, features=analysis.get("features"), plan_data=plan_json)
        complexity_result = {
            "level": complexity.level.value,
            "score": complexity.score,
            "label": complexity.label,
            "factors": complexity.factors,
            "recommended_rules": complexity.recommended_rules,
            "bottleneck_description": complexity.bottleneck_description,
            "complexity_explanation": complexity.complexity_explanation,
        }

        # Step 3: Rule recommendations (WITH plan context)
        rule_recs = self.select_rules(sql, plan_context=plan_summary)

        # Step 3b: Cross-rule interaction analysis
        selected_rules = [r.get("rule") for r in (rule_recs.get("recommendations") or [])]
        interaction_report = detect_interactions(selected_rules)

        # Step 3c: Index recommendations from plan analysis
        index_recs = []
        if plan_json:
            raw_recs = self.index_advisor.analyze_plan(plan_json)
            index_recs = [
                {
                    "table": r.table_name,
                    "column": r.column_name,
                    "index_type": r.index_type,
                    "estimated_size": r.estimated_size,
                    "seq_scan_rows": r.seq_scan_rows,
                    "cost_before": round(r.cost_before, 2),
                    "cost_after": round(r.cost_estimate_after, 2),
                    "improvement_pct": round(r.improvement_pct, 1),
                    "rationale": r.rationale,
                    "sql": r.sql,
                }
                for r in raw_recs[:5]  # Top 5 recommendations
            ]

        # Step 4: Generate candidates
        candidates = self.generate_rewrites(sql, max_candidates)

        # Step 5: Compare plans (requires DB connection)
        candidates = self.compare_plans(sql, candidates)

        # Step 6: Semantic verification (requires DB connection)
        candidates = self.verify_semantic(sql, candidates)

        # Step 7: Recommendation
        recommendation = self.recommend(sql, candidates)

        return {
            "query_id": analysis["query_id"],
            "timestamp": analysis["timestamp"],
            "original_sql": sql,
            "analysis": analysis,
            "rule_recommendations": rule_recs,
            "explain_plan": plan_json,  # Raw plan JSON for Visual EXPLAIN Tree
            "rule_interactions": {
                "has_conflicts": interaction_report.has_conflicts,
                "has_order_issues": interaction_report.has_order_issues,
                "has_missing_prereqs": interaction_report.has_missing_prereqs,
                "interactions": [
                    {
                        "type": i.interaction_type,
                        "rule_a": i.rule_a,
                        "rule_b": i.rule_b,
                        "description": i.description,
                        "severity": i.severity,
                        "suggestion": i.suggestion,
                    }
                    for i in interaction_report.interactions
                ],
                "safe_sequence": interaction_report.safe_sequence,
                "warnings": interaction_report.warnings,
            },
            "index_recommendations": index_recs,
            "complexity": complexity_result,
            "candidates": candidates,
            "recommendation": recommendation,
            "metadata": {
                "llm_used": self.use_llm,
                "dbname": self.dbname,
                "total_candidates": len(candidates),
                "equivalent_candidates": sum(
                    1 for c in candidates
                    if c.get("semantic_check", {}).get("equivalent", False)
                ),
            }
        }

    def explain_rule(self, rule_name: str, sql: str) -> dict:
        """Get detailed explanation for why a rule applies."""
        rule = get_rule(rule_name)
        if not rule:
            return {"error": f"Rule '{rule_name}' not found"}

        explanation = rule.explain(sql)
        features = self.extractor.extract(sql)

        return {
            "rule": rule_name,
            "metadata": rule.METADATA,
            "analysis": explanation,
            "sql_features": features.get("complexity", {}),
        }
