import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

STRAVA_TOKEN = os.getenv("STRAVA_TOKEN")


def require_env(name, value):
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_last_run_stats():
    strava_token = require_env("STRAVA_TOKEN", STRAVA_TOKEN)

    res = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {strava_token}"}
    )
    if not res.ok:
        print("STRAVA STATUS:", res.status_code)
        print("STRAVA RESPONSE:", res.text)
        res.raise_for_status()

    activities = res.json()
    runs = [activity for activity in activities if activity.get("type") == "Run"]
    if not runs:
        raise RuntimeError("No recent Strava runs found")

    run = runs[0]
    distance_km = run["distance"] / 1000
    time_min = run["moving_time"] / 60
    pace_min_per_km = time_min / distance_km if distance_km else None
    avg_heartrate = run.get("average_heartrate")
    max_heartrate = run.get("max_heartrate")
    avg_cadence = run.get("average_cadence")
    location_parts = [
        run.get("location_city"),
        run.get("location_state"),
        run.get("location_country"),
    ]
    location = ", ".join(part for part in location_parts if part)

    return {
        "id": run.get("id"),
        "name": run.get("name", "Last run"),
        "distance_km": round(distance_km, 2),
        "moving_time_min": round(time_min, 1),
        "pace_min_per_km": round(pace_min_per_km, 2) if pace_min_per_km else None,
        "start_date": run.get("start_date_local") or run.get("start_date"),
        "kudos_count": run.get("kudos_count", 0),
        "comment_count": run.get("comment_count", 0),
        "achievement_count": run.get("achievement_count", 0),
        "photo_count": run.get("total_photo_count", run.get("photo_count", 0)),
        "average_heartrate": round(avg_heartrate) if avg_heartrate else None,
        "max_heartrate": round(max_heartrate) if max_heartrate else None,
        "average_cadence": round(avg_cadence, 1) if avg_cadence else None,
        "trainer": run.get("trainer", False),
        "location": location or None,
        "has_location": bool(location or run.get("start_latlng")),
    }


def format_date(value):
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%b %-d at %-I:%M %p")
    except ValueError:
        return value


def format_run_summary(run_stats):
    pace = run_stats.get("pace_min_per_km")
    pace_text = f" at {pace:.2f} min/km" if pace else ""
    date_text = format_date(run_stats.get("start_date"))
    date_prefix = f"{date_text}: " if date_text else ""
    return (
        f"{date_prefix}{run_stats['name']} - {run_stats['distance_km']:.2f} km "
        f"in {run_stats['moving_time_min']:.1f} min{pace_text}"
    )


def format_run_details(run_stats):
    details = [format_run_summary(run_stats)]

    heart_rate = run_stats.get("average_heartrate")
    max_heart_rate = run_stats.get("max_heartrate")
    if heart_rate:
        max_text = f", max {max_heart_rate} bpm" if max_heart_rate else ""
        details.append(f"Heart rate: avg {heart_rate} bpm{max_text}.")

    cadence = run_stats.get("average_cadence")
    if cadence:
        details.append(f"Cadence: {cadence} spm.")

    details.append(
        f"Kudos: {run_stats.get('kudos_count', 0)}. "
        f"Photos: {run_stats.get('photo_count', 0)}. "
        f"Achievements: {run_stats.get('achievement_count', 0)}."
    )

    if run_stats.get("trainer"):
        details.append("Location: no route/location data; this looks like an indoor or trainer run.")
    elif run_stats.get("location"):
        details.append(f"Location: {run_stats['location']}.")
    elif not run_stats.get("has_location"):
        details.append("Location: not available from Strava for this activity.")

    return "\n".join(details)


def format_kudos_summary(run_stats):
    kudos = run_stats.get("kudos_count", 0)
    return f'Your last run, "{run_stats["name"]}", has {kudos} kudos so far.'


def format_location_summary(run_stats):
    if run_stats.get("trainer"):
        return "Strava does not have route/location data for your last run. It looks like an indoor or trainer run."
    if run_stats.get("location"):
        return f"Your last run location shows as {run_stats['location']}."
    if not run_stats.get("has_location"):
        return "Strava does not have location data for your last run."
    return "Your last run has GPS data, but this app is not reading the map route yet."


def get_last_run():
    return format_run_summary(get_last_run_stats())


if __name__ == "__main__":
    print("STRAVA_TOKEN loaded:", bool(STRAVA_TOKEN))
    print("STRAVA_TOKEN length:", len(STRAVA_TOKEN or ""))
    print(get_last_run())
