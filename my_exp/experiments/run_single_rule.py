import json
import csv
import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.rules.rule_registry import RULES as OLD_RULES

from my_exp.ast_rewriter.ast_predicate_pushdown import ASTPredicatePushdown
from my_exp.ast_rewriter.ast_projection_pruning import ASTProjectionPruning
from my_exp.ast_rewriter.ast_subquery_unnesting import ASTSubqueryUnnesting
from my_exp.ast_rewriter.ast_join_reordering import ASTJoinReordering
from my_exp.ast_rewriter.ast_aggregation_pushdown import ASTAggregationPushdown
from my_exp.ast_rewriter.ast_redundant_join_elimination import ASTRedundantJoinElimination
from my_exp.ast_rewriter.ast_filter_into_join import ASTFilterIntoJoin

try:
    # pyrefly: ignore [missing-import]
    from my_exp.ast_rewriter.ast_limit_pushdown import ASTLimitPushdown
except ImportError:
    class ASTLimitPushdown:
        def apply(self, sql: str) -> str:
            return sql

from my_exp.evaluator.postgres_runner import PostgresRunner
from my_exp.evaluator.explain_parser import ExplainParser
from my_exp.evaluator.result_checker import ResultChecker
from my_exp.evaluator.plan_comparator import PlanComparator

def calculate_improvement(original, new_val):
    if original is None or new_val is None or original == 0:
        return 0.0
    return float(round(((original - new_val) / original) * 100, 2))

def run_single_rule_experiments():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    queries_file = os.path.join(base_dir, 'queries', 'test_cases.json')
    results_file = os.path.join(base_dir, 'results', 'single_rule_results.csv')

    if not os.path.exists(queries_file):
        print(f"Error: {queries_file} not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    # 1. Combine all rules
    all_rules = {}
    for name, rule in OLD_RULES.items():
        all_rules[f"old_{name}"] = rule
        
    all_rules.update({
        "ast_predicate_pushdown": ASTPredicatePushdown(),
        "ast_projection_pruning": ASTProjectionPruning(),
        "ast_subquery_unnesting": ASTSubqueryUnnesting(),
        "ast_join_reordering": ASTJoinReordering(),
        "ast_aggregation_pushdown": ASTAggregationPushdown(),
        "ast_redundant_join_elimination": ASTRedundantJoinElimination(),
        "ast_filter_into_join": ASTFilterIntoJoin(),
        "ast_limit_pushdown": ASTLimitPushdown()
    })

    runner = None
    parser = None
    checker = None
    comparator = None
    
    try:
        runner = PostgresRunner()
        parser = ExplainParser()
        checker = ResultChecker()
        comparator = PlanComparator()
        runner.connect()
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    results = []
    
    print("Starting single-rule experiments...")

    for i, query in enumerate(queries, 1):
        query_id = query.get('query_id', f'unknown_{i}')
        original_sql = query.get('sql', '')
        
        # 2. Get baseline metrics for the original query
        orig_plan = None
        orig_time = None
        orig_cost = None
        
        try:
            orig_plan = runner.explain_analyze(original_sql)
            if orig_plan:
                orig_metrics = parser.parse(orig_plan)
                orig_time = orig_metrics.get("execution_time")
                orig_cost = orig_metrics.get("total_cost")
        except Exception:
            pass

        # Evaluate every rule on this query
        for rule_name, rule_instance in all_rules.items():
            rewritten_sql = original_sql
            changed = False
            is_equivalent = False
            note = ""
            
            opt_time = None
            opt_cost = None
            imp_pct = None
            cost_pct = None
            reasoning = ""
            
            # 2. Apply Rule
            try:
                candidate_sql = rule_instance.apply(original_sql)
                if candidate_sql.strip() != original_sql.strip():
                    rewritten_sql = candidate_sql
                    changed = True
            except Exception as e:
                # 9. Rule Error Handling
                note = f"rule error: {str(e)}"
                
            if note:
                # Skip further checks if rule errored
                pass
            elif not changed:
                # 5. No Change
                note = "no change"
            else:
                # 2. Semantic equivalence check
                equiv_res = checker.check_equivalence(original_sql, rewritten_sql)
                is_equivalent = equiv_res.get("is_equivalent", False)
                
                if not is_equivalent:
                    # 6. Mismatch
                    note = "semantic mismatch"
                else:
                    # 2. Valid Rewrite -> Run Explain
                    try:
                        cand_plan = runner.explain_analyze(rewritten_sql)
                        if cand_plan:
                            cand_metrics = parser.parse(cand_plan)
                            opt_time = cand_metrics.get("execution_time")
                            opt_cost = cand_metrics.get("total_cost")
                            
                            imp_pct = calculate_improvement(orig_time, opt_time)
                            cost_pct = calculate_improvement(orig_cost, opt_cost)
                            
                            # Use Plan Comparator
                            if orig_plan:
                                comp_rep = comparator.generate_analysis_report(orig_plan, cand_plan)
                                r_list = comp_rep.get("optimizer_reasoning", [])
                                reasoning = " ".join(r_list) if r_list else ""
                                
                            # 7. & 8. Evaluate Improvement
                            if (imp_pct and imp_pct > 0) or (cost_pct and cost_pct > 0):
                                note = "rewrite successful"
                            else:
                                note = "rewrite valid but not better"
                    except Exception as e:
                        note = f"explain error: {str(e)}"

            results.append({
                'query_id': query_id,
                'rule_name': rule_name,
                'original_sql': original_sql,
                'rewritten_sql': rewritten_sql,
                'changed': changed,
                'is_equivalent': is_equivalent,
                'execution_time_original': orig_time,
                'execution_time_rewritten': opt_time,
                'cost_original': orig_cost,
                'cost_rewritten': opt_cost,
                'improvement_percent': imp_pct,
                'cost_reduction_percent': cost_pct,
                'optimizer_reasoning': reasoning,
                'note': note
            })

    # 3. & 4. Export to CSV
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'query_id', 'rule_name', 'original_sql', 'rewritten_sql', 
            'changed', 'is_equivalent', 'execution_time_original', 
            'execution_time_rewritten', 'cost_original', 'cost_rewritten', 
            'improvement_percent', 'cost_reduction_percent', 
            'optimizer_reasoning', 'note'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    if runner: runner.close()
    if checker: checker.close()
    
    print(f"Single rule evaluation completed. Results saved to: {results_file}")

if __name__ == "__main__":
    run_single_rule_experiments()
