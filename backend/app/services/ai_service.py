import google.generativeai as genai
import json
import re
from typing import Optional, Dict, Any, List
from app.core.config import settings

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

COMPLEX_QUERY_KEYWORDS = [
    "update", "delete", "insert", "join", "subquery",
    "having", "union", "with", "group by", "nested",
    "create table", "alter table", "drop table", "ddl", "schema"
]

INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above)\s+instructions",
    r"forget\s+your\s+instructions",
    r"system\s*:",
    r"developer\s*:",
    r"<\s*script",
    r"drop\s+all\s+tables",
    r";\s*(drop\s+database|truncate|delete\s+from)\s+",
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


SYSTEM_PROMPT = """You are an expert SQL assistant for a database copilot app.
Given a database schema and a natural language request, generate valid SQL.
Always respond with ONLY a JSON object. No markdown, no explanation outside JSON.

Required JSON structure:
{
  "sql": "SELECT * FROM table WHERE condition",
  "explanation": "plain English explanation",
  "confidence_score": 0.85,
  "optimization_score": 0.80,
  "risk_level": "low",
  "risk_score": 0.1,
  "risk_reasons": [],
  "query_type": "SELECT",
  "estimated_rows": 10,
  "estimated_time_ms": 20.0,
  "alternatives": [],
  "optimization_tips": [],
  "learning_tips": [],
  "clauses_explained": {},
  "warnings": []
}

Rules:
- sql field must always contain a valid SQL query string.
- Never return empty sql field.
- query_type must be SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, or DROP.
- For table creation requests, generate CREATE TABLE SQL.
- Prefer SQLite-compatible SQL unless the schema clearly belongs to PostgreSQL or MySQL.
- Use IF NOT EXISTS for CREATE TABLE when appropriate.
- For DDL, create safe SQL only. Do not generate CREATE DATABASE, DROP DATABASE, TRUNCATE, GRANT, REVOKE, EXEC, CALL.
- For UPDATE and DELETE, always include a WHERE clause.
- If unsure, generate the safest SELECT query or CREATE TABLE structure and include a warning.
- risk_level must be low, medium, high, or critical.
"""


def detect_prompt_injection(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in INJECTION_PATTERNS)


def select_model(natural_language: str) -> str:
    nl_lower = natural_language.lower()
    needs_pro = any(keyword in nl_lower for keyword in COMPLEX_QUERY_KEYWORDS)
    return settings.GEMINI_PRO_MODEL if needs_pro else settings.GEMINI_FLASH_MODEL


