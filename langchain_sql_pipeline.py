# langchain_sql_pipeline.py
import os
import pickle
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate



load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def load_faiss_retriever():
    with open("vectorstore/schema_meta.pkl", "rb") as f:
        metadata = pickle.load(f)
    texts = [f"{item['table']} - {item['column']}" for item in metadata]

    embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_texts(texts, embedder)
    return db.as_retriever(search_type="similarity", k=5), metadata

def generate_sql_with_langchain(user_query, schema_dict):
    retriever, _ = load_faiss_retriever()
    docs = retriever.get_relevant_documents(user_query)
    semantic_context = "\n".join([doc.page_content for doc in docs])
    schema_text = "\n".join([f"Table: {t} — Columns: {', '.join(c)}" for t, c in schema_dict.items()])

    prompt_template = PromptTemplate.from_template("""
You are a SQL expert. Given the database schema and relevant columns, write a SQL query for the user question.

### DATABASE SCHEMA
{schema}

### RELEVANT COLUMNS
{context}

### USER QUESTION
{question}

Only use valid table and column names. Do not hallucinate.

SQL:
""")

    chain = LLMChain(
        llm=GoogleGenerativeAI(model="models/gemini-1.5-pro", google_api_key=GEMINI_API_KEY),
        prompt=prompt_template
    )

    return chain.run(schema=schema_text, context=semantic_context, question=user_query)
