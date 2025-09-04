import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from pyairtable import Api
from bs4 import BeautifulSoup
import re

# Charger le fichier .env
load_dotenv()

# Clés depuis .env
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

# Vérifier que les clés sont bien lues
if not all([FIRECRAWL_API_KEY, AIRTABLE_API_KEY, BASE_ID, TABLE_NAME]):
    raise ValueError("Une ou plusieurs clés API ne sont pas définies dans .env")

# Initialisation Firecrawl et Airtable
fc = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
api = Api(AIRTABLE_API_KEY)
table = api.table(BASE_ID, TABLE_NAME)

# Liste des concurrents
COMPETITOR_SITES = {
    "Nike": "https://www.nike.com/t/air-jordan-4-retro-cave-stone-and-black-mens-shoes-bH4bzP2d/FV5029-200",
    "IKEA Billy Bookcase": "https://www.ikea.com/us/en/p/vaelgrundad-bottom-freezer-refrigerator-stainless-steel-70462158/"
}

def extract_fields(html_text):
    """Extraire le nom et le prix d’un produit depuis le HTML"""
    soup = BeautifulSoup(html_text, "html.parser")

    # Récupérer le nom
    name_tag = soup.select_one("h1")
    name = name_tag.get_text(strip=True) if name_tag else "Nom non trouvé"

    # Récupérer le prix via regex
    text = soup.get_text(" ", strip=True)
    price_match = re.search(r"\$\d+\.?\d*", text)
    price_text = price_match.group() if price_match else "Prix non trouvé"

    # Convertir en float si possible
    try:
        price = float(price_text.replace("$", ""))
    except ValueError:
        price = None

    return {
        "Product Name": name,
        "Price Text": price_text,
        "Price": price
    }

def main():
    for comp, url in COMPETITOR_SITES.items():
        print(f"\nScraping {comp}...")
        try:
            # Scraper le HTML avec Firecrawl
            result = fc.scrape(url=url, formats=["html"])
        except Exception as e:
            print(f"[ERREUR] Firecrawl pour {comp}: {e}")
            continue  # passer au concurrent suivant

        if hasattr(result, "html") and result.html:
            data = extract_fields(result.html)
            record = {
                "Competitor": comp,
                "Product Name": data["Product Name"],
                "Price": data["Price"],
                "Price Text": data["Price Text"],
                "URL": url
            }
            print("Envoi vers Airtable:", record)
            try:
                table.create(record)
                print(f"[OK] Données envoyées pour {comp}")
            except Exception as e:
                print(f"[ERREUR] Airtable pour {comp}: {e}")
        else:
            print(f"[INFO] Aucune donnée HTML extraite pour {comp}")

if __name__ == "__main__":
    main()
