import google.generativeai as genai
import json
import re
from typing import Optional, Dict, Any, List
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

COMPLEX_QUERY_KEYWORDS = [
    "update", "delete", "insert", "join", "subquery",
    "having", "union", "with", "group by", "nested",
    "create", "drop", "alter", "truncate",
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

SYSTEM_PROMPT = """You are an expert SQL assistant. Generate SQL from natural language.

Respond with ONLY a valid JSON object. No markdown, no backticks, no explanation outside JSON.

JSON structure (all fields required):
{
  "sql": "SELECT id, name FROM students WHERE cgpa > 8.5;",
  "explanation": "Fetches students with CGPA above 8.5",
  "confidence_score": 0.92,
  "optimization_score": 0.85,
  "risk_level": "low",
  "risk_score": 0.05,
  "risk_reasons": [],
  "query_type": "SELECT",
  "estimated_rows": 25,
  "estimated_time_ms": 12.0,
  "alternatives": [],
  "optimization_tips": ["Add index on cgpa column"],
  "learning_tips": ["WHERE clause filters rows before returning results"],
  "clauses_explained": {"SELECT": "Chooses columns", "WHERE": "Filters by cgpa"},
  "warnings": []
}

Critical rules:
- sql must ALWAYS be a non-empty valid SQL string
- alternatives must be a JSON array (can be empty [])
- query_type: SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER
- risk_level: low, medium, high, critical
- Never invent table or column names not in the schema
- For DDL (CREATE TABLE, ALTER TABLE, DROP TABLE): set query_type accordingly"""


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
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        raise


def normalize_result(result: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    final = DEFAULT_RESPONSE.copy()
    final.update(result)
    final["confidence_score"] = float(final.get("confidence_score") or 0)
    final["optimization_score"] = float(final.get("optimization_score") or 0)
    final["risk_score"] = float(final.get("risk_score") or 0)
    final["_model_used"] = model_name
    # Ensure alternatives is always a list
    if not isinstance(final.get("alternatives"), list):
        final["alternatives"] = []
    return final


def get_relevant_schema_context(natural_language: str, schema: Dict[str, Any]) -> str:
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
    relevant_tables = [t for _, t in scored_tables[:6]] if scored_tables else tables[:5]

    summary_parts = []
    for table in relevant_tables:
        columns = table.get("columns", [])[:25]
        col_text = ", ".join(
            f"{c.get('name')} ({c.get('type')}"
            f"{' PK' if c.get('primary_key') else ''}"
            f"{' FK' if c.get('foreign_key') else ''})"
            for c in columns
        )
        summary_parts.append(f"Table: {table.get('name')}\nColumns: {col_text}")
    return "\n\n".join(summary_parts)


def fallback_sql(natural_language: str, schema_context: str) -> str:
    nl = natural_language.lower()
    if "student" in nl:
        if "cgpa" in nl:
            number = re.search(r"\d+(\.\d+)?", nl)
            cgpa = number.group(0) if number else "8.5"
            return f"SELECT * FROM students WHERE cgpa > {cgpa};"
        return "SELECT * FROM students LIMIT 50;"
    if "employee" in nl or "staff" in nl:
        return "SELECT * FROM employees LIMIT 50;"
    if "product" in nl:
        return "SELECT * FROM products LIMIT 50;"
    if "order" in nl:
        return "SELECT * FROM orders LIMIT 50;"
    if "customer" in nl:
        return "SELECT * FROM customers LIMIT 50;"
    table_match = re.search(r"Table:\s*(\w+)", schema_context)
    if table_match:
        return f"SELECT * FROM {table_match.group(1)} LIMIT 50;"
    return "SELECT 1;"


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
            "explanation": "Query blocked: possible prompt injection detected.",
            "risk_level": "critical",
            "risk_score": 1.0,
            "risk_reasons": ["Prompt injection pattern detected"],
            "query_type": "BLOCKED",
            "warnings": ["Request blocked for security reasons."],
        })
        return blocked

    model_name = select_model(natural_language)

    history_context = ""
    if conversation_history:
        short_history = conversation_history[-3:]
        history_context = "\nConversation Context:\n"
        for msg in short_history:
            history_context += f"Previous: {msg.get('user', '')}\nSQL: {msg.get('sql', '')}\n"

    lang_instruction = ""
    if language == "hi":
        lang_instruction = "User may write in Hindi. Understand the request and generate SQL. Explain in English.\n"

    prompt = f"""{SYSTEM_PROMPT}

{lang_instruction}
Mode: {mode}

Database Schema:
{schema_context}
{history_context}

User Request: {natural_language}

Return ONLY the JSON object. sql field must not be empty."""

    try:
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
            },
        )

        response = model.generate_content(prompt)
        text = response.text.strip()
        print(f"[GEMINI RAW] model={model_name} len={len(text)} preview={text[:150]}")

        result = safe_json_parse(text)
        normalized = normalize_result(result, model_name)

        if not normalized.get("sql", "").strip():
            print("[GEMINI] Empty SQL returned — using fallback")
            normalized["sql"] = fallback_sql(natural_language, schema_context)
            normalized["warnings"] = normalized.get("warnings", []) + ["AI returned empty SQL; fallback used"]
            normalized["confidence_score"] = 0.45

        return normalized

    except json.JSONDecodeError as e:
        print(f"[JSON ERROR] {e} — raw: {text[:300] if 'text' in dir() else 'no text'}")
        sql = fallback_sql(natural_language, schema_context)
        failed = DEFAULT_RESPONSE.copy()
        failed.update({
            "sql": sql,
            "explanation": "AI returned invalid format. Fallback SQL generated.",
            "confidence_score": 0.45,
            "optimization_score": 0.5,
            "query_type": "SELECT",
            "warnings": ["AI JSON parsing failed. Fallback SQL used."],
        })
        return failed

    except Exception as e:
        print(f"[GEMINI ERROR] {type(e).__name__}: {str(e)}")
        sql = fallback_sql(natural_language, schema_context)
        failed = DEFAULT_RESPONSE.copy()
        failed.update({
            "sql": sql,
            "explanation": f"AI service error. Fallback SQL generated.",
            "confidence_score": 0.45,
            "optimization_score": 0.5,
            "query_type": "SELECT",
            "warnings": [f"AI service failed: {str(e)[:100]}. Fallback SQL used."],
        })
        return failed


async def generate_schema_summary(schema: Dict[str, Any]) -> str:
    tables = schema.get("tables", [])[:8]
    summary_parts = []
    for table in tables:
        cols = ", ".join(
            f"{c['name']} ({c['type']}{'  PK' if c.get('primary_key') else ''}{'  FK' if c.get('foreign_key') else ''})"
            for c in table.get("columns", [])[:10]
        )
        summary_parts.append(f"Table: {table['name']}\nColumns: {cols}")
    return "\n\n".join(summary_parts)