/**
 * mockData.js
 * Realistic mock data matching the exact backend payload structure
 * from my_exp/api/models.py (AnalysisResult).
 * Uses real TPC-H schema: customer, orders, lineitem, nation, region, part, supplier, partsupp.
 */

export const mockAnalysisResult = {
  query_id: "q_tpch001",
  timestamp: "2026-06-07T08:00:00Z",

  // TPC-H schema: customer (c_*), orders (o_*)
  original_sql: `SELECT c.c_name, o.o_totalprice
FROM customer c
LEFT JOIN orders o ON c.c_custkey = o.o_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
  AND o.o_totalprice > 1000`,

  rule_recommendations: {
    method: "llm",
    overall_analysis:
      "Query joins customer and orders on TPC-H schema (c_custkey/o_custkey). " +
      "LEFT JOIN preserves all customers even without orders. WHERE filter on o_totalprice is mandatory. " +
      "Two optimizations recommended: (1) Convert LEFT JOIN to INNER JOIN — filter makes LEFT JOIN redundant, " +
      "(2) Prune columns to only c_name and o_totalprice.",
    recommendations: [
      {
        rule: "join_reordering",
        priority: 1,
        reason:
          "LEFT JOIN with WHERE o.o_totalprice > 1000 eliminates NULL orders anyway. " +
          "Converting LEFT JOIN to INNER JOIN is safe and enables Hash Join with the smaller, " +
          "filtered orders table driving first, reducing intermediate rows significantly.",
        before_snippet: "FROM customer c LEFT JOIN orders o ON c.c_custkey = o.o_custkey",
        after_snippet: "FROM orders o INNER JOIN customer c ON o.o_custkey = c.c_custkey",
      },
      {
        rule: "projection_pruning",
        priority: 2,
        reason:
          "SELECT c.*, o.* retrieves all columns from both tables. " +
          "Only c.c_name and o.o_totalprice are referenced. " +
          "Pruning to these 2 columns reduces I/O bandwidth and memory footprint by ~75%.",
        before_snippet: "SELECT c.*, o.*",
        after_snippet: "SELECT c.c_name, o.o_totalprice",
      },
    ],
  },

  metrics: {
    total_cost: 820.0,
    io_cost: 380.0,
    cpu_cost: 440.0,
    execution_time_ms: 125.0,
  },

  candidates: [
    {
      id: "cand_0",
      sql: `SELECT c.c_name, o.o_totalprice
FROM customer c
LEFT JOIN orders o ON c.c_custkey = o.o_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
  AND o.o_totalprice > 1000`,
      is_original: true,
      changed: false,
      rules_applied: [],
      semantic_check: {
        equivalent: true,
        error: null,
        details: "Original query — baseline for comparison (TPC-H schema: customer, orders)",
      },
      plan_comparison: {
        original: {
          metrics: { total_cost: 1450, io_cost: 850, cpu_cost: 600, estimated_time_ms: 340 },
        },
        rewritten: {
          metrics: { total_cost: 1450, io_cost: 850, cpu_cost: 600, estimated_time_ms: 340 },
        },
        comparison: {
          cost_improvement_pct: 0, io_improvement_pct: 0, cpu_improvement_pct: 0,
        },
      },
      confidence: "High",
      warning: null,
    },
    {
      id: "cand_1",
      sql: `SELECT c.c_name, o.o_totalprice
FROM orders o
INNER JOIN customer c ON o.o_custkey = c.c_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
  AND o.o_totalprice > 1000`,
      is_original: false,
      changed: true,
      rules_applied: ["join_reordering"],
      semantic_check: {
        equivalent: true,
        error: null,
        details:
          "LEFT JOIN converted to INNER JOIN — safe because WHERE o.o_totalprice > 1000 " +
          "eliminates NULL orders, making LEFT JOIN equivalent to INNER JOIN. " +
          "Join order reversed: smaller filtered orders table drives Hash Join.",
      },
      plan_comparison: {
        original: {
          metrics: { total_cost: 1450, io_cost: 850, cpu_cost: 600, estimated_time_ms: 340 },
        },
        rewritten: {
          metrics: { total_cost: 820, io_cost: 380, cpu_cost: 440, estimated_time_ms: 125 },
        },
        comparison: {
          cost_improvement_pct: -43.4, io_improvement_pct: -55.3, cpu_improvement_pct: -26.7,
        },
      },
      confidence: "High",
      warning: null,
    },
    {
      id: "cand_2",
      sql: `SELECT c.c_name, o.o_totalprice
FROM customer c
INNER JOIN orders o ON c.c_custkey = o.o_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
  AND o.o_totalprice > 1000`,
      is_original: false,
      changed: true,
      rules_applied: ["projection_pruning"],
      semantic_check: {
        equivalent: true,
        error: null,
        details: "Projection Pruning applied — columns reduced to c_name and o_totalprice only.",
      },
      plan_comparison: {
        original: {
          metrics: { total_cost: 1450, io_cost: 850, cpu_cost: 600, estimated_time_ms: 340 },
        },
        rewritten: {
          metrics: { total_cost: 1180, io_cost: 620, cpu_cost: 560, estimated_time_ms: 210 },
        },
        comparison: {
          cost_improvement_pct: -18.6, io_improvement_pct: -27.1, cpu_improvement_pct: -6.7,
        },
      },
      confidence: "Medium",
      warning: null,
    },
  ],

  recommendation: {
    best_candidate_id: "cand_1",
    best_sql: `SELECT c.c_name, o.o_totalprice
FROM orders o
INNER JOIN customer c ON o.o_custkey = c.c_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
  AND o.o_totalprice > 1000`,
    best_rules: ["join_reordering"],
    improvement_pct: -43.4,
    semantic_equivalent: true,
    confidence: 0.95,
  },
};

/** 6 Knowledge Base rules */
export const KNOWLEDGE_BASE_RULES = [
  {
    id: "predicate_pushdown",
    name: "Predicate Pushdown",
    description: "Push WHERE from outer query into subquery / FROM clause",
    benefit: "High — reduces intermediate rows",
    risk: "Low",
  },
  {
    id: "projection_pruning",
    name: "Projection Pruning",
    description: "Remove unnecessary columns from SELECT clause",
    benefit: "Medium — reduces I/O bandwidth",
    risk: "Low",
  },
  {
    id: "join_reordering",
    name: "Join Reordering",
    description: "Reorder JOIN sequence based on table size",
    benefit: "High — reduces intermediate rows",
    risk: "Medium",
  },
  {
    id: "subquery_unnesting",
    name: "Subquery Unnesting",
    description: "Convert IN/EXISTS subquery to JOIN for Hash Join",
    benefit: "High — O(n*m) to O(n+m)",
    risk: "Medium",
  },
  {
    id: "aggregation_pushdown",
    name: "Aggregation Pushdown",
    description: "Push GROUP BY from outer query into subquery",
    benefit: "High — reduces rows before aggregation",
    risk: "Medium",
  },
  {
    id: "redundant_join_elimination",
    name: "Redundant Join Elimination",
    description: "Remove JOINs where table is not referenced",
    benefit: "Medium — eliminates hash join cost",
    risk: "Low",
  },
];
