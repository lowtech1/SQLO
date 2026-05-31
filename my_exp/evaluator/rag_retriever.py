"""
RAG Retriever: Tìm queries tương tự từ rewrite pools để inject vào LLM prompt.
Giúp LLM học từ kinh nghiệm thực tế (positive/negative rewrite examples).
"""

import csv
import os
import re

# Path to rewrite pools (from repo root /data/data_llmr2/pools/)
_POOL_DIR = os.path.join(os.path.dirname(__file__), '../../data/data_llmr2/pools')

# Cache
_pools_cache = None


def load_pools():
    """Load all rewrite pool examples. Kết quả được cache để tái sử dụng."""
    global _pools_cache
    if _pools_cache is not None:
        return _pools_cache

    pools = []
    for dataset in ['tpch', 'dsb', 'job_syn']:
        for kind in ['pos', 'neg']:
            # Try cleaned version first, then raw
            for fname in [
                f'{kind}_pool_{dataset}_cleaned.csv',
                f'{kind}_pool_{dataset}_updated.csv',
            ]:
                path = os.path.join(_POOL_DIR, fname)
                if os.path.exists(path):
                    try:
                        with open(path, encoding='utf-8', errors='ignore') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                query_text = (row.get('original_sql', '') or '').strip()
                                if query_text:
                                    pools.append({
                                        'dataset': dataset,
                                        'kind': kind,
                                        'query': query_text,
                                        'rule': row.get('activated_rules', ''),
                                    })
                    except Exception:
                        pass
                    break  # Only load first found file per dataset/kind
    _pools_cache = pools
    return pools


def _extract_keywords(sql: str) -> set:
    """Trích xuất keywords có ý nghĩa từ SQL (loại bỏ stopwords)."""
    stopwords = {
        'select', 'from', 'where', 'and', 'or', 'not', 'in', 'exists', 'is', 'null',
        'join', 'left', 'right', 'inner', 'outer', 'on', 'as', 'by', 'group', 'order',
        'having', 'limit', 'offset', 'asc', 'desc', 'distinct', 'all', 'into', 'set',
        'values', 'insert', 'update', 'delete', 'create', 'drop', 'alter', 'table',
        'index', 'view', 'between', 'like', 'case', 'when', 'then', 'else', 'end',
        'union', 'intersect', 'except', 'over', 'partition', 'with', 'count', 'sum',
        'avg', 'min', 'max', 'inner', 'cross', 'full', 'natural', 'using',
        'cast', 'coalesce', 'nullif', 'greatest', 'least', 'generate_series',
    }
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', sql.lower())
    return set(w for w in words if w not in stopwords and len(w) > 2)


def find_similar(sql: str, pools: list, top_k: int = 3) -> list:
    """
    Tìm top-k queries tương tự dựa trên keyword overlap (Jaccard-like).
    Returns: list of dicts with 'dataset', 'kind', 'query', 'rule'
    """
    if not pools:
        return []
    sql_kw = _extract_keywords(sql)
    if not sql_kw:
        return []

    scored = []
    for pool in pools:
        pool_kw = _extract_keywords(pool['query'])
        if not pool_kw:
            continue
        overlap = len(sql_kw & pool_kw)
        union = len(sql_kw | pool_kw)
        if overlap >= 2 and union > 0:
            jaccard = overlap / union
            # Also boost by absolute overlap count
            scored.append((overlap + jaccard * 10, pool))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_k]]


def build_rag_context(sql: str, pools: list = None, top_k: int = 3) -> str:
    """
    Build context string từ similar queries trong pools.
    Inject vào LLM prompt để cung cấp thêm thông tin.
    """
    if pools is None:
        pools = load_pools()
    similar = find_similar(sql, pools, top_k)
    if not similar:
        return ""

    lines = [
        "\n\nTHỰC TẾ TỪ REWRITE POOLS (tham khảo thêm):",
        "(Dựa trên các rewrite đã thử nghiệm trước đó trên cùng loại queries)"
    ]
    for ex in similar:
        outcome = "CẢI THIỆN" if ex['kind'] == 'pos' else "KÉM HƠN"
        lines.append(f"  • Rule `{ex['rule']}` → {outcome} (trên {ex['dataset']})")
    return "\n".join(lines)
