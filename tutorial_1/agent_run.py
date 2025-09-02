import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from notion_retriever_sync import return_knowledge_base
from notion_retriever_async import return_knowledge_base_async
import asyncio

load_dotenv()

def run_sync():
    agent = Agent(
        model=Gemini(id="gemini-1.5-flash"),
        knowledge=None,
        search_knowledge=False  
    )

    prompt = input("Enter Your Prompt: ")

    docs = return_knowledge_base(agent, prompt, threshold=0.1)
    
    # On concatène les contenus trouvés pour enrichir le prompt
    knowledge_context = "\n\n".join([doc["content"] for doc in docs])
    enriched_prompt = f"Voici des informations extraites de la base de connaissances:\n{knowledge_context}\n\nQuestion: {prompt}\nRéponse:"

    agent.print_response(enriched_prompt)


async def run_async():
    agent = Agent(
        model=Gemini(id="gemini-1.5-pro"),
        knowledge=None,
        search_knowledge=False
    )

    prompt = input("Enter Your Prompt: ")

    docs = await return_knowledge_base_async(agent, prompt, threshold=0.1)
    knowledge_context = "\n\n".join([doc["content"] for doc in docs])
    enriched_prompt = f"Voici des informations extraites de la base de connaissances:\n{knowledge_context}\n\nQuestion: {prompt}\nRéponse:"

    await agent.aprint_response(enriched_prompt)


if __name__ == "__main__":
    mode = os.getenv("MODE", "sync")
    if mode == "async":
        asyncio.run(run_async())
    else:
        run_sync()
