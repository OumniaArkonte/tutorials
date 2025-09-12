import os
import requests
import logging
from fastapi.responses import JSONResponse
from agent_service import process_user_message as get_response


WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
VERSION = os.getenv('VERSION')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')

def send_message(recipient, text):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": text}
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.json()
    except Exception as e:
        logging.error(e)
        return {"status": "error"}

def process_whatsapp_message(body: dict):
    value = body["entry"][0]["changes"][0]["value"]
    wa_id = value["contacts"][0]["wa_id"]  # identifiant unique user
    message = value["messages"][0]

    if message["type"] == "text":
        user_input = message["text"]["body"]
    elif message["type"] == "image":
        # Téléchargement de l’image
        img_id = message["image"]["id"]
        url = f"https://graph.facebook.com/{VERSION}/{img_id}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
        meta = requests.get(url, headers=headers).json()
        file_url = meta["url"]
        img_data = requests.get(file_url, headers=headers).content
        file_path = f"images/{img_id}.jpg"
        with open(file_path, "wb") as f:
            f.write(img_data)
        user_input = {"file_path": file_path, "media_type": "image/jpeg",
                      "caption": message["image"].get("caption", "")}
    else:
        user_input = "Unsupported message type"

    # Passer au LLM avec mémoire
    response_text = get_response(wa_id, user_input)

    # Envoyer la réponse à WhatsApp
    send_message(wa_id, response_text)
