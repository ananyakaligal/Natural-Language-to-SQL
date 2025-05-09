import streamlit as st
import pandas as pd
import sqlite3
import tempfile
from sqlalchemy import create_engine

from utils.schema_extractor import extract_schema_sqlite, extract_schema_rdbms
from utils.embeddings import build_or_load_index
from utils.llm_sql_generator import (
    generate_sql_from_prompt,
    generate_sql_schema_only,
)
from langchain_sql_pipeline import generate_sql_with_langchain
from utils.er_diagram import render_er_diagram

# --- Page setup ---
st.set_page_config(
    page_title="Text-to-SQL RAG Demo",
    layout="wide",
)

# hide Streamlit chrome
st.markdown(
    """
    <style>
      #MainMenu, header, footer { visibility: hidden; }
      /* make all containers true black without any white */
      .css-12oz5g7, .block-container { background: #000 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar for DB setup ---
with st.sidebar:
    st.header("Database Setup")
    db_type = st.selectbox("Type", ["SQLite", "PostgreSQL", "MySQL"])
    schema_data = None
    db_connector = None

    if db_type == "SQLite":
        uploaded = st.file_uploader("Upload .db/.sqlite/.sql", type=["db","sqlite","sql"])
        if uploaded:
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
            tf.write(uploaded.read())
            tf.close()
            schema_data = extract_schema_sqlite(tf.name)
            db_connector = lambda q: pd.read_sql_query(q, sqlite3.connect(tf.name))

    else:
        with st.expander("Enter credentials"):
            host = st.text_input("Host")
            port = st.text_input("Port", "5432" if db_type=="PostgreSQL" else "3306")
            user = st.text_input("User")
            pwd  = st.text_input("Password", type="password")
            name = st.text_input("Database")
        if st.button("Connect"):
            uri = (
                f"postgresql://{user}:{pwd}@{host}:{port}/{name}"
                if db_type=="PostgreSQL" 
                else f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}"
            )
            try:
                schema_data = extract_schema_rdbms(uri)
                engine = create_engine(uri)
                db_connector = lambda q: pd.read_sql_query(q, engine)
                st.success("Connected")
            except Exception as e:
                st.error(f"{e}")

# --- Main panel ---
st.title("Text-to-SQL Generator")

if schema_data:
    # Schema diagram
    st.subheader("Schema Diagram")
    st.graphviz_chart(render_er_diagram(schema_data))

    # Question + mode
    st.subheader("Ask Your Database")
    q_col, m_col = st.columns((3,1))
    with q_col:
        question = st.text_input("", placeholder="e.g. List rock-genre tracks")
    with m_col:
        mode = st.selectbox(
            "Mode",
            ["LangChain RAG", "Manual FAISS", "Schema Only"],
            help="How to generate the SQL"
        )

    # Generate button
    generate = st.button("Generate SQL", use_container_width=True)

    if generate and question:
        with st.spinner("Generating…"):
            if mode == "LangChain RAG":
                raw = generate_sql_with_langchain(question, schema_data)
            elif mode == "Manual FAISS":
                idx, meta = build_or_load_index(schema_data)
                raw = generate_sql_from_prompt(question, idx, meta, schema_data)
            else:
                raw = generate_sql_schema_only(question, schema_data)
        sql = raw.replace("```sql","").replace("```","").strip()

        # Show SQL
        st.subheader("Generated SQL")
        st.code(sql, language="sql")

        # Show results
        if db_connector:
            st.subheader("Results")
            try:
                df = db_connector(sql)
                st.metric("Rows returned", len(df))
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Execution failed: {e}")

else:
    st.info("Use the sidebar to upload or connect to a database.")