def detect_query_type(sql: str) -> str:
    sql_upper = (sql or "").strip().upper()
    match = re.match(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", sql_upper)
    return match.group(1) if match else "UNKNOWN"


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
    final.update(result or {})

    final["sql"] = str(final.get("sql") or "").strip()
    detected_type = detect_query_type(final["sql"])
    if detected_type != "UNKNOWN":
        final["query_type"] = detected_type

    final["confidence_score"] = float(final.get("confidence_score") or 0)
    final["optimization_score"] = float(final.get("optimization_score") or 0)
    final["risk_score"] = float(final.get("risk_score") or 0)
    final["alternatives"] = final.get("alternatives") or []
    final["optimization_tips"] = final.get("optimization_tips") or []
    final["learning_tips"] = final.get("learning_tips") or []
    final["clauses_explained"] = final.get("clauses_explained") or {}
    final["warnings"] = final.get("warnings") or []
    final["risk_reasons"] = final.get("risk_reasons") or []
    final["_model_used"] = model_name

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

    if scored_tables:
        relevant_tables = [table for _, table in scored_tables[:6]]
    else:
        relevant_tables = tables[:8]

    if not relevant_tables:
        return "No existing tables found. You may generate DDL such as CREATE TABLE to define a new schema."

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


def is_database_builder_request(natural_language: str) -> bool:
    nl = natural_language.lower()
    builder_words = [
        "create database", "create a database", "database for", "management system",
        "schema for", "build database", "design database", "create an app database",
        "create ecommerce", "create e-commerce", "create hospital", "create library",
        "create school", "create college", "create university", "create inventory",
    ]
    return any(word in nl for word in builder_words)


def _sqlite_type(type_name: str) -> str:
    mapping = {
        "id": "INTEGER",
        "int": "INTEGER",
        "integer": "INTEGER",
        "number": "INTEGER",
        "decimal": "DECIMAL(10,2)",
        "amount": "DECIMAL(10,2)",
        "price": "DECIMAL(10,2)",
        "date": "DATE",
        "time": "TIMESTAMP",
        "text": "TEXT",
        "email": "VARCHAR(120)",
        "phone": "VARCHAR(20)",
        "name": "VARCHAR(100)",
    }
    return mapping.get(type_name.lower(), type_name)


def _builder_templates(natural_language: str) -> Dict[str, Any]:
    nl = natural_language.lower()

    if any(k in nl for k in ["ecommerce", "e-commerce", "online shopping", "shopping"]):
        name = "ecommerce"
        summary = "Ecommerce database with customers, products, orders, and order items."
        sql = """CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    city VARCHAR(60),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(80),
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    total_amount DECIMAL(10,2) DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);"""
        tables = ["customers", "products", "orders", "order_items"]
    elif any(k in nl for k in ["hospital", "clinic", "medical"]):
        name = "hospital_management"
        summary = "Hospital database with patients, doctors, appointments, and billing."
        sql = """CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    gender VARCHAR(20),
    date_of_birth DATE,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id INTEGER PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(120) UNIQUE
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    appointment_date TIMESTAMP NOT NULL,
    status VARCHAR(30) DEFAULT 'scheduled',
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    appointment_id INTEGER,
    amount DECIMAL(10,2) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'pending',
    bill_date DATE NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
);"""
        tables = ["patients", "doctors", "appointments", "bills"]
    elif any(k in nl for k in ["library", "books"]):
        name = "library_management"
        summary = "Library database with authors, books, members, and borrow records."
        sql = """CREATE TABLE IF NOT EXISTS authors (
    author_id INTEGER PRIMARY KEY,
    author_name VARCHAR(100) NOT NULL,
    country VARCHAR(60)
);

CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    author_id INTEGER,
    isbn VARCHAR(30) UNIQUE,
    category VARCHAR(80),
    available_copies INTEGER DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES authors(author_id)
);

CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    joined_at DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS borrow_records (
    borrow_id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    borrow_date DATE NOT NULL,
    return_date DATE,
    status VARCHAR(30) DEFAULT 'borrowed',
    FOREIGN KEY (member_id) REFERENCES members(member_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);"""
        tables = ["authors", "books", "members", "borrow_records"]
    else:
        name = "student_management"
        summary = "Student management database with departments, students, courses, and enrollments."
        sql = """CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(120) UNIQUE,
    branch VARCHAR(80),
    semester INTEGER,
    cgpa DECIMAL(3,2),
    phone VARCHAR(20),
    city VARCHAR(60),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY,
    course_name VARCHAR(120) NOT NULL,
    department_id INTEGER,
    credits INTEGER DEFAULT 3,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrollment_date DATE DEFAULT CURRENT_DATE,
    grade VARCHAR(5),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);"""
        tables = ["departments", "students", "courses", "enrollments"]

    return {
        "sql": sql,
        "explanation": summary,
        "confidence_score": 0.78,
        "optimization_score": 0.75,
        "query_type": "CREATE",
        "database_builder": {
            "database_name": name,
            "summary": summary,
            "tables": tables,
            "execution_order": tables,
        },
        "warnings": [
            "AI Database Builder generated multiple CREATE TABLE statements.",
            "Execute this only on a writable connection. Schema will refresh after execution.",
        ],
    }


def fallback_sql(natural_language: str, schema_context: str) -> Dict[str, Any]:
    nl = natural_language.lower()

    if is_database_builder_request(natural_language):
        result = _builder_templates(natural_language)
        result["warnings"] = result.get("warnings", []) + ["Fallback schema builder was used because AI service failed or quota was exceeded."]
        return result

    create_match = re.search(r"create\s+(?:a\s+)?(?:new\s+)?(?:table\s+)?([a-zA-Z_][\w]*)\s*(?:table)?", nl)
    if "create" in nl and ("table" in nl or not re.search(r"show|list|find|get", nl)):
        table_name = create_match.group(1) if create_match else "records"
        if table_name in {"a", "table", "new", "database", "the"}:
            table_name = "records"
        sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"""
        return {
            "sql": sql,
            "explanation": f"Fallback generated a safe CREATE TABLE statement for {table_name}.",
            "confidence_score": 0.45,
            "optimization_score": 0.5,
            "query_type": "CREATE",
            "warnings": ["Fallback SQL generated because AI service failed."],
        }

    if "student" in nl:
        if "cgpa" in nl and ("above" in nl or ">" in nl):
            number = re.search(r"\d+(\.\d+)?", nl)
            cgpa = number.group(0) if number else "8.5"
            sql = f"SELECT * FROM students WHERE cgpa > {cgpa} LIMIT 50;"
        else:
            sql = "SELECT * FROM students LIMIT 50;"
    elif "employee" in nl:
        sql = "SELECT * FROM employees LIMIT 50;"
    elif "product" in nl:
        sql = "SELECT * FROM products LIMIT 50;"
    else:
        table_match = re.search(r"Table:\s*(\w+)", schema_context)
        sql = f"SELECT * FROM {table_match.group(1)} LIMIT 50;" if table_match else "SELECT 1;"

    return {
        "sql": sql,
        "explanation": "Fallback SQL was generated because the AI service failed.",
        "confidence_score": 0.45,
        "optimization_score": 0.5,
        "query_type": detect_query_type(sql),
        "warnings": ["Fallback SQL generated because AI service failed."],
    }

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

    prompt = f"""{SYSTEM_PROMPT}

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
- Use only provided schema for SELECT/INSERT/UPDATE/DELETE queries.
- For CREATE TABLE requests, create the new table requested by the user.
- If the user asks to create/design/build a database or management system, return multiple CREATE TABLE statements in the sql field, separated by semicolons.
- For database builder requests, include a database_builder object with database_name, summary, tables, and execution_order.
- If there are no existing tables, CREATE TABLE is allowed.
- Do not invent existing table names for SELECT queries.
- Do not generate CREATE DATABASE, DROP DATABASE, TRUNCATE, GRANT, REVOKE, EXEC, or CALL.
"""

    try:
        if not settings.GEMINI_API_KEY:
            fallback = fallback_sql(natural_language, schema_context)
            fallback["explanation"] += " Gemini API key is missing."
            return normalize_result(fallback, "fallback")

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
        normalized = normalize_result(result, model_name)
        if not normalized["sql"]:
            fallback = fallback_sql(natural_language, schema_context)
            fallback["warnings"] = fallback.get("warnings", []) + ["AI returned empty SQL, so fallback SQL was used."]
            return normalize_result(fallback, "fallback")
        return normalized

    except json.JSONDecodeError:
        fallback = fallback_sql(natural_language, schema_context)
        fallback["warnings"] = fallback.get("warnings", []) + ["AI JSON parsing failed, so fallback SQL was used."]
        return normalize_result(fallback, "fallback")

    except Exception as exc:
        fallback = fallback_sql(natural_language, schema_context)
        fallback["warnings"] = fallback.get("warnings", []) + [f"AI service error: {str(exc)}"]
        return normalize_result(fallback, "fallback")


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
