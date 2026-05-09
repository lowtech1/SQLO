import os
import sys
import json

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.experiments.candidate_generator import CandidateGenerator
from my_exp.evaluator.result_checker import ResultChecker
from my_exp.evaluator.postgres_runner import PostgresRunner
from my_exp.evaluator.explain_parser import ExplainParser
from my_exp.evaluator.plan_comparator import PlanComparator

class CostAwareOptimizer:
    """
    Evaluates generated candidates against PostgreSQL, checks semantic equivalence,
    and applies a multi-factor scoring formula to select the best query rewrite.
    """

    def __init__(self):
        self.generator = CandidateGenerator()
        self.checker = ResultChecker()
        self.runner = PostgresRunner()
        self.parser = ExplainParser()
        self.comparator = PlanComparator()

    def _calculate_improvement(self, original, new_val):
        if original is None or new_val is None or original == 0:
            return 0.0
        return float(((original - new_val) / original) * 100)

    def optimize(self, sql: str) -> dict:
        """
        Runs the full optimization workflow for a given SQL query.
        """
        # 1. Generate candidate rewrites using the new extensive CandidateGenerator
        candidates = self.generator.generate_candidates(sql)
        
        try:
            self.runner.connect()
        except Exception as e:
            return {
                "best_sql": sql, 
                "best_rules": [], 
                "best_score": 0.0, 
                "optimizer_reasoning": f"DB connection failed: {e}",
                "evaluated_candidates": 0,
                "rejected_candidates": [{"reason": str(e)}]
            }

        # Baseline EXPLAIN ANALYZE for the original SQL
        orig_plan = None
        orig_time = float('inf')
        orig_cost = float('inf')
        
        try:
            orig_plan = self.runner.explain_analyze(sql)
            if orig_plan:
                orig_metrics = self.parser.parse(orig_plan)
                orig_time = orig_metrics.get("execution_time") or float('inf')
                orig_cost = orig_metrics.get("total_cost") or float('inf')
        except Exception as e:
            return {
                "best_sql": sql, 
                "best_rules": [], 
                "best_score": 0.0, 
                "optimizer_reasoning": f"Could not EXPLAIN ANALYZE original SQL: {e}",
                "evaluated_candidates": 0,
                "rejected_candidates": []
            }
        
        best_candidate = None
        best_score = 0.0
        best_reasoning = ""
        
        evaluated_count = 0
        rejected_candidates = []

        # 2. Evaluate each candidate
        for cand in candidates:
            c_id = cand.get("candidate_id")
            c_sql = cand.get("rewritten_sql", "")
            c_rules = cand.get("applied_rules", [])
            c_error = cand.get("error")
            
            # 4. Handle candidate generation errors gracefully
            if c_error:
                rejected_candidates.append({
                    "candidate_id": c_id,
                    "rules": c_rules,
                    "reason": f"Generation error: {c_error}"
                })
                continue
                
            if not c_sql or c_sql.strip() == sql.strip():
                rejected_candidates.append({
                    "candidate_id": c_id,
                    "rules": c_rules,
                    "reason": "No SQL changes produced"
                })
                continue
                
            # 2. Semantic equivalence check
            try:
                equiv_res = self.checker.check_equivalence(sql, c_sql)
                if not equiv_res.get("is_equivalent", False):
                    rejected_candidates.append({
                        "candidate_id": c_id,
                        "rules": c_rules,
                        "reason": f"Semantic mismatch: {equiv_res.get('message', 'Result sets differ')}"
                    })
                    continue
            except Exception as e:
                rejected_candidates.append({
                    "candidate_id": c_id,
                    "rules": c_rules,
                    "reason": f"Equivalence check crashed: {e}"
                })
                continue
                
            # 2. EXPLAIN ANALYZE for the candidate
            try:
                cand_plan = self.runner.explain_analyze(c_sql)
                if not cand_plan:
                    rejected_candidates.append({
                        "candidate_id": c_id,
                        "rules": c_rules,
                        "reason": "Explain analyze returned empty plan"
                    })
                    continue
            except Exception as e:
                rejected_candidates.append({
                    "candidate_id": c_id,
                    "rules": c_rules,
                    "reason": f"Explain analyze crashed: {e}"
                })
                continue
                
            evaluated_count += 1
            cand_metrics = self.parser.parse(cand_plan)
            cand_time = cand_metrics.get("execution_time") or float('inf')
            cand_cost = cand_metrics.get("total_cost") or float('inf')
            
            # 2. Plan comparison to get specific reduction metrics
            comp_report = self.comparator.generate_analysis_report(orig_plan, cand_plan)
            perf_sum = comp_report.get("performance_summary", {})
            scan_red = perf_sum.get("scan_reduction", 0)
            join_eff = perf_sum.get("join_efficiency", 0)
            
            # Scale row reduction to a manageable 0-100 baseline score 
            row_red = perf_sum.get("row_reduction", 0)
            row_reduction_score = min(100.0, float(row_red) / 100.0) if row_red > 0 else 0.0
            
            cost_reduction_percent = self._calculate_improvement(orig_cost, cand_cost)
            time_improvement_percent = self._calculate_improvement(orig_time, cand_time)
            
            # 3. Scoring formula
            score = (
                (0.30 * time_improvement_percent) + 
                (0.30 * cost_reduction_percent) + 
                (0.15 * scan_red) + 
                (0.15 * join_eff) + 
                (0.10 * row_reduction_score)
            )
            
            # Update best candidate
            if score > best_score:
                best_score = score
                best_candidate = cand
                reasoning_list = comp_report.get("optimizer_reasoning", [])
                
                # Make output fully explainable
                explainable_parts = []
                if time_improvement_percent > 0:
                    explainable_parts.append(f"Time improved by {time_improvement_percent:.1f}%")
                if cost_reduction_percent > 0:
                    explainable_parts.append(f"Cost reduced by {cost_reduction_percent:.1f}%")
                if scan_red > 0:
                    explainable_parts.append(f"Removed {scan_red} sequential scans")
                if join_eff > 0:
                    explainable_parts.append("Improved join strategy")
                if row_red > 0:
                    explainable_parts.append(f"Reduced intermediate rows by {row_red}")
                    
                custom_reason = ", ".join(explainable_parts)
                if reasoning_list:
                    best_reasoning = f"{custom_reason}. Analysis: {' '.join(reasoning_list)}"
                else:
                    best_reasoning = custom_reason if custom_reason else "Score improvement observed without distinct plan shifts."

        # 5. Output
        if best_candidate and best_score > 0:
            return {
                "best_sql": best_candidate["rewritten_sql"],
                "best_rules": best_candidate["applied_rules"],
                "best_score": round(best_score, 2),
                "optimizer_reasoning": best_reasoning,
                "evaluated_candidates": evaluated_count,
                "rejected_candidates": rejected_candidates
            }
            
        # 6. Keep original if no candidate is better
        return {
            "best_sql": sql,
            "best_rules": [],
            "best_score": 0.0,
            "optimizer_reasoning": "No candidate improved the query. Kept original SQL.",
            "evaluated_candidates": evaluated_count,
            "rejected_candidates": rejected_candidates
        }

    def close(self):
        """Clean up DB connections."""
        self.checker.close()
        self.runner.close()

if __name__ == "__main__":
    print("Testing CostAwareOptimizer...")
    optimizer = CostAwareOptimizer()
    
    # Mock Test Query
    test_sql = "SELECT * FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders);"
    print(f"Original SQL:\n{test_sql}\n")
    
    result = optimizer.optimize(test_sql)
    
    print("Optimizer Decision:")
    print(json.dumps({
        "best_rules": result["best_rules"],
        "best_score": result["best_score"],
        "optimizer_reasoning": result["optimizer_reasoning"],
        "evaluated_count": result["evaluated_candidates"],
        "rejected_count": len(result["rejected_candidates"])
    }, indent=2))
    optimizer.close()
