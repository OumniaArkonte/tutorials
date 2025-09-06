import os
import pandas as pd
from pypdf import PdfReader
from dotenv import load_dotenv
from textwrap import dedent
import json

# === Arize & Instrumentation ===
from arize.otel import register
from openinference.instrumentation.agno import AgnoInstrumentor

# === Agno Agent avec Mistral ===
from agno.agent import Agent
from agno.models.mistral import MistralChat

# Charger .env
load_dotenv()

# ======================
# 1. Charger le PDF
# ======================
pdf_path = "UK_Agriculture_Report.pdf"
reader = PdfReader(pdf_path)
pdf_text = "\n".join([page.extract_text() for page in reader.pages])

# ======================
# 2. Configurer tracing Arize
# ======================
tracer_provider = register(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    api_key=os.getenv("ARIZE_API_KEY"),
    project_name="uk-agriculture-agent",
)
AgnoInstrumentor().instrument(tracer_provider=tracer_provider)

# ======================
# 3. Créer l’agent principal (analyseur)
# ======================
agent = Agent(
    model=MistralChat(id="mistral-medium"),
    description=dedent("""\
        You are a senior agricultural policy analyst. 
        Analyse UK farming policies and their impacts on communities.
    """),
    expected_output=dedent("""\
        # UK Agricultural Policy Analysis 

        ## Executive Summary
        {Overview of the current agricultural landscape and key challenges}

        ## Key Findings
        - **Economic Impacts:** {...}
        - **Environmental Outcomes:** {...}
        - **Social & Rural Development:** {...}

        ## Recommendations
        1. **Immediate Actions:** {...}
        2. **Mid-term Strategy:** {...}
        3. **Long-term Vision:** {...}
    """),
    markdown=True,
)

# ======================
# 4. Run l’agent
# ======================
user_input = "Analyse ce rapport et donne les implications pour les communautés agricoles au Royaume-Uni."
context = f"Voici le contenu du rapport officiel DEFRA:\n\n{pdf_text[:4000]}..."

print("=== AGENT OUTPUT ===")
response = agent.run(f"{user_input}\n\n{context}")
actual_output = str(response)
print(actual_output)

# ======================
# 5. Préparer DataFrame
# ======================
df = pd.DataFrame({
    "input": [user_input],
    "actual_output": [actual_output],
    "expected_output": [agent.expected_output]
})

# Nettoyer les noms de colonnes
df.columns = [c.strip() for c in df.columns]

# ======================
# 6. Définir le template d’évaluation
# ======================
ROUTER_EVAL_TEMPLATE = """
You are a helpful AI evaluator.
Your task is to check if the policy analysis is impactful for UK farming communities.

Here is the data:

[Input]: {input}

[Actual Output]: {actual_output}

[Expected Output]: {expected_output}

Your response must follow this JSON format only:
{{
  "label": "impactful" | "not impactful",
  "explanation": "your reasoning here"
}}
"""

# ======================
# 7. Fonction d’évaluation avec Mistral
# ======================
def mistral_classify(row):
    eval_agent = Agent(
        model=MistralChat(id="mistral-medium"),
        description="You are an evaluator of policy analysis.",
    )
    prompt = ROUTER_EVAL_TEMPLATE.format(
        input=row["input"],
        actual_output=row["actual_output"],
        expected_output=row["expected_output"]
    )

    # Debug : afficher le prompt
    print("\n--- PROMPT ---\n", prompt)

    result_text = eval_agent.run(prompt)

    # Debug : afficher le résultat brut
    print("\n--- RESULT ---\n", result_text)

    # Convertir en dict Python de manière sécurisée
    try:
        # Extraire JSON contenu dans le texte
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        json_str = result_text[start:end]
        result_dict = json.loads(json_str)
    except Exception as e:
        print("Erreur lors de la conversion JSON :", e)
        result_dict = {"label": "error", "explanation": str(result_text)}

    return result_dict

# ======================
# 8. Lancer l’évaluation
# ======================
print("\n=== EVALUATION RESULTS (Mistral) ===")
df["eval_result"] = df.apply(mistral_classify, axis=1)

for r in df["eval_result"]:
    print(r)

df.to_csv("policy_analysis_eval_mistral.csv", index=False)
print("\nRésultats sauvegardés dans 'policy_analysis_eval_mistral.csv'")
