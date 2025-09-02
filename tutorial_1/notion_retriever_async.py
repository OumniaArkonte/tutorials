import asyncio
from typing import Optional, List, Dict
from notion_retriever_sync import return_knowledge_base as sync_retriever

async def return_knowledge_base_async(agent, query: str, num_documents: Optional[int] = None, threshold: float = 0.6, **kwargs) -> Optional[List[Dict]]:
    
    def sync_call():
        return sync_retriever(agent, query, num_documents=num_documents, threshold=threshold, **kwargs)
    return await asyncio.to_thread(sync_call)
