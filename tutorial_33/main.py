import os
import logging
from threading import Thread
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
import requests
import re
import sqlite3
import base64
from googlesearch import search  

load_dotenv()

# --- Variables d'environnement ---
VERSION = os.getenv("VERSION", "v20.0")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# --- FastAPI app ---
app = FastAPI()
logging.basicConfig(level=logging.INFO)
DB_FILE = "logistics.db"  # SQLite DB avec tarifs

# ----------------------------
# --- WhatsApp Helper ---
# ----------------------------
def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        logging.info(f" Sent message to {to}: {message}")
    except Exception as e:
        logging.error(f" Error sending message: {e}")

# ----------------------------
# --- Agent 1 : Service Agent ---
# ----------------------------
def extract_specs_from_text(text):
    """Extrait transporteur et poids depuis le texte"""
    text = text.strip()
    match = re.match(r"^(DHL|UPS|FedEx),\s*(\d+(\.\d+)?)kg$", text, re.IGNORECASE)
    if match:
        return {
            "carrier": match.group(1).capitalize(),
            "weight": float(match.group(2))
        }
    return None

def process_service_agent_text(text):
    """Agent 1 : traitement texte"""
    specs = extract_specs_from_text(text)
    if not specs:
        return None, " Format incorrect. Utilise : Transporteur, Poidskg (ex: DHL, 3kg)"
    return specs, None

def process_service_agent_image(image_url):
    """Agent 1 : traitement image avec OCR Mistral AI"""
    try:
        response = requests.get(image_url)
        image_bytes = response.content
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Appel Mistral AI OCR
        ocr_response = requests.post(
            "https://api.mistral.ai/ocr",
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
            json={"image_base64": image_base64}
        )
        result = ocr_response.json()
        text = result.get("text", "")

        specs = extract_specs_from_text(text)
        if not specs:
            return None, " Impossible d'extraire les spécifications depuis l'image"
        return specs, None
    except Exception as e:
        logging.error(f" Error processing image OCR: {e}")
        return None, " Une erreur est survenue lors du traitement de l'image"

# ----------------------------
# --- Agent 2 : Freight Agent ---
# ----------------------------
def get_price_from_db(carrier: str, weight: float):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT price FROM prices WHERE carrier=? AND max_weight>=? ORDER BY max_weight ASC LIMIT 1",
            (carrier, weight)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logging.error(f" Error accessing DB: {e}")
        return None

def get_price_from_google(carrier, weight):
    """Recherche Google pour trouver un prix approximatif"""
    query = f"{carrier} shipping cost {weight}kg"
    try:
        for url in search(query, num_results=3):
            # Ici on peut parser le site pour extraire le prix réel
            # Pour l'exemple, on retourne un prix fictif
            if carrier == "DHL": return 25.0
            if carrier == "UPS": return 28.0
            if carrier == "FedEx": return 45.0
    except Exception as e:
        logging.error(f" Error fetching price from Google: {e}")
    return None

def process_freight_agent(specs):
    """Agent 2 : recherche tarif et comparatif multi-sources"""
    carriers = ["DHL", "UPS", "FedEx"]
    prices = {}
    for c in carriers:
        price = get_price_from_db(c, specs["weight"])
        if price is None:
            price = get_price_from_google(c, specs["weight"])
        if price is not None:
            prices[c] = price

    if not prices:
        return f" Désolé, pas de tarif trouvé pour {specs['carrier']} avec {specs['weight']}kg."
    
    best_carrier = min(prices, key=prices.get)
    message = f" Meilleur tarif : {best_carrier} {prices[best_carrier]}€ pour {specs['weight']}kg\n"
    message += "Comparatif : " + ", ".join([f"{c} {p}€" for c, p in prices.items()])
    return message

# ----------------------------
# --- Traitement Message WhatsApp ---
# ----------------------------
def process_whatsapp_message(from_number, text=None, image_url=None):
    text = (text or "").strip()

    # --- Salutations ---
    if text.lower() in ["bonjour", "salut", "hello", "hi"]:
        send_whatsapp_message(
            from_number,
            " ^^ Bonjour ! Je suis ton assistant logistique IA. "
            "Demande-moi un tarif en utilisant : Transporteur, Poidskg (ex: DHL, 3kg) 📦."
        )
        return

    # Agent 1 : récupérer specs
    if image_url:
        specs, err_msg = process_service_agent_image(image_url)
    else:
        specs, err_msg = process_service_agent_text(text)

    if err_msg:
        send_whatsapp_message(from_number, err_msg)
        return
    
    # Agent 2 : calcul tarif optimal
    response_message = process_freight_agent(specs)
    send_whatsapp_message(from_number, response_message)

# ----------------------------
# --- Routes FastAPI ---
# ----------------------------
@app.get("/")
async def read_root():
    return {"message": "Welcome to the WhatsApp logistics portal!"}

@app.get("/webhook")
async def webhook_verify(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logging.info("WEBHOOK_VERIFIED")
            return PlainTextResponse(content=challenge or "VERIFIED", status_code=200)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    raise HTTPException(status_code=400, detail="Missing parameters")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        logging.info(f"Incoming webhook body: {body}")
    except Exception:
        logging.exception("Invalid JSON")
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid JSON"})

    # Status update (delivery/read)
    if body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("statuses"):
        logging.info("Received a WhatsApp status update.")
        return JSONResponse(content={"status": "ok"})

    # Message utilisateur
    try:
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        text = message.get("text", {}).get("body")
        image_url = message.get("image", {}).get("url")
        logging.info(f" Message reçu de {from_number} : {text or 'image'}")

        Thread(target=process_whatsapp_message, args=(from_number, text, image_url), daemon=True).start()
    except Exception as e:
        logging.warning(f"Webhook received but not a user message: {e}")
        return JSONResponse(status_code=200, content={"status": "ignored"})

    return JSONResponse(content={"status": "ok"})

# ----------------------------
# --- Test Endpoint ---
# ----------------------------
@app.get("/test")
def test():
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": RECIPIENT_PHONE_NUMBER,
        "type": "template",
        "template": {"name": "hello_world", "language": {"code": "en_US"}},
    }
    response = requests.post(url, headers=headers, json=data, timeout=10)
    return {"message": "Test sent", "status_code": response.status_code, "response": response.json()}

# ----------------------------
# --- Run Server ---
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
