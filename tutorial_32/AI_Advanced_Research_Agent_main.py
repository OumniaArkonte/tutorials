import os
import requests
import streamlit as st
from textwrap import dedent
from agno.agent import Agent
from mistralai import Mistral
from agno.models.google import Gemini
from agno.vectordb.pgvector import PgVector
from agno.tools.reasoning import ReasoningTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.knowledge.markdown import MarkdownKnowledgeBase
from dotenv import load_dotenv

load_dotenv()

# Chargement des clés API
mistral_key = os.getenv("MISTRAL_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")
client = Mistral(api_key=mistral_key)

# ------------------ OCR PDF ------------------
def ocr_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        st.error("PDF file not found")
        return

    uploaded_pdf = client.files.upload(
        file={
            "file_name": os.path.basename(pdf_path),
            "content": open(pdf_path, "rb"),
        },
        purpose="ocr"
    )

    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
        include_image_base64=True
    )

    with open("DocumentMarkdown/ocr_document.md", "w", encoding="utf-8") as f:
        for page in ocr_response.pages:
            f.write(page.markdown + "\n")

# ------------------ Knowledge Base ------------------
def knowledge_base_setup():
    knowledge_base = MarkdownKnowledgeBase(
        path="DocumentMarkdown/ocr_document.md",
        vector_db=PgVector(
            table_name="markdown_documents",
            db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
        ),
    )
    return knowledge_base


# ------------------ Summary Agent ------------------
def summary_agent():
    kb = knowledge_base_setup()
    agent = Agent(
        name="Summary Agent",
        model=Gemini(id="gemini-2.0-flash", api_key=gemini_key),
        instructions=dedent("""
            You are a summary agent designed to summarize the document.
            Read the entire document stored in the knowledge base (in markdown format) 
            and produce a concise summary in plain English. 
            Focus on the paper’s objective, methodology, and key findings.
        """),
        knowledge=kb,
        search_knowledge=True,
    )
    agent.knowledge.load(recreate=False)
    return agent

# ------------------ Research Agent ------------------
def agent_setup():
    kb = knowledge_base_setup()
    agent = Agent(
        name="Research Agent",
        model=Gemini(id="gemini-2.0-flash", api_key=gemini_key),
        instructions=dedent("""
            You are a research assistant designed to simplify and answer questions about academic papers.

            1. Use the knowledge base first and cite exact sources.
            2. Fallback to semantic_scholar_search or GoogleSearchTools if needed.
            3. Format answers cleanly and highlight sources.
            Prioritize accuracy, traceability, clarity.
        """),
        knowledge=kb,
        search_knowledge=True,
        tools=[ReasoningTools(add_instructions=True), semantic_scholar_search, GoogleSearchTools()],
    )
    agent.knowledge.load(recreate=False)
    return agent

# ------------------ Streamlit UI ------------------
if __name__ == "__main__":
    st.title("Advanced Research Assistant (Gemini + OCR) ")

    if "ocr_done" not in st.session_state:
        st.session_state.ocr_done = False
    if "summary_agent" not in st.session_state:
        st.session_state.summary_agent = None
    if "agent" not in st.session_state:
        st.session_state.agent = None

    uploaded_file = st.file_uploader("Upload your research paper", type=["pdf"])

    if uploaded_file and not st.session_state.ocr_done:
        os.makedirs("DocumentMarkdown", exist_ok=True)
        pdf_path = f"DocumentMarkdown/{uploaded_file.name}"
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.read())

        with st.spinner("Performing OCR..."):
            ocr_pdf(pdf_path)
        st.success("OCR completed successfully")

        # Créer les agents
        st.session_state.summary_agent = summary_agent()
        with st.spinner("Generating summary..."):
            summary_response = st.session_state.summary_agent.run("Summarize the document")
            st.write(summary_response.content)

        st.session_state.agent = agent_setup()
        st.session_state.ocr_done = True

    if st.session_state.ocr_done:
        user_input = st.text_input("Enter a question: ")
        if st.button("Submit"):
            with st.spinner('Generating response...'):
                st.session_state.agent.print_response(
                    user_input,
                    stream=True,
                    show_full_reasoning=True,
                    stream_intermediate_steps=True
                )
            st.success('Response generated successfully ')
