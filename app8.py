import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
from sqlalchemy import create_engine

from utils.schema_extractor import extract_schema_sqlite, extract_schema_rdbms
from utils.vector_store import build_or_load_index
from utils.llm_sql_generator import generate_sql_from_prompt, generate_sql_schema_only
from langchain_sql_pipeline import generate_sql_with_langchain
from utils.er_diagram import render_er_diagram

from evaluate import load  # 👈 For BLEU and ROUGE

# Set up page
st.set_page_config(page_title="🧠 Text-to-SQL RAG App")
st.title("🧠 Text-to-SQL Generator using RAG + Gemini")

# Step 1: Choose DB
db_type = st.selectbox("Choose Database Type", ["SQLite (.db)", "SQLite (.sqlite)", "PostgreSQL", "MySQL"])
schema_data = None
db_connector = None

# Step 2: SQLite upload
if db_type in ["SQLite (.db)", "SQLite (.sqlite)"]:
    uploaded_sqlite = st.file_uploader("📎 Upload SQLite file", type=["db", "sqlite", "sql"])
    if uploaded_sqlite:
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
        temp_db.write(uploaded_sqlite.read())
        temp_db.close()
        schema_data = extract_schema_sqlite(temp_db.name)
        db_connector = lambda query: pd.read_sql_query(query, sqlite3.connect(temp_db.name))

# Step 3: RDBMS
elif db_type in ["PostgreSQL", "MySQL"]:
    with st.expander("🔐 Enter RDBMS Credentials"):
        host = st.text_input("Host")
        port = st.text_input("Port", "5432" if db_type == "PostgreSQL" else "3306")
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        dbname = st.text_input("Database Name")
    
    if st.button("🔌 Connect to Database"):
        uri = f"{'postgresql' if db_type == 'PostgreSQL' else 'mysql+pymysql'}://{user}:{password}@{host}:{port}/{dbname}"
        try:
            schema_data = extract_schema_rdbms(uri)
            engine = create_engine(uri)
            db_connector = lambda query: pd.read_sql_query(query, engine)
            st.success("Connected!")
        except Exception as e:
            st.error(f"Failed: {e}")

# Step 4: Prompt + Mode + SQL
if schema_data:
    st.subheader("📊 ER Diagram")
    st.graphviz_chart(render_er_diagram(schema_data))

    user_query = st.text_input("Ask your database:", placeholder="e.g., Show all rock genre tracks")
    mode = st.radio("Choose Query Mode:", ["🔁 LangChain RAG", "🛠️ Manual FAISS RAG", "📄 No RAG (schema only)"])

    sql_query = ""
    cleaned_query = ""

    if st.button("🚀 Generate SQL"):
        if mode == "🔁 LangChain RAG":
            sql_query = generate_sql_with_langchain(user_query, schema_data)
        elif mode == "🛠️ Manual FAISS RAG":
            index, metadata = build_or_load_index(schema_data)
            sql_query = generate_sql_from_prompt(user_query, index, metadata, schema_data)
        else:
            sql_query = generate_sql_schema_only(user_query, schema_data)

        cleaned_query = sql_query.strip().replace("```sql", "").replace("```", "").strip()
        st.code(cleaned_query, language="sql")

        if db_connector:
            try:
                df = db_connector(cleaned_query)
                st.success("✅ Query executed successfully!")
                st.dataframe(df)
            except Exception as e:
                st.error(f"❌ Execution Failed: {e}")

    # Step 5: Evaluation
    st.markdown("✅ Optional: Enter reference SQL to evaluate generated SQL")
    reference_sql = st.text_area("Reference SQL")

    if reference_sql and cleaned_query and st.button("📊 Evaluate SQL"):
        rouge = load("rouge")
        bleu = load("bleu")

        ref = reference_sql.strip().replace("```sql", "").replace("```", "").strip()
        pred = cleaned_query

        rouge_result = rouge.compute(predictions=[pred], references=[ref], rouge_types=["rougeL"])
        bleu_result = bleu.compute(predictions=[pred], references=[ref])

        st.markdown(f"🔹 **ROUGE-L Score:** `{rouge_result['rougeL']:.4f}`")
        st.markdown(f"🔹 **BLEU Score:** `{bleu_result['bleu']:.4f}`")
