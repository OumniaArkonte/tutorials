import os
from exa_py import Exa
from textwrap import dedent
from typing import Iterator
from dotenv import load_dotenv
from agno.workflow import Workflow
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini
from agno.utils.pprint import pprint_run_response
import time

# Charger les variables d'environnement
load_dotenv()
exa_api_key = os.environ.get("EXA_API_KEY")
gemini_api_key = os.environ.get("GEMINI_API_KEY")

exa = Exa(api_key=exa_api_key)


# === Agent 1 : Market Research (données concurrentielles) ===
def exa_market_research(product: str):
    """
    Utilise Exa pour trouver 3 concurrents du produit donné.
    Renvoie une description structurée en markdown.
    """
    try:
        # Crée la tâche de recherche
        task_stub = exa.research.create_task(
            instructions=f"""
            You are a market research assistant.
            Find 3 competitors for the product: {product}.
            For each competitor, return:
            - Product Name
            - Price
            - Short description
            - 3 negative customer reviews (real product complaints)
            Present results in clean markdown.
            """,
            model="exa-research",
            output_infer_schema=False
        )

        # Polling jusqu'à ce que la tâche soit terminée
        task = exa.research.get_task(task_stub.id)
        while task.status not in ("completed", "failed"):
            time.sleep(2)
            task = exa.research.get_task(task_stub.id)

        if task.status == "completed":
            return task.data  # données brutes ou format Markdown
        else:
            raise RuntimeError(f"Research task failed: {task.status}")

    except AttributeError:
        # Fallback si create_task n’existe pas
        query = f"Top 3 competitors for {product} with price, description, 3 negative reviews each."
        sr = exa.search_and_contents(query, num_results=5, text=True)
        summary = f"Here are some competitor results for {product}:\n"
        for r in sr.results[:3]:
            title = getattr(r, "title", "No title")
            content = getattr(r, "text", "")
            url = getattr(r, "url", "")
            summary += f"- **{title}** ({url}): {content[:200]}...\n"
        return summary


# === Agent 2 : Pricing Strategist (Gemini) ===
class PredictivePricingWorkflow(Workflow):
    pricing_agent: Agent = Agent(
        name="Predictive Pricing Agent",
        model=Gemini(id="gemini-1.5-flash", api_key=gemini_api_key),
        instructions=dedent("""
            You are an AI pricing strategist.
            You will receive competitor research data.

            Your tasks:
            1. Analyze competitor prices and positioning (budget / midrange / premium).
            2. Identify common customer complaints from negative reviews.
            3. Predict an optimal price range for the new product to maximize profit while being competitive.
            4. Justify your recommended price range using competitor prices, positioning, and customer pain points.
            5. Suggest 2–3 tactical recommendations to differentiate our product (e.g., bundles, feature improvements, promotions).
        """),
        expected_output=dedent("""
            Return your output in this markdown format:

            ---

            ## ^^^ Recommended Price Range
            **Range**: `$XX – $YY`  
            **Tier**: _Budget / Midrange / Premium_

            ---

            ## ^^^ Competitor Analysis
            - **[Competitor Name]** – `$XX.XX`: _Short comparison note_  
            - Bad Reviews:  
                1. "..."  
                2. "..."  
                3. "..."

            ---

            ## ^^^ Rationale
            _Explain why this price range fits the market._

            ---

            ## ^^^ Tactical Recommendations
            - **[Recommendation 1]**
            - **[Recommendation 2]**
            - **[Recommendation 3]**
        """),
        markdown=True,
    )

    def run(self, product: str):
        research = exa_market_research(product)
        print("=== MARKET RESEARCH DATA ===")
        print(research)
        print("============================")
        yield from self.pricing_agent.run(research, stream=True)


if __name__ == "__main__":
    from rich.prompt import Prompt

    product = Prompt.ask("Enter your product name")
    if product:
        workflow = PredictivePricingWorkflow()
        response: Iterator[RunResponse] = workflow.run(product=product)
        pprint_run_response(response, markdown=True)
