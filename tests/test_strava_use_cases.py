import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from strava_stats import (
    format_activity_splits,
    format_clubs_summary,
    format_half_marathon_summary,
    format_kudoers_summary,
    get_activity_laps,
    get_activity_kudoers,
    get_half_marathon_run,
    get_last_run_stats,
    get_my_clubs,
)

print("Half marathon:")
half_run = get_half_marathon_run()
print(format_half_marathon_summary(half_run))
print()

print("Half marathon splits:")
print(format_activity_splits(half_run, get_activity_laps(half_run["id"])))
print()

last_run = get_last_run_stats()
print("Last run kudoers:")
print(format_kudoers_summary(last_run, get_activity_kudoers(last_run["id"])))
print()

print("Clubs:")
print(format_clubs_summary(get_my_clubs()))
