"""
my_exp.dss.llm_rule_selector
=============================
LLM-powered rule recommendation for SQL optimization.
Priority: Groq API → Anthropic API → Pattern scoring fallback.
"""

import os
import json
import sys
import requests
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(_root_env)

from my_exp.core.rules import get_all_rules
from my_exp.core.sql_analyzer import SQLFeatureExtractor, RuleApplicabilityScorer


RULE_DESCRIPTIONS = {
    "predicate_pushdown": "Day dieu kien WHERE tu query ngoai vao subquery trong FROM clause de giam so dong trung gian.",
    "projection_pruning": "Loai bo cot khong can thiet khoi SELECT de giam I/O bandwidth.",
    "join_reordering": "Sap xep lai thu tu JOIN theo kich thuoc bang de giam intermediate row explosion.",
    "subquery_unnesting": "Chuyen IN/EXISTS subquery thanh JOIN de tranh Nested Loop, tang toc do bang Hash Join.",
    "aggregation_pushdown": "Day GROUP BY/aggregate xuong subquery de giam so dong truoc khi aggregate.",
    "redundant_join_elimination": "Loai bo JOIN ma bang duoc JOIN khong duoc su dung trong SELECT/WHERE/GROUP/ORDER.",
    "filter_into_join": "Day WHERE filter vao JOIN ON clause de filter chay cung voi JOIN operation.",
    "limit_pushdown": "Day LIMIT/OFFSET xuong subquery de tranh sort toan bo du lieu.",
}


def build_llm_prompt(sql: str, features: dict, applicable_rules: list) -> str:
    """Build LLM prompt for rule recommendation."""
    rule_list = "\n".join([
        f'  - {name}: {RULE_DESCRIPTIONS.get(name, "")}'
        for name in applicable_rules
    ])

    complexity = features.get("complexity", {})
    structural = features.get("structural", {})

    prompt = f"""Ban la mot chuyen gia toi uu hoa truy van SQL. Nhiem vu: phan tich cau truc SQL va goi y cac quy tac toi uu hoa phu hop.

## CAU TRUC SQL
{'-' * 50}
SQL: {sql}
{'-' * 50}

## FEATURES
- Do phuc tap: {complexity.get('level', 'N/A')} (score: {complexity.get('score', 0)})
- So bang: {features.get('table_count', 0)}
- So JOIN: {features.get('join_count', 0)}
- So subquery: {features.get('subquery_count', 0)}
- Co aggregation: {features.get('has_aggregation', False)}
- Co GROUP BY: {features.get('has_group_by', False)}
- Co ORDER BY: {features.get('has_order_by', False)}
- Co LIMIT: {features.get('has_limit', False)}

## CAC QUY TAC CO SAN
{rule_list}

## YEU CAU
1. Phan tich cau truc SQL tren
2. Chon TOP-3 quy tac phu hop nhat (hoac it hon neu khong co nhieu)
3. Moi quy tac can co:
   - Ly do chon: Giai thich TAI SAO quy tac nay duoc chon
   - Loi ich mong doi: Hau qua cua viec ap dung quy tac
   - Muc do tu van: Cao / Trung binh / Thap
   - Thu tu uu tien: 1 (cao nhat), 2, 3
4. Giai thich bang TIENG VIET, ngac nhien va de hieu

## OUTPUT FORMAT (JSON)
{{
  "recommendations": [
    {{
      "rule": "ten_quy_tac",
      "priority": 1,
      "reason": "Ly do chon quy tac nay",
      "expected_benefit": "Loi ich cu the",
      "confidence": "Cao/Trung binh/Thap",
      "warning": "Canh bao neu co (VD: semantic thay doi, co risk)"
    }}
  ],
  "overall_analysis": "Tong quan 1-2 cau ve cau truc SQL nay"
}}
"""
    return prompt


def call_llm(prompt: str) -> Optional[str]:
    """Call LLM API — Groq first, then Anthropic, then None (pattern fallback)."""
    # ── Priority 1: Groq API ───────────────────────────────────────────────
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"[Groq] API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[Groq] Request failed: {e}")

    # ── Priority 2: Gemini via requests ──────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.1},
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"[Gemini] API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[Gemini] Request failed: {e}")

    # ── Priority 4: No LLM available — use pattern scoring only ───────────
    print("[LLM] No LLM API key available — using pattern-based scoring")
    return None


def parse_llm_response(response: str) -> dict:
    """Parse LLM JSON response."""
    if not response:
        return {}

    # Try to extract JSON from markdown code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON object
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        return {"error": "Could not parse LLM response", "raw": response[:500]}


class LLMRuleSelector:
    """
    LLM-powered rule selector.
    Uses Claude Opus 4.6 to analyze SQL and recommend optimization rules.
    Falls back to pattern-based selection if LLM is unavailable.
    """

    def __init__(self, use_llm: bool = True, model: str = "llama-3.3-70b-versatile"):
        # LLM available if any API key is set (Groq, Gemini, or Anthropic)
        has_llm_key = bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        self.use_llm = use_llm and has_llm_key
        self.model = model
        self.extractor = SQLFeatureExtractor()
        self.scorer = RuleApplicabilityScorer()
        self.pattern_rules = get_all_rules()

    def select_rules(self, sql: str) -> dict:
        """
        Select optimization rules for a SQL query.

        Returns:
            dict with keys:
              - method: "llm" or "pattern"
              - recommendations: list of rule recommendations
              - features: SQL features
              - raw_llm_response: (if LLM was used)
        """
        # Extract features
        features = self.extractor.extract(sql)
        scores, _, _ = self.scorer.score(sql)
        applicable_rules = [
            rule for rule, result in scores.items()
            if result["applicable"]
        ]

        # Fallback: pattern-based
        if not self.use_llm:
            return self._pattern_selection(sql, features, applicable_rules, scores)

        # Try LLM
        prompt = build_llm_prompt(sql, features, applicable_rules)
        response = call_llm(prompt)
        parsed = parse_llm_response(response)

        if parsed and "error" not in parsed and "recommendations" in parsed:
            return {
                "method": "llm",
                "recommendations": parsed.get("recommendations", []),
                "overall_analysis": parsed.get("overall_analysis", ""),
                "features": features,
                "applicable_rules": applicable_rules,
                "raw_llm_response": response,
            }
        else:
            # Fall back to pattern-based
            return self._pattern_selection(sql, features, applicable_rules, scores)

    def _pattern_selection(self, sql: str, features: dict, applicable_rules: list, scores: dict = None) -> dict:
        """Fallback pattern-based rule selection."""
        if scores is None:
            scores, _, _ = self.scorer.score(sql)
        recommendations = []
        priority = 1

        confidence_map = {"high": "Cao", "medium": "Trung binh", "low": "Thap"}

        for rule_name in applicable_rules:
            result = scores.get(rule_name, {})
            confidence = confidence_map.get(result.get("confidence", "medium"), "Trung binh")
            recommendations.append({
                "rule": rule_name,
                "priority": priority,
                "reason": result.get("reason", "Phat hien co hoi toi uu"),
                "expected_benefit": result.get("benefit", "Giam chi phi thuc thi"),
                "confidence": confidence,
                "warning": None,
            })
            priority += 1

        return {
            "method": "pattern",
            "recommendations": recommendations,
            "overall_analysis": f"Phat hien {len(applicable_rules)} co hoi toi uu. Do phuc tap: {features.get('complexity', {}).get('level', 'N/A')}.",
            "features": features,
            "applicable_rules": applicable_rules,
            "raw_llm_response": None,
        }
