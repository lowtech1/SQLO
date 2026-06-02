"""
my_exp.core.rules
=================
Central rule implementations for SQL query optimization.
All 8 optimization rules are registered here.
"""

from my_exp.core.rules.predicate_pushdown import PredicatePushdownRule
from my_exp.core.rules.projection_pruning import ProjectionPruningRule
from my_exp.core.rules.join_reordering import JoinReorderingRule
from my_exp.core.rules.subquery_unnesting import SubqueryUnnestingRule
from my_exp.core.rules.aggregation_pushdown import AggregationPushdownRule
from my_exp.core.rules.redundant_join_elimination import RedundantJoinEliminationRule
from my_exp.core.rules.filter_into_join import FilterIntoJoinRule
from my_exp.core.rules.limit_pushdown import LimitPushdownRule

RULES = {
    "predicate_pushdown": PredicatePushdownRule,
    "projection_pruning": ProjectionPruningRule,
    "join_reordering": JoinReorderingRule,
    "subquery_unnesting": SubqueryUnnestingRule,
    "aggregation_pushdown": AggregationPushdownRule,
    "redundant_join_elimination": RedundantJoinEliminationRule,
    "filter_into_join": FilterIntoJoinRule,
    "limit_pushdown": LimitPushdownRule,
}

RULE_METADATA = {name: cls.METADATA for name, cls in RULES.items()}


def get_rule(name: str):
    cls = RULES.get(name)
    return cls() if cls else None


def get_all_rules():
    return {name: cls() for name, cls in RULES.items()}


def get_rule_metadata(name: str):
    return RULE_METADATA.get(name)


def list_rules_by_category():
    cats = {}
    for name, meta in RULE_METADATA.items():
        cat = meta.get("category", "other")
        if cat not in cats:
            cats[cat] = []
        cats[cat].append({**meta, "name": name})
    return cats
