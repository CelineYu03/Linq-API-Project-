import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# These are read once when the module imports. refresh_strava_token() updates
# the module values and the .env file when Strava rotates tokens.
STRAVA_TOKEN = os.getenv("STRAVA_TOKEN")
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def require_env(name, value):
    """Return an environment variable or fail with a clear setup message."""
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def update_env_value(name, value):
    """Persist a changed token value back to the project .env file.

    Strava can rotate refresh tokens. Writing the new values to .env prevents
    the app from using an old token the next time it starts.
    """
    if not ENV_PATH.exists():
        return

    lines = ENV_PATH.read_text().splitlines()
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(f"{name}="):
            lines[index] = f"{name}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{name}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n")


def refresh_strava_token():
    """Use Strava's refresh-token flow to get a fresh access token."""
    global STRAVA_TOKEN, STRAVA_REFRESH_TOKEN

    # Strava access tokens expire; the refresh token lets us get a fresh one.
    client_id = require_env("STRAVA_CLIENT_ID", STRAVA_CLIENT_ID)
    client_secret = require_env("STRAVA_CLIENT_SECRET", STRAVA_CLIENT_SECRET)
    refresh_token = require_env("STRAVA_REFRESH_TOKEN", STRAVA_REFRESH_TOKEN)

    res = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    if not res.ok:
        print("STRAVA REFRESH STATUS:", res.status_code)
        print("STRAVA REFRESH RESPONSE:", res.text)
        res.raise_for_status()

    token_data = res.json()
    access_token = token_data["access_token"]
    new_refresh_token = token_data.get("refresh_token")

    update_env_value("STRAVA_TOKEN", access_token)
    if new_refresh_token:
        update_env_value("STRAVA_REFRESH_TOKEN", new_refresh_token)

    STRAVA_TOKEN = access_token
    if new_refresh_token:
        STRAVA_REFRESH_TOKEN = new_refresh_token

    print("STRAVA TOKEN: refreshed access token")
    return access_token


def get_strava_access_token():
    """Return a usable Strava access token for API requests.

    If the long-term refresh credentials are configured, this refreshes first.
    Otherwise, it falls back to STRAVA_TOKEN for simpler local testing.
    """
    if STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN:
        return refresh_strava_token()

    return require_env("STRAVA_TOKEN", STRAVA_TOKEN)


def strava_get(path, params=None):
    """Call a Strava GET endpoint and return parsed JSON.

    The path should start with a slash, such as /athlete/clubs.
    """
    strava_token = get_strava_access_token()
    res = requests.get(
        f"https://www.strava.com/api/v3{path}",
        headers={"Authorization": f"Bearer {strava_token}"},
        params=params,
        timeout=30,
    )
    if not res.ok:
        print("STRAVA STATUS:", res.status_code)
        print("STRAVA RESPONSE:", res.text)
        res.raise_for_status()

    return res.json()


def fetch_activities(strava_token, params=None):
    """Call Strava's athlete activities endpoint with optional query filters."""
    return requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {strava_token}"},
        params=params,
        timeout=30,
    )


def get_activities(params=None):
    """Fetch athlete activities and retry once after token refresh on 401."""
    strava_token = get_strava_access_token()

    res = fetch_activities(strava_token, params=params)
    if res.status_code == 401 and STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN:
        print("STRAVA TOKEN: access token rejected; refreshing once and retrying")
        strava_token = refresh_strava_token()
        res = fetch_activities(strava_token, params=params)

    if not res.ok:
        print("STRAVA STATUS:", res.status_code)
        print("STRAVA RESPONSE:", res.text)
        res.raise_for_status()

    return res.json()


def verify_strava_access():
    """Fetch one activity to confirm Strava auth and token refresh are working."""
    activities = get_activities(params={"per_page": 1})
    return len(activities)
