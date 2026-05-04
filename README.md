# Linq API + Strava Stats

This project connects the Strava API to the Linq API so you can text your Linq number from your phone and get your latest Strava run stats back as a reply.

## What It Does

- Receives incoming Linq chat messages through a Flask webhook.
- Checks whether the message asks about a run.
- Calls the Strava API for your latest activity.
- Uses an optional AI agent to turn the Strava stats into a conversational reply.
- Sends the reply back through the Linq API.

## Project Files

- `app.py` - Flask webhook server for receiving Linq messages and sending replies.
- `strava.py` - Gets your latest activity from the Strava API.
- `agent.py` - Optional AI agent that writes a friendly Strava stats reply.
- `send_message.py` - Simple test script for sending a Linq message.
- `requirements.txt` - Python packages needed for the project.
- `.env` - Local secret values like API keys and phone numbers. Do not commit this file.
- `.env.example` - Template showing which environment variables are needed.

## Setup

### 1. Install dependencies

From the project folder, run:

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

Create a file named `.env` in the project folder:

```bash
cp .env.example .env
```

Then fill in your real values:

```bash
LINQ_API_KEY=your_linq_api_key_here
LINQ_FROM_NUMBER=your_linq_phone_number_here
LINQ_TEST_TO_NUMBER=your_personal_phone_number_here
STRAVA_TOKEN=your_strava_access_token_here
AI_PROVIDER=claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Example phone number format:

```bash
LINQ_FROM_NUMBER=+12055550123
```

Keep `.env` private because it contains secrets.

`AI_PROVIDER` can be `claude` or `gemini`. If the selected provider is missing a key or the AI request fails, the app still replies with a manual Strava summary.

## How The AI Agent Works

The project keeps each responsibility in a separate file:

```text
phone text -> Linq webhook -> app.py -> strava.py -> agent.py -> Linq reply
```

- `app.py` receives the Linq webhook and decides what to do with the message.
- `strava.py` gets structured stats for your latest Strava run.
- `agent.py` sends those stats and the user's message to Claude or Gemini, then returns a text-message-friendly response.

For example, instead of only returning:

```text
Last run: 5.20 km in 32.1 min
```

the AI agent can reply with something more natural:

```text
Nice run. You covered 5.2 km in 32.1 min, around 6.17 min/km. Looks like a steady aerobic effort.
```

## Running the Webhook

Start the Flask app:

```bash
python app.py
```

By default, the app runs locally at:

```text
http://127.0.0.1:5000
```

The Linq webhook endpoint is:

```text
/webhook
```

So the full local URL is:

```text
http://127.0.0.1:5000/webhook
```

## Exposing the Webhook

Linq needs a public URL to send webhook events to your local Flask app. For local development, you can use a tunneling tool like ngrok:

```bash
ngrok http 5000
```

Ngrok will give you a public URL. Use that URL plus `/webhook` in your Linq webhook settings:

```text
https://your-ngrok-url.ngrok-free.app/webhook
```

## Testing a Linq Message

To test sending a message through the Linq API:

```bash
python send_message.py
```

This uses:

- `LINQ_API_KEY`
- `LINQ_FROM_NUMBER`
- `LINQ_TEST_TO_NUMBER`

from your `.env` file.

## Testing Strava Only

To test whether your Strava token works:

```bash
python strava.py
```

If the token is valid, it should print your latest run stats.

## Testing The AI Agent Only

The AI agent is used automatically when you text the Linq number and the selected provider key is set in `.env`.

If the AI key is missing, `agent.py` falls back to the manual Strava summary so the project can still run without AI.

To test Claude without sending a Linq text:

```bash
python test_claude.py
```

If Claude is connected, the terminal should show `AI AGENT: using Claude model ...` and `AI AGENT REPLY: ...`.

To test Gemini without sending a Linq text:

```bash
python test_gemini.py
```

If Gemini is connected, the terminal should show `AI AGENT: using Gemini model ...` and `AI AGENT REPLY: ...`.

## How To Use It From Your Phone

Once the Flask app is running and your Linq webhook is configured, send a message like this to your Linq number:

```text
last run
```

The app should reply with your latest Strava run distance and moving time.

## Notes

- Do not commit `.env`.
- If your Strava token expires, you will need to generate or refresh it.
- If Linq cannot reach your webhook, make sure your Flask app and ngrok tunnel are both running.
