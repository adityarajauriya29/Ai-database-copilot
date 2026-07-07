import google.generativeai as genai
import httpx
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from app.core.config import settings

if settings.GEMINI_API_KEY:
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

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "give", "get", "in", "into",
    "is", "list", "me", "of", "on", "or", "show", "table", "tables", "the", "to", "top", "with", "all",
    "find", "fetch", "display", "details", "data", "records", "rows", "where", "whose", "which", "that",
}

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
- Use only the schema provided in this prompt
- For DDL (CREATE TABLE, ALTER TABLE, DROP TABLE): set query_type accordingly"""


def detect_prompt_injection(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in INJECTION_PATTERNS)


def select_gemini_model(natural_language: str) -> str:
    nl_lower = natural_language.lower()
    needs_pro = any(keyword in nl_lower for keyword in COMPLEX_QUERY_KEYWORDS)
    return settings.GEMINI_PRO_MODEL if needs_pro else settings.GEMINI_FLASH_MODEL


def safe_json_parse(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def normalize_result(result: Dict[str, Any], model_name: str, provider: str = "unknown") -> Dict[str, Any]:
    final = DEFAULT_RESPONSE.copy()
    final.update(result or {})
    final["confidence_score"] = float(final.get("confidence_score") or 0)
    final["optimization_score"] = float(final.get("optimization_score") or 0)
    final["risk_score"] = float(final.get("risk_score") or 0)
    final["_model_used"] = model_name
    final["_provider_used"] = provider
    if not isinstance(final.get("alternatives"), list):
        final["alternatives"] = []
    if not isinstance(final.get("warnings"), list):
        final["warnings"] = [str(final.get("warnings"))]
    return final


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", (text or "").lower())
    result = []
    for w in words:
        if w in STOP_WORDS or len(w) <= 1:
            continue
        result.append(w)
        if w.endswith("s") and len(w) > 3:
            result.append(w[:-1])
        else:
            result.append(w + "s")
    return result


def _table_text(table: Dict[str, Any]) -> str:
    pieces = [str(table.get("name", ""))]
    for c in table.get("columns", []) or []:
        pieces.append(str(c.get("name", "")))
        pieces.append(str(c.get("type", "")))
        if c.get("foreign_key"):
            pieces.append(str(c.get("foreign_key")))
    return " ".join(pieces).lower()


def _score_table(natural_language: str, table: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    words = set(_tokens(natural_language))
    table_name = str(table.get("name", "")).lower()
    table_name_parts = set(_tokens(table_name.replace("_", " ")))
    columns = table.get("columns", []) or []

    score = 0
    if table_name in words or table_name.rstrip("s") in words:
        score += 25
    score += 8 * len(words & table_name_parts)

    scored_columns = []
    for col in columns:
        col_name = str(col.get("name", "")).lower()
        col_parts = set(_tokens(col_name.replace("_", " ")))
        col_score = 0
        if col_name in words or col_name.rstrip("s") in words:
            col_score += 12
        col_score += 5 * len(words & col_parts)
        if col.get("primary_key"):
            col_score += 1
        if col.get("foreign_key"):
            col_score += 2
        if col_score > 0:
            scored_columns.append((col_score, col))
            score += col_score

    # Light semantic boosts common in business databases.
    joined_text = _table_text(table)
    synonyms = {
        "buy": ["order", "sale", "purchase", "invoice"],
        "bought": ["order", "sale", "purchase", "invoice"],
        "selling": ["order", "sale", "product"],
        "revenue": ["amount", "total", "price", "payment", "order"],
        "user": ["customer", "student", "employee", "account"],
        "people": ["customer", "student", "employee", "user"],
    }
    for w in words:
        for synonym in synonyms.get(w, []):
            if synonym in joined_text:
                score += 4

    scored_columns.sort(key=lambda item: item[0], reverse=True)
    return score, [c for _, c in scored_columns]


def get_relevant_schema_context(natural_language: str, schema: Dict[str, Any], max_tables: int = 6, max_columns: int = 14) -> str:
    """Token-efficient schema retrieval.

    Sends only the most relevant tables/columns to the LLM instead of the full schema.
    This is the main protection against token/context-limit errors on large databases.
    """
    tables = schema.get("tables", []) or []
    if not tables:
        return "No schema loaded."

    scored = []
    for table in tables:
        score, matching_cols = _score_table(natural_language, table)
        if score > 0:
            scored.append((score, table, matching_cols))

    if not scored:
        # For broad questions, keep only a compact table list.
        scored = [(1, table, []) for table in tables[:max_tables]]

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[:max_tables]

    # Include directly related FK tables when available and still within limit.
    selected_names = {str(t.get("name")) for _, t, _ in selected}
    all_by_name = {str(t.get("name")): t for t in tables}
    for _, table, _ in list(selected):
        if len(selected) >= max_tables:
            break
        for col in table.get("columns", []) or []:
            fk = col.get("foreign_key")
            if not fk:
                continue
            ref_table = str(fk).split(".")[0]
            if ref_table in all_by_name and ref_table not in selected_names:
                selected.append((1, all_by_name[ref_table], []))
                selected_names.add(ref_table)
                if len(selected) >= max_tables:
                    break

    parts = [
        "Relevant database schema only. Do not use tables or columns not listed here."
    ]
    for score, table, matching_cols in selected:
        columns = table.get("columns", []) or []
        important = []
        seen = set()

        # Keep matched columns first.
        for col in matching_cols:
            name = col.get("name")
            if name and name not in seen:
                important.append(col)
                seen.add(name)

        # Always keep PK/FK because joins need them.
        for col in columns:
            name = col.get("name")
            if name and name not in seen and (col.get("primary_key") or col.get("foreign_key")):
                important.append(col)
                seen.add(name)

        # Then add a few leading columns as context.
        for col in columns:
            name = col.get("name")
            if len(important) >= max_columns:
                break
            if name and name not in seen:
                important.append(col)
                seen.add(name)

        col_text = ", ".join(
            f"{c.get('name')} ({c.get('type')}"
            f"{' PK' if c.get('primary_key') else ''}"
            f"{' FK->' + str(c.get('foreign_key')) if c.get('foreign_key') else ''})"
            for c in important
        )
        omitted = max(0, len(columns) - len(important))
        suffix = f"; {omitted} other columns omitted" if omitted else ""
        parts.append(f"Table: {table.get('name')}\nColumns: {col_text}{suffix}")
    return "\n\n".join(parts)


def fallback_sql(natural_language: str, schema_context: str) -> str:
    nl = natural_language.lower()
    # Choose first table in relevant context; this is safer than hardcoded demo names.
    table_match = re.search(r"Table:\s*([A-Za-z_][A-Za-z0-9_]*)", schema_context)
    first_table = table_match.group(1) if table_match else None
    if any(x in nl for x in ["show tables", "list tables", "all tables"]):
        return "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    if first_table:
        return f"SELECT * FROM {first_table} LIMIT 50;"
    return "SELECT 1;"


def _build_prompt(natural_language: str, schema_context: str, conversation_history: Optional[List[Dict]], mode: str, language: str) -> str:
    history_context = ""
    if conversation_history:
        short_history = conversation_history[-2:]
        history_context = "\nCompressed Conversation Context:\n"
        for msg in short_history:
            user_text = str(msg.get("user", ""))[:160]
            sql_text = str(msg.get("sql", ""))[:260]
            history_context += f"Previous: {user_text}\nSQL: {sql_text}\n"

    lang_instruction = ""
    if language == "hi":
        lang_instruction = "User may write in Hindi. Understand the request and generate SQL. Explain in English.\n"

    verbosity_instruction = "Return concise explanations. Do not generate long learning content unless mode is developer."
    if mode == "developer":
        verbosity_instruction = "Developer mode: include useful but concise optimization and learning tips."

    return f"""{SYSTEM_PROMPT}

