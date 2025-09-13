import streamlit as st
import json
import os
import warnings
from textwrap import dedent
from agno.agent import Agent
from agno.models.google import Gemini
from inference import InferencePipeline
from twilio.rest import Client
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

# ---------- Config ----------
roboflow_key = os.getenv('ROBOFLOW_API_KEY')
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_from = os.getenv('TWILIO_FROM_NUMBER')
twilio_to = os.getenv('TWILIO_TO_NUMBER')

client = None
if account_sid and auth_token:
    try:
        client = Client(account_sid, auth_token)
    except Exception as e:
        # Preserve app start even if Twilio misconfigured
        client = None
        st.warning(f"Twilio client init failed: {e}")

MAX_FRAMES = 80
DETECTIONS_FOUND = []
DONE_ALERTS = []
threat_data = []
pipeline = None  

# ---------- Load threat DB ----------
try:
    with open('threat_database.json', 'r', encoding='utf-8') as file:
        threat_data = json.load(file)
except FileNotFoundError:
    st.error(" 'threat_database.json' not found.")
except json.JSONDecodeError:
    st.error(" JSON format error in 'threat_database.json'.")

# ---------- Twilio sender used by the agent ----------
def send_alert(threat_info: str):
    st.info(f" Sending alert: {threat_info}")
    if client is None or not twilio_from or not twilio_to:
        st.error("Twilio not configured (missing credentials or numbers).")
        return None
    try:
        message = client.messages.create(
            from_=twilio_from,
            to=twilio_to,
            body=threat_info
        )
        return message.sid
    except Exception as e:
        st.error(f"Twilio send failed: {e}")
        return None

# ---------- Agent setup ----------
agent = Agent(
    model=Gemini(id="gemini-1.5-flash"),
    instructions=dedent("""
        You are a homeland security alert system. 
        You receive JSON input with detection data for a suspicious target.

        Your task is:
        1. Extract the actual values from the JSON input:
        - target_id
        - type (weapon, abandoned_bag, suspicious_person, etc.)
        - location
        - date_time
        - risk_level
        - recommended_action

        2. Format a single alert message exactly like this:
        " ALERT: [type] detected at [location] | TIME: [date_time] | RISK LEVEL: [risk_level] | RECOMMENDED ACTION: [recommended_action] | Target ID: [target_id]"

        3. Use the `send_alert` tool to send this message as a string.

        Return a JSON response in this format:
        {
        "status": "success",
        "message": "Alert sent for target [target_id]",
        "alert_sent": "[full_alert_message]"
        }
        If anything fails, return:
        {
        "status": "failed",
        "message": "Failed to send alert",
        "error": "[error_details]"
        }

        IMPORTANT:
        - Do NOT invent or guess any data. Only use what's provided in the input.
        - NEVER use placeholders.
    """),
    tools=[send_alert]
)

# ---------- Helper: lookup threat ----------
def threat_lookup(target_id: str):
    for t in threat_data:
        if target_id == t.get('target_id') and target_id not in DONE_ALERTS:
            return t
    return False

# ---------- Sink called by InferencePipeline for each frame ----------
def my_sink(result, video_frame):
    global pipeline
    try:
        if video_frame.frame_id is not None and video_frame.frame_id >= MAX_FRAMES:
            pipeline.terminate()
            return
    except Exception:
        pass


    frame_targets = set()
    try:
        for group in result.get('open_ai', []):
            for res in group:
                if res.get('output'):
                    frame_targets.add(res['output'].strip())
    except Exception as e:
        st.warning(f"Couldn't parse workflow result: {e}")
        return

    for target in frame_targets:
        threat_info = threat_lookup(target)
        if threat_info:
            if threat_info['target_id'] not in DONE_ALERTS:
                DONE_ALERTS.append(threat_info['target_id'])
                st.success(f" Threat detected: {target}")
                try:
                    agent_response = agent.run(json.dumps(threat_info))
                except Exception as e:
                    st.error(f"Agent execution failed: {e}")
                    continue

                final_agent_output = None
                for msg in reversed(getattr(agent_response, "messages", [])):
                    if getattr(msg, "role", None) == 'assistant' and getattr(msg, "content", None):
                        final_agent_output = msg.content
                        break

                if final_agent_output:
                    try:
                        st.json(json.loads(final_agent_output))
                    except json.JSONDecodeError:
                        st.error(f" Agent returned non-JSON content:\n{final_agent_output}")
                else:
                    st.warning(" No assistant response received.")

# ---------- Streamlit UI ----------
st.title(" Homeland Security - Targeted Detection Workflow")

st.markdown("""
**Mode**: je lis une vidéo locale et j’envoie chaque frame **vers l'input `image`** du Workflow .  
""")

if st.button(" Start Security Monitoring"):
    with st.spinner("Analyzing surveillance video..."):
        try:
            pipeline = InferencePipeline.init_with_workflow(
                api_key=roboflow_key,
                workspace_name="tuto26",
                workflow_id="custom-workflow",
                video_reference='video/security-footage.mp4',  
                max_fps=30,
                on_prediction=my_sink,
                image_input_name="image"   
            )
            pipeline.start()
            pipeline.join()
        except Exception as e:
            st.error(f"Pipeline init/run failed: {e}")

    st.success("✅ Finished analyzing video.")
