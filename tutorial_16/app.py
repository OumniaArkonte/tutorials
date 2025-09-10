from flask import Flask, request
import requests
import os
import sqlite3

app = Flask(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def init_db():
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            done BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET"])
def home():
    return "Webhook WhatsApp + Gemini + TodoList (SQLite) "

@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        verify_token = "Whatssap123Oum" 
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode and token and token == verify_token:
            return challenge
        return "Erreur vérification", 403

    if request.method == "POST":
        data = request.json
        try:
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
            from_number = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

            #  Vérifier si c’est une commande TodoList
            response = handle_todo_command(message)

            if not response:
                # Si ce n’est pas une commande TodoList → passer par Gemini
                response = call_gemini(message)

            # Envoyer la réponse sur WhatsApp
            send_whatsapp_message(from_number, response)

        except Exception as e:
            print("Erreur:", e)

        return "OK", 200

# ---  Gestion TodoList avec SQLite ---
def handle_todo_command(text):
    text = text.strip().lower()

    if text.startswith("add "):
        task = text[4:].strip()
        add_task(task)
        return f" Tâche ajoutée : {task}"

    elif text == "list":
        tasks = get_tasks()
        if not tasks:
            return " Aucune tâche pour l’instant."
        result = " Ta TodoList :\n"
        for i, (task_id, task, done) in enumerate(tasks, 1):
            status = "terminé" if done else "not"
            result += f"{i}. {task} {status}\n"
        return result

    elif text.startswith("done "):
        try:
            index = int(text.split()[1]) - 1
            tasks = get_tasks()
            if 0 <= index < len(tasks):
                task_id = tasks[index][0]
                mark_task_done(task_id)
                return f" Tâche terminée : {tasks[index][1]}"
            else:
                return " Numéro de tâche invalide."
        except:
            return " Utilise : done <numéro>"

    elif text.startswith("update "):
        try:
            parts = text.split(" ", 2)
            index = int(parts[1]) - 1
            new_task = parts[2]
            tasks = get_tasks()
            if 0 <= index < len(tasks):
                task_id = tasks[index][0]
                update_task(task_id, new_task)
                return f" Tâche modifiée : {new_task}"
            else:
                return " Numéro de tâche invalide."
        except:
            return " Utilise : update <numéro> <nouvelle tâche>"

    elif text.startswith("delete "):
        try:
            index = int(text.split()[1]) - 1
            tasks = get_tasks()
            if 0 <= index < len(tasks):
                task_id = tasks[index][0]
                delete_task(task_id)
                return f" Tâche supprimée : {tasks[index][1]}"
            else:
                return " Numéro de tâche invalide."
        except:
            return " Utilise : delete <numéro>"

    return None

# ---  Fonctions SQLite ---
def add_task(task):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (task) VALUES (?)", (task,))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, done FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def mark_task_done(task_id):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def update_task(task_id, new_task):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET task = ? WHERE id = ?", (new_task, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# ---  Appel Gemini ---
def call_gemini(user_message):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {"contents": [{"parts": [{"text": user_message}]}]}
    response = requests.post(url, headers=headers, params=params, json=payload)
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

# ---  Envoi WhatsApp ---
def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
