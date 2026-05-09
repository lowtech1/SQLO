import os
import json
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Try importing requested providers if available, else mock will be used safely
try:
    import requests
except ImportError:
    pass
    
try:
    import google.generativeai as genai
except ImportError:
    pass

try:
    from groq import Groq
except ImportError:
    pass

# Load environment variables from .env
load_dotenv()

class LLMRuleSelector:
    """
    LLM-based SQL Rule Selector.
    This component does NOT rewrite SQL. It analyzes a SQL query (and optional EXPLAIN plans)
    to select the best sequence of optimization rules from the available registry.
    """

    AVAILABLE_RULES = [
        "predicate_pushdown", 
        "projection_pruning", 
        "subquery_unnesting",
        "ast_predicate_pushdown",
        "ast_projection_pruning", 
        "ast_subquery_unnesting"
    ]

    def __init__(self, provider: str = "mock", model_name: str = None):
        """
        provider: 'openrouter', 'gemini', 'groq', or 'mock'
        """
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = None
        
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
        
        # Fallback to mock if API key is missing and it's not explicitly mock
        if self.provider != "mock" and not self.api_key:
            print(f"Warning: No API key found for {self.provider}. Falling back to 'mock' mode.")
            self.provider = "mock"

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
        Asks the configured LLM to select the best sequence of optimization rules.
        """
        prompt = self._build_prompt(sql, explain_plan, stats)
        
        if self.provider == "mock":
            return self._mock_call(sql)
        elif self.provider == "openrouter":
            return self._call_openrouter(prompt)
        elif self.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.provider == "groq":
            return self._call_groq(prompt)
        else:
            return self._mock_call(sql)

    def _parse_response(self, text: str) -> dict:
        try:
            # Strip markdown formatting if any
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
                
            if text.endswith("```"):
                text = text[:-3]
            
            parsed = json.loads(text.strip())
            
            # Ensure format matches expected output
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

    def _mock_call(self, sql: str) -> dict:
        """Mock mode simply guesses rules based on simple string matching heuristics."""
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
            reason.append("No obvious nested patterns detected, applying fallback pushdown attempt.")
            rules.append("ast_predicate_pushdown")
            
        return {
            "recommended_rules": rules,
            "reasoning": " ".join(reason) + " [Mock Mode used (No API Key)]"
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
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except Exception as e:
            return {"recommended_rules": [], "reasoning": f"OpenRouter API error: {e}"}

    def _call_gemini(self, prompt: str) -> dict:
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            return {"recommended_rules": [], "reasoning": f"Gemini API error: {e}"}

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
            return {"recommended_rules": [], "reasoning": f"Groq API error: {e}"}


if __name__ == "__main__":
    # Test Mock Mode (No API Key needed)
    selector = LLMRuleSelector(provider="mock")
    
    print("=== Test 1: Subquery Query ===")
    sql1 = "SELECT a, b FROM (SELECT a, b, c FROM table_name) AS sub WHERE a > 10;"
    print("SQL:", sql1)
    print("Decision:", json.dumps(selector.select_rules(sql1), indent=2))
    
    print("\n=== Test 2: Projection Query ===")
    sql2 = "SELECT * FROM orders WHERE status = 'shipped';"
    print("SQL:", sql2)
    print("Decision:", json.dumps(selector.select_rules(sql2), indent=2))
    
    print("\n=== Test 3: Nested Query ===")
    sql3 = "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders WHERE total > 1000);"
    print("SQL:", sql3)
    print("Decision:", json.dumps(selector.select_rules(sql3), indent=2))
