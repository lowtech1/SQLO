"""Generate synthetic DSB test cases using available tables."""
import json

cases = []

cases.append({
    'query_id': 'dsb_1',
    'name': 'Predicate Pushdown 1 (WHERE on subquery)',
    'sql': 'SELECT t.d_year, SUM(ss_net_paid) FROM (SELECT d_date_sk, d_year FROM date_dim WHERE d_year >= 2000) AS t JOIN store_sales AS s ON t.d_date_sk = s.ss_sold_date_sk WHERE t.d_year = 2001 GROUP BY t.d_year',
    'target_rules': ['ast_predicate_pushdown'],
    'expected_optimization': 'Push WHERE d_year into subquery'
})
cases.append({
    'query_id': 'dsb_2',
    'name': 'Predicate Pushdown 2 (multiple conditions)',
    'sql': 'SELECT i.i_category, SUM(ss_net_paid) FROM (SELECT i_item_sk, i_category FROM item WHERE i_current_price > 100) AS t JOIN store_sales AS s ON t.i_item_sk = s.ss_item_sk JOIN date_dim AS d ON s.ss_sold_date_sk = d.d_date_sk WHERE d.d_year >= 2000 AND d.d_quarter > 2 GROUP BY i.i_category',
    'target_rules': ['ast_predicate_pushdown'],
    'expected_optimization': 'Multiple predicates on subquery'
})
cases.append({
    'query_id': 'dsb_3',
    'name': 'Projection Pruning 1 (SELECT *)',
    'sql': 'SELECT t.d_year, SUM(t.ss_net_paid) FROM (SELECT * FROM store_sales AS s JOIN date_dim AS d ON s.ss_sold_date_sk = d.d_date_sk) AS t WHERE t.d_year = 2001 GROUP BY t.d_year',
    'target_rules': ['ast_projection_pruning'],
    'expected_optimization': 'Remove unused columns from SELECT *'
})
cases.append({
    'query_id': 'dsb_4',
    'name': 'Projection Pruning 2 (nested SELECT *)',
    'sql': 'SELECT * FROM (SELECT * FROM store_sales WHERE ss_quantity > 5) AS t WHERE t.ss_net_paid > 100',
    'target_rules': ['ast_projection_pruning'],
    'expected_optimization': 'SELECT * in outer and inner query'
})
cases.append({
    'query_id': 'dsb_5',
    'name': 'Subquery Unnesting 1 (IN subquery)',
    'sql': 'SELECT i_item_sk FROM item WHERE i_item_sk IN (SELECT ss_item_sk FROM store_sales WHERE ss_net_paid > 500)',
    'target_rules': ['ast_subquery_unnesting'],
    'expected_optimization': 'Convert IN subquery to JOIN'
})
cases.append({
    'query_id': 'dsb_6',
    'name': 'Subquery Unnesting 2 (EXISTS)',
    'sql': "SELECT i_category FROM item WHERE EXISTS (SELECT 1 FROM store_sales WHERE store_sales.ss_item_sk = item.i_item_sk AND ss_quantity > 10)",
    'target_rules': ['ast_subquery_unnesting'],
    'expected_optimization': 'Convert EXISTS to JOIN'
})
cases.append({
    'query_id': 'dsb_7',
    'name': 'Join Reordering 1 (3-table join)',
    'sql': 'SELECT d.d_year, i.i_category, SUM(ss_net_paid) FROM store_sales AS s JOIN date_dim AS d ON s.ss_sold_date_sk = d.d_date_sk JOIN item AS i ON s.ss_item_sk = i.i_item_sk WHERE d.d_year >= 2000 GROUP BY d.d_year, i.i_category',
    'target_rules': ['ast_join_reordering'],
    'expected_optimization': 'Reorder joins by table size'
})
cases.append({
    'query_id': 'dsb_8',
    'name': 'Aggregation Pushdown 1',
    'sql': 'SELECT i_category, SUM(net) FROM (SELECT ss_item_sk, ss_net_paid AS net, i_item_sk FROM store_sales AS s JOIN item AS i ON s.ss_item_sk = i.i_item_sk) AS t GROUP BY i_category',
    'target_rules': ['ast_aggregation_pushdown'],
    'expected_optimization': 'Push GROUP BY into subquery'
})
cases.append({
    'query_id': 'dsb_9',
    'name': 'Redundant Join Elimination 1 (unused promo JOIN)',
    'sql': 'SELECT s.ss_item_sk, s.ss_net_paid FROM store_sales AS s JOIN promotion AS p ON s.ss_promo_sk = p.p_promo_sk JOIN store AS st ON s.ss_store_sk = st.s_store_sk WHERE p.p_cost > 100 AND st.s_market_id = 1',
    'target_rules': ['ast_redundant_join_elimination'],
    'expected_optimization': 'Remove promotion JOIN when only used in filter'
})
cases.append({
    'query_id': 'dsb_10',
    'name': 'Redundant Join Elimination 2 (unused store JOIN)',
    'sql': 'SELECT d.d_year, SUM(ss_net_paid) FROM store_sales AS s JOIN date_dim AS d ON s.ss_sold_date_sk = d.d_date_sk JOIN store AS st ON s.ss_store_sk = st.s_store_sk WHERE d.d_year = 2001 GROUP BY d.d_year',
    'target_rules': ['ast_redundant_join_elimination'],
    'expected_optimization': 'Eliminate store JOIN when unused'
})
cases.append({
    'query_id': 'dsb_11',
    'name': 'Filter Into Join 1',
    'sql': "SELECT d.d_year, i.i_category, SUM(ss_net_paid) FROM store_sales AS s JOIN date_dim AS d ON s.ss_sold_date_sk = d.d_date_sk JOIN item AS i ON s.ss_item_sk = i.i_item_sk WHERE d.d_year >= 2000 AND i.i_category = 'Books' GROUP BY d.d_year, i.i_category",
    'target_rules': ['ast_filter_into_join'],
    'expected_optimization': 'Move WHERE filter into JOIN ON clause'
})
cases.append({
    'query_id': 'dsb_12',
    'name': 'Limit Pushdown 1',
    'sql': 'SELECT i_category, SUM(ss_net_paid) FROM (SELECT ss_item_sk, ss_net_paid FROM store_sales LIMIT 1000) AS t JOIN item AS i ON t.ss_item_sk = i.i_item_sk GROUP BY i_category',
    'target_rules': ['ast_limit_pushdown'],
    'expected_optimization': 'Push LIMIT into subquery'
})
cases.append({
    'query_id': 'dsb_13',
    'name': 'Predicate Pushdown 3 (BETWEEN)',
    'sql': 'SELECT d_year, COUNT(*) FROM (SELECT d_date_sk, d_year FROM date_dim WHERE d_year BETWEEN 1999 AND 2003) AS t JOIN store_sales AS s ON t.d_date_sk = s.ss_sold_date_sk GROUP BY d_year',
    'target_rules': ['ast_predicate_pushdown'],
    'expected_optimization': 'BETWEEN predicate pushdown'
})
cases.append({
    'query_id': 'dsb_14',
    'name': 'Multi-rule: Predicate + Projection',
    'sql': 'SELECT d.d_year, SUM(t.net) FROM (SELECT ss_sold_date_sk, ss_net_paid AS net FROM store_sales WHERE ss_quantity > 1) AS t JOIN date_dim AS d ON t.ss_sold_date_sk = d.d_date_sk WHERE d.d_year >= 2000 GROUP BY d.d_year',
    'target_rules': ['ast_predicate_pushdown', 'ast_projection_pruning'],
    'expected_optimization': 'Push WHERE and prune SELECT in subquery'
})
cases.append({
    'query_id': 'dsb_15',
    'name': 'Join Reordering 2 (4-table)',
    'sql': 'SELECT st.s_store_name, d.d_year, i.i_category, SUM(ss_net_paid) FROM store_sales AS s JOIN store AS st ON s.ss_store_sk = st.s_store_sk JOIN date_dim AS d ON s.ss_sold_date_sk = d.d_date_sk JOIN item AS i ON s.ss_item_sk = i.i_item_sk WHERE st.s_market_id = 1 AND d.d_year >= 2000 GROUP BY st.s_store_name, d.d_year, i.i_category',
    'target_rules': ['ast_join_reordering', 'ast_filter_into_join'],
    'expected_optimization': 'Reorder 4-table join and move filter into JOIN'
})

with open('my_exp/queries/test_cases_dsb.json', 'w', encoding='utf-8') as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
print(f'Created {len(cases)} synthetic DSB test cases')
