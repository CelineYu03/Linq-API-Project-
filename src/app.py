from flask import Flask, request
import requests
from ai_agent import generate_strava_reply
from strava_stats import (
    extract_photo_url,
    format_activity_splits,
    format_clubs_summary,
    format_half_marathon_summary,
    format_kudoers_summary,
    format_social_post_caption,
    get_activity_laps,
    get_activity_kudoers,
    get_activity_photos,
    get_half_marathon_run,
    get_last_run_stats,
    get_my_clubs,
)
import os
from dotenv import load_dotenv

# load_dotenv() reads the local .env file so the app can use API keys without
# hardcoding them in source code.
load_dotenv()

app = Flask(__name__)

# Linq credentials and optional fallback image URL for social-post previews.
LINQ_API_KEY = os.getenv("LINQ_API_KEY")
LINQ_FROM_NUMBER = os.getenv("LINQ_FROM_NUMBER")
DEFAULT_POST_IMAGE_URL = os.getenv("DEFAULT_POST_IMAGE_URL")
MARATHON_POST_IMAGE_URL = os.getenv("MARATHON_POST_IMAGE_URL")


def require_env(name, value):
    """Return an environment variable or raise a readable setup error."""
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def send_reply(to, message, media_url=None):
    """Send a text reply, and optionally a public image URL, back through Linq.

    Linq expects messages as a list of "parts". This function always sends one
    text part and adds a media part when the app has a public image URL.
    """
    api_key = require_env("LINQ_API_KEY", LINQ_API_KEY)
    from_number = require_env("LINQ_FROM_NUMBER", LINQ_FROM_NUMBER)

    # Linq messages are made of parts. Text is one part; media can be another.
    # For now, media_url must be a public HTTPS URL Linq can fetch.
    parts = [{"type": "text", "value": message}]
    if media_url:
        parts.append({"type": "media", "url": media_url})

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
                "parts": parts
            }
        }
    )

    print("SEND STATUS:", res.status_code)
    print("SEND RESPONSE:", res.text)


def extract_incoming_message(data):
    """Extract the sender phone number and text from a Linq webhook payload.

    The app has seen two payload shapes while developing, so this handles both
    the current v3 shape and the older sender_handle/parts shape.
    """
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
    """Return a short command menu for users who text something vague."""
    return (
        "Text me one of these:\n"
        "- last run\n"
        "- last run stats\n"
        "- last run kudos\n"
        "- where was my last run?\n"
        "- who gave me kudos?\n"
        "- my clubs\n"
        "- Nov 22 half marathon\n"
        "- set up a post"
    )


def wants_social_post(text):
    """Return True when the user is asking for a shareable post or caption."""
    return (
        "post" in text
        or "caption" in text
        or "share" in text
        or "instagram" in text
    )


def wants_race_activity(text):
    """Return True for phrases that should use the saved Nov 22 race activity."""
    return (
        "race" in text
        or "marathon" in text
        or "half marathon" in text
        or "half-marathon" in text
        or "nov 22" in text
        or "november 22" in text
    )


def build_social_post_reply(run_stats, image_url=None, label="last activity"):
    """Create a social-post draft from activity stats and an optional image.

    Race posts can pass a specific image URL. Generic posts try Strava photos
    first, then fall back to DEFAULT_POST_IMAGE_URL from .env.
    """
    caption = format_social_post_caption(run_stats)
    photo_url = image_url

    # Prefer an actual Strava activity photo. If Strava does not expose one,
    # fall back to a configured public URL from .env.
    if not photo_url and run_stats.get("photo_count", 0) > 0:
        photo_url = extract_photo_url(get_activity_photos(run_stats["id"]))

    if not photo_url:
        photo_url = DEFAULT_POST_IMAGE_URL

    image_status = "image ready to post" if photo_url else "caption ready; add DEFAULT_POST_IMAGE_URL to attach an image"
    message = (
        f"Okay 🎉 here are your {label} stats and {image_status}. Want to share? 📲\n\n"
        f"Caption: {caption}"
    )
    return message, photo_url


def build_ai_reply(text):
    """Build the response for an incoming text message.

    Product-specific commands such as clubs, race splits, and post setup are
    handled deterministically. If no route matches, the latest run stats are
    sent to the AI agent for a conversational reply.
    """
    if not text.strip():
        return help_prompt()

    normalized_text = text.lower()

    try:
        # Handle exact Strava API use cases before handing general wording to AI.
        if "club" in normalized_text:
            return format_clubs_summary(get_my_clubs())

        if wants_race_activity(normalized_text):
            half_run = get_half_marathon_run()
            if wants_social_post(normalized_text):
                return build_social_post_reply(
                    half_run,
                    image_url=MARATHON_POST_IMAGE_URL,
                    label="half marathon race",
                )
            if "split" in normalized_text or "lap" in normalized_text or "pace" in normalized_text:
                return format_activity_splits(half_run, get_activity_laps(half_run["id"]))
            return format_half_marathon_summary(half_run)

        run_stats = get_last_run_stats()
        if wants_social_post(normalized_text):
            return build_social_post_reply(run_stats)
        if "who" in normalized_text and "kudo" in normalized_text:
            return format_kudoers_summary(run_stats, get_activity_kudoers(run_stats["id"]))
    except Exception as e:
        print("STRAVA ERROR:", e)
        return "I got your text, but I could not read Strava right now. Check your Strava token and try again."

    return generate_strava_reply(text, run_stats)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive Linq webhooks, build a response, and send it back to the user.

    This is the only public endpoint Linq needs. It acknowledges every webhook
    with "ok" so Linq knows the event was received.
    """
    data = request.json
    print("FULL DATA:", data)  # keep this for debugging

    try:
        user_number, text = extract_incoming_message(data)

        reply = build_ai_reply(text)

        if user_number:
            if isinstance(reply, tuple):
                send_reply(user_number, reply[0], media_url=reply[1])
            else:
                send_reply(user_number, reply)

    except Exception as e:
        print("ERROR:", e)

    return "ok"


if __name__ == "__main__":
    # Local dev server. Use ngrok to expose this port to Linq webhooks.
    app.run(port=5000)
