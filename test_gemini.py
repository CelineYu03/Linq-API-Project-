from agent import generate_strava_reply

sample_run = {
    "name": "Nike Run Club: A Cold Run",
    "distance_km": 4.16,
    "moving_time_min": 34.0,
    "pace_min_per_km": 8.18,
    "start_date": "2026-05-01T18:35:48Z",
    "kudos_count": 0,
    "comment_count": 0,
    "achievement_count": 0,
    "photo_count": 1,
    "average_heartrate": 139,
    "max_heartrate": 168,
    "average_cadence": 70.9,
    "trainer": True,
    "location": None,
    "has_location": False,
}

print(generate_strava_reply("hype me up for a run with emojis", sample_run))