{lang_instruction}
Mode: {mode}
{verbosity_instruction}

Database Schema:
{schema_context}
{history_context}

User Request: {natural_language}

Return ONLY the JSON object. sql field must not be empty."""


def _should_fallback_to_groq(error: Exception) -> bool:
    message = str(error).lower()
    return any(term in message for term in ["quota", "429", "rate", "token", "context", "timeout", "deadline", "503", "500", "unavailable"])


async def _generate_with_gemini(prompt: str, natural_language: str) -> Dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    model_name = select_gemini_model(natural_language)
    model = genai.GenerativeModel(
        model_name,
        generation_config={
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1536,
            "response_mime_type": "application/json",
        },
    )
    response = model.generate_content(prompt)
    text = response.text.strip()
    print(f"[GEMINI RAW] model={model_name} len={len(text)} preview={text[:150]}")
    return normalize_result(safe_json_parse(text), model_name, "gemini")


async def _generate_with_groq(prompt: str) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    model_name = settings.GROQ_MODEL
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You generate SQL and return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1536,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=35) as client:
        response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    text = data["choices"][0]["message"]["content"].strip()
    print(f"[GROQ RAW] model={model_name} len={len(text)} preview={text[:150]}")
    return normalize_result(safe_json_parse(text), model_name, "groq")


async def _generate_with_openrouter(prompt: str) -> Dict[str, Any]:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    model_name = settings.OPENROUTER_MODEL
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You generate SQL and return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1536,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": getattr(settings, "APP_URL", "https://ai-database-copilot.com"),
        "X-Title": settings.APP_NAME,
    }
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    text = data["choices"][0]["message"]["content"].strip()
    print(f"[OPENROUTER RAW] model={model_name} len={len(text)} preview={text[:150]}")
    return normalize_result(safe_json_parse(text), model_name, "openrouter")


async def _call_provider(provider: str, prompt: str, natural_language: str) -> Dict[str, Any]:
    provider = (provider or "gemini").lower()
    if provider == "gemini":
        return await _generate_with_gemini(prompt, natural_language)
    if provider == "groq":
        return await _generate_with_groq(prompt)
    if provider == "openrouter":
        return await _generate_with_openrouter(prompt)
    raise RuntimeError(f"Unsupported LLM provider: {provider}")


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

    prompt = _build_prompt(natural_language, schema_context, conversation_history, mode, language)
    providers = []
    for p in [settings.PRIMARY_LLM, settings.FALLBACK_LLM, settings.OPTIONAL_LLM]:
        p = (p or "").strip().lower()
        if p and p not in providers:
            providers.append(p)
    if not providers:
        providers = ["gemini", "groq"]

    errors = []
    for idx, provider in enumerate(providers):
        try:
            result = await _call_provider(provider, prompt, natural_language)
            if not result.get("sql", "").strip():
                result["sql"] = fallback_sql(natural_language, schema_context)
                result["warnings"] = result.get("warnings", []) + ["AI returned empty SQL; local fallback used"]
                result["confidence_score"] = min(float(result.get("confidence_score") or 0), 0.45)
            if errors:
                result["warnings"] = result.get("warnings", []) + ["Primary LLM failed; fallback provider used"]
            return result
        except json.JSONDecodeError as e:
            errors.append(f"{provider}: invalid JSON ({str(e)[:120]})")
            print(f"[{provider.upper()} JSON ERROR] {e}")
        except Exception as e:
            errors.append(f"{provider}: {type(e).__name__}: {str(e)[:160]}")
            print(f"[{provider.upper()} ERROR] {type(e).__name__}: {str(e)}")
            # Continue to configured fallback providers for all errors. Token/quota errors are the common case.
            continue

    sql = fallback_sql(natural_language, schema_context)
    failed = DEFAULT_RESPONSE.copy()
    failed.update({
        "sql": sql,
        "explanation": "All configured AI providers failed. Local fallback SQL generated.",
        "confidence_score": 0.35,
        "optimization_score": 0.5,
        "query_type": "SELECT" if sql.strip().lower().startswith("select") else "UNKNOWN",
        "warnings": ["; ".join(errors)[:500], "Local fallback used."],
        "_model_used": "local-fallback",
        "_provider_used": "local",
    })
    return failed


async def generate_schema_summary(schema: Dict[str, Any]) -> str:
    tables = schema.get("tables", [])[:8]
    summary_parts = []
    for table in tables:
        cols = ", ".join(
            f"{c['name']} ({c['type']}{' PK' if c.get('primary_key') else ''}{' FK' if c.get('foreign_key') else ''})"
            for c in table.get("columns", [])[:10]
        )
        summary_parts.append(f"Table: {table['name']}\nColumns: {cols}")
    return "\n\n".join(summary_parts)
