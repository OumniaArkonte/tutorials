import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

# ---------------- CONFIG ----------------
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_model = Gemini(id="gemini-2.0-flash", api_key=gemini_api_key)

# Créer l’agent AI
compliance_agent = Agent(
    model=gemini_model,
    name="Compliance Agent",
    instructions="""
Tu es un expert en conformité réglementaire.
Analyse les mises à jour fournies et produis un résumé structuré avec les sections suivantes :
1. Nouvelles obligations
2. Impacts sur les processus existants
3. Ressources nécessaires
4. Calendrier de mise en conformité
5. Risques de non-conformité
6. Formation et sensibilisation
7. Suivi et surveillance
"""
)

# ---------------- DONNÉES STATIQUES ----------------
def get_static_updates():
    updates = [
        {
            "title": "Nouvelle directive sur la protection des données personnelles",
            "link": "https://www.exemple.com/news/data-protection",
            "content": "Cette directive impose de nouvelles obligations pour la collecte et le traitement des données clients."
        },
        {
            "title": "Mise à jour des règles de conformité financière",
            "link": "https://www.exemple.com/news/financial-compliance",
            "content": "Les institutions financières doivent adapter leurs processus internes pour respecter ces nouvelles règles."
        },
        {
            "title": "Publication des lignes directrices sur la gestion des risques",
            "link": "https://www.exemple.com/news/risk-management",
            "content": "Ces lignes directrices recommandent la mise en place de mécanismes de suivi et de reporting renforcés."
        }
    ]

    print(f" Debug : {len(updates)} articles prêts pour l'analyse")
    for u in updates:
        print("-", u["title"])

    return updates

# ---------------- ANALYSE ----------------
def analyze_updates(updates):
    text = "Voici les mises à jour réglementaires pour analyse :\n\n"
    for i, u in enumerate(updates, 1):
        text += f"{i}. {u['title']} ({u['link']})\n{u['content']}\n\n"

    text += (
        "Analyse les impacts pour le département compliance et structure la réponse "
        "avec ces sections clairement séparées :\n"
        "## Nouvelles obligations\n"
        "## Impacts sur les processus existants\n"
        "## Ressources nécessaires\n"
        "## Calendrier de mise en conformité\n"
        "## Risques de non-conformité\n"
        "## Formation et sensibilisation\n"
        "## Suivi et surveillance\n"
    )

    response = compliance_agent.run(text)
    return response.content

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print(" Récupération des updates (statique pour la démo)...")
    updates = get_static_updates()
    print(f" Updates récupérées : {len(updates)}\n")

    print(" Analyse AI en cours...\n")
    analysis = analyze_updates(updates)

    print(" Résultat de l’analyse :\n")
    print(analysis)
