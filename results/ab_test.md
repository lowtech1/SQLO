# LLM-R2 Multi-Run A/B Test Report

*Generated: 2026-06-10 20:31*

**Runs per query**: 5 | **Metrics**: p50, p95, p99, mean, stddev

## Per-Query Results

### Q1 aggregate
| Metric | Original | Rewritten | Delta |
|--------|----------|-----------|-------|
| p50    | 33479.2ms | - | - |
| p95    | 33634.3ms | - | — |
| p99    | 33648.0ms | - | — |
| Mean   | 30462.0ms | - | — |
| StdDev | 5376.0ms | - | — |
| Min    | 24255.1ms | - | — |
| Max    | 33651.5ms | - | — |
**Stable**: No | **Runs**: 3 | **Improvement**: -

### Q6 discount
| Metric | Original | Rewritten | Delta |
|--------|----------|-----------|-------|
| p50    | 12046.6ms | - | - |
| p95    | 13198.9ms | - | — |
| p99    | 13301.3ms | - | — |
| Mean   | 10943.6ms | - | — |
| StdDev | 3086.4ms | - | — |
| Min    | 7457.1ms | - | — |
| Max    | 13326.9ms | - | — |
**Stable**: No | **Runs**: 3 | **Improvement**: -

### SELECT JOIN
| Metric | Original | Rewritten | Delta |
|--------|----------|-----------|-------|
| p50    | 34.3ms | - | - |
| p95    | 71.0ms | - | — |
| p99    | 74.3ms | - | — |
| Mean   | 46.2ms | - | — |
| StdDev | 25.2ms | - | — |
| Min    | 29.1ms | - | — |
| Max    | 75.1ms | - | — |
**Stable**: No | **Runs**: 3 | **Improvement**: -

### Subquery
| Metric | Original | Rewritten | Delta |
|--------|----------|-----------|-------|
| p50    | 395.2ms | - | - |
| p95    | 416.6ms | - | — |
| p99    | 418.5ms | - | — |
| Mean   | 397.6ms | - | — |
| StdDev | 20.2ms | - | — |
| Min    | 378.8ms | - | — |
| Max    | 418.9ms | - | — |
**Stable**: Yes | **Runs**: 3 | **Improvement**: -

## Summary

- Queries tested: 4
- Stable results (stddev < 10%): 1/4