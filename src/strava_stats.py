from datetime import datetime, timedelta

from strava_auth import get_activities, strava_get


def activity_to_stats(run):
    """Normalize one Strava activity into the stats object used by the app.

    Strava returns distance in meters. This function keeps km internally for
    half-marathon matching, but user-facing replies use miles.
    """
    distance_km = run["distance"] / 1000
    distance_mi = run["distance"] / 1609.344
    time_min = run["moving_time"] / 60
    pace_min_per_km = time_min / distance_km if distance_km else None
    pace_min_per_mi = time_min / distance_mi if distance_mi else None
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
        "name": run.get("name", "Run"),
        "distance_km": round(distance_km, 2),
        "distance_mi": round(distance_mi, 2),
        "moving_time_min": round(time_min, 1),
        "pace_min_per_km": round(pace_min_per_km, 2) if pace_min_per_km else None,
        "pace_min_per_mi": round(pace_min_per_mi, 2) if pace_min_per_mi else None,
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


def get_last_run_stats():
    """Return normalized stats for the most recent Strava run."""
    activities = get_activities()
    runs = [activity for activity in activities if activity.get("type") == "Run"]
    if not runs:
        raise RuntimeError("No recent Strava runs found")

    return activity_to_stats(runs[0])


def get_runs_on_date(date_text):
    """Return normalized run stats for all runs on a given YYYY-MM-DD date."""
    target_date = datetime.fromisoformat(date_text)
    after = int(target_date.timestamp())
    before = int((target_date + timedelta(days=1)).timestamp())
    activities = get_activities(params={"after": after, "before": before, "per_page": 100})
    return [
        activity_to_stats(activity)
        for activity in activities
        if activity.get("type") == "Run"
    ]


def get_half_marathon_run(date_text="2025-11-22"):
    """Pick the run closest to half-marathon distance on the given date."""
    runs = get_runs_on_date(date_text)
    if not runs:
        raise RuntimeError(f"No runs found on {date_text}")

    half_marathon_km = 21.0975
    return min(runs, key=lambda run: abs(run["distance_km"] - half_marathon_km))


def get_activity_kudoers(activity_id):
    """Return athletes Strava exposes as having given kudos to an activity."""
    return strava_get(f"/activities/{activity_id}/kudos", params={"per_page": 30})


def get_activity_laps(activity_id):
    """Return lap/split data for an activity."""
    return strava_get(f"/activities/{activity_id}/laps")


def get_activity_photos(activity_id):
    """Return Strava photos for an activity, if Strava exposes them."""
    return strava_get(
        f"/activities/{activity_id}/photos",
        params={"size": 2048, "photo_sources": 1},
    )


def get_my_clubs():
    """Return Strava clubs for the authenticated athlete."""
    return strava_get("/athlete/clubs")


def format_date(value):
    """Convert a Strava ISO timestamp into a friendly text-message date."""
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%b %-d at %-I:%M %p")
    except ValueError:
        return value


def format_run_summary(run_stats):
    """Return a one-line run summary in miles and min/mi pace."""
    pace = run_stats.get("pace_min_per_mi")
    pace_text = f" at {pace:.2f} min/mi" if pace else ""
    date_text = format_date(run_stats.get("start_date"))
    date_prefix = f"{date_text}: " if date_text else ""
    return (
        f"{date_prefix}{run_stats['name']} - {run_stats['distance_mi']:.2f} mi "
        f"in {run_stats['moving_time_min']:.1f} min{pace_text}"
    )


def format_run_details(run_stats):
    """Return a multi-line run summary with heart rate, kudos, and location."""
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
        f"Kudos: {run_stats.get('kudos_count', 0)} 👏 "
        f"Photos: {run_stats.get('photo_count', 0)} 📸 "
        f"Achievements: {run_stats.get('achievement_count', 0)} 🏅"
    )

    if run_stats.get("trainer"):
        details.append("Location: no route/location data; this looks like an indoor or trainer run.")
    elif run_stats.get("location"):
        details.append(f"Location: {run_stats['location']}.")
    elif not run_stats.get("has_location"):
        details.append("Location: not available from Strava for this activity.")

    return "\n".join(details)


