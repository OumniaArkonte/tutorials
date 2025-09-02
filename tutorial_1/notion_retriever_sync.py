import os
import logging
from typing import Optional, List, Dict, Any
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DB_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

notion = Client(auth=NOTION_TOKEN)


def _plain_text_from_rich(rich_field: Any) -> str:
    if not rich_field:
        return ""
    return " ".join([t.get("plain_text", "") for t in rich_field])


def return_knowledge_base(
    agent, query: str, num_documents: Optional[int] = None, threshold: float = 0.6, **kwargs
) -> Optional[List[Dict]]:
    """
    Synchronous custom retriever compatible with Agno.
    Returns list[{"content": str, "meta_data": dict}]
    """
    try:
        all_pages = []
        start_cursor = None
        while True:
            body = {}
            if start_cursor:
                body["start_cursor"] = start_cursor
            resp = notion.databases.query(database_id=DATABASE_ID, **body)
            results = resp.get("results", [])
            all_pages.extend(results)
            if not resp.get("has_more"):
                break
            start_cursor = resp.get("next_cursor")

        logger.info(f"Fetched {len(all_pages)} pages from Notion DB {DATABASE_ID}")

        query_words = set(query.lower().split())
        matching_documents = []

        for page in all_pages:
            props = page.get("properties", {})
            logger.debug(f"Properties for page {page.get('id')}: {props.keys()}")

            # Question (title)
            question = ""
            q_prop = props.get("question", {})
            if q_prop and q_prop.get("type") == "title":
                question = _plain_text_from_rich(q_prop.get("title", []))

            # Answer
            answer = ""
            a_prop = props.get("answer", {})
            if a_prop and a_prop.get("type") == "rich_text":
                answer = _plain_text_from_rich(a_prop.get("rich_text", []))

            # Department (select)
            department = "Unknown"
            dept_prop = props.get("department", {})
            if dept_prop and dept_prop.get("type") == "select":
                sel = dept_prop.get("select")
                if sel:
                    department = sel.get("name", "Unknown")

            # Tags (multi_select)
            tags = []
            tags_prop = props.get("tags", {})
            if tags_prop and tags_prop.get("type") == "multi_select":
                tags = [t.get("name") for t in tags_prop.get("multi_select", [])]

            # Matching score
            all_words = set((question + " " + answer).lower().split())
            matches = len(query_words.intersection(all_words))
            match_ratio = matches / len(query_words) if query_words else 0.0

            if match_ratio >= float(threshold):
                content = f"Q: {question}\nA: {answer}"
                if tags:
                    content += f"\nTags: {', '.join(tags)}"
                matching_documents.append({
                    "content": content,
                    "meta_data": {
                        "source": "Notion",
                        "department": department,
                        "tags": tags,
                        "match_score": match_ratio,
                        "page_id": page.get("id")
                    }
                })

        matching_documents.sort(key=lambda x: x["meta_data"]["match_score"], reverse=True)

        if not matching_documents:
            return [{"content": "No matching entry found in the knowledge base.", "meta_data": {"source": "Notion"}}]

        return matching_documents[:num_documents] if num_documents else matching_documents

    except Exception as e:
        logger.exception("Error in return_knowledge_base")
        return [{"content": f"Error: {str(e)}", "meta_data": {"source": "Error"}}]
