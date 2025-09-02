import assemblyai as aai
from dotenv import load_dotenv
import os

load_dotenv()

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

if not aai.settings.api_key:
    raise ValueError("API Key AssemblyAI introuvable ! Vérifie ton fichier .env")


audio_file = "https://assembly.ai/wildfires.mp3"

config = aai.TranscriptionConfig(
    speech_model=aai.SpeechModel.best,
    sentiment_analysis=True
)

# Transcrire et analyser
transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe(audio_file)


if transcript.status == "error":
    raise RuntimeError(f"Transcription échouée : {transcript.error}")

print("\n--- Texte transcrit ---")
print(transcript.text)

# Afficher les résultats de sentiment analysis
print("\n--- Analyse des sentiments ---")
for sentiment in transcript.sentiment_analysis:
    print(
        f"[{sentiment.start/1000:.2f}s - {sentiment.end/1000:.2f}s] "
        f"({sentiment.sentiment.upper()}) → {sentiment.text}"
    )
