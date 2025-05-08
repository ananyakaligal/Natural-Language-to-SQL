# app6_lang.py

import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
from sqlalchemy import create_engine
from utils.schema_extractor import extract_schema_sqlite, extract_schema_rdbms
from utils.vector_store import build_or_load_index
from utils.llm_sql_generator import generate_sql_from_prompt
from langchain_sql_pipeline import generate_sql_with_langchain
from utils.er_diagram import render_er_diagram

# Page setup
st.set_page_config(page_title="🧠 Text-to-SQL RAG App")
st.title("🧠 Text-to-SQL Generator using RAG + Gemini")

# Step 1: Choose database type
db_type = st.selectbox("Choose Database Type", ["SQLite (.db)", "SQLite (.sqlite)", "PostgreSQL", "MySQL"])

schema_data = None
db_connector = None

# Step 2: Handle SQLite uploads
if db_type in ["SQLite (.db)", "SQLite (.sqlite)"]:
    uploaded_sqlite = st.file_uploader("📎 Upload SQLite database file (.db or .sqlite or .sql)", type=["db", "sqlite", "sql"])
    if uploaded_sqlite:
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
        temp_db.write(uploaded_sqlite.read())
        temp_db.close()
        schema_data = extract_schema_sqlite(temp_db.name)
        db_connector = lambda query: pd.read_sql_query(query, sqlite3.connect(temp_db.name))

# Step 3: Handle RDBMS (PostgreSQL / MySQL)
elif db_type in ["PostgreSQL", "MySQL"]:
    with st.expander("🔐 Enter Database Credentials"):
        host = st.text_input("Host")
        port = st.text_input("Port", value="5432" if db_type == "PostgreSQL" else "3306")
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        dbname = st.text_input("Database Name")

    db_uri = ""
    if db_type == "PostgreSQL":
        db_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == "MySQL":
        db_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"

    if st.button("🔌 Connect to Database"):
        try:
            schema_data = extract_schema_rdbms(db_uri)
            engine = create_engine(db_uri)
            db_connector = lambda query: pd.read_sql_query(query, engine)
            st.success("Connected and schema loaded!")
        except Exception as e:
            st.error(f"Failed to connect: {e}")

# Step 4: Display schema + Input + Generate
if schema_data:
    st.subheader("📊 ER Diagram of Database Schema")
    st.graphviz_chart(render_er_diagram(schema_data))

    user_question = st.text_input("Ask your database:", placeholder="e.g., Show patients over 60 years old")

    use_langchain = st.toggle("🔁 Use LangChain with RAG")

    if st.button("🚀 Generate SQL"):
        if use_langchain:
            sql_query = generate_sql_with_langchain(user_question, schema_data)
        else:
            index, metadata = build_or_load_index(schema_data)
            sql_query = generate_sql_from_prompt(user_question, index, metadata, schema_data)

        # Clean markdown formatting from LLM output
        cleaned_query = sql_query.strip().replace("```sql", "").replace("```", "").strip()

        st.code(cleaned_query, language="sql")

        if db_connector:
            try:
                df = db_connector(cleaned_query)
                st.success("✅ Query executed successfully!")
                st.dataframe(df)
            except Exception as e:
                st.error(f"❌ Query Execution Failed: {e}")
