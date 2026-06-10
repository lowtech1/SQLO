# LLM-R2 Ablation Study Report

*Generated: 2026-06-10 22:43*

**Total queries**: 2 | **Successful**: 1 | **Errors**: 1

## Summary Metrics

| Metric | Value |
|--------|-------|
| BETTER (cost ↓) | 1/1 (100.0%) |
| WORSE (cost ↑) | 0/1 (0.0%) |
| NO_CANDIDATE | 0/1 (0.0%) |
| Semantic OK | 0/1 (0.0%) |
| Seq Scan detected | 0/1 (0.0%) |
| Index recommendations | 1 total |
| Avg improvement | +4.2% |

## Per-Query Results

| Q | Complexity | Top Node | Cost | Time | Imp% | Semantic | Index Recs | Conflicts |
|---|------------|----------|------|------|------|----------|------------|-----------|
| Q01 | ERROR: HTTPConnectionPool(host='127.0.0.1', por | | | | | | | |
| Q06 | O(n^2) | Aggregate | 169994 | 1402.8ms | +4.2% | N | 1 | N |

## Complexity Distribution

| Complexity Level | Count |
|-----------------|-------|
| N/A | 1 |
| O(n^2) | 1 |

## EXPLAIN Node Type Distribution

| Node Type | Count |
|-----------|-------|
| N/A | 1 |
| Aggregate | 1 |