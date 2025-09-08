import os
from dotenv import load_dotenv
from notion_client import Client
from agno.agent import Agent
from agno.models.google import Gemini  
from rapidfuzz import fuzz  

load_dotenv()

# Variables d'environnement
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  

notion = Client(auth=NOTION_TOKEN)

def _plain_text_from_rich(rt):
    """Convertit rich_text/title Notion en texte simple"""
    if not rt:
        return ""
    return "".join([t.get("plain_text", "") for t in rt])

def query_notion_kb(agent, query, num_documents=None, threshold=0.6, **kwargs):
    """Retourne une liste de documents triés par score depuis Notion."""
    all_matches = []
    start_cursor = None

    while True:
        resp = notion.databases.query(
            database_id=DATABASE_ID,
            start_cursor=start_cursor,
            page_size=100
        )

        for page in resp.get("results", []):
            props = page.get("properties", {})

            # Champs question / answer
            qprop = props.get("question", {}).get("rich_text", [])
            question = _plain_text_from_rich(qprop)

            aprop = props.get("answer", {}).get("rich_text", [])
            answer = _plain_text_from_rich(aprop)

            text = f"Q: {question}\nA: {answer}"

            # Similarité
            q_words = set(w.lower() for w in query.split() if w.strip())
            doc_words = set((question + " " + answer).lower().split())
            basic_match_ratio = len(q_words & doc_words) / (len(q_words) or 1)
            fuzzy_score = fuzz.partial_ratio(query, question + " " + answer) / 100.0
            score = max(basic_match_ratio, fuzzy_score)

            # Métadonnées
            department = (props.get("department") or {}).get("select", {}) and props["department"]["select"].get("name", "Unknown")
            tags = [t["name"] for t in (props.get("tags") or {}).get("multi_select", [])]

            if score >= threshold:
                all_matches.append({
                    "content": text,
                    "meta_data": {
                        "source": "Notion KB",
                        "department": department,
                        "tags": tags,
                        "match_score": score
                    }
                })

        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")

    all_matches.sort(key=lambda x: x["meta_data"]["match_score"], reverse=True)
    if not all_matches:
        return [{"content": "No matching entry found in the knowledge base.", "meta_data": {"source": "Company Knowledge Base"}}]
    return all_matches[:num_documents] if num_documents else all_matches


# l'agent Gemini 
agent = Agent(
    model=Gemini(id="gemini-2.0-flash", api_key=GEMINI_API_KEY),
    knowledge=True,
    search_knowledge=True,
    retriever=query_notion_kb,
    reasoning=False
)

if __name__ == "__main__":
    prompt = input("Enter your prompt: ")
    documents = query_notion_kb(agent, prompt, num_documents=3)
    if documents:
        for doc in documents:
            print(f"\n--- Réponse depuis Notion (score {doc['meta_data'].get('match_score', 0):.2f}) ---")
            print(doc["content"])
    else:
        print("Aucune réponse trouvée dans la base de connaissances.")
