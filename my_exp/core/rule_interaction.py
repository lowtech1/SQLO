"""
my_exp/core/rule_interaction.py
==============================
Detects cross-rule interactions: conflicts, order constraints,
prerequisite chains, and redundant applications.
"""

from dataclasses import dataclass
from typing import Optional


# ── Rule metadata ──────────────────────────────────────────────────────────────

class RuleMeta:
    def __init__(
        self,
        rule_id: str,
        description: str,
        stage: str = "early",   # early | mid | late
        prerequisites: list[str] = None,
        conflicts_with: list[str] = None,
        must_precede: list[str] = None,
    ):
        self.rule_id = rule_id
        self.description = description
        self.stage = stage          # when in the pipeline it should run
        self.prerequisites = prerequisites or []   # rules that must be applied first
        self.conflicts_with = conflicts_with or [] # cannot coexist
        self.must_precede = must_precede or []     # must run before these


RULE_METADATA = {
    "predicate_pushdown": RuleMeta(
        rule_id="predicate_pushdown",
        description="Move WHERE conditions closer to base tables",
        stage="early",
        must_precede=["projection_pruning", "subquery_unnesting"],
    ),
    "projection_pruning": RuleMeta(
        rule_id="projection_pruning",
        description="Remove unused columns from SELECT",
        stage="early",
        prerequisites=["predicate_pushdown"],
        must_precede=["join_reordering"],
    ),
    "filter_into_join": RuleMeta(
        rule_id="filter_into_join",
        description="Convert WHERE filter to JOIN condition",
        stage="early",
        prerequisites=["predicate_pushdown"],
        conflicts_with=["subquery_merging"],
    ),
    "subquery_unnesting": RuleMeta(
        rule_id="subquery_unnesting",
        description="Convert subqueries to JOINs",
        stage="mid",
        prerequisites=["predicate_pushdown"],
        must_precede=["join_reordering", "redundant_join_elimination"],
    ),
    "join_reordering": RuleMeta(
        rule_id="join_reordering",
        description="Reorder JOINs for better cardinality",
        stage="mid",
        prerequisites=["subquery_unnesting", "projection_pruning"],
        conflicts_with=["redundant_join_elimination"],  # reordering can re-introduce redundant joins
    ),
    "subquery_merging": RuleMeta(
        rule_id="subquery_merging",
        description="Merge nested subqueries",
        stage="mid",
        conflicts_with=["filter_into_join"],
    ),
    "redundant_join_elimination": RuleMeta(
        rule_id="redundant_join_elimination",
        description="Remove unnecessary JOINs",
        stage="late",
        prerequisites=["subquery_unnesting"],
        conflicts_with=["join_reordering"],  # elimination can make reordering irrelevant
    ),
    "constant_folding": RuleMeta(
        rule_id="constant_folding",
        description="Evaluate constant expressions at compile time",
        stage="early",
        must_precede=["predicate_pushdown"],  # fold before pushing
    ),
}


class InteractionType:
    CONFLICT = "conflict"           # rules cannot coexist
    ORDER_CONSTRAINT = "order"      # one must run before the other
    PREREQUISITE_MISSING = "missing_prereq"  # rule needs another first
    REDUNDANT = "redundant"         # same rule applied twice


@dataclass
class RuleInteraction:
    interaction_type: str
    rule_a: str
    rule_b: Optional[str]
    description: str
    severity: str = "warning"  # info | warning | error
    suggestion: str = ""


@dataclass
class InteractionReport:
    has_conflicts: bool
    has_order_issues: bool
    has_missing_prereqs: bool
    interactions: list[RuleInteraction]
    safe_sequence: list[str]    # topologically sorted rule order
    warnings: list[str]


