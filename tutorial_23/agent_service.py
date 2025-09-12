import os
import logging
from letta_client import Letta
from dotenv import load_dotenv

load_dotenv()

LETTA_TOKEN = os.getenv("LETTA_API_KEY")
AGENT_ID = os.getenv("AGENT_ID")

client = Letta(token=LETTA_TOKEN)


def process_user_message(user_id: str, content: str):
    logging.info(f"--- Agent triggered by {user_id} ---")
    try:
        # Envoi du message à l'agent
        answer = client.agents.messages.create(
            agent_id=AGENT_ID,
            messages=[{"role": "user", "content": content}],
        )

        # Extraction du texte de réponse
        for msg in answer.messages:
            if hasattr(msg, "content") and msg.content:
                if isinstance(msg.content, list):
                    # Prendre uniquement le texte
                    texts = [c.text for c in msg.content if hasattr(c, "text")]
                    if texts:
                        return "\n".join(texts)
                elif isinstance(msg.content, str):
                    return msg.content

        return "Agent responded with no content."

    except Exception as e:
        logging.error(f"Agent error: {e}")
        return "Sorry, I ran into an issue. Please try again!"
