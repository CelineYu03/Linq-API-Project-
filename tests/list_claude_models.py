import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

response = requests.get(
    "https://api.anthropic.com/v1/models",
    headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    },
    timeout=30,
)
response.raise_for_status()

for model in response.json().get("data", []):
    print(model["id"])