def detect_interactions(selected_rules: list[str]) -> InteractionReport:
    """
    Analyze a set of selected rules for cross-rule interactions.

    Returns an InteractionReport with:
    - conflicts between rules
    - order constraints (must-run-before relationships)
    - missing prerequisites
    - a topologically sorted safe sequence
    """
    if not selected_rules:
        return InteractionReport(
            has_conflicts=False,
            has_order_issues=False,
            has_missing_prereqs=False,
            interactions=[],
            safe_sequence=[],
            warnings=[],
        )

    interactions = []
    warnings = []
    selected_set = set(selected_rules)

    # 1. Detect conflicts
    for rule_id in selected_rules:
        meta = RULE_METADATA.get(rule_id)
        if not meta:
            continue
        for conflict in meta.conflicts_with:
            if conflict in selected_set:
                interactions.append(RuleInteraction(
                    interaction_type=InteractionType.CONFLICT,
                    rule_a=rule_id,
                    rule_b=conflict,
                    description=(
                        f"'{rule_id}' conflicts with '{conflict}'. "
                        f"Applying both may produce unexpected results or semantic changes."
                    ),
                    severity="warning",
                    suggestion=f"Choose either '{rule_id}' OR '{conflict}', not both.",
                ))
                warnings.append(f"Conflict: {rule_id} ↔ {conflict}")

    # 2. Detect missing prerequisites
    for rule_id in selected_rules:
        meta = RULE_METADATA.get(rule_id)
        if not meta:
            continue
        for prereq in meta.prerequisites:
            if prereq not in selected_set:
                interactions.append(RuleInteraction(
                    interaction_type=InteractionType.PREREQUISITE_MISSING,
                    rule_a=rule_id,
                    rule_b=prereq,
                    description=(
                        f"'{rule_id}' works best when '{prereq}' is applied first. "
                        f"'{prereq}' is not in the selected rules."
                    ),
                    severity="info",
                    suggestion=f"Consider adding '{prereq}' to improve '{rule_id}' effectiveness.",
                ))

    # 3. Detect order constraint violations
    for rule_id in selected_rules:
        meta = RULE_METADATA.get(rule_id)
        if not meta:
            continue
        for must_run_before in meta.must_precede:
            if must_run_before not in selected_set:
                continue
            # Check if 'rule_id' actually comes after 'must_run_before' in the list
            # If 'must_run_before' appears first, that's a violation
            pos_a = selected_rules.index(rule_id)
            pos_b = selected_rules.index(must_run_before)
            if pos_a >= pos_b:  # rule_id comes at same index or after — violation
                interactions.append(RuleInteraction(
                    interaction_type=InteractionType.ORDER_CONSTRAINT,
                    rule_a=rule_id,
                    rule_b=must_run_before,
                    description=(
                        f"'{rule_id}' should run BEFORE '{must_run_before}' "
                        f"(order constraint), but '{must_run_before}' appears earlier in the list."
                    ),
                    severity="warning",
                    suggestion=f"Reorder: place '{rule_id}' before '{must_run_before}'.",
                ))
                warnings.append(f"Order violation: {rule_id} should precede {must_run_before}")

    # 4. Compute safe topological sequence
    safe_seq = _topo_sort(selected_rules)

    return InteractionReport(
        has_conflicts=any(i.interaction_type == InteractionType.CONFLICT for i in interactions),
        has_order_issues=any(i.interaction_type == InteractionType.ORDER_CONSTRAINT for i in interactions),
        has_missing_prereqs=any(i.interaction_type == InteractionType.PREREQUISITE_MISSING for i in interactions),
        interactions=interactions,
        safe_sequence=safe_seq,
        warnings=warnings,
    )


def _topo_sort(rules: list[str]) -> list[str]:
    """
    Topologically sort rules by their stage (early → mid → late).
    Within the same stage, preserve original order.
    """
    stage_order = {"early": 0, "mid": 1, "late": 2, "unknown": 3}

    def stage(r: str) -> int:
        return stage_order.get(RULE_METADATA.get(r, RuleMeta(r, "", "unknown")).stage, 3)

    return sorted(rules, key=lambda r: (stage(r), rules.index(r)))


def suggest_rule_order(selected_rules: list[str]) -> list[str]:
    """
    Given a list of selected rules, return them in a safe execution order
    that respects prerequisite chains and order constraints.
    """
    return _topo_sort(selected_rules)
