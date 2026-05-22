import re
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.rules.rule_registry import RULES as OLD_RULES
from my_exp.ast_rewriter.ast_predicate_pushdown import ASTPredicatePushdown
from my_exp.ast_rewriter.ast_projection_pruning import ASTProjectionPruning
from my_exp.ast_rewriter.ast_subquery_unnesting import ASTSubqueryUnnesting
from my_exp.ast_rewriter.ast_join_reordering import ASTJoinReordering
from my_exp.ast_rewriter.ast_aggregation_pushdown import ASTAggregationPushdown
from my_exp.ast_rewriter.ast_redundant_join_elimination import ASTRedundantJoinElimination
from my_exp.ast_rewriter.ast_filter_into_join import ASTFilterIntoJoin


from my_exp.ast_rewriter.ast_limit_pushdown import ASTLimitPushdown


# All rules map
ALL_RULES = {}
for name, rule in OLD_RULES.items():
    ALL_RULES[f"old_{name}"] = rule
ALL_RULES.update({
    "ast_predicate_pushdown": ASTPredicatePushdown(),
    "ast_projection_pruning": ASTProjectionPruning(),
    "ast_subquery_unnesting": ASTSubqueryUnnesting(),
    "ast_join_reordering": ASTJoinReordering(),
    "ast_aggregation_pushdown": ASTAggregationPushdown(),
    "ast_redundant_join_elimination": ASTRedundantJoinElimination(),
    "ast_filter_into_join": ASTFilterIntoJoin(),
    "ast_limit_pushdown": ASTLimitPushdown(),
})


