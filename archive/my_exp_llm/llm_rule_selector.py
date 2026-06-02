"""
LLM-based SQL Rule Selector + Pattern-Based Fallback.

Module nay co hai che do hoat dong:
  1. LLM Mode: Su dung OpenRouter/Gemini/Groq de phan tich SQL va goi y rule
  2. Pattern Mode: Su dung pattern matching (khong can LLM) khi khong co API key

Cach su dung:
  from my_exp.llm.llm_rule_selector import LLMRuleSelector

  # Su dung pattern-based (khong can API key)
  selector = LLMRuleSelector(provider="pattern")
  result = selector.select_rules(sql)

  # Su dung LLM (can API key)
  selector = LLMRuleSelector(provider="openrouter", model_name="anthropic/claude-3-haiku")
  result = selector.select_rules(sql)
"""

import os
import json
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import requests
except ImportError:
    pass

try:
    import google.generativeai as genai
except ImportError:
    pass

try:
    # pyrefly: ignore [missing-import]
    from groq import Groq
except ImportError:
    pass

load_dotenv()


class LLMRuleSelector:
    """
    LLM-based SQL Rule Selector (co fallback sang pattern-based).

    Muc dich: Phan tich SQL query de goi y cac rule viets lai tot nhat.
    Hoat dong trong 2 che do:
      - LLM: Su dung OpenRouter/Gemini/Groq API
      - Pattern: Pattern matching (khong can API) - FALLBACK

    Lenh di:
      1. Phan tich cau truc SQL (pattern)
      2. Neu co API key + provider != "pattern": goi LLM
      3. Neu khong co API key: tu dong fallback sang pattern-based
    """

    AVAILABLE_RULES = [
        "predicate_pushdown",
        "projection_pruning",
        "subquery_unnesting",
        "ast_predicate_pushdown",
        "ast_projection_pruning",
        "ast_subquery_unnesting",
        "ast_join_reordering",
        "ast_aggregation_pushdown",
        "ast_redundant_join_elimination",
        "ast_filter_into_join",
        "ast_limit_pushdown"
    ]

    def __init__(self, provider: str = "pattern", model_name: str = None):
        """
        Args:
            provider: 'openrouter', 'gemini', 'groq', hoac 'pattern'
            model_name: Ten model LLM (neu dung provider LLM)
        """
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = None
        self._pattern_selector = None

        if self.provider == "openrouter":
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            if not self.model_name:
                self.model_name = "anthropic/claude-3-haiku"
        elif self.provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY")
            if self.api_key:
                genai.configure(api_key=self.api_key)
            if not self.model_name:
                self.model_name = "gemini-1.5-flash"
        elif self.provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.model_name:
                self.model_name = "llama3-70b-8192"

        # Fallback: neu provider LLM nhung khong co API key -> pattern
        if self.provider != "pattern" and not self.api_key:
            print(f"Warning: No API key for {self.provider}. Falling back to 'pattern' mode.")
            self.provider = "pattern"

    def _get_pattern_selector(self):
        """Lazy-load pattern selector."""
        if self._pattern_selector is None:
            from my_exp.llm.pattern_rule_selector import PatternRuleSelector
            self._pattern_selector = PatternRuleSelector()
        return self._pattern_selector

    def _build_prompt(self, sql: str, explain_plan: str = None, stats: str = None) -> str:
        prompt = f"""You are an expert PostgreSQL Database Administrator and Query Optimizer.
Your task is to analyze the following SQL query and recommend a sequence of optimization rules to apply.

CRITICAL CONSTRAINTS:
1. YOU MUST NOT REWRITE THE SQL YOURSELF.
2. YOU MUST ONLY RETURN A JSON OBJECT WITH TWO KEYS: "recommended_rules" AND "reasoning".
3. "recommended_rules" must be a list of strings, chosen ONLY from this available list:
   {json.dumps(self.AVAILABLE_RULES)}
4. Focus strictly on rule selection based on the structure of the query.

OPTIMIZATION PRIORITIES:
- Prioritize semantic safety (do not change query results).
- Avoid creating duplicate rows (e.g. naive unnesting of IN).
- Prioritize reducing 'Seq Scan' operations.
- Prioritize enabling 'Index Scan' operations.
- Prioritize 'Hash Join' over 'Nested Loop' if the query suggests large data processing.

SQL QUERY:
{sql}
"""
        if explain_plan:
            prompt += f"\nEXPLAIN PLAN:\n{explain_plan}\n"
        if stats:
            prompt += f"\nOPTIMIZER STATS:\n{stats}\n"

        prompt += """
EXPECTED OUTPUT FORMAT (Valid JSON only, no markdown blocks if possible):
{
    "recommended_rules": ["rule_1", "rule_2"],
    "reasoning": "Explanation of why these rules were chosen based on the priorities..."
}
"""
        return prompt

    def select_rules(self, sql: str, explain_plan: str = None, stats: str = None) -> dict:
        """
        Phan tich SQL va tra ve cac rule duoc goi y.
        Uu tien: LLM > Pattern-based (khi LLM that bai hoac khong co API).
        """
        if self.provider == "pattern":
            ps = self._get_pattern_selector()
            return ps.select_rules(sql, explain_plan, stats)
        elif self.provider == "openrouter":
            return self._call_openrouter(self._build_prompt(sql, explain_plan, stats))
        elif self.provider == "gemini":
            return self._call_gemini(self._build_prompt(sql, explain_plan, stats))
        elif self.provider == "groq":
            return self._call_groq(self._build_prompt(sql, explain_plan, stats))
        else:
            # Fallback ve pattern
            return self._get_pattern_selector().select_rules(sql, explain_plan, stats)

    def _parse_response(self, text: str) -> dict:
        try:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]

            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())

            if "recommended_rules" not in parsed:
                parsed["recommended_rules"] = []
            if "reasoning" not in parsed:
                parsed["reasoning"] = "No reasoning provided."

            return parsed
        except Exception as e:
            return {
                "recommended_rules": [],
                "reasoning": f"Failed to parse LLM response: {e}\nRaw Output: {text}"
            }

    def _call_openrouter(self, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=data
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except Exception as e:
            # Fallback to pattern on error
            return self._get_pattern_selector().select_rules(
                "", None, None
            )

    def _call_gemini(self, prompt: str) -> dict:
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            return self._get_pattern_selector().select_rules("", None, None)

    def _call_groq(self, prompt: str) -> dict:
        try:
            client = Groq(api_key=self.api_key)
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            return self._parse_response(completion.choices[0].message.content)
        except Exception as e:
            return self._get_pattern_selector().select_rules("", None, None)


def compare_pattern_vs_mock():
    """
    So sanh pattern-based selector voi mock selector cu.
    Chay tren cac test query de xem su khac biet.
    """
    from my_exp.llm.pattern_rule_selector import PatternRuleSelector

    # Mock selector cu
    def mock_select(sql):
        rules = []
        reason = []
        s = sql.upper()
        if "WHERE" in s and "SELECT" in s[s.find("FROM"):]:
            rules.append("predicate_pushdown")
            reason.append("Subquery detected with outer WHERE, pushing down predicates is recommended.")
        if "IN (SELECT" in s:
            rules.append("subquery_unnesting")
            reason.append("IN (SELECT ...) pattern detected, unnesting into a JOIN can enable Hash Joins.")
        if "SELECT *" in s:
            rules.append("projection_pruning")
            reason.append("SELECT * detected, pruning unnecessary columns is recommended to reduce I/O.")
        if not rules:
            rules.append("ast_predicate_pushdown")
        return {"recommended_rules": rules, "reasoning": " ".join(reason)}

    pattern = PatternRuleSelector()
    test_queries = [
        ("Predicate Pushdown",
         "SELECT sub.c_name FROM (SELECT c_custkey, c_name FROM customer) AS sub WHERE sub.c_mktsegment = 'BUILDING';"),
        ("Subquery Unnesting",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
        ("Projection Pruning",
         "SELECT c_name, c_phone FROM (SELECT * FROM customer WHERE c_mktsegment='AUTOMOBILE') AS sub;"),
        ("Filter Into Join",
         "SELECT * FROM orders o JOIN customer c ON o.o_custkey = c.c_custkey WHERE c.c_mktsegment = 'HOUSEHOLD';"),
        ("Aggregation",
         "SELECT SUM(o_totalprice) FROM (SELECT o_custkey, o_totalprice FROM orders) AS sub GROUP BY o_custkey;"),
        ("Multi-rule",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 50000) AND c_mktsegment='AUTOMOBILE';"),
    ]

    print(f"{'Query':<30} | {'Mock':<35} | {'Pattern'}")
    print("-" * 120)
    for name, sql in test_queries:
        mock_res = mock_select(sql)
        pattern_res = pattern.select_rules(sql)

        mock_rules = ", ".join(mock_res["recommended_rules"][:2])
        pat_rules = ", ".join(pattern_res["recommended_rules"][:2])
        print(f"{name:<30} | {mock_rules:<35} | {pat_rules}")


if __name__ == "__main__":
    print("=== Test Pattern-Based Selector ===")
    selector = LLMRuleSelector(provider="pattern")

    test_cases = [
        "SELECT sub.c_name FROM (SELECT c_custkey, c_name FROM customer) AS sub WHERE sub.c_mktsegment = 'BUILDING';",
        "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);",
        "SELECT c_name FROM (SELECT * FROM customer) AS sub WHERE c_mktsegment='AUTOMOBILE';",
        "SELECT * FROM orders o JOIN customer c ON o.o_custkey = c.c_custkey WHERE c.c_mktsegment = 'HOUSEHOLD';",
    ]

    for sql in test_cases:
        result = selector.select_rules(sql)
        print(f"\nSQL: {sql[:70]}...")
        print(f"  Recommended: {result['recommended_rules']}")
        print(f"  Scores: {result['rule_scores']}")
        print(f"  Reasoning: {result['reasoning']}")

    print("\n\n=== Pattern vs Mock Comparison ===")
    compare_pattern_vs_mock()
