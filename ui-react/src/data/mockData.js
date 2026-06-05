/**
 * mockData.js
 * Realistic mock data matching the exact backend payload structure
 * from my_exp/api/models.py (AnalysisResult).
 * All text in standard professional English.
 */

export const mockAnalysisResult = {
  query_id: "q_99281",
  timestamp: "2026-06-04T10:30:00Z",
  original_sql: `SELECT a.*, b.*
FROM orders a
LEFT JOIN customers b
  ON a.cust_id = b.id
WHERE b.status = 'ACTIVE'
  AND a.order_date >= '2026-01-01';`,

  rule_recommendations: {
    method: "llm",
    overall_analysis:
      "Query contains 2 tables, 1 LEFT JOIN, and 2 filter conditions. " +
      "Two optimizations available: (1) Remove unnecessary columns from SELECT, " +
      "(2) Convert LEFT JOIN to INNER JOIN since all filters are mandatory.",
    recommendations: [
      {
        rule: "projection_pruning",
        priority: 1,
        reason:
          "SELECT a.*, b.* retrieves all columns from both tables. " +
          "Only a.id, a.order_date, and b.name are needed. " +
          "Removing unnecessary columns reduces memory footprint and network I/O significantly. " +
          "Additionally, since WHERE b.status = 'ACTIVE' is mandatory, " +
          "the LEFT JOIN is effectively equivalent to an INNER JOIN.",
        before_snippet: "SELECT a.*, b.*",
        after_snippet: "SELECT a.id, a.order_date, b.name",
      },
      {
        rule: "join_reordering",
        priority: 2,
        reason:
          "LEFT JOIN customers b ON a.cust_id = b.id " +
          "WHERE b.status = 'ACTIVE' — filter is mandatory on table b. " +
          "Pushing the WHERE condition into the JOIN condition and converting LEFT JOIN to INNER JOIN " +
          "places the smaller table (customers, with filter applied) first, reducing intermediate rows exponentially.",
        before_snippet: "FROM orders a LEFT JOIN customers b ON a.cust_id = b.id",
        after_snippet: "FROM customers b INNER JOIN orders a ON b.id = a.cust_id",
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
      sql: `SELECT a.*, b.*
FROM orders a
LEFT JOIN customers b
  ON a.cust_id = b.id
WHERE b.status = 'ACTIVE'
  AND a.order_date >= '2026-01-01';`,
      is_original: true,
      changed: false,
      rules_applied: [],
      semantic_check: {
        equivalent: true,
        error: null,
        details: "Original query — baseline for comparison",
      },
      plan_comparison: {
        original: {
          metrics: {
            total_cost: 1450,
            io_cost: 850,
            cpu_cost: 600,
            estimated_time_ms: 340,
          },
        },
        rewritten: {
          metrics: {
            total_cost: 1450,
            io_cost: 850,
            cpu_cost: 600,
            estimated_time_ms: 340,
          },
        },
        comparison: {
          cost_improvement_pct: 0,
          io_improvement_pct: 0,
          cpu_improvement_pct: 0,
        },
      },
      confidence: "High",
      warning: null,
    },
    {
      id: "cand_1",
      sql: `SELECT
  a.id,
  a.order_date,
  b.name
FROM customers b
INNER JOIN orders a
  ON b.id = a.cust_id
WHERE b.status = 'ACTIVE'
  AND a.order_date >= '2026-01-01';`,
      is_original: false,
      changed: true,
      rules_applied: ["projection_pruning", "join_reordering"],
      semantic_check: {
        equivalent: true,
        error: null,
        details:
          "Projection Pruning + Join Reordering applied. " +
          "LEFT JOIN converted to INNER JOIN — equivalent given mandatory WHERE filter on b.status.",
      },
      plan_comparison: {
        original: {
          metrics: {
            total_cost: 1450,
            io_cost: 850,
            cpu_cost: 600,
            estimated_time_ms: 340,
          },
        },
        rewritten: {
          metrics: {
            total_cost: 820,
            io_cost: 380,
            cpu_cost: 440,
            estimated_time_ms: 125,
          },
        },
        comparison: {
          cost_improvement_pct: -43.4,
          io_improvement_pct: -55.3,
          cpu_improvement_pct: -26.7,
        },
      },
      confidence: "High",
      warning:
        "Only equivalent if b.status is NOT NULL for every customer. " +
        "If there are customers with no orders, the result set will differ.",
    },
    {
      id: "cand_2",
      sql: `SELECT
  a.id,
  a.order_date,
  a.cust_id,
  b.name,
  b.status
FROM orders a
LEFT JOIN customers b
  ON a.cust_id = b.id
WHERE b.status = 'ACTIVE'
  AND a.order_date >= '2026-01-01';`,
      is_original: false,
      changed: true,
      rules_applied: ["projection_pruning"],
      semantic_check: {
        equivalent: true,
        error: null,
        details: "Projection Pruning only — LEFT JOIN preserved",
      },
      plan_comparison: {
        original: {
          metrics: {
            total_cost: 1450,
            io_cost: 850,
            cpu_cost: 600,
            estimated_time_ms: 340,
          },
        },
        rewritten: {
          metrics: {
            total_cost: 1180,
            io_cost: 620,
            cpu_cost: 560,
            estimated_time_ms: 210,
          },
        },
        comparison: {
          cost_improvement_pct: -18.6,
          io_improvement_pct: -27.1,
          cpu_improvement_pct: -6.7,
        },
      },
      confidence: "Medium",
      warning: null,
    },
  ],

  recommendation: {
    best_candidate_id: "cand_1",
    best_sql: `SELECT
  a.id,
  a.order_date,
  b.name
FROM customers b
INNER JOIN orders a
  ON b.id = a.cust_id
WHERE b.status = 'ACTIVE'
  AND a.order_date >= '2026-01-01';`,
    best_rules: ["projection_pruning", "join_reordering"],
    improvement_pct: -43.4,
    semantic_equivalent: true,
    confidence: 0.95,
  },
};

/** 6 Knowledge Base rules — English labels only */
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
    benefit: "High — O(n*m) → O(n+m)",
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
