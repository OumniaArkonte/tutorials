import os
import time
import faiss
import numpy as np
from mistralai import Mistral
from dotenv import load_dotenv  

load_dotenv()  


# ---------------- CONFIG ----------------
PDF_PATH = "pdf/light-duty-vehicules.pdf"
INDEX_PATH = "legal_index.faiss"
CHUNK_SIZE = 1500    
CHUNK_OVERLAP = 200  
TOP_K = 3           

# Init Mistral client
api_key = os.environ["MISTRAL_API_KEY"]
client = Mistral(api_key=api_key)


# -----------  OCR DU PDF -----------
def ocr_pdf():
    uploaded_pdf = client.files.upload(
        file={"file_name": os.path.basename(PDF_PATH), "content": open(PDF_PATH, "rb")},
        purpose="ocr"
    )
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    print(" OCR en cours...")
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": signed_url.url},
        include_image_base64=False
    )
    print(" OCR terminé")

    text_pages = [page.markdown for page in ocr_response.pages]
    return "\n\n".join(text_pages)


# -----------  CHUNKING -----------
def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        chunks.append(chunk)
        start += size - overlap
    return chunks


# -----------  EMBEDDINGS -----------
def get_embedding(input_text):
    resp = client.embeddings.create(model="mistral-embed", inputs=input_text)
    return resp.data[0].embedding


# -----------  CHAT COMPLETION -----------
def run_mistral(prompt, model="mistral-small-latest"):
    messages = [{"role": "system", "content": "You are a legal assistant. Answer only with the given CONTEXT."},
                {"role": "user", "content": prompt}]
    resp = client.chat.complete(model=model, messages=messages)
    return resp.choices[0].message.content


# -----------  MAIN PIPELINE -----------
def main():
    #  OCR du PDF
    text = ocr_pdf()

    # Chunking
    chunks = chunk_text(text)
    print(f" {len(chunks)} morceaux créés")

    #  Embeddings des chunks
    embeddings = []
    for chunk in chunks:
        emb = get_embedding(chunk)
        embeddings.append(emb)
        time.sleep(1)  # éviter le rate limit
    embeddings = np.array(embeddings).astype("float32")

    # Indexation FAISS
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    print(" Index vectoriel construit")

    # Question utilisateur
    question = input("\n   Pose ta question ?: ")
    q_emb = np.array([get_embedding(question)]).astype("float32")
    D, I = index.search(q_emb, k=TOP_K)
    retrieved = [chunks[i] for i in I[0]]

    # Construction du prompt
    context = "\n\n".join(retrieved)
    prompt = f"""
    CONTEXT:
    -----------------
    {context}
    -----------------
    Question: {question}
    Réponds uniquement avec le contexte ci-dessus (citer page si possible).
    """

    response = run_mistral(prompt)
    print("\n Réponse du Legal Co-Pilot:\n")
    print(response)


if __name__ == "__main__":
    main()
