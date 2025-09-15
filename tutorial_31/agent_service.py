import os
from dotenv import load_dotenv
from agno.models.google import Gemini

# Charger les variables depuis .env
load_dotenv()

# Création du client Gemini avec ta clé API
gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"))


def process_user_message(prompt: str) -> str:
    """
    Envoie une requête à Gemini ("gemini-1.5-flash").
    Retourne uniquement le texte de réponse.
    """
    try:
        response = gemini.chat(
            model="gemini-1.5-flash",
            messages=[
                {"role": "system", "content": "You are a helpful AI procurement assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.output_text  # la réponse textuelle
    except Exception as e:
        return f"⚠️ Erreur Gemini: {e}"
