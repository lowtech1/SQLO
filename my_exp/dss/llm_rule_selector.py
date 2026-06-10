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
    "predicate_pushdown": "Move WHERE conditions from outer query into subquery in FROM clause to reduce intermediate rows.",
    "projection_pruning": "Remove unnecessary columns from SELECT to reduce I/O bandwidth.",
    "join_reordering": "Reorder JOIN sequence by table size to reduce intermediate row explosion.",
    "subquery_unnesting": "Convert IN/EXISTS subquery to JOIN to avoid Nested Loop, improve with Hash Join.",
    "aggregation_pushdown": "Push GROUP BY/aggregate down into subquery to reduce rows before aggregation.",
    "redundant_join_elimination": "Remove JOINs where joined table columns are not used in SELECT/WHERE/GROUP/ORDER.",
    "filter_into_join": "Push WHERE filter into JOIN ON clause so filter runs with JOIN operation.",
    "limit_pushdown": "Push LIMIT/OFFSET down to subquery to avoid sorting all data.",
}


def build_llm_prompt(sql: str, features: dict, applicable_rules: list) -> str:
    """Build LLM prompt for rule recommendation."""
    rule_list = "\n".join([
        f'  - {name}: {RULE_DESCRIPTIONS.get(name, "")}'
        for name in applicable_rules
    ])

    complexity = features.get("complexity", {})

    prompt = f"""You are an expert SQL query optimizer. Analyze the SQL and recommend optimization rules.

## SQL STRUCTURE
{'-' * 50}
SQL: {sql}
{'-' * 50}

## SQL FEATURES
- Complexity: {complexity.get('level', 'N/A')} (score: {complexity.get('score', 0)})
- Tables used: {features.get('table_count', 0)}
- JOINs: {features.get('join_count', 0)}
- Subqueries: {features.get('subquery_count', 0)}
- Has aggregation: {features.get('has_aggregation', False)}
- Has GROUP BY: {features.get('has_group_by', False)}
- Has ORDER BY: {features.get('has_order_by', False)}
- Has LIMIT: {features.get('has_limit', False)}

## AVAILABLE RULES (use EXACT rule IDs from this list)
{rule_list}

## REQUIREMENTS
1. Analyze the SQL structure above.
2. Choose the TOP-3 most applicable rules (or fewer if not many apply).
3. For each rule, provide:
   - **rule**: EXACT rule ID from the list above (e.g., "projection_pruning", "join_reordering"). Do NOT use Vietnamese or generic names.
   - **priority**: 1 (highest), 2, or 3
   - **reason**: Why this rule applies to this specific SQL (1-2 sentences)
   - **expected_benefit**: Specific benefit with approximate % reduction if possible
   - **confidence**: High / Medium / Low
   - **before_snippet**: The exact SQL fragment that WILL BE CHANGED (use empty string if rule doesn't produce a visible fragment)
   - **after_snippet**: The exact SQL fragment AFTER the rewrite is applied (use empty string if no visible change)
   - **warning**: If semantic equivalence may be affected, note it here
4. Output in English only.

## OUTPUT FORMAT (JSON)
{{
  "recommendations": [
    {{
      "rule": "projection_pruning",
      "priority": 1,
      "reason": "SELECT * retrieves all 8 columns from customer but only 2 are used in the output.",
      "expected_benefit": "I/O reduction: ~75% fewer columns scanned (8 → 2).",
      "confidence": "High",
      "before_snippet": "SELECT *",
      "after_snippet": "SELECT c_custkey, c_name",
      "warning": null
    }}
  ],
  "overall_analysis": "This query joins 2 tables with a filter condition. Two optimizations are recommended..."
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
    Uses Groq (Llama 3.3 70B) to analyze SQL and recommend optimization rules.
    Falls back to pattern-based selection if LLM is unavailable.
    """

    def __init__(self, use_llm: bool = True, model: str = "llama-3.3-70b-versatile"):
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
        features = self.extractor.extract(sql)
        scores, _, _ = self.scorer.score(sql)
        applicable_rules = [
            rule for rule, result in scores.items()
            if result["applicable"]
        ]

        if not self.use_llm:
            return self._pattern_selection(sql, features, applicable_rules, scores)

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
            return self._pattern_selection(sql, features, applicable_rules, scores)

    def _pattern_selection(self, sql: str, features: dict, applicable_rules: list, scores: dict = None) -> dict:
        """Fallback pattern-based rule selection."""
        if scores is None:
            scores, _, _ = self.scorer.score(sql)
        recommendations = []
        priority = 1

        confidence_map = {"high": "High", "medium": "Medium", "low": "Low"}

        for rule_name in applicable_rules:
            result = scores.get(rule_name, {})
            recommendations.append({
                "rule": rule_name,
                "priority": priority,
                "reason": result.get("reason", f"Pattern detected: applicable rule {rule_name}"),
                "expected_benefit": result.get("benefit", f"Applies {rule_name} to reduce execution cost"),
                "confidence": confidence_map.get(result.get("confidence", "medium"), "Medium"),
                "warning": None,
            })
            priority += 1

        return {
            "method": "pattern",
            "recommendations": recommendations,
            "overall_analysis": f"Found {len(applicable_rules)} optimization opportunities. Complexity: {features.get('complexity', {}).get('level', 'N/A')}.",
            "features": features,
            "applicable_rules": applicable_rules,
            "raw_llm_response": None,
        }
