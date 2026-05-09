import json
import csv
import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_predicate_pushdown import ASTPredicatePushdown
from my_exp.ast_rewriter.ast_projection_pruning import ASTProjectionPruning
from my_exp.ast_rewriter.ast_subquery_unnesting import ASTSubqueryUnnesting
from my_exp.ast_rewriter.ast_join_reordering import ASTJoinReordering
from my_exp.ast_rewriter.ast_aggregation_pushdown import ASTAggregationPushdown
from my_exp.ast_rewriter.ast_redundant_join_elimination import ASTRedundantJoinElimination
from my_exp.ast_rewriter.ast_filter_into_join import ASTFilterIntoJoin

# Safe import for limit_pushdown in case it's missing
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

AST_RULES = {
    "ast_predicate_pushdown": ASTPredicatePushdown(),
    "ast_projection_pruning": ASTProjectionPruning(),
    "ast_subquery_unnesting": ASTSubqueryUnnesting(),
    "ast_join_reordering": ASTJoinReordering(),
    "ast_aggregation_pushdown": ASTAggregationPushdown(),
    "ast_redundant_join_elimination": ASTRedundantJoinElimination(),
    "ast_filter_into_join": ASTFilterIntoJoin(),
    "ast_limit_pushdown": ASTLimitPushdown()
}

PIPELINES = {
    "pipeline_1_basic": [
        "ast_predicate_pushdown", 
        "ast_projection_pruning"
    ],
    "pipeline_2_join": [
        "ast_filter_into_join", 
        "ast_join_reordering"
    ],
    "pipeline_3_subquery_join": [
        "ast_subquery_unnesting", 
        "ast_join_reordering"
    ],
    "pipeline_4_aggregation": [
        "ast_predicate_pushdown", 
        "ast_aggregation_pushdown"
    ],
    "pipeline_5_cleanup": [
        "ast_projection_pruning", 
        "ast_redundant_join_elimination"
    ],
    "pipeline_6_limit": [
        "ast_projection_pruning", 
        "ast_limit_pushdown"
    ],
    "pipeline_7_full": [
        "ast_predicate_pushdown",
        "ast_projection_pruning",
        "ast_subquery_unnesting",
        "ast_filter_into_join",
        "ast_join_reordering",
        "ast_aggregation_pushdown",
        "ast_redundant_join_elimination",
        "ast_limit_pushdown"
    ]
}

def calculate_improvement(original, new_val):
    if original is None or new_val is None or original == 0:
        return 0.0
    return float(round(((original - new_val) / original) * 100, 2))

def run_multi_rule_experiments():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    queries_file = os.path.join(base_dir, 'queries', 'test_cases.json')
    results_file = os.path.join(base_dir, 'results', 'multi_rule_results.csv')

    if not os.path.exists(queries_file):
        print(f"Error: {queries_file} not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    results = []
    
    try:
        runner = PostgresRunner()
        parser = ExplainParser()
        checker = ResultChecker()
        comparator = PlanComparator()
        runner.connect()
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        return

    print(f"Starting multi-rule experiments across {len(PIPELINES)} pipelines...")

    for i, query in enumerate(queries, 1):
        query_id = query.get('query_id', f'unknown_{i}')
        original_sql = query.get('sql', '')
        
        # Baseline execution
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

        # Evaluate each pipeline on this query
        for pipeline_name, rule_order in PIPELINES.items():
            current_sql = original_sql
            applied_rules = []
            rolled_back_rules = []
            intermediate_sqls = []
            rollback_notes = []

            for rule_name in rule_order:
                rule_instance = AST_RULES.get(rule_name)
                if not rule_instance:
                    continue
                    
                try:
                    candidate_sql = rule_instance.apply(current_sql)
                except Exception as e:
                    rollback_notes.append(f"[{rule_name} runtime error: {e}]")
                    rolled_back_rules.append(rule_name)
                    continue
                    
                if candidate_sql.strip() != current_sql.strip():
                    # Check semantic equivalence against the original query to prevent cumulative drift
                    equiv_result = checker.check_equivalence(original_sql, candidate_sql)
                    is_equiv = equiv_result.get("is_equivalent", False)
                    
                    if is_equiv:
                        # Accept rewrite step
                        current_sql = candidate_sql
                        applied_rules.append(rule_name)
                        intermediate_sqls.append(current_sql)
                    else:
                        # Rollback this rule
                        msg = equiv_result.get("message", "Semantic mismatch")
                        rollback_notes.append(f"[{rule_name} rolled back: {msg}]")
                        rolled_back_rules.append(rule_name)

            final_sql = current_sql
            changed_overall = (original_sql.strip() != final_sql.strip())
            
            final_time = None
            final_cost = None
            imp_pct = None
            cost_pct = None
            reasoning = ""
            note = ""

            # Check improvements if changed
            if not changed_overall:
                note = "no effective rewrite"
            else:
                try:
                    fin_plan = runner.explain_analyze(final_sql)
                    if fin_plan:
                        fin_metrics = parser.parse(fin_plan)
                        final_time = fin_metrics.get("execution_time")
                        final_cost = fin_metrics.get("total_cost")
                        
                        imp_pct = calculate_improvement(orig_time, final_time)
                        cost_pct = calculate_improvement(orig_cost, final_cost)
                        
                        if orig_plan:
                            comp_rep = comparator.generate_analysis_report(orig_plan, fin_plan)
                            r_list = comp_rep.get("optimizer_reasoning", [])
                            reasoning = " ".join(r_list) if r_list else ""
                            
                        # Evaluate benefit
                        if (imp_pct and imp_pct > 0) or (cost_pct and cost_pct > 0):
                            note = "multi-rule optimization successful"
                        else:
                            note = "multi-rule optimization not beneficial"
                except Exception as e:
                    note = f"Explain Error: {str(e)}"

            if rollback_notes:
                if note:
                    note += " | " + "; ".join(rollback_notes)
                else:
                    note = "; ".join(rollback_notes)

            # Record Result
            results.append({
                'query_id': query_id,
                'pipeline_name': pipeline_name,
                'original_sql': original_sql,
                'final_sql': final_sql,
                'applied_rules': json.dumps(applied_rules),
                'rolled_back_rules': json.dumps(rolled_back_rules),
                'intermediate_sqls': json.dumps(intermediate_sqls),
                'original_time': orig_time,
                'final_time': final_time,
                'original_cost': orig_cost,
                'final_cost': final_cost,
                'improvement_percent': imp_pct,
                'cost_reduction_percent': cost_pct,
                'optimizer_reasoning': reasoning,
                'note': note.strip()
            })
            
    # Export to CSV
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'query_id', 'pipeline_name', 'original_sql', 'final_sql', 
            'applied_rules', 'rolled_back_rules', 'intermediate_sqls', 
            'original_time', 'final_time', 'original_cost', 'final_cost',
            'improvement_percent', 'cost_reduction_percent', 
            'optimizer_reasoning', 'note'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    if runner: runner.close()
    if checker: checker.close()

    print(f"Multi-rule pipelines evaluation completed. Results saved to: {results_file}")

if __name__ == "__main__":
    run_multi_rule_experiments()
