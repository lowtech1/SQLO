import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 1. Import old rewrite rules
from my_exp.rules.rule_registry import RULES as OLD_RULES

# 1. Import new AST rewrite rules
from my_exp.ast_rewriter.ast_predicate_pushdown import ASTPredicatePushdown
from my_exp.ast_rewriter.ast_projection_pruning import ASTProjectionPruning
from my_exp.ast_rewriter.ast_subquery_unnesting import ASTSubqueryUnnesting
from my_exp.ast_rewriter.ast_join_reordering import ASTJoinReordering
from my_exp.ast_rewriter.ast_aggregation_pushdown import ASTAggregationPushdown
from my_exp.ast_rewriter.ast_redundant_join_elimination import ASTRedundantJoinElimination
from my_exp.ast_rewriter.ast_filter_into_join import ASTFilterIntoJoin

# Safe import for ast_limit_pushdown in case it hasn't been implemented yet
try:
    from my_exp.ast_rewriter.ast_limit_pushdown import ASTLimitPushdown
except ImportError:
    class ASTLimitPushdown:
        def apply(self, sql: str) -> str:
            return sql

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

class CandidateGenerator:
    """
    Generates multiple potential rewrites (candidates) for a given SQL query
    by applying combinations of string-based rules and AST-based rules.
    """

    def generate_candidates(self, sql: str) -> list:
        """
        Generates candidate SQL rewrites using single rules, multi-rules, and AST rules.
        Does not filter out duplicate candidates.

        Args:
            sql (str): The original SQL query.

        Returns:
            list: A list of dicts representing each candidate.
        """
        candidates = []
        candidate_count = 0
        
        def add_candidate(applied_rules, rewritten_sql, error=None):
            nonlocal candidate_count
            candidate_count += 1
            cand = {
                "candidate_id": f"cand_{candidate_count}",
                "applied_rules": applied_rules,
                "rewritten_sql": rewritten_sql
            }
            if error:
                cand["error"] = error
            candidates.append(cand)

        # --- 3. Single-rule rewrites (Old Rules) ---
        for rule_name, rule_instance in OLD_RULES.items():
            try:
                new_sql = rule_instance.apply(sql)
                add_candidate([f"old_{rule_name}"], new_sql)
            except Exception as e:
                add_candidate([f"old_{rule_name}"], sql, error=str(e))

        # --- 3. Single-rule rewrites (AST Rules) ---
        for rule_name, rule_instance in AST_RULES.items():
            try:
                new_sql = rule_instance.apply(sql)
                add_candidate([rule_name], new_sql)
            except Exception as e:
                add_candidate([rule_name], sql, error=str(e))

        # --- 4. Multi-rule rewrites (AST Combinations) ---
        combinations = [
            ("ast_predicate_pushdown", "ast_projection_pruning"),
            ("ast_predicate_pushdown", "ast_join_reordering"),
            ("ast_predicate_pushdown", "ast_aggregation_pushdown"),
            ("ast_filter_into_join", "ast_join_reordering"),
            ("ast_subquery_unnesting", "ast_join_reordering"),
            ("ast_redundant_join_elimination", "ast_projection_pruning"),
            ("ast_limit_pushdown", "ast_projection_pruning"),
            (
                "ast_predicate_pushdown",
                "ast_projection_pruning",
                "ast_subquery_unnesting",
                "ast_join_reordering",
                "ast_aggregation_pushdown",
                "ast_redundant_join_elimination",
                "ast_filter_into_join",
                "ast_limit_pushdown"
            )
        ]

        for combo in combinations:
            current_sql = sql
            applied_combo = list(combo)
            combo_error = None
            
            for rule_name in combo:
                rule_instance = AST_RULES.get(rule_name)
                if rule_instance:
                    try:
                        candidate_sql = rule_instance.apply(current_sql)
                        if candidate_sql.strip() != current_sql.strip():
                            current_sql = candidate_sql
                    except Exception as e:
                        combo_error = f"Error in {rule_name}: {str(e)}"
                        break # Halt this pipeline if an error occurs
                        
            # Always add the candidate, even if it failed midway or didn't change the SQL
            add_candidate(applied_combo, current_sql, error=combo_error)

        return candidates

if __name__ == "__main__":
    import json
    
    generator = CandidateGenerator()
    test_sql = "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders);"
    
    print("Testing CandidateGenerator...\n")
    candidates = generator.generate_candidates(test_sql)
    
    print(f"Generated {len(candidates)} candidates total.\n")
    
    if candidates:
        print("=== Sample Candidate (Single Old Rule) ===")
        print(json.dumps(candidates[0], indent=2))
        
        print("\n=== Sample Candidate (Full AST Pipeline) ===")
        print(json.dumps(candidates[-1], indent=2))
