"""
my_exp.dss.test_dss
==================
Test DSS components without database connection.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.dss.optimizer_pipeline import OptimizationPipeline
from my_exp.dss.llm_rule_selector import LLMRuleSelector, build_llm_prompt, parse_llm_response
from my_exp.core.sql_analyzer import SQLFeatureExtractor
from my_exp.core.multi_rewrite_engine import MultiRewriteEngine


def test_sql_analyzer():
    print("=" * 70)
    print("TEST: SQL Feature Extractor")
    print("=" * 70)

    extractor = SQLFeatureExtractor()
    tests = [
        "SELECT * FROM orders WHERE o_totalprice > 100",
        "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000)",
        "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a",
        "SELECT a.id, a.name FROM a JOIN b ON a.b_id = b.id WHERE a.status = 1",
        "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 10",
        "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 10",
        "SELECT l.l_orderkey, l.l_quantity, c.c_name FROM lineitem l JOIN orders o ON l.l_orderkey = o.o_orderkey JOIN customer c ON o.o_custkey = c.c_customerkey WHERE l.l_quantity > 30",
    ]

    for sql in tests:
        features = extractor.extract(sql)
        print(f"\nSQL: {sql[:60]}...")
        print(f"  Tables={features['table_count']}, Joins={features['join_count']}, "
              f"Subqueries={features['subquery_count']}")
        print(f"  Complexity: {features['complexity']['level']} (score={features['complexity']['score']})")
        print(f"  Opps: {[o['rule'] for o in features['optimization_opportunities']]}")


def test_multi_rewrite():
    print("\n" + "=" * 70)
    print("TEST: Multi-Rewrite Engine")
    print("=" * 70)

    engine = MultiRewriteEngine()
    tests = [
        ("Predicate Pushdown", "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 10"),
        ("Subquery Unnesting", "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders);"),
        ("Projection Pruning", "SELECT c_name FROM (SELECT * FROM customer) AS sub"),
        ("Multiple JOINs", "SELECT * FROM orders o JOIN lineitem l ON o.id=l.o_id JOIN nation n ON o.n_id=n.id WHERE o.o_totalprice > 10000"),
    ]

    for name, sql in tests:
        print(f"\n[{name}]")
        print(f"  Original: {sql[:60]}...")
        summary = engine.get_summary(sql)
        print(f"  Applicable rules: {summary.get('applicable_rules', [])}")
        candidates = engine.generate_candidates(sql, max_candidates=5)
        print(f"  Candidates: {len(candidates)}")
        for c in candidates:
            print(f"    [{c['id']}] original={c['is_original']}, rules={c['rules_applied']}, "
                  f"changed={c['changed']}")
            if c['rules_applied']:
                print(f"         -> {c['sql'][:60]}...")


def test_pipeline():
    print("\n" + "=" * 70)
    print("TEST: Full Optimization Pipeline (no DB)")
    print("=" * 70)

    pipeline = OptimizationPipeline(use_llm=False, dbname=None)
    sql = "SELECT a FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10"

    print(f"\nSQL: {sql}")
    result = pipeline.run_full(sql, max_candidates=5)

    print(f"\nQuery ID: {result['query_id']}")
    print(f"Total candidates: {result['metadata']['total_candidates']}")
    print(f"Equivalent: {result['metadata']['equivalent_candidates']}")

    print(f"\nRule Recommendations ({result['rule_recommendations']['method']}):")
    for rec in result['rule_recommendations']['recommendations']:
        print(f"  P{rec['priority']}: {rec['rule']} ({rec['confidence']}) - {rec['reason']}")

    print(f"\nCandidates:")
    for c in result['candidates']:
        sem = c.get('semantic_check', {})
        plan = c.get('plan_comparison', {})
        print(f"  [{c['id']}] rules={c['rules_applied']}, "
              f"changed={c['changed']}, "
              f"semantic={sem.get('equivalent')}, "
              f"plan_error={plan.get('error', 'ok')[:30] if plan.get('error') else 'ok'}")


def test_rule_explainer():
    print("\n" + "=" * 70)
    print("TEST: Rule Explainer")
    print("=" * 70)

    pipeline = OptimizationPipeline(use_llm=False)
    sql = "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 10"

    rules_to_explain = ["predicate_pushdown", "subquery_unnesting", "join_reordering"]
    for rule in rules_to_explain:
        result = pipeline.explain_rule(rule, sql)
        print(f"\n[{rule}]")
        if "error" in result:
            print(f"  {result['error']}")
        else:
            meta = result["metadata"]
            analysis = result["analysis"]
            print(f"  Rule: {meta.get('name_vi')} ({meta.get('name')})")
            print(f"  Can apply: {analysis['can_apply']}")
            print(f"  Reason: {analysis['reason']}")
            print(f"  Benefit: {analysis['benefit']}")
            ex = analysis.get("example", {})
            if ex:
                print(f"  Example: {ex.get('input', '')[:40]}... -> ...")


def run_all():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    print("\n" + "#" * 70)
    print("#  LLM-R2 DSS: COMPONENT TESTS")
    print("#" * 70)

    test_sql_analyzer()
    test_multi_rewrite()
    test_pipeline()
    test_rule_explainer()

    print("\n" + "#" * 70)
    print("#  DSS TESTS COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    run_all()
