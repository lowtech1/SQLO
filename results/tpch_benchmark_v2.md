# TPC-H Benchmark Results — LLM-R2 Enhanced

*Generated: 2026-06-10 19:56*

**Configuration**: PostgreSQL TPC-H, Groq llama-3.3-70b-versatile
**Rules applied**: predicate_pushdown, projection_pruning, join_reordering, subquery_unnesting, aggregation_pushdown, filter_into_join, limit_pushdown, redundant_join_elimination

**Summary**: 18/22 queries completed
**Better**: 3 | 
**Worse**: 6 | 
**No candidate**: 9 | 
**Errors**: 4

## Detailed Results

| Q | Status | Orig Cost | Opt Cost | Cost | Type | Rules | Semantic | Index Recs |
|---|--------|-----------|----------|--------|--------|-------|---------|------------|
| Q01 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q02 | [~] | 517.0 | 527.5 | -2.0% | NO_CANDIDATE | — | OK | 4 idx |
| Q03 | [-] | 1931.2 | 4124.7 | -43.2% | WORSE | limit_pushdown | OK | 3 idx |
| Q04 | [-] | 2540.7 | 4309.6 | -35.8% | WORSE | projection_pruning | OK | 2 idx |
| Q05 | [-] | 1941.4 | 2521.7 | -13.7% | WORSE | aggregation_pushdown | OK | 4 idx |
| Q06 | [~] | 1295.3 | 1329.2 | -2.5% | NO_CANDIDATE | — | OK | 1 idx |
| Q07 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q08 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q09 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q10 | [-] | 1981.2 | 2606.3 | -23.9% | WORSE | limit_pushdown | OK | 3 idx |
| Q11 | [+] | 481.3 | 433.7 | +31.7% | BETTER | aggregation_pushdown | OK | 2 idx |
| Q12 | [-] | 2027.0 | 2856.3 | -27.2% | WORSE | aggregation_pushdown | OK | 2 idx |
| Q13 | [-] | 1416.7 | 1672.5 | -16.1% | WORSE | aggregation_pushdown | OK | 2 idx |
| Q14 | [~] | 1226.7 | 1359.7 | -9.8% | NO_CANDIDATE | — | OK | 2 idx |
| Q15 | [~] | — | — | — | NO_CANDIDATE | — | ERR | — |
| Q16 | [+] | 1546.7 | 1342.4 | +6.1% | BETTER | aggregation_pushdown | OK | 1 idx |
| Q17 | TIMEOUT | — | — | — | — | — | — | — |
| Q18 | TIMEOUT | — | — | — | — | — | — | — |
| Q19 | [~] | 1665.1 | 2006.7 | -17.0% | NO_CANDIDATE | — | OK | 2 idx |
| Q20 | TIMEOUT | — | — | — | — | — | — | — |
| Q21 | TIMEOUT | — | — | — | — | — | — | — |
| Q22 | [+] | 922.0 | 869.7 | +1.4% | BETTER | projection_pruning | OK | 2 idx |

## Legend
- **Cost**: PostgreSQL planner estimated cost (from EXPLAIN)
- **Time**: Actual execution time from EXPLAIN ANALYZE
- **Cost Δ%**: (orig_cost - rew_cost) / orig_cost × 100 — positive = improved
- **Time Δ%**: (orig_time - rew_time) / orig_time × 100 — positive = improved
- **Semantic**: ✅ equivalent, ❌ not equivalent
- **Rules**: optimization rules applied by LLM-R2
- **Method**: LLM (Groq llama-3.3-70b-versatile) or pattern fallback