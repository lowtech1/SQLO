# TPC-H Benchmark Results — LLM-R2 Enhanced

*Generated: 2026-06-10 22:38*

**Configuration**: PostgreSQL TPC-H, Groq llama-3.3-70b-versatile
**Rules applied**: predicate_pushdown, projection_pruning, join_reordering, subquery_unnesting, aggregation_pushdown, filter_into_join, limit_pushdown, redundant_join_elimination

**Summary**: 13/22 queries completed
**Better**: 1 | 
**Worse**: 3 | 
**No candidate**: 9 | 
**Errors**: 9

## Detailed Results

| Q | Status | Orig Cost | Opt Cost | Cost | Type | Rules | Semantic | Index Recs |
|---|--------|-----------|----------|--------|--------|-------|---------|------------|
| Q01 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q02 | [~] | 389.3 | 356.6 | +9.2% | NO_CANDIDATE | — | OK | 4 idx |
| Q03 | TIMEOUT | — | — | — | — | — | — | — |
| Q04 | TIMEOUT | — | — | — | — | — | — | — |
| Q05 | TIMEOUT | — | — | — | — | — | — | — |
| Q06 | [~] | 1611.4 | 2208.3 | -27.0% | NO_CANDIDATE | — | OK | 1 idx |
| Q07 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q08 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q09 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q10 | TIMEOUT | — | — | — | — | — | — | — |
| Q11 | [-] | 514.4 | 460.3 | -12.6% | WORSE | aggregation_pushdown | OK | 2 idx |
| Q12 | TIMEOUT | — | — | — | — | — | — | — |
| Q13 | [-] | 1778.9 | 2989.6 | -55.0% | WORSE | aggregation_pushdown | OK | 2 idx |
| Q14 | [~] | 1349.5 | 1450.0 | -6.9% | NO_CANDIDATE | — | OK | 2 idx |
| Q15 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q16 | [-] | 1851.3 | 2582.0 | -33.2% | WORSE | aggregation_pushdown | OK | 1 idx |
| Q17 | TIMEOUT | — | — | — | — | — | — | — |
| Q18 | TIMEOUT | — | — | — | — | — | — | — |
| Q19 | [~] | 1872.1 | 13698.5 | -86.3% | NO_CANDIDATE | — | OK | 2 idx |
| Q20 | TIMEOUT | — | — | — | — | — | — | — |
| Q21 | TIMEOUT | — | — | — | — | — | — | — |
| Q22 | [+] | 591.3 | 515.5 | +16.6% | BETTER | projection_pruning | OK | 2 idx |

## Legend
- **Cost**: PostgreSQL planner estimated cost (from EXPLAIN)
- **Time**: Actual execution time from EXPLAIN ANALYZE
- **Cost Δ%**: (orig_cost - rew_cost) / orig_cost × 100 — positive = improved
- **Time Δ%**: (orig_time - rew_time) / orig_time × 100 — positive = improved
- **Semantic**: ✅ equivalent, ❌ not equivalent
- **Rules**: optimization rules applied by LLM-R2
- **Method**: LLM (Groq llama-3.3-70b-versatile) or pattern fallback