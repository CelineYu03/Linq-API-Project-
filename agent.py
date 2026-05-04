import os

import requests
from dotenv import load_dotenv

from strava import (
    format_kudos_summary,
    format_location_summary,
    format_run_details,
    format_run_summary,
)

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

SYSTEM_PROMPT = """You are a concise Strava running assistant inside a Linq text message chat.
You interpret the user's text, even if it has typos, slang, or rough grammar.
You answer using only the latest Strava run data provided.

Rules:
- Reply in one short text message, under 240 characters.
- Use 1-3 emojis when they make the reply warmer, especially for motivation or if the user asks for emojis.
- For run stat questions, include distance, moving time, and average pace when available.
- For kudos questions, answer the kudos count directly.
- For location questions, say location is not available unless location data is provided.
- For motivation requests, give a short motivational running message and optionally reference the latest run.
- For help/menu questions, list 3-5 example texts the user can send.
- Do not start with filler like "Hey" or "Hey there".
- Do not end mid-sentence.
- Do not invent stats that were not provided.
"""


def wants_motivation(text):
    motivation_words = [
        "motivat",
        "quote",
        "hype",
        "inspire",
        "encourage",
        "pep talk",
        "dont feel",
        "don't feel",
        "lazy",
        "tired",
        "push me",
    ]
    return any(word in text for word in motivation_words)


def wants_emojis(text):
    return "emoji" in text or "emojis" in text or "fun" in text


def format_motivation(run_stats, use_emojis=True):
    emojis = " 🏃‍♀️🔥" if use_emojis else ""
    return (
        f"You already banked {run_stats['distance_km']:.2f} km on your last run. "
        f"Today, just win the first 10 minutes. Momentum can take it from there.{emojis}"
    )


def manual_reply(user_text, run_stats):
    normalized_text = user_text.lower()

    if wants_motivation(normalized_text) or wants_emojis(normalized_text):
        return format_motivation(run_stats, use_emojis=True)
    if "kudo" in normalized_text:
        return f"{format_kudos_summary(run_stats)} 👏"
    if "where" in normalized_text or "location" in normalized_text:
        return f"{format_location_summary(run_stats)} 📍"
    if "stat" in normalized_text or "detail" in normalized_text:
        return format_run_details(run_stats)
    if "help" in normalized_text or "what can" in normalized_text:
        return (
            "Try: last run stats, last run kudos, where was my last run, "
            "motivate me, or hype me up 🏃‍♀️"
        )
    return f"{format_run_summary(run_stats)} 🏃‍♀️"


def generate_strava_reply(user_text, run_stats):
    """Create an AI-written Strava reply, falling back to manual logic."""
    fallback_reply = manual_reply(user_text, run_stats)

    prompt = build_prompt(user_text, run_stats)

    if AI_PROVIDER == "claude":
        return generate_claude_reply(prompt, fallback_reply)

    if AI_PROVIDER == "gemini":
        return generate_gemini_reply(prompt, fallback_reply)

    print(f"AI AGENT: unknown AI_PROVIDER '{AI_PROVIDER}'; using manual fallback")
    return fallback_reply


def build_prompt(user_text, run_stats):
    return f"""{SYSTEM_PROMPT}

User message:
{user_text}

Latest Strava run:
- Name: {run_stats.get("name")}
- Distance: {run_stats.get("distance_km")} km
- Moving time: {run_stats.get("moving_time_min")} min
- Average pace: {run_stats.get("pace_min_per_km")} min/km
- Start date: {run_stats.get("start_date")}
- Kudos: {run_stats.get("kudos_count")}
- Photos: {run_stats.get("photo_count")}
- Achievements: {run_stats.get("achievement_count")}
- Average heart rate: {run_stats.get("average_heartrate")} bpm
- Max heart rate: {run_stats.get("max_heartrate")} bpm
- Average cadence: {run_stats.get("average_cadence")} spm
- Indoor/trainer run: {run_stats.get("trainer")}
- Location: {run_stats.get("location")}
- Has GPS/location data: {run_stats.get("has_location")}

If the user asks for motivation, hype, a quote, or emojis, prioritize encouragement over stats.
Write only the reply text. Make it complete and concise."""


def generate_gemini_reply(prompt, fallback_reply):
    if not GEMINI_API_KEY:
        print("AI AGENT: GEMINI_API_KEY is missing; using manual fallback")
        return fallback_reply

    print(f"AI AGENT: using Gemini model {GEMINI_MODEL}")

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "content-type": "application/json",
            },
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 250,
                    "temperature": 0.7,
                },
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        content = candidates[0].get("content", {}) if candidates else {}
        parts = content.get("parts", [])
        text_parts = [part.get("text", "") for part in parts]
        reply = "\n".join(text_parts).strip()
        print("AI AGENT REPLY:", reply)
        return reply or fallback_reply
    except Exception as e:
        print("AI AGENT ERROR:", e)
        if hasattr(e, "response") and e.response is not None:
            print("AI AGENT RESPONSE:", e.response.text)
        return fallback_reply


def generate_claude_reply(prompt, fallback_reply):
    if not ANTHROPIC_API_KEY:
        print("AI AGENT: ANTHROPIC_API_KEY is missing; using manual fallback")
        return fallback_reply

    print(f"AI AGENT: using Claude model {ANTHROPIC_MODEL}")

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 250,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("content", [])
        text_parts = [
            part.get("text", "")
            for part in content
            if part.get("type") == "text"
        ]
        reply = "\n".join(text_parts).strip()
        print("AI AGENT REPLY:", reply)
        return reply or fallback_reply
    except Exception as e:
        print("AI AGENT ERROR:", e)
        if hasattr(e, "response") and e.response is not None:
            print("AI AGENT RESPONSE:", e.response.text)
        return fallback_reply
