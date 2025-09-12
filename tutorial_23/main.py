import os
import uvicorn
import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from whatsapp_utils import process_whatsapp_message

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AI Companion API running!"}

# Vérification webhook
@app.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    mode, token, challenge = params.get("hub.mode"), params.get("hub.verify_token"), params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return JSONResponse(status_code=403, content={"error": "Verification failed"})

# Réception des messages
@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        process_whatsapp_message(body)
        return {"status": "ok"}
    except Exception as e:
        logging.error(e)
        return {"status": "error"}

        

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
