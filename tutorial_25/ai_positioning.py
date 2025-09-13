import os
from textwrap import dedent
from typing import Iterator
from dotenv import load_dotenv
from agno.workflow import Workflow
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini
from agno.utils.pprint import pprint_run_response
from openai import OpenAI

load_dotenv()

# Clé API Exa dans .env
exa_api_key = os.environ.get("EXA_API_KEY")
gemini_api_key = os.environ.get("GEMINI_API_KEY")

# Fonction de recherche de concurrents via Exa
def exa_market_research(product_idea: str) -> str:
    client = OpenAI(
        base_url="https://api.exa.ai",
        api_key=exa_api_key
    )

    prompt = dedent(f"""
        You are an expert in market research and competitor analysis.
        Find 3-5 competitor products similar to: {product_idea}.
        For each competitor, return:
        - Product Name
        - Price
        - Short Description
        - 3 negative reviews highlighting real customer complaints
        Present the output in clear, structured markdown.
    """)

    completion = client.chat.completions.create(
        model="exa-research",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    full_content = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            full_content += chunk.choices[0].delta.content

    return full_content


# Workflow pour le Product Positioning
class AIProductPositioning(Workflow):
    positioning_agent: Agent = Agent(
        name="Product Positioning Strategist",
        model=Gemini(id="gemini-1.5-flash"),
        instructions=dedent("""
            You are a product positioning and market strategy expert.

            You receive structured competitor market data, including:
            - Competitor Name
            - Price
            - Short Description
            - 3 negative reviews

            Your tasks:
            1. Analyze competitors and identify market gaps.
            2. Suggest the perfect positioning for the new product (Budget, Midrange, Premium).
            3. Give 2-4 tactical recommendations to improve the product and stand out.
            4. Output should be in Markdown.
        """),
        markdown=True
    )

    def run(self) -> Iterator[RunResponse]:
        research_data = exa_market_research(self.product_idea)
        print("=== MARKET RESEARCH DATA ===")
        print(research_data)
        print("============================")
        yield from self.positioning_agent.run(research_data, stream=True)




if __name__ == "__main__":
    from rich.prompt import Prompt

    product_idea = Prompt.ask("Enter your product idea")
    if product_idea:
        workflow = AIProductPositioning()
        # On définit l'attribut product_idea
        workflow.product_idea = product_idea
        # Exécution du workflow
        response: Iterator[RunResponse] = workflow.run()
        pprint_run_response(response, markdown=True)


