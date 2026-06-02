"""
my_exp.core.test_rules
=====================
Comprehensive unit tests cho tat ca 8 rules.
Chay: python my_exp/core/run_tests.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Fix Windows console encoding for Vietnamese output
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def _norm(s):
    """Normalize SQL string for comparison: strip semicolons and extra whitespace."""
    return s.strip().rstrip(';').strip()

from my_exp.core.rules import get_rule
from my_exp.core.multi_rewrite_engine import MultiRewriteEngine
from my_exp.core.sql_analyzer import SQLFeatureExtractor


def test_predicate_pushdown():
    print("=" * 70)
    print("TEST: Predicate Pushdown")
    print("=" * 70)

    rule = get_rule("predicate_pushdown")
    tests = [
        ("Safe pushdown",
         "SELECT a, b FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10",
         True, "WHERE được đẩy vào subquery"),
        ("Unsafe — DISTINCT",
         "SELECT a FROM (SELECT DISTINCT a, b FROM t) AS sub WHERE a = 5",
         False, "DISTINCT không an toàn"),
        ("Unsafe — AGG",
         "SELECT sum_b FROM (SELECT a, SUM(b) AS sum_b FROM t GROUP BY a) AS sub WHERE sum_b > 100",
         False, "Aggregate không an toàn"),
        ("Unsafe — GROUP BY",
         "SELECT * FROM (SELECT a, b FROM t GROUP BY a, b) AS sub WHERE a > 5",
         False, "GROUP BY không an toàn"),
        ("Safe — multiple conditions",
         "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 5 AND b < 10",
         True, "Nhiều điều kiện AND được đẩy"),
        ("No subquery",
         "SELECT a FROM t WHERE a > 10",
         False, "Không có subquery"),
        ("TPC-H Q1 style",
         "SELECT l_returnflag, l_linestatus, SUM(l_quantity) AS sum_qty, SUM(l_extendedprice) AS sum_base_price FROM (SELECT l_orderkey, l_returnflag, l_linestatus, l_quantity, l_extendedprice FROM lineitem) AS li WHERE l_quantity > 0 GROUP BY l_returnflag, l_linestatus",
         True, "TPC-H Q1 pattern — pushdown được"),
        ("Missing column",
         "SELECT x FROM (SELECT b AS x FROM t) AS sub WHERE y = 1",
         False, "Cột y không tồn tại trong subquery"),
    ]

    passed = 0
    for name, sql, expected_can, desc in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        status = "PASS" if can_apply == expected_can else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"\n[{status}] {name}")
        print(f"  SQL: {sql[:70]}...")
        print(f"  Expected can_apply={expected_can}, got={can_apply}")
        print(f"  Reason: {reason}")
        print(f"  Changed: {changed}")
        if changed and can_apply:
            print(f"  Rewritten: {rewritten[:80]}...")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_projection_pruning():
    print("\n" + "=" * 70)
    print("TEST: Projection Pruning")
    print("=" * 70)

    rule = get_rule("projection_pruning")
    # NOTE: This rule only handles SELECT * patterns (via ast_rewriter)
    tests = [
        ("SELECT * — co the prune",
         "SELECT c_name FROM (SELECT * FROM customer) AS sub",
         True, True),
        ("Khong co SELECT *",
         "SELECT a FROM (SELECT a, b, c FROM t) AS sub",
         False, False),
    ]

    passed = 0
    for name, sql, expected_can, expected_changed in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = can_apply == expected_can and changed == expected_changed
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name}")
        print(f"  can_apply={can_apply} (expected {expected_can}), changed={changed} (expected {expected_changed})")
        if changed:
            print(f"  → {rewritten[:80]}...")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_join_reordering():
    print("\n" + "=" * 70)
    print("TEST: Join Reordering")
    print("=" * 70)

    rule = get_rule("join_reordering")
    tests = [
        ("3 INNER JOINs",
         "SELECT * FROM orders o JOIN lineitem l ON o.id=l.o_id JOIN nation n ON o.n_id=n.id",
         True, "Đủ JOIN, đổi thứ tự"),
        ("LEFT JOIN — unsafe",
         "SELECT * FROM a LEFT JOIN b ON a.id=b.id JOIN c ON b.id=c.id",
         False, "OUTER JOIN không an toàn"),
        ("1 JOIN",
         "SELECT * FROM a JOIN b ON a.id=b.id",
         False, "Ít hơn 2 JOIN"),
    ]

    passed = 0
    for name, sql, expected_can, desc in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = can_apply == expected_can
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name} — {desc}")
        print(f"  can_apply={can_apply}")
        if changed:
            print(f"  → {rewritten[:80]}...")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_subquery_unnesting():
    print("\n" + "=" * 70)
    print("TEST: Subquery Unnesting")
    print("=" * 70)

    rule = get_rule("subquery_unnesting")
    tests = [
        ("Simple IN subquery",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);",
         True, True),
        ("NOT IN — AST van transform",
         "SELECT * FROM a WHERE a.id NOT IN (SELECT b.id FROM b);",
         True, True),  # AST chuyen doi thanh JOIN, semantic warning duoc ghi nhan trong rule explanation
        ("No subquery",
         "SELECT * FROM orders WHERE o_totalprice > 50000;",
         False, False),
        ("Multiple IN",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000) AND c_custkey > 5;",
         True, True),
    ]

    passed = 0
    for name, sql, expected_can, expected_changed in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = (can_apply == expected_can) and (changed == expected_changed)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name}")
        print(f"  can_apply={can_apply}, changed={changed}")
        if changed:
            print(f"  -> {rewritten[:100]}...")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_aggregation_pushdown():
    print("\n" + "=" * 70)
    print("TEST: Aggregation Pushdown")
    print("=" * 70)

    rule = get_rule("aggregation_pushdown")
    tests = [
        ("GROUP BY over subquery",
         "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a;",
         True, True),
        ("Co HAVING",
         "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a HAVING SUM(sub.b) > 100;",
         True, False),  # AST kiem tra HAVING, khong rewrite
    ]

    passed = 0
    for name, sql, expected_can, expected_changed in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = (can_apply == expected_can) and (changed == expected_changed)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name}")
        if changed:
            print(f"  -> {rewritten[:80]}...")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_redundant_join():
    print("\n" + "=" * 70)
    print("TEST: Redundant Join Elimination")
    print("=" * 70)

    rule = get_rule("redundant_join_elimination")
    tests = [
        ("Co JOIN — kiem tra usage",
         "SELECT a.id, a.name FROM a JOIN b ON a.b_id = b.id WHERE a.status = 1;",
         True, True),
        ("OUTER JOIN",
         "SELECT a.id FROM a LEFT JOIN b ON a.id = b.id;",
         True, False),  # AST giu nguyen LEFT JOIN
        ("Co aggregate",
         "SELECT a.name, COUNT(a.id) FROM a JOIN b ON a.id = b.id GROUP BY a.name;",
         True, False),  # AST giu nguyen vi co aggregate
    ]

    passed = 0
    for name, sql, expected_can, expected_changed in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = (can_apply == expected_can) and (changed == expected_changed)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name}")
        if changed:
            print(f"  -> {rewritten}")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_filter_into_join():
    print("\n" + "=" * 70)
    print("TEST: Filter Into Join")
    print("=" * 70)

    rule = get_rule("filter_into_join")
    tests = [
        ("INNER JOIN",
         "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE' AND a.type = 1;",
         True, True),
        ("LEFT JOIN — giu nguyen WHERE",
         "SELECT * FROM a LEFT JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE';",
         True, False),
    ]

    passed = 0
    for name, sql, expected_can, expected_changed in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = (can_apply == expected_can) and (changed == expected_changed)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name}")
        if changed:
            print(f"  → {rewritten[:80]}...")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_limit_pushdown():
    print("\n" + "=" * 70)
    print("TEST: Limit Pushdown")
    print("=" * 70)

    rule = get_rule("limit_pushdown")
    tests = [
        ("LIMIT trên subquery",
         "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 10;",
         True, True),
        ("LIMIT san trong subquery",
         "SELECT * FROM (SELECT * FROM orders LIMIT 5) AS sub LIMIT 10;",
         True, False),  # AST giu nguyen, inner LIMIT khong bi ghi de
    ]

    passed = 0
    for name, sql, expected_can, expected_changed in tests:
        can_apply, reason = rule.can_apply(sql)
        rewritten = rule.apply(sql)
        changed = _norm(rewritten) != _norm(sql)
        ok = (can_apply == expected_can) and (changed == expected_changed)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n[{status}] {name}")
        if changed:
            print(f"  → {rewritten}")

    print(f"\nResult: {passed}/{len(tests)} passed")
    return passed, len(tests)


def test_multi_rewrite():
    print("\n" + "=" * 70)
    print("TEST: Multi-Rewrite Engine")
    print("=" * 70)

    engine = MultiRewriteEngine()

    sql = "SELECT a, b FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10"
    summary = engine.get_summary(sql)
    print(f"\nSQL: {sql}")
    print(f"Complexity: {summary.get('complexity', {})}")
    print(f"Applicable rules: {summary.get('applicable_rules', [])}")

    candidates = engine.generate_candidates(sql, max_candidates=5)
    print(f"\nGenerated {len(candidates)} candidates:")
    for c in candidates:
        print(f"  [{c['id']}] original={c['is_original']}, rules={c['rules_applied']}, changed={c['changed']}")
        if c['changed']:
            print(f"      → {c['sql'][:60]}...")


def test_sql_analyzer():
    print("\n" + "=" * 70)
    print("TEST: SQL Feature Extractor")
    print("=" * 70)

    extractor = SQLFeatureExtractor()
    tests = [
        "SELECT * FROM orders WHERE o_totalprice > 100",
        "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000)",
        "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a",
        "SELECT a.id, a.name FROM a JOIN b ON a.b_id = b.id WHERE a.status = 1",
    ]

    for sql in tests:
        features = extractor.extract(sql)
        print(f"\nSQL: {sql[:60]}...")
        print(f"  Tables: {features.get('table_count', 0)}, Joins: {features.get('join_count', 0)}, "
              f"Subqueries: {features.get('subquery_count', 0)}")
        print(f"  Complexity: {features.get('complexity', {}).get('level', 'N/A')}")
        print(f"  Opportunities: {len(features.get('optimization_opportunities', []))}")


def run_all_tests():
    print("\n" + "#" * 70)
    print("#  LLM-R2-ENHANCED: COMPREHENSIVE RULE TESTS")
    print("#" * 70)

    total_passed = 0
    total_tests = 0

    funcs = [
        ("Predicate Pushdown", test_predicate_pushdown),
        ("Projection Pruning", test_projection_pruning),
        ("Join Reordering", test_join_reordering),
        ("Subquery Unnesting", test_subquery_unnesting),
        ("Aggregation Pushdown", test_aggregation_pushdown),
        ("Redundant Join Elimination", test_redundant_join),
        ("Filter Into Join", test_filter_into_join),
        ("Limit Pushdown", test_limit_pushdown),
    ]

    for name, func in funcs:
        try:
            p, t = func()
            total_passed += p
            total_tests += t
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")

    test_multi_rewrite()
    test_sql_analyzer()

    print("\n" + "#" * 70)
    print(f"#  OVERALL: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.1f}%)")
    print("#" * 70)

    return total_passed, total_tests


if __name__ == "__main__":
    run_all_tests()
