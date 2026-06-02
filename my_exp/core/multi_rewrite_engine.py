"""
my_exp.core.multi_rewrite_engine
================================
Generates N candidate rewrites for a SQL query using the rule KB.
Each candidate = unique combination of applicable rules.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.core.rules import get_rule, get_all_rules, RULE_METADATA
from my_exp.core.sql_analyzer import SQLFeatureExtractor
from typing import Optional
import itertools


class MultiRewriteEngine:
    """
    Sinh N candidate rewrites từ 1 SQL query gốc.

    Chiến lược:
    1. Phân tích SQL → trích xuất features
    2. Đánh giá từng rule riêng lẻ
    3. Sinh combinations của top rules
    4. Mỗi candidate = original hoặc rewrite với 1+ rules

    Output: Danh sách candidates với metadata đầy đủ
    """

    def __init__(self):
        self.extractor = SQLFeatureExtractor()
        self.all_rules = get_all_rules()

    def generate_candidates(
        self,
        sql: str,
        max_candidates: int = 5,
        include_original: bool = True
    ) -> list:
        """
        Sinh candidate rewrites.

        Args:
            sql: SQL query gốc
            max_candidates: Số lượng candidates tối đa
            include_original: Có bao gồm query gốc không

        Returns:
            List of candidate dicts, mỗi candidate có:
              - id: int
              - sql: str (rewritten SQL hoặc original)
              - is_original: bool
              - rules_applied: list of rule names
              - rule_explanations: list of explanation dicts
              - changed: bool (SQL có thay đổi không)
        """
        candidates = []
        candidate_id = 0

        # Phân tích features
        features = self.extractor.extract(sql)
        if not features.get("parsing", {}).get("success"):
            return [{
                "id": 0,
                "sql": sql,
                "is_original": True,
                "rules_applied": [],
                "rule_explanations": [],
                "changed": False,
                "error": "Parse error"
            }]

        # Đánh giá từng rule
        rule_results = {}
        for rule_name, rule in self.all_rules.items():
            can_apply, reason = rule.can_apply(sql)
            rule_results[rule_name] = {
                "can_apply": can_apply,
                "reason": reason,
                "explanation": rule.explain(sql),
            }

        # Rule có thể áp dụng
        applicable = [
            name for name, result in rule_results.items()
            if result["can_apply"]
        ]

        # Candidate 0: Query gốc
        if include_original:
            candidates.append({
                "id": candidate_id,
                "sql": sql,
                "is_original": True,
                "rules_applied": [],
                "rule_explanations": [],
                "changed": False,
                "features": features,
                "applicable_rules": applicable,
                "all_rule_results": rule_results,
            })
            candidate_id += 1

        # Candidate 1: Từng rule riêng lẻ
        for rule_name in applicable:
            if candidate_id >= max_candidates:
                break
            rule = get_rule(rule_name)
            try:
                rewritten = rule.apply(sql)
            except Exception as e:
                rewritten = sql

            changed = rewritten.strip() != sql.strip()
            candidates.append({
                "id": candidate_id,
                "sql": rewritten if changed else sql,
                "is_original": False,
                "rules_applied": [rule_name],
                "rule_explanations": [rule_results[rule_name]["explanation"]],
                "changed": changed,
                "features": features,
                "applicable_rules": applicable,
                "all_rule_results": rule_results,
            })
            candidate_id += 1

        # Candidate 2+: Combinations (2 rules)
        if len(applicable) >= 2 and candidate_id < max_candidates:
            for combo in itertools.combinations(applicable, 2):
                if candidate_id >= max_candidates:
                    break
                rule_instances = [get_rule(name) for name in combo]
                current_sql = sql
                explanations = []
                applied_rules = []

                for rule, name in zip(rule_instances, combo):
                    try:
                        rewritten = rule.apply(current_sql)
                        if rewritten.strip() != current_sql.strip():
                            current_sql = rewritten
                            applied_rules.append(name)
                            explanations.append(rule_results[name]["explanation"])
                    except Exception:
                        pass

                changed = current_sql.strip() != sql.strip()
                if changed:
                    candidates.append({
                        "id": candidate_id,
                        "sql": current_sql,
                        "is_original": False,
                        "rules_applied": applied_rules,
                        "rule_explanations": explanations,
                        "changed": True,
                        "features": features,
                        "applicable_rules": applicable,
                        "all_rule_results": rule_results,
                    })
                    candidate_id += 1

        # Truncate if too many
        if len(candidates) > max_candidates:
            # Ưu tiên: original, rồi single rules, rồi combinations
            candidates = candidates[:max_candidates]

        return candidates

    def get_summary(self, sql: str) -> dict:
        """Lấy tóm tắt phân tích SQL."""
        features = self.extractor.extract(sql)
        if not features.get("parsing", {}).get("success"):
            return {"error": "Parse error"}

        all_rules = get_all_rules()
        rule_results = {}
        for rule_name, rule in all_rules.items():
            can_apply, reason = rule.can_apply(sql)
            rule_results[rule_name] = {
                "can_apply": can_apply,
                "reason": reason,
            }

        applicable = [name for name, r in rule_results.items() if r["can_apply"]]

        return {
            "sql": sql,
            "complexity": features.get("complexity", {}),
            "features": {
                "table_count": features.get("table_count", 0),
                "join_count": features.get("join_count", 0),
                "subquery_count": features.get("subquery_count", 0),
                "has_aggregation": features.get("has_aggregation", False),
                "has_group_by": features.get("has_group_by", False),
                "has_limit": features.get("has_limit", False),
                "has_order_by": features.get("has_order_by", False),
            },
            "optimization_opportunities": features.get("optimization_opportunities", []),
            "applicable_rules": applicable,
            "all_rule_results": rule_results,
        }
