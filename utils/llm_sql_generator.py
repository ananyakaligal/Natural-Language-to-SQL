# llm_sql_generator.py (Gemini + Auto Schema Injection)

import os
import re
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import sqlite3

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
model = genai.GenerativeModel("models/gemini-1.5-pro")


def clean_sql_output(llm_text: str) -> str:
    """
    Clean LLM output by removing markdown SQL blocks like ```sql ... ```
    and trimming unnecessary whitespace.
    """
    cleaned = re.sub(r"```sql|```", "", llm_text, flags=re.IGNORECASE).strip()
    return cleaned


def extract_schema_from_db(db_path: str) -> dict:
    """Extracts table and column names from SQLite DB."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = [row[1] for row in cursor.fetchall()]
        schema[table] = columns
    conn.close()
    return schema


def format_schema_for_prompt(schema: dict) -> str:
    formatted = ""
    for table, columns in schema.items():
        formatted += f"Table: {table} — Columns: {', '.join(columns)}\n"
    return formatted.strip()


def generate_sql_from_prompt(user_query: str, index, metadata, schema_dict: dict, top_k: int = 5) -> str:
    """
    Uses Gemini + schema context to generate clean SQL query from user question.
    """
    query_emb = embed_model.encode([user_query])
    D, I = index.search(np.array(query_emb).astype("float32"), top_k)

    # Top-k semantic context
    semantic_context = ""
    for idx in I[0]:
        item = metadata[idx]
        semantic_context += f"Table: {item['table']} | Column: {item['column']}\n"

    # Schema context
    schema_context = format_schema_for_prompt(schema_dict)

    prompt = f"""
You are a SQL expert.

Use only the following schema and column names when generating SQL.

### DATABASE SCHEMA
{schema_context}

### RELEVANT COLUMNS
{semantic_context}

### USER QUESTION
{user_query}

Generate valid SQL using only the exact schema and column names provided.
Do not hallucinate table or column names.
"""

    response = model.generate_content(prompt)
    return clean_sql_output(response.text)

def generate_sql_schema_only(user_query: str, schema_dict: dict) -> str:
    import os
    import re
    from dotenv import load_dotenv
    import google.generativeai as genai

    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("models/gemini-1.5-pro")

    def format_schema(schema: dict) -> str:
        return "\n".join([f"Table: {table} — Columns: {', '.join(cols)}" for table, cols in schema.items()])

    schema_context = format_schema(schema_dict)

    prompt = f"""
You are a SQL expert.

Below is the full schema of the database:

{schema_context}

User question:
{user_query}

Write a valid SQL query using only the tables and columns from the schema above.
Do not hallucinate table or column names.
"""

    response = model.generate_content(prompt)
    return re.sub(r"```sql|```", "", response.text).strip()
