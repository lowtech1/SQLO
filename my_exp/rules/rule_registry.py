from my_exp.rules.predicate_pushdown import PredicatePushdownRule
from my_exp.rules.projection_pruning import ProjectionPruningRule
from my_exp.rules.subquery_unnesting import SubqueryUnnestingRule

# Registry mapping rule names to their respective instances
RULES = {
    "predicate_pushdown": PredicatePushdownRule(),
    "projection_pruning": ProjectionPruningRule(),
    "subquery_unnesting": SubqueryUnnestingRule()
}

def get_rule(rule_name: str):
    """
    Retrieves a rule instance by its name.
    
    Args:
        rule_name (str): The name of the rule (e.g., 'predicate_pushdown').
        
    Returns:
        The rule instance if found, otherwise None.
    """
    return RULES.get(rule_name)
