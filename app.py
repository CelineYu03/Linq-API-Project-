from flask import Flask, request
import requests
from agent import generate_strava_reply
from strava import get_last_run_stats
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

LINQ_API_KEY = os.getenv("LINQ_API_KEY")
LINQ_FROM_NUMBER = os.getenv("LINQ_FROM_NUMBER")


def require_env(name, value):
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def send_reply(to, message):
    api_key = require_env("LINQ_API_KEY", LINQ_API_KEY)
    from_number = require_env("LINQ_FROM_NUMBER", LINQ_FROM_NUMBER)

    res = requests.post(
        "https://api.linqapp.com/api/partner/v3/chats",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "from": from_number,
            "to": [to],
            "message": {
                "parts": [{"type": "text", "value": message}]
            }
        }
    )

    print("SEND STATUS:", res.status_code)
    print("SEND RESPONSE:", res.text)


def extract_incoming_message(data):
    event = data.get("data", {})

    user_number = event.get("from")
    message = event.get("message", {})
    parts = message.get("parts", [])

    if not user_number:
        user_number = event.get("sender_handle", {}).get("handle")
        parts = event.get("parts", [])

    text = parts[0].get("value", "") if parts else ""
    return user_number, text


def help_prompt():
    return (
        "Text me one of these:\n"
        "- last run\n"
        "- last run stats\n"
        "- last run kudos\n"
        "- where was my last run?\n"
        "- last run photos"
    )


def build_ai_reply(text):
    if not text.strip():
        return help_prompt()

    try:
        run_stats = get_last_run_stats()
    except Exception as e:
        print("STRAVA ERROR:", e)
        return "I got your text, but I could not read Strava right now. Check your Strava token and try again."

    return generate_strava_reply(text, run_stats)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("FULL DATA:", data)  # keep this for debugging

    try:
        user_number, text = extract_incoming_message(data)

        reply = build_ai_reply(text)

        if user_number:
            send_reply(user_number, reply)

    except Exception as e:
        print("ERROR:", e)

    return "ok"


if __name__ == "__main__":
    app.run(port=5000)
