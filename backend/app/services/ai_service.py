import google.generativeai as genai
import json
import re
from typing import Optional, Dict, Any, List
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

COMPLEX_QUERY_KEYWORDS = [
    "update", "delete", "insert", "join", "subquery",
    "having", "union", "with", "group by", "nested"
]

INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above)\s+instructions",
    r"forget\s+your\s+instructions",
    r"system\s*:",
    r"developer\s*:",
    r"<\s*script",
    r"drop\s+all\s+tables",
    r";\s*(drop|truncate|alter|delete\s+from)\s+",
]

DEFAULT_RESPONSE = {
    "sql": "",
    "explanation": "",
    "confidence_score": 0.0,
    "optimization_score": 0.0,
    "risk_level": "low",
    "risk_score": 0.0,
    "risk_reasons": [],
    "query_type": "UNKNOWN",
    "estimated_rows": None,
    "estimated_time_ms": None,
    "alternatives": [],
    "optimization_tips": [],
    "learning_tips": [],
    "clauses_explained": {},
    "warnings": [],
}


SYSTEM_PROMPT = """
You are an expert SQL assistant for a secure AI Database Copilot.

Your job:
1. Convert natural language into optimized SQL.
2. Use only tables and columns available in the provided schema.
3. Avoid SELECT * unless absolutely necessary.
4. Prefer safe SELECT queries.
5. Warn about UPDATE, DELETE, INSERT, ALTER, DROP, TRUNCATE.
6. Never generate DROP or TRUNCATE.
7. Never generate UPDATE or DELETE without WHERE.
8. Return valid JSON only. No markdown. No explanation outside JSON.

Return exactly this JSON format:
{
  "sql": "SQL query here",
  "explanation": "simple explanation for non-technical users",
  "confidence_score": 0.0,
  "optimization_score": 0.0,
  "risk_level": "low|medium|high|critical",
  "risk_score": 0.0,
  "risk_reasons": ["reason"],
  "query_type": "SELECT|INSERT|UPDATE|DELETE|BLOCKED|UNKNOWN",
  "estimated_rows": 0,
  "estimated_time_ms": 0,
  "alternatives": [
    {
      "sql": "alternative SQL",
      "explanation": "why this alternative is useful",
      "rank": 1,
      "reason": "reason"
    }
  ],
  "optimization_tips": ["tip"],
  "learning_tips": ["tip"],
  "clauses_explained": {
    "SELECT": "meaning",
    "FROM": "meaning",
    "WHERE": "meaning"
  },
  "warnings": ["warning"]
}
"""


def detect_prompt_injection(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in INJECTION_PATTERNS)


def select_model(natural_language: str) -> str:
    nl_lower = natural_language.lower()
    needs_pro = any(keyword in nl_lower for keyword in COMPLEX_QUERY_KEYWORDS)
    return settings.GEMINI_PRO_MODEL if needs_pro else settings.GEMINI_FLASH_MODEL


def safe_json_parse(text: str) -> Dict[str, Any]:
    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def normalize_result(result: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    final = DEFAULT_RESPONSE.copy()
    final.update(result)

    final["confidence_score"] = float(final.get("confidence_score") or 0)
    final["optimization_score"] = float(final.get("optimization_score") or 0)
    final["risk_score"] = float(final.get("risk_score") or 0)
    final["_model_used"] = model_name

    return final


def get_relevant_schema_context(natural_language: str, schema: Dict[str, Any]) -> str:
    """
    Token-optimized schema retrieval.
    Sends only relevant tables/columns instead of full schema.
    """
    words = set(re.findall(r"\w+", natural_language.lower()))
    tables = schema.get("tables", [])
    scored_tables = []

    for table in tables:
        table_name = table.get("name", "")
        table_words = set(re.findall(r"\w+", table_name.lower()))
        columns = table.get("columns", [])

        score = 0

        if table_name.lower() in words:
            score += 5

        if table_words & words:
            score += 3

        for col in columns:
            col_name = col.get("name", "")
            col_words = set(re.findall(r"\w+", col_name.lower()))

            if col_name.lower() in words:
                score += 3

            if col_words & words:
                score += 2

        if score > 0:
            scored_tables.append((score, table))

    scored_tables.sort(key=lambda x: x[0], reverse=True)

    if scored_tables:
        relevant_tables = [table for _, table in scored_tables[:6]]
    else:
        relevant_tables = tables[:5]

    summary_parts = []

    for table in relevant_tables:
        columns = table.get("columns", [])[:25]

        col_text = ", ".join(
            f"{c.get('name')} ({c.get('type')}"
            f"{' PK' if c.get('primary_key') else ''}"
            f"{' FK' if c.get('foreign_key') else ''})"
            for c in columns
        )

        summary_parts.append(
            f"Table: {table.get('name')}\nColumns: {col_text}"
        )

    return "\n\n".join(summary_parts)


async def generate_sql(
    natural_language: str,
    schema_context: str,
    conversation_history: Optional[List[Dict]] = None,
    mode: str = "simple",
    language: str = "en",
) -> Dict[str, Any]:

    if detect_prompt_injection(natural_language):
        blocked = DEFAULT_RESPONSE.copy()
        blocked.update({
            "explanation": "Query blocked because a possible prompt injection attempt was detected.",
            "risk_level": "critical",
            "risk_score": 1.0,
            "risk_reasons": ["Prompt injection pattern detected"],
            "query_type": "BLOCKED",
            "warnings": ["This request was blocked for security reasons."],
        })
        return blocked

    model_name = select_model(natural_language)

    history_context = ""
    if conversation_history:
        short_history = conversation_history[-3:]
        history_context = "\nConversation Context:\n"
        for msg in short_history:
            history_context += (
                f"Previous user request: {msg.get('user', '')}\n"
                f"Previous SQL: {msg.get('sql', '')}\n"
            )

    lang_instruction = ""
    if language == "hi":
        lang_instruction = (
            "The user may ask in Hindi. Understand the request, "
            "generate SQL, and explain in simple English."
        )

    prompt = f"""
{SYSTEM_PROMPT}

{lang_instruction}

User Mode:
{mode}

Database Schema Context:
{schema_context}

{history_context}

User Request:
{natural_language}

Important:
- Return JSON only.
- Use only provided schema.
- If request is unclear, generate safest SELECT query or add warning.
- Do not invent table or column names.
"""

    try:
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
            },
        )

        response = model.generate_content(prompt)
        text = response.text.strip()

        result = safe_json_parse(text)
        return normalize_result(result, model_name)

    except json.JSONDecodeError:
        failed = DEFAULT_RESPONSE.copy()
        failed.update({
            "explanation": "AI returned an invalid response format. Please try again.",
            "warnings": ["AI JSON parsing failed."],
        })
        return failed

    except Exception as e:
        failed = DEFAULT_RESPONSE.copy()
        failed.update({
            "explanation": "AI service failed. Please check Gemini API key, model name, or internet connection.",
            "warnings": [str(e)],
        })
        return failed


async def generate_schema_summary(schema: Dict[str, Any]) -> str:
    """
    Backward-compatible full schema summary.
    Use get_relevant_schema_context() for token-efficient generation.
    """
    tables = schema.get("tables", [])
    summary_parts = []

    for table in tables:
        columns = table.get("columns", [])

        cols = ", ".join(
            f"{c.get('name')} ({c.get('type')}"
            f"{' PK' if c.get('primary_key') else ''}"
            f"{' FK' if c.get('foreign_key') else ''})"
            for c in columns
        )

        summary_parts.append(
            f"Table: {table.get('name')}\nColumns: {cols}"
        )

    return "\n\n".join(summary_parts)