class SQLPatternAnalyzer:
    """
    Phan tich cau truc SQL de xac dinh rule co the ap dung va uoc tinh loi ich.
    Khong can database — chi phan tich pattern cua SQL.

    Muc dich: Cung cap ket qua co the chay thuc nghiem ma khong phu thuoc
    vao PostgreSQL, giup demo va phan tich rule effectiveness.
    """

    def analyze(self, sql: str) -> dict:
        """
        Phan tich mot SQL query va tra ve cac dac diem cau truc.

        Cong thuc tinh diem:
          - predicate_pushdown: +1 neu co subquery + WHERE o ngoai
          - projection_pruning: +1 neu co SELECT * hoac cot thua
          - subquery_unnesting: +1 neu co IN/EXISTS subquery
          - join_reordering: +1 neu co nhieu hon 2 bang trong JOIN
          - aggregation_pushdown: +1 neu co GROUP BY over subquery
          - redundant_join_elimination: +1 neu co JOIN ma cot join khong duoc dung
          - filter_into_join: +1 neu co WHERE tren cot bang trong JOIN
          - limit_pushdown: +1 neu co LIMIT tren subquery
        """
        s = sql.upper()
        info = {
            "has_subquery": bool(re.search(r'\b(SELECT\s+.*?\bFROM\s+.*?)\s*\bWHERE\b', sql, re.DOTALL | re.IGNORECASE)),
            "has_where_on_outer": bool(re.search(r'\)\s+AS\s+\w+\s+WHERE\b', sql, re.IGNORECASE)),
            "has_select_star": "SELECT *" in s,
            "has_in_subquery": bool(re.search(r'\bIN\s*\(\s*SELECT\b', sql, re.IGNORECASE)),
            "has_exists_subquery": bool(re.search(r'\bEXISTS\s*\(\s*SELECT\b', sql, re.IGNORECASE)),
            "num_joins": len(re.findall(r'\bJOIN\b', s)),
            "has_group_by": bool(re.search(r'\bGROUP\s+BY\b', sql, re.IGNORECASE)),
            "has_aggregation": bool(re.search(r'\b(SUM|COUNT|AVG|MIN|MAX|STDDEV|VARIANCE)\s*\(', sql, re.IGNORECASE)),
            "has_limit": bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE)),
            "has_order_by": bool(re.search(r'\bORDER\s+BY\b', sql, re.IGNORECASE)),
            "has_nested_agg": self._has_aggregation_over_subquery(sql),
            "num_tables": self._count_tables(sql),
            "has_where_on_joined": self._has_filter_on_join_table(sql),
            "has_distinct": "DISTINCT" in s,
            "has_having": bool(re.search(r'\bHAVING\b', sql, re.IGNORECASE)),
            "has_limit_on_subquery": self._has_limit_on_subquery(sql),
            "joined_table_names": self._get_joined_table_names(sql),
        }
        return info

    def _has_aggregation_over_subquery(self, sql: str) -> bool:
        """Kiem tra co GROUP BY over subquery (pattern: GROUP BY tren subquery)."""
        return bool(re.search(r'\)\s+AS\s+\w+\s+GROUP\s+BY\b', sql, re.IGNORECASE))

    def _count_tables(self, sql: str) -> int:
        """Dem so bang trong query."""
        tables = set()
        for m in re.finditer(r'\bFROM\s+([\w\"`]+(?:\s+AS\s+\w+)?)', sql, re.IGNORECASE):
            tbl = m.group(1).strip().split()[0].strip('"`')
            if tbl.upper() not in ("SELECT"):
                tables.add(tbl)
        for m in re.finditer(r'\bJOIN\s+([\w\"`]+)', sql, re.IGNORECASE):
            tables.add(m.group(1).strip().strip('"`'))
        return len(tables)

    def _get_joined_table_names(self, sql: str) -> list:
        """Lay danh sach ten bang trong JOIN."""
        names = []
        for m in re.finditer(r'\bJOIN\s+([\w\"`]+)(?:\s+(?:AS\s+)?([\w\"`]+))?', sql, re.IGNORECASE):
            tbl = m.group(1).strip().strip('"`')
            alias = m.group(2).strip().strip('"`') if m.group(2) else tbl
            names.append((tbl, alias))
        return names

    def _has_filter_on_join_table(self, sql: str) -> bool:
        """
        Kiem tra co WHERE filter tren cot cua bang trong JOIN.
        Chi True neu: co JOIN + co WHERE + WHERE co cot thuoc bang trong JOIN.
        """
        if not re.search(r'\bJOIN\b', sql, re.IGNORECASE):
            return False
        if not re.search(r'\bWHERE\b', sql, re.IGNORECASE):
            return False

        # Lay ten bang/alias trong JOIN
        joined = self._get_joined_table_names(sql)
        if not joined:
            return False

        # Kiem tra WHERE co tham chieu den cot cua bang trong JOIN
        # Tach WHERE tu query
        where_match = re.search(r'\bWHERE\b(.+?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|\bHAVING\b|$)',
                               sql, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return False

        where_clause = where_match.group(1)
        for tbl, alias in joined:
            # Kiem tra ten bang hoac alias xuat hien trong WHERE
            if re.search(rf'\b{re.escape(alias)}\b\.', where_clause, re.IGNORECASE):
                return True
            if re.search(rf'\b{re.escape(tbl)}\b\.', where_clause, re.IGNORECASE):
                return True
        return False

    def _has_limit_on_subquery(self, sql: str) -> bool:
        """Kiem tra LIMIT o ngoai subquery (khong o trong subquery)."""
        if not re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
            return False
        if not re.search(r'\)\s+AS\s+\w+\b', sql, re.IGNORECASE):
            return False
        # LIMIT nam sau subquery (ngoai) chu khong phai trong
        return bool(re.search(r'\)\s+AS\s+\w+\s*(?:WHERE\b.*?)?\s*LIMIT\b', sql, re.IGNORECASE | re.DOTALL))

    def estimate_rule_benefit(self, sql: str) -> dict:
        """
        Uoc tinh loi ich cua moi rule dua tren pattern SQL.
        Tra ve dict: {rule_name: {"applicable": bool, "estimated_benefit": str, "confidence": str}}

        Muc do confidence:
          - high: Pattern ro rang, co so lieu ly thuyet chang chan
          - medium: Pattern co the ap dung, can xac nhan them
          - low: Chi la goi y, co the khong tot hon
        """
        info = self.analyze(sql)
        result = {}

        # 1. Predicate Pushdown
        if info["has_subquery"] and info["has_where_on_outer"]:
            result["ast_predicate_pushdown"] = {
                "applicable": True,
                "estimated_benefit": "Cao — WHERE duoc day vao subquery, giam so dong trung gian",
                "confidence": "high",
                "pattern": "WHERE tren subquery ngoai",
                "formula": "So dong giam = So dong subquery × Ti so filter"
            }
        elif info["has_subquery"]:
            result["ast_predicate_pushdown"] = {
                "applicable": False,
                "estimated_benefit": "Khong co WHERE o ngoai de day",
                "confidence": "high",
                "pattern": "Khong co WHERE tren subquery",
                "formula": None
            }
        else:
            result["ast_predicate_pushdown"] = {
                "applicable": False,
                "estimated_benefit": "Khong co subquery",
                "confidence": "high",
                "pattern": "Query khong co subquery",
                "formula": None
            }

        # 2. Projection Pruning
        has_extra_cols = self._has_extra_columns(sql)
        if info["has_select_star"]:
            result["ast_projection_pruning"] = {
                "applicable": True,
                "estimated_benefit": "Trung binh — loai bo cot thua, giam I/O nhung can schema de expand *",
                "confidence": "medium",
                "pattern": "SELECT * duoc phat hien",
                "formula": "I/O giam = (So cot - So cot can thiet) / Tong so cot × 100%"
            }
        elif has_extra_cols:
            result["ast_projection_pruning"] = {
                "applicable": True,
                "estimated_benefit": "Trung binh — cot thua trong subquery co the loai bo",
                "confidence": "high",
                "pattern": "Subquery chua cot thua",
                "formula": "So cot loai bo / Tong so cot × I/O reduction"
            }
        else:
            result["ast_projection_pruning"] = {
                "applicable": False,
                "estimated_benefit": "Khong co cot thua",
                "confidence": "high",
                "pattern": "Tat ca cot deu duoc su dung",
                "formula": None
            }

        # 3. Subquery Unnesting
        if info["has_in_subquery"] or info["has_exists_subquery"]:
            if info["num_tables"] > 1:
                result["ast_subquery_unnesting"] = {
                    "applicable": True,
                    "estimated_benefit": "Cao — Nested Loop O(n×m) -> Hash Join O(n+m)",
                    "confidence": "high",
                    "pattern": f"IN/EXISTS subquery voi {info['num_tables']} bang",
                    "formula": "Time: O(n×m) -> O(n+m), Space: O(1) -> O(m)"
                }
            else:
                result["ast_subquery_unnesting"] = {
                    "applicable": True,
                    "estimated_benefit": "Trung binh — co the tang toc nhung hieu qua phu thuoc du lieu",
                    "confidence": "medium",
                    "pattern": "IN/EXISTS subquery (1 bang)",
                    "formula": "Phu thuoc vao kich thuoc du lieu"
                }
        else:
            result["ast_subquery_unnesting"] = {
                "applicable": False,
                "estimated_benefit": "Khong co IN/EXISTS subquery",
                "confidence": "high",
                "pattern": "Query khong co subquery de unnest",
                "formula": None
            }

        # 4. Join Reordering
        if info["num_joins"] >= 2:
            result["ast_join_reordering"] = {
                "applicable": True,
                "estimated_benefit": "Cao — thu tu JOIN tot co the giam dang ke so dong trung gian",
                "confidence": "high",
                "pattern": f"{info['num_joins']} JOINs trong query",
                "formula": "Dong trung gian = tich kich thuoc cac bang giua 2 JOIN"
            }
        elif info["num_joins"] == 1:
            result["ast_join_reordering"] = {
                "applicable": False,
                "estimated_benefit": "Chi co 1 JOIN, khong can reorder",
                "confidence": "high",
                "pattern": "Khong co nhieu hon 1 JOIN",
                "formula": None
            }
        else:
            result["ast_join_reordering"] = {
                "applicable": False,
                "estimated_benefit": "Khong co JOIN",
                "confidence": "high",
                "pattern": "Query khong co JOIN",
                "formula": None
            }

        # 5. Aggregation Pushdown
        if info["has_nested_agg"]:
            result["ast_aggregation_pushdown"] = {
                "applicable": True,
                "estimated_benefit": "Cao — GROUP BY tren subquery co the day xuong, giam dong",
                "confidence": "high",
                "pattern": "GROUP BY over subquery",
                "formula": "So dong truoc = N × M, Sau = N (sau aggregate)"
            }
        elif info["has_group_by"] and info["has_subquery"]:
            result["ast_aggregation_pushdown"] = {
                "applicable": True,
                "estimated_benefit": "Trung binh — co the co GROUP BY tren subquery",
                "confidence": "medium",
                "pattern": "GROUP BY voi subquery",
                "formula": "Phu thuoc vao kich thuoc subquery"
            }
        else:
            result["ast_aggregation_pushdown"] = {
                "applicable": False,
                "estimated_benefit": "Khong co GROUP BY over subquery",
                "confidence": "high",
                "pattern": "Khong co GROUP BY tren subquery",
                "formula": None
            }

        # 6. Redundant Join Elimination
        if info["num_joins"] >= 1 and not info["has_where_on_joined"]:
            result["ast_redundant_join_elimination"] = {
                "applicable": True,
                "estimated_benefit": "Trung binh — JOIN co the khong can thiet neu cot join khong duoc dung",
                "confidence": "medium",
                "pattern": "JOIN nhung khong co filter tren bang duoc JOIN",
                "formula": "Chi loai bo neu cot join khong nam trong SELECT/WHERE/GROUP"
            }
        elif info["num_joins"] >= 1:
            result["ast_redundant_join_elimination"] = {
                "applicable": False,
                "estimated_benefit": "JOIN co su dung trong WHERE/SELECT",
                "confidence": "high",
                "pattern": "Cot join duoc su dung o ngoai",
                "formula": None
            }
        else:
            result["ast_redundant_join_elimination"] = {
                "applicable": False,
                "estimated_benefit": "Khong co JOIN",
                "confidence": "high",
                "pattern": "Khong co JOIN de loai bo",
                "formula": None
            }

        # 7. Filter Into Join
        if info["num_joins"] >= 1 and info["has_where_on_joined"]:
            result["ast_filter_into_join"] = {
                "applicable": True,
                "estimated_benefit": "Cao — filter chay cung voi JOIN, giam so dong dau vao",
                "confidence": "high",
                "pattern": "WHERE filter tren cot bang trong JOIN",
                "formula": "So dong JOIN giam = So dong bieu thuc WHERE × Ti so selectitivity"
            }
        else:
            result["ast_filter_into_join"] = {
                "applicable": False,
                "estimated_benefit": "Khong co filter de day vao JOIN",
                "confidence": "high",
                "pattern": "Khong co WHERE tren bang trong JOIN",
                "formula": None
            }

        # 8. Limit Pushdown
        if info["has_limit_on_subquery"]:
            result["ast_limit_pushdown"] = {
                "applicable": True,
                "estimated_benefit": "Cao — LIMIT duoc day vao subquery, tranh sort toan bo",
                "confidence": "high",
                "pattern": "LIMIT nam ngoai subquery",
                "formula": "So dong sort truoc = N, Sau = LIMIT (thuong nho hon N)"
            }
        elif info["has_limit"] and info["has_order_by"]:
            result["ast_limit_pushdown"] = {
                "applicable": True,
                "estimated_benefit": "Trung binh — LIMIT co the day vao subquery",
                "confidence": "medium",
                "pattern": "LIMIT + ORDER BY",
                "formula": "Phu thuoc vao vi tri LIMIT"
            }
        else:
            result["ast_limit_pushdown"] = {
                "applicable": False,
                "estimated_benefit": "Khong co LIMIT tren subquery",
                "confidence": "high",
                "pattern": "Khong co LIMIT de day",
                "formula": None
            }

        return result

    def _has_extra_columns(self, sql: str) -> bool:
        """Kiem tra subquery co cot thua (inner co nhieu cot hon outer can)."""
        # Pattern: SELECT x, y FROM (SELECT a, b, c, d FROM t) AS sub
        # Inner co 4 cot, outer chi can 2
        return bool(re.search(
            r'SELECT\s+(?:sub\.\w+|\w+)\s+FROM\s+\(\s*SELECT\s+\w[\w,\s]+\s+FROM\b',
            sql, re.IGNORECASE | re.DOTALL
        ))

    def select_best_rules(self, sql: str) -> dict:
        """
        Chon ra cac rule tot nhat cho query, khong can LLM.
        Su dung pattern matching + heuristic scoring.

        Cong thuc chon rule:
          score(rule) = applicable × confidence_weight × benefit_weight

        Trong do:
          - applicable: 1 neu rule co the ap dung, 0 neu khong
          - confidence_weight: high=1.0, medium=0.7, low=0.4
          - benefit_weight: Cao=1.0, Trung binh=0.6, Thap=0.3

        Lay top-3 rules co diem cao nhat.
        """
        benefits = self.estimate_rule_benefit(sql)
        scores = {}

        benefit_map = {"Cao": 1.0, "Trung binh": 0.6, "Thap": 0.3}
        confidence_map = {"high": 1.0, "medium": 0.7, "low": 0.4}

        for rule_name, info in benefits.items():
            if info["applicable"]:
                benefit = info["estimated_benefit"]
                b_weight = 0.0
                for key, val in benefit_map.items():
                    if key.lower() in benefit.lower():
                        b_weight = val
                        break
                c_weight = confidence_map.get(info["confidence"], 0.5)
                scores[rule_name] = b_weight * c_weight
            else:
                scores[rule_name] = 0.0

        # Sap xep theo diem giam dan
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_rules = [(name, score) for name, score in ranked if score > 0][:3]

        return {
            "recommended_rules": [r[0] for r in top_rules],
            "rule_scores": {name: round(score, 3) for name, score in ranked if score > 0},
            "analysis": benefits,
            "sql_analysis": self.analyze(sql),
            "selection_method": "Pattern-based heuristic (no LLM)",
            "total_rules_applicable": sum(1 for s in scores.values() if s > 0)
        }


def run_offline_evaluation():
    """Chay danh gia tat ca rules tren test_cases.json — khong can PostgreSQL."""
    import json
    import os

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    queries_file = os.path.join(base_dir, 'my_exp', 'queries', 'test_cases.json')
    results_dir = os.path.join(base_dir, 'my_exp', 'results')
    os.makedirs(results_dir, exist_ok=True)

    if not os.path.exists(queries_file):
        print(f"Error: {queries_file} not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    analyzer = SQLPatternAnalyzer()
    results = []

    print(f"Running offline evaluation on {len(queries)} test queries...")
    print("=" * 80)

    for query in queries:
        qid = query.get("query_id", "?")
        sql = query.get("sql", "")
        target = query.get("target_rules", [])

        # Phan tich SQL
        analysis = analyzer.select_best_rules(sql)

        # Ap dung tat ca rules de xem co thay doi khong
        rule_results = {}
        for rule_name, rule in ALL_RULES.items():
            try:
                rewritten = rule.apply(sql)
                changed = rewritten.strip() != sql.strip()
                rule_results[rule_name] = {
                    "changed": changed,
                    "rewritten": rewritten if changed else None,
                    "analysis": analysis["analysis"].get(rule_name, {}),
                }
            except Exception as e:
                rule_results[rule_name] = {"changed": False, "error": str(e)}

        results.append({
            "query_id": qid,
            "name": query.get("name", ""),
            "sql": sql,
            "target_rules": target,
            "recommended_rules": analysis["recommended_rules"],
            "rule_scores": analysis["rule_scores"],
            "sql_patterns": {k: v for k, v in analysis["sql_analysis"].items() if v},
            "rule_results": rule_results,
        })

        # In ket qua ngan gon
        print(f"\n[{qid}] {query.get('name', '')}")
        print(f"  Patterns: {', '.join(k for k, v in analysis['sql_analysis'].items() if v)}")
        print(f"  Recommended: {analysis['recommended_rules']}")
        applicable = [r for r, s in analysis['rule_scores'].items() if s > 0]
        print(f"  Applicable rules: {applicable}")
        changed_rules = [r for r, res in rule_results.items() if res.get('changed')]
        print(f"  Rules that changed SQL: {changed_rules}")
        print(f"  Target: {target}")
        print(f"  Rec matches target: {any(r in target for r in analysis['recommended_rules'])}")

    # Luu ket qua chi tiet
    results_file = os.path.join(results_dir, 'offline_evaluation_results.json')
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Tao bang tom tat
    summary_file = os.path.join(results_dir, 'offline_evaluation_summary.csv')
    with open(summary_file, 'w', encoding='utf-8', newline='') as f:
        f.write("query_id,name,recommended_rules,applicable_count,changed_count,target_match,sql_patterns\n")
        for r in results:
            patterns = "; ".join(f"{k}={v}" for k, v in r["sql_patterns"].items() if v)
            changed = len([x for x in r["rule_results"].values() if x.get("changed")])
            target_match = any(rr in r["target_rules"] for rr in r["recommended_rules"])
            f.write(f'"{r["query_id"]}","{r["name"]}","{", ".join(r["recommended_rules"])}",'
                    f'{len(r["rule_scores"])},{changed},{target_match},"{patterns}"\n')

    print(f"\n{'=' * 80}")
    print(f"Offline evaluation complete.")
    print(f"  Results: {results_file}")
    print(f"  Summary: {summary_file}")

    # Thong ke tong hop
    print(f"\n=== SUMMARY ===")
    total = len(results)
    matched = sum(1 for r in results if any(rr in r["target_rules"] for rr in r["recommended_rules"]))
    print(f"Total queries: {total}")
    print(f"Recommendation matches target: {matched}/{total} ({matched/total*100:.1f}%)")

    rule_freq = {}
    for r in results:
        for rule in r["recommended_rules"]:
            rule_freq[rule] = rule_freq.get(rule, 0) + 1
    print(f"\nRule frequency in recommendations:")
    for rule, count in sorted(rule_freq.items(), key=lambda x: x[1], reverse=True):
        print(f"  {rule}: {count}/{total}")

    changed_freq = {}
    for r in results:
        for rule, res in r["rule_results"].items():
            if res.get("changed"):
                changed_freq[rule] = changed_freq.get(rule, 0) + 1
    print(f"\nRules that changed SQL:")
    for rule, count in sorted(changed_freq.items(), key=lambda x: x[1], reverse=True):
        print(f"  {rule}: {count}/{total}")


if __name__ == "__main__":
    run_offline_evaluation()
