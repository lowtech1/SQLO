"""
Pattern-Based SQL Rewrite Rule Selector — Khong can LLM API.

Module nay phan tich cau truc SQL (pattern matching) de goi y cac rule
viets lai tot nhat, khong phu thuoc vao bat ky LLM API nao.

Kien truc:
  SQL Pattern Analyzer
       |
       v
  8 Rule Analyzers (mot rule cho moi loai)
       |
       v
  Scoring Engine (tinh diem dua tren confidence + benefit)
       |
       v
  Top-K Recommendations (tra ve top rules co diem cao nhat)

Cong thuc chon rule:
  score(rule) = applicable × benefit_weight × confidence_weight

Trong do:
  - applicable: 1 neu rule co the ap dung, 0 neu khong
  - benefit_weight: Cao=1.0, Trung binh=0.6, Thap=0.3
  - confidence_weight: high=1.0, medium=0.7, low=0.4

Vi du:
  Query: "SELECT * FROM orders o JOIN customer c ON o.custkey = c.custkey WHERE c.mktsegment = 'BUILDING'"
  Analysis:
    - has_select_star = True -> ast_projection_pruning (Cao, high)
    - has_where_on_joined = True -> ast_filter_into_join (Cao, high)
  Scores:
    - ast_projection_pruning: 1.0 × 1.0 = 1.0
    - ast_filter_into_join: 1.0 × 1.0 = 1.0
    - ast_redundant_join_elimination: 0.5 × 0.7 = 0.35 (co JOIN nhung co WHERE)
  Output: ["ast_projection_pruning", "ast_filter_into_join"]
"""

import re
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.evaluator.sql_analyzer import SQLPatternAnalyzer, ALL_RULES


