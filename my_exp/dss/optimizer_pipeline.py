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
from my_exp.core.rules import get_all_rules, get_rule
from my_exp.dss.llm_rule_selector import LLMRuleSelector
from my_exp.dss.semantic_checker import SemanticChecker
from my_exp.dss.plan_comparator import PlanComparator


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

    def select_rules(self, sql: str) -> dict:
        """Step 2: Get rule recommendations."""
        return self.rule_selector.select_rules(sql)

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

    def run_full(self, sql: str, max_candidates: int = 5) -> dict:
        """
        Run the complete optimization pipeline.

        Returns comprehensive analysis with all candidates ranked.
        """
        # Step 1: Analyze
        analysis = self.analyze(sql)

        # Step 2: Rule recommendations
        rule_recs = self.select_rules(sql)

        # Step 3: Generate candidates
        candidates = self.generate_rewrites(sql, max_candidates)

        # Step 4: Compare plans (requires DB connection)
        candidates = self.compare_plans(sql, candidates)

        # Step 5: Semantic verification (requires DB connection)
        candidates = self.verify_semantic(sql, candidates)

        # Step 6: Recommendation
        recommendation = self.recommend(sql, candidates)

        return {
            "query_id": analysis["query_id"],
            "timestamp": analysis["timestamp"],
            "original_sql": sql,
            "analysis": analysis,
            "rule_recommendations": rule_recs,
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
