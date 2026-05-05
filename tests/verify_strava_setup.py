import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from strava_auth import verify_strava_access


activity_count = verify_strava_access()
print(f"Strava setup verified. Retrieved {activity_count} recent activity.")
