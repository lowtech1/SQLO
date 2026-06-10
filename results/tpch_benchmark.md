# TPC-H Benchmark Results — LLM-R2 Enhanced

*Generated: 2026-06-10 18:49*

**Configuration**: PostgreSQL TPC-H, Groq llama-3.3-70b-versatile
**Rules applied**: predicate_pushdown, projection_pruning, join_reordering, subquery_unnesting, aggregation_pushdown, filter_into_join, limit_pushdown, redundant_join_elimination

**Summary**: 18/22 queries completed
**Better**: 1 | 
**Worse**: 8 | 
**No candidate**: 9 | 
**Errors**: 4

## Detailed Results

| Q | Status | Orig Cost | Opt Cost | Cost Δ% | Orig Time | Opt Time | Time Δ% | Type | Rules | Semantic |
|---|--------|-----------|----------|---------|-----------|----------|---------|------|-------|---------|
| Q01 | [~] OK | — | — | — | — | — | — | NO_CANDIDATE | — | ❌ |
| Q02 | [~] OK | 308.6 | 382.7 | -19.4% | 309ms | 383ms | -24.0% | NO_CANDIDATE | — | ✅ |
| Q03 | [-] OK | 1643.7 | 1805.4 | -7.7% | 1644ms | 1805ms | -9.8% | WORSE | limit_pushdown | ✅ |
| Q04 | [-] OK | 2626.2 | 3308.5 | -17.6% | 2626ms | 3308ms | -26.0% | WORSE | projection_pruning | ✅ |
| Q05 | [-] OK | 1523.0 | 1695.8 | -0.1% | 1523ms | 1696ms | -11.3% | WORSE | aggregation_pushdown | ✅ |
| Q06 | [~] OK | 982.3 | 1085.3 | -9.5% | 982ms | 1085ms | -10.5% | NO_CANDIDATE | — | ✅ |
| Q07 | [~] OK | — | — | — | — | — | — | NO_CANDIDATE | — | ❌ |
| Q08 | [~] OK | — | — | — | — | — | — | NO_CANDIDATE | — | ❌ |
| Q09 | [~] OK | — | — | — | — | — | — | NO_CANDIDATE | — | ❌ |
| Q10 | [-] OK | 1580.9 | 1799.1 | -7.5% | 1581ms | 1799ms | -13.8% | WORSE | limit_pushdown | ✅ |
| Q11 | [-] OK | 317.8 | 454.5 | -19.0% | 318ms | 454ms | -43.0% | WORSE | aggregation_pushdown | ✅ |
| Q12 | [-] OK | 1522.9 | 1671.6 | -6.2% | 1523ms | 1672ms | -9.8% | WORSE | aggregation_pushdown | ✅ |
| Q13 | [-] OK | 1076.8 | 1193.3 | -0.5% | 1077ms | 1193ms | -10.8% | WORSE | aggregation_pushdown | ✅ |
| Q14 | [~] OK | 1031.3 | 1171.2 | -11.9% | 1031ms | 1171ms | -13.6% | NO_CANDIDATE | — | ✅ |
| Q15 | [~] OK | — | — | — | — | — | — | NO_CANDIDATE | — | ❌ |
| Q16 | [-] OK | 1211.8 | 1257.9 | -0.5% | 1212ms | 1258ms | -3.8% | WORSE | aggregation_pushdown | ✅ |
| Q17 | TIMEOUT | — | — | — | — | — | — | — | — | — |
| Q18 | TIMEOUT | — | — | — | — | — | — | — | — | — |
| Q19 | [~] OK | 1590.4 | 1798.3 | -11.6% | 1590ms | 1798ms | -13.1% | NO_CANDIDATE | — | ✅ |
| Q20 | TIMEOUT | — | — | — | — | — | — | — | — | — |
| Q21 | TIMEOUT | — | — | — | — | — | — | — | — | — |
| Q22 | [+] OK | 588.5 | 707.9 | +26.7% | 588ms | 708ms | -20.3% | BETTER | projection_pruning | ✅ |

## Legend
- **Cost**: PostgreSQL planner estimated cost (from EXPLAIN)
- **Time**: Actual execution time from EXPLAIN ANALYZE
- **Cost Δ%**: (orig_cost - rew_cost) / orig_cost × 100 — positive = improved
- **Time Δ%**: (orig_time - rew_time) / orig_time × 100 — positive = improved
- **Semantic**: ✅ equivalent, ❌ not equivalent
- **Rules**: optimization rules applied by LLM-R2
- **Method**: LLM (Groq llama-3.3-70b-versatile) or pattern fallback