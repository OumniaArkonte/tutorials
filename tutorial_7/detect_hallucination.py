import os
import asyncio
import pandas as pd
from uqlm import BlackBoxUQ
from langchain_google_genai import ChatGoogleGenerativeAI
from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()

async def run_svamp_detection(n_prompts: int = 5, threshold: float = 0.5, model_name: str = "gemini-2.0-flash"):
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key is None:
        raise RuntimeError("GOOGLE_API_KEY introuvable dans l’environnement.")

    # Initialiser le modèle Gemini (température = 0 pour des réponses déterministes)
    llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_api_key, temperature=0)

    # Charger un sous-ensemble du dataset SVAMP
    ds = load_dataset("ChilleD/SVAMP", split=f"test[:{n_prompts}]")
    df = pd.DataFrame(ds)
    df.columns = [c.lower() for c in df.columns]

    if "question" not in df.columns:
        raise RuntimeError(f"Colonne 'question' introuvable. Colonnes dispo : {df.columns.tolist()}")

    prompts = df["question"].astype(str).tolist()

    # BlackBoxUQ
    uq = BlackBoxUQ(llm=llm)

    # Générer et scorer
    results = await uq.generate_and_score(prompts=prompts, num_responses=1)
    results_df = results.to_df()

    # Supprimer les colonnes inutiles
    results_df = results_df.drop(columns=["sampled_responses"], errors="ignore")

    print("Colonnes disponibles après nettoyage :", results_df.columns.tolist())

    # Utiliser semantic_negentropy comme métrique principale
    score_col = "semantic_negentropy"
    if score_col not in results_df.columns:
        raise RuntimeError(f"La colonne '{score_col}' n’existe pas. Colonnes : {results_df.columns.tolist()}")

    # Détection d’hallucination : plus bas score = plus d’incertitude
    results_df["hallucination_flag"] = results_df[score_col] < threshold

    # DataFrame final
    final_df = results_df[["prompt", "response", score_col, "hallucination_flag"]]

    print("\n--- Résultats ---")
    print(final_df)

    # Sauvegarde
    final_df.to_csv("svamp_hallucination_results.csv", index=False, encoding="utf-8")
    try:
        final_df.to_excel("svamp_hallucination_results.xlsx", index=False)
    except Exception:
        print("(Excel non sauvegardé — dépendance manquante)")

    print("\nSauvegardé : svamp_hallucination_results.csv (+ xlsx si possible)")

    return final_df


if __name__ == "__main__":
    asyncio.run(run_svamp_detection(n_prompts=5, threshold=0.5))
