import os
import json
import csv
from typing import List

from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

from exa_py import Exa
from agent_service import process_user_message as get_response  

# ============================
# CONFIGURATION
# ============================
EXA_API_KEY = os.getenv("EXA_API_KEY")
if not EXA_API_KEY:
    raise ValueError(" Veuillez définir EXA_API_KEY dans .env")

exa = Exa(EXA_API_KEY)
app = FastAPI()

CSV_FILE = "data.csv"


# ============================
# 1. RECHERCHE FOURNISSEURS AVEC EXA
# ============================
def exa_search(product_list: List[str], location: str) -> str:
    """
    Utilise Exa pour rechercher les meilleurs vendeurs pour chaque produit.
    Retourne un rapport brut en Markdown.
    """
    query = f"Trouve les meilleurs vendeurs pour {', '.join(product_list)} à {location}."

    response = exa.research(
        query=query,
        text=f"""
        Objectif : fournir une analyse détaillée des vendeurs.
        Pour chaque produit :
        - Nom du vendeur
        - Prix
        - Site
        - Description
        - Livraison
        - Quantité minimum (MOQ)
        - Réductions disponibles
        Format : tableau Markdown.
        """,
        num_results=5,
        type="neural",
        include_domains=["amazon.com", "alibaba.com", "ebay.com", "walmart.com"],
        exclude_domains=["linkedin.com", "facebook.com"],
    )

    markdown = response.results[0].text if response.results else "Aucun résultat trouvé."
    return markdown


# ============================
# 2. TRAITEMENT DES RESULTATS
# ============================
def process_results(markdown: str) -> dict:
    """
    Demande à GPT de transformer le Markdown en JSON structuré.
    """
    instruction = f"""
    Voici un tableau en Markdown listant des vendeurs.
    Transforme-le en JSON structuré avec le format :
    {{
      "data": [
        {{
          "product": "...",
          "vendor": "...",
          "price": "...",
          "website": "...",
          "description": "...",
          "delivery": "...",
          "MOQ": "...",
          "discounts": "..."
        }}
      ]
    }}
    """

    structured = get_response(instruction + "\n\n" + markdown)
    try:
        parsed = json.loads(structured)
        return parsed
    except Exception:
        return {"data": []}


def save_csv(data: List[dict]):
    """
    Sauvegarde les données JSON dans un fichier CSV.
    """
    if not data:
        return

    headers = ["product", "vendor", "price", "website", "description", "delivery", "MOQ", "discounts"]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


# ============================
# 3. API FASTAPI
# ============================
@app.post("/procure")
async def procure(product_list: List[str], location: str):
    # Étape 1 : recherche Exa
    markdown = exa_search(product_list, location)

    # Étape 2 : structuration
    structured = process_results(markdown)

    # Étape 3 : sauvegarde CSV
    save_csv(structured.get("data", []))

    return {"markdown": markdown, "csv_available": True}


@app.get("/csv")
async def get_csv():
    return FileResponse(CSV_FILE, media_type="text/csv", filename="data.csv")


# ============================
# 4. MODE STANDALONE
# ============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
