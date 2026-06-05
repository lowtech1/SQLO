/**
 * TypeScript-like JSDoc type definitions.
 * These mirror the exact backend payload from optimizer_pipeline.py.
 */

/**
 * @typedef {'pending' | 'approved' | 'rejected'} DecisionStatus
 */

/**
 * @typedef {'llm' | 'pattern' | 'hybrid'} RuleMethod
 */

/**
 * @typedef {'Cao' | 'Trung binh' | 'Thap'} ConfidenceLevel
 */

/**
 * @typedef {Object} SemanticCheck
 * @property {boolean} equivalent
 * @property {string|null} error
 * @property {string|null} details
 */

/**
 * @typedef {Object} Metrics
 * @property {number} total_cost
 * @property {number} io_cost
 * @property {number} cpu_cost
 * @property {number} estimated_time_ms
 */

/**
 * @typedef {Object} PlanMetrics
 * @property {{metrics: Metrics}} original
 * @property {{metrics: Metrics}} rewritten
 */

/**
 * @typedef {Object} PlanComparison
 * @property {number} cost_improvement_pct
 * @property {number} io_improvement_pct
 * @property {number} cpu_improvement_pct
 */

/**
 * @typedef {Object} RuleRecommendation
 * @property {string} rule
 * @property {number} priority
 * @property {string} reason
 * @property {string} expected_benefit
 * @property {ConfidenceLevel} confidence
 * @property {string|null} warning
 */

/**
 * @typedef {Object} RuleRecommendationsResult
 * @property {RuleMethod} method
 * @property {string} overall_analysis
 * @property {RuleRecommendation[]} recommendations
 */

/**
 * @typedef {Object} Candidate
 * @property {string} id
 * @property {string[]} rules_applied
 * @property {string} sql
 * @property {boolean} is_original
 * @property {boolean} changed
 * @property {SemanticCheck} semantic_check
 * @property {{comparison: PlanComparison, original: {metrics: Metrics}, rewritten: {metrics: Metrics}}|null} plan_comparison
 */

/**
 * @typedef {Object} BestCandidate
 * @property {string} best_candidate_id
 * @property {string} best_sql
 * @property {string[]} best_rules
 * @property {boolean} is_original
 * @property {number} improvement_pct
 * @property {boolean} semantic_equivalent
 * @property {number} confidence
 */

/**
 * @typedef {Object} AnalysisResult
 * @property {string} query_id
 * @property {string} timestamp
 * @property {string} original_sql
 * @property {RuleRecommendationsResult} rule_recommendations
 * @property {Candidate[]} candidates
 * @property {BestCandidate|null} recommendation
 */

export const TYPE_CHECK = null;