class PatternRuleSelector:
    """
    Rule Selector bang pattern matching — khong can LLM.

    Day la mot thay the cho llm_rule_selector.py khi khong co API key.
    Hoat dong bang cach phan tich cau truc SQL va ap dung heuristic scoring.

    Cac buoc:
      1. Phan tich SQL de trich xuat dac diem cau truc
      2. Kiem tra xem moi rule co the ap dung khong
      3. Tinh diem cho tung rule
      4. Tra ve top-k rules co diem cao nhat

    Tai sao khong can LLM:
      - Cac rule SQL co pattern co dinh: IN subquery, SELECT *, JOIN, etc.
      - Co the nhan dien chinh xac qua regex/AST parsing
      - Khong can hieu ngu nghia ngon ngu tu nhien
    """

    AVAILABLE_RULES = list(ALL_RULES.keys())

    # Ban do tuong ung rule cu - rule AST (vi stub rules da duoc implement)
    OLD_TO_AST_MAP = {
        "old_predicate_pushdown": "ast_predicate_pushdown",
        "old_projection_pruning": "ast_projection_pruning",
        "old_subquery_unnesting": "ast_subquery_unnesting",
    }

    def __init__(self, top_k: int = 3):
        """
        Args:
            top_k: So luong rule toi da tra ve (mac dinh 3)
        """
        self.top_k = top_k
        self.analyzer = SQLPatternAnalyzer()

    def select_rules(self, sql: str, explain_plan: str = None, stats: str = None) -> dict:
        """
        Phan tich SQL va tra ve cac rule duoc goi y.

        Args:
            sql: SQL query can phan tich
            explain_plan: Khong su dung trong phien ban nay (cho LLM)
            stats: Khong su dung trong phien ban nay (cho LLM)

        Returns:
            dict: {
                "recommended_rules": ["rule1", "rule2"],
                "reasoning": "Giai thich vi sao cac rule nay duoc chon",
                "rule_scores": {"rule1": 1.0, "rule2": 0.7},
                "analysis": {thong tin chi tiet ve pattern SQL}
            }
        """
        analysis = self.analyzer.select_best_rules(sql)

        recommended = analysis["recommended_rules"][:self.top_k]

        # Map old rules to AST versions
        mapped_recommended = []
        for r in recommended:
            if r in self.OLD_TO_AST_MAP:
                mapped_recommended.append(self.OLD_TO_AST_MAP[r])
            else:
                mapped_recommended.append(r)

        # Xay dung reasoning
        reasons = []
        for rule_name in mapped_recommended:
            rule_info = analysis["analysis"].get(rule_name, {})
            if rule_info.get("applicable"):
                reasons.append(
                    f"{rule_name}: {rule_info.get('estimated_benefit', 'N/A')} "
                    f"({rule_info.get('pattern', 'N/A')})"
                )

        return {
            "recommended_rules": mapped_recommended,
            "reasoning": " | ".join(reasons) if reasons else "Khong co rule nao phu hop.",
            "rule_scores": analysis["rule_scores"],
            "analysis": analysis,
            "sql_patterns": analysis["sql_analysis"],
            "selection_method": "Pattern-based heuristic (no LLM)",
            "total_applicable": analysis["total_rules_applicable"],
        }

    def get_rule_explanation(self, rule_name: str) -> dict:
        """
        Tra ve giai thich chi tiet ve mot rule.

        Returns:
            dict: {
                "name": ten rule,
                "description": mo ta chuc nang,
                "when_to_apply": khi nao thi ap dung,
                "formula": cong thuc tinh loi ich,
                "risks": cac rui ro khi ap dung,
                "example": vi du SQL
            }
        """
        explanations = {
            "ast_predicate_pushdown": {
                "name": "Predicate Pushdown",
                "description": "Day dieu kien WHERE tu query ngoai vao trong subquery",
                "when_to_apply": "Khi co WHERE tren subquery ngoai, inner khong co DISTINCT/GROUP BY/aggregate",
                "formula": "So dong giam = So dong subquery × Ti so filter (selectivity)",
                "risks": "Co the thay doi thu tu thuc hien neu inner query su dung index",
                "example": "SELECT a FROM (SELECT a,b FROM t) AS sub WHERE a>10 -> SELECT a FROM (SELECT a,b FROM t WHERE a>10) AS sub"
            },
            "ast_projection_pruning": {
                "name": "Projection Pruning",
                "description": "Loai bo cot thua khoi SELECT cua subquery",
                "when_to_apply": "Khi outer query chi su dung mot phan cot cua subquery",
                "formula": "I/O giam = (Tong cot - Cot can thiet) / Tong cot × Reduction%",
                "risks": "Khong mo rong SELECT * khi khong co schema; co the thay doi ket qua neu cot bi an",
                "example": "SELECT a FROM (SELECT a,b,c FROM t) AS sub -> SELECT a FROM (SELECT a FROM t) AS sub"
            },
            "ast_subquery_unnesting": {
                "name": "Subquery Unnesting",
                "description": "Chuyen IN/EXISTS subquery thanh JOIN de cho phep Hash Join",
                "when_to_apply": "Khi co IN/EXISTS subquery don gian (khong correlated)",
                "formula": "Time: O(n×m) Nested Loop -> O(n+m) Hash Join",
                "risks": "Correlated subquery co the tao duplicate; NOT IN co van de NULL",
                "example": "SELECT * FROM t1 WHERE x IN (SELECT y FROM t2) -> SELECT DISTINCT t1.* FROM t1 JOIN t2 ON t1.x=t2.y"
            },
            "ast_join_reordering": {
                "name": "Join Reordering",
                "description": "Sap xep lai thu tu cac bang trong JOIN de giam so dong trung gian",
                "when_to_apply": "Khi co nhieu hon 1 JOIN, nhung bang co kich thuoc rat khac nhau",
                "formula": "Dong trung gian = tich kich thuoc cac bang giua 2 JOIN",
                "risks": "LEFT/RIGHT JOIN khong the reorder; co the thay doi nghi ngu",
                "example": "Tat ca INNER JOINs co the reorder; bang nho hon (nation, part) nen o truoc"
            },
            "ast_aggregation_pushdown": {
                "name": "Aggregation Pushdown",
                "description": "Day GROUP BY/aggregate tu query ngoai vao subquery",
                "when_to_apply": "Khi co GROUP BY over subquery, outer khong co HAVING/window functions",
                "formula": "So dong truoc = N × M, Sau pushdown = N (sau khi aggregate)",
                "risks": "Khong pushdown khi outer co HAVING, DISTINCT, window functions",
                "example": "SELECT SUM(x) FROM (SELECT x,y FROM t) AS sub GROUP BY x -> SELECT x, SUM(y) FROM t GROUP BY x"
            },
            "ast_redundant_join_elimination": {
                "name": "Redundant Join Elimination",
                "description": "Loai bo JOIN ma cot join khong duoc su dung o ngoai",
                "when_to_apply": "Khi JOIN tao ra cot nhung cot do khong xuat hien trong SELECT/WHERE/GROUP",
                "formula": "An toan khi: bang_khong_su_dung ∉ used_columns AND khong_phai_OUTER_JOIN",
                "risks": "OUTER/LEFT/RIGHT/FULL JOIN khong the loai bo; co the thay doi nghi ngu",
                "example": "SELECT c.name FROM customer c JOIN nation n ON c.nation=n.id WHERE c.type='A' -> SELECT c.name FROM customer c WHERE c.type='A'"
            },
            "ast_filter_into_join": {
                "name": "Filter Into Join",
                "description": "Day WHERE filter vao trong JOIN ON clause",
                "when_to_apply": "Khi co WHERE filter tren cot cua bang trong JOIN (chua co trong ON)",
                "formula": "So dong dau vao JOIN giam = So dong × Selectivity(cot WHERE)",
                "risks": "Chi ap dung INNER JOIN; LEFT/RIGHT/FULL JOIN co nghi ngu khac",
                "example": "SELECT * FROM t1 JOIN t2 ON t1.id=t2.id WHERE t2.type='A' -> SELECT * FROM t1 JOIN t2 ON t1.id=t2.id AND t2.type='A'"
            },
            "ast_limit_pushdown": {
                "name": "Limit Pushdown",
                "description": "Day LIMIT/OFFSET vao subquery de tranh xu ly toan bo",
                "when_to_apply": "Khi co LIMIT tren subquery, inner khong co LIMIT/OFFSET",
                "formula": "So dong sort truoc = N, Sau pushdown = min(LIMIT, N)",
                "risks": "Khong pushdown khi co ORDER BY toan cuc can giu thu tu",
                "example": "SELECT * FROM (SELECT * FROM t ORDER BY x) AS sub LIMIT 10 -> SELECT * FROM (SELECT * FROM t ORDER BY x LIMIT 10) AS sub"
            },
        }

        # Map old rule names to AST equivalents for lookup
        lookup_name = self.OLD_TO_AST_MAP.get(rule_name, rule_name)
        return explanations.get(lookup_name, {
            "name": rule_name,
            "description": "Khong co thong tin",
            "when_to_apply": "N/A",
            "formula": "N/A",
            "risks": "N/A",
            "example": "N/A"
        })

    def explain_selection(self, sql: str) -> str:
        """
        Tao mot chuoi giai thich chi tiet ve viec chon rule.
        Phu hop de in ra hoac trinh bay trong bao cao.
        """
        result = self.select_rules(sql)
        lines = []
        lines.append("=" * 70)
        lines.append("PATTERN-BASED RULE SELECTION REPORT")
        lines.append("=" * 70)
        lines.append(f"\nSQL: {sql}")
        lines.append(f"\nSelection Method: {result['selection_method']}")
        lines.append(f"Total Applicable Rules: {result['total_applicable']}")

        lines.append("\n--- SQL Pattern Analysis ---")
        patterns = result["sql_patterns"]
        for k, v in patterns.items():
            if v and v is not None:
                lines.append(f"  {k}: {v}")

        lines.append("\n--- Rule Scores ---")
        for rule, score in result["rule_scores"].items():
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            lines.append(f"  {rule:40s} {bar} {score:.2f}")

        lines.append("\n--- Recommended Rules ---")
        for i, rule in enumerate(result["recommended_rules"], 1):
            info = self.get_rule_explanation(rule)
            lines.append(f"\n  {i}. {info['name']} ({rule})")
            lines.append(f"     Benefit: {info['when_to_apply']}")
            lines.append(f"     Formula: {info['formula']}")
            lines.append(f"     Risks: {info['risks']}")

        lines.append(f"\n--- Reasoning ---")
        lines.append(result["reasoning"])
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


def demo():
    """Demo cho thay vu / bao cao tot nghiep."""
    selector = PatternRuleSelector(top_k=3)

    test_queries = [
        ("Predicate Pushdown",
         "SELECT sub.c_name, sub.c_phone FROM (SELECT c_custkey, c_name, c_phone FROM customer) AS sub WHERE sub.c_mktsegment = 'BUILDING';"),
        ("Projection Pruning",
         "SELECT c_name, c_phone FROM (SELECT * FROM customer WHERE c_mktsegment='AUTOMOBILE') AS sub;"),
        ("Subquery Unnesting",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
        ("Filter Into Join",
         "SELECT * FROM orders o JOIN customer c ON o.o_custkey = c.c_custkey WHERE c.c_mktsegment = 'HOUSEHOLD';"),
        ("Aggregation Pushdown",
         "SELECT sub.o_custkey, SUM(sub.o_totalprice) AS sum_price FROM (SELECT o_custkey, o_totalprice FROM orders) AS sub GROUP BY sub.o_custkey;"),
        ("Complex multi-rule",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 50000) AND c_mktsegment = 'AUTOMOBILE';"),
    ]

    for name, sql in test_queries:
        print(selector.explain_selection(sql))
        print()


if __name__ == "__main__":
    demo()