def format_half_marathon_summary(run_stats):
    """Return the date-matched half-marathon summary."""
    return "Half marathon match 🏁 " + format_run_details(run_stats)


def format_kudos_summary(run_stats):
    """Return a short sentence with the activity's kudos count."""
    kudos = run_stats.get("kudos_count", 0)
    return f'Your last run, "{run_stats["name"]}", has {kudos} kudos so far.'


def format_kudoers_summary(run_stats, kudoers):
    """Return a readable list of people who gave kudos to an activity."""
    if not kudoers:
        return f'Your last run, "{run_stats["name"]}", has no kudos listed yet.'

    names = [
        " ".join(
            part
            for part in [person.get("firstname"), person.get("lastname")]
            if part
        ).strip()
        for person in kudoers
    ]
    names = [name for name in names if name]
    shown = ", ".join(names[:8])
    extra = len(names) - 8
    extra_text = f", and {extra} more" if extra > 0 else ""
    return f'Kudos on "{run_stats["name"]}": {shown}{extra_text}.'


def format_clubs_summary(clubs):
    """Return a short list of the user's Strava clubs."""
    if not clubs:
        return "I could not find any Strava clubs for your account."

    names = [club.get("name") for club in clubs if club.get("name")]
    shown = ", ".join(names[:8])
    extra = len(names) - 8
    extra_text = f", and {extra} more" if extra > 0 else ""
    return f"Your Strava clubs: {shown}{extra_text}."


def format_activity_splits(run_stats, laps, max_laps=8):
    """Format the first few laps/splits in miles so texts stay readable."""
    if not laps:
        return f'Strava does not list splits/laps for "{run_stats["name"]}".'

    split_lines = []
    for index, lap in enumerate(laps[:max_laps], start=1):
        distance_mi = (lap.get("distance") or 0) / 1609.344
        moving_min = (lap.get("moving_time") or lap.get("elapsed_time") or 0) / 60
        pace = moving_min / distance_mi if distance_mi else None
        pace_text = f"{pace:.2f}/mi" if pace else "pace n/a"
        split_lines.append(f"{index}: {distance_mi:.2f} mi @ {pace_text}")

    extra = len(laps) - max_laps
    extra_text = f" + {extra} more" if extra > 0 else ""
    return f'Splits for "{run_stats["name"]}": ' + "; ".join(split_lines) + extra_text


def extract_photo_url(photos):
    """Return the first usable image URL from Strava's photo response."""
    for photo in photos:
        urls = photo.get("urls") or {}
        if urls:
            return urls.get("2048") or urls.get("1024") or urls.get("600") or next(iter(urls.values()))

        if photo.get("url"):
            return photo["url"]

    return None


def format_social_post_caption(run_stats):
    """Create a celebratory caption users can copy into a social post."""
    return (
        "Still smiling about this one. Proof that showing up, mile by mile, "
        "turns into something worth celebrating. 🏃‍♀️✨🏁 #RideOrStride #Strava"
    )


def format_location_summary(run_stats):
    """Explain location data honestly, including indoor/trainer runs."""
    if run_stats.get("trainer"):
        return "Strava does not have route/location data for your last run. It looks like an indoor or trainer run."
    if run_stats.get("location"):
        return f"Your last run location shows as {run_stats['location']}."
    if not run_stats.get("has_location"):
        return "Strava does not have location data for your last run."
    return "Your last run has GPS data, but this app is not reading the map route yet."


def get_last_run():
    """Convenience function used by direct command-line testing."""
    return format_run_summary(get_last_run_stats())


if __name__ == "__main__":
    print(get_last_run())
