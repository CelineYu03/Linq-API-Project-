import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = "https://api.linqapp.com/api/partner/v3/chats"

linq_api_key = os.getenv("LINQ_API_KEY")
linq_from_number = os.getenv("LINQ_FROM_NUMBER")
linq_test_to_number = os.getenv("LINQ_TEST_TO_NUMBER")

if not linq_api_key:
    raise RuntimeError("Missing required environment variable: LINQ_API_KEY")
if not linq_from_number:
    raise RuntimeError("Missing required environment variable: LINQ_FROM_NUMBER")
if not linq_test_to_number:
    raise RuntimeError("Missing required environment variable: LINQ_TEST_TO_NUMBER")

headers = {
    "Authorization": f"Bearer {linq_api_key}",
    "Content-Type": "application/json"
}

data = {
    "from": linq_from_number,
    "to": [linq_test_to_number],
    "message": {
        "parts": [
            {"type": "text", "value": "Hello from Linq!"}
        ]
    }
}

response = requests.post(url, json=data, headers=headers)

print("Status:", response.status_code)
print("Response:", response.text)